"""Windows Computer Control Agent using Anthropic API."""

import asyncio
import base64
import datetime
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Union, cast

from anthropic import Anthropic
from anthropic.types import ContentBlock, TextBlock, ToolUseBlock
from anthropic.types.beta import (
    BetaContentBlockParam,
    BetaImageBlockParam,
    BetaMessageParam,
    BetaTextBlockParam,
    BetaToolResultBlockParam,
    BetaToolUseBlockParam,
)

from config import load_config
from tools import ComputerTool, EditorTool, PowerShellTool, ToolError, ToolResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("agent.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def filter_recent_screenshots(messages, keep_count=3):
    """Keep only the most recent N screenshots in the conversation history."""
    # Find all image blocks in the messages
    image_blocks = []
    
    for message in messages:
        if isinstance(message.get("content"), list):
            for i, block in enumerate(message["content"]):
                # Check if block is a dictionary before accessing keys
                if isinstance(block, dict) and block.get("type") == "image":
                    image_blocks.append((message, i, block))
    
    # If we have more images than we want to keep, remove the oldest ones
    if len(image_blocks) > keep_count:
        # Sort by recency (assuming later in the list is more recent)
        to_remove = image_blocks[:-keep_count]
        
        # Remove the oldest images by setting their content to None
        for message, index, _ in to_remove:
            # Ensure content is a list and index is valid
            if isinstance(message.get("content"), list) and index < len(message["content"]):
                 message["content"][index] = None # Mark for removal
            
        # Clean up None values from content lists
        for message in messages:
            if isinstance(message.get("content"), list):
                message["content"] = [item for item in message["content"] if item is not None]
    
    return messages

class WindowsAgent:
    """Agent for controlling Windows with Claude."""

    def __init__(self):
        """Initialize the agent."""
        self.config = load_config()
        self.api_key = self.config["api_key"]
        self.model = self.config["model"]
        self.max_tokens = self.config["max_output_tokens"]
        self.thinking_budget = self.config["thinking_budget"]
        self.system_prompt = self.config["system_prompt"]
        self.only_n_most_recent_images = self.config.get("only_n_most_recent_images", 3)
        
        # Initialize tools
        self.computer_tool = ComputerTool()
        self.powershell_tool = PowerShellTool()
        self.editor_tool = EditorTool()
        
        # Collect all tools
        self.tools = {
            tool.name: tool 
            for tool in [self.computer_tool, self.powershell_tool, self.editor_tool]
        }
        
        # Initialize Anthropic client
        self.client = Anthropic(api_key=self.api_key)
        
    async def start_conversation(
        self,
        messages: List[BetaMessageParam],
        output_callback: Callable[[Union[BetaContentBlockParam, ToolResult, str]], None],
        tool_output_callback: Callable[[ToolResult, str], None] = None,
    ) -> List[BetaMessageParam]:
        """
        Start or continue a conversation with Claude.
        
        Args:
            messages: List of message parameters to send to Claude
            output_callback: Callback function for Claude's outputs
            tool_output_callback: Callback function for tool outputs
            
        Returns:
            Updated message history
        """
        # Create system message
        system = BetaTextBlockParam(type="text", text=self.system_prompt)
        
        # Get tools parameters
        tool_params = [tool.to_params() for tool in self.tools.values()]
        
        # Configure thinking parameter if needed
        thinking_param = None
        temperature_value = 0
        
        if self.thinking_budget and self.thinking_budget > 0:
            # Ensure thinking_budget is an integer
            budget = int(self.thinking_budget)
            thinking_param = {"type": "enabled", "budget_tokens": budget}
            # When thinking is enabled, temperature must be 1
            temperature_value = 1
        
        try:
            # Right before calling the Claude API
            if self.only_n_most_recent_images and self.only_n_most_recent_images > 0:
                # We need to operate on a copy if messages is used elsewhere
                messages_to_send = filter_recent_screenshots(messages.copy(), keep_count=self.only_n_most_recent_images)
            else:
                messages_to_send = messages
            
            # Call Claude API
            response = self.client.beta.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=messages_to_send, # Use the potentially filtered messages
                system=[system],
                tools=tool_params,
                temperature=temperature_value,
                betas=["computer-use-2025-01-24"],
                **({"thinking": thinking_param} if thinking_param else {})
            )
            
            # Process response content blocks
            response_params = self._response_to_params(response.content)
            messages.append(
                {
                    "role": "assistant",
                    "content": response_params,
                }
            )
            
            # Handle tool calls
            tool_result_content = []
            for content_block in response_params:
                # Send content to callback
                output_callback(content_block)
                
                # Handle tool use blocks
                if content_block["type"] == "tool_use":
                    # Get tool and run it
                    tool_name = content_block["name"]
                    tool_input = cast(Dict[str, Any], content_block["input"])
                    tool_id = content_block["id"]
                    
                    try:
                        # Run tool
                        tool = self.tools.get(tool_name)
                        if not tool:
                            result = ToolResult(error=f"Tool {tool_name} not found")
                        else:
                            result = await tool(**tool_input)
                        
                        # Create API tool result
                        tool_result = self._make_tool_result(result, tool_id)
                        tool_result_content.append(tool_result)
                        
                        # Send tool result to callback
                        if tool_output_callback:
                            tool_output_callback(result, tool_id)
                        output_callback(result)
                    except Exception as e:
                        logger.error(f"Error running tool {tool_name}: {str(e)}")
                        tool_result = self._make_tool_result(
                            ToolResult(error=f"Error: {str(e)}"), 
                            tool_id,
                            is_error=True
                        )
                        tool_result_content.append(tool_result)
                        
                        # Send error to callback
                        if tool_output_callback:
                            tool_output_callback(ToolResult(error=f"Error: {str(e)}"), tool_id)
                        output_callback(f"Error running tool {tool_name}: {str(e)}")
            
            # If tools were used, send results back to Claude
            if tool_result_content:
                messages.append({"content": tool_result_content, "role": "user"})
                return await self.start_conversation(messages, output_callback, tool_output_callback)
            
            return messages
        
        except Exception as e:
            logger.error(f"Error in conversation: {str(e)}")
            output_callback(f"Error: {str(e)}")
            return messages
    
    def _response_to_params(self, content: List[ContentBlock]) -> List[BetaContentBlockParam]:
        """Convert API response content to message parameters."""
        result = []
        for block in content:
            if isinstance(block, TextBlock):
                # Handle text blocks
                if block.text:
                    result.append(BetaTextBlockParam(type="text", text=block.text))
                    
                # Handle thinking blocks
                elif getattr(block, "type", None) == "thinking":
                    thinking_block = {
                        "type": "thinking",
                        "thinking": getattr(block, "thinking", None),
                    }
                    if hasattr(block, "signature"):
                        thinking_block["signature"] = getattr(block, "signature", None)
                    result.append(cast(BetaContentBlockParam, thinking_block))
            elif isinstance(block, ToolUseBlock):
                # Handle tool use blocks
                result.append(cast(BetaToolUseBlockParam, block.model_dump()))
            else:
                # Other blocks
                result.append(cast(BetaContentBlockParam, block.model_dump()))
        return result
    
    def _make_tool_result(
        self, result: ToolResult, tool_use_id: str, is_error: bool = False
    ) -> BetaToolResultBlockParam:
        """Convert a ToolResult to an API ToolResultBlockParam."""
        tool_result_content = []
        
        # Handle errors
        if result.error or is_error:
            is_error = True
            error_text = result.error or "Unknown error"
            if result.system:
                error_text = f"<system>{result.system}</system>\n{error_text}"
            tool_result_content = error_text
            
        else:
            # Handle output text
            if result.output:
                output_text = result.output
                if result.system:
                    output_text = f"<system>{result.system}</system>\n{output_text}"
                tool_result_content.append({
                    "type": "text",
                    "text": output_text,
                })
                
            # Handle screenshots
            if result.base64_image:
                tool_result_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": result.base64_image,
                    },
                })
                
        # Create tool result block
        return {
            "type": "tool_result",
            "content": tool_result_content,
            "tool_use_id": tool_use_id,
            "is_error": is_error,
        }