"""Streamlit interface for Windows Claude Computer Control."""

import asyncio
import base64
import os
import time
from io import BytesIO
from typing import List, Optional, Union, cast

import streamlit as st
from anthropic.types.beta import (
    BetaContentBlockParam,
    BetaMessageParam,
    BetaTextBlockParam,
    BetaToolResultBlockParam,
)
from PIL import Image, ImageGrab

from config import get_api_key, load_config, save_api_key, save_config
from tools import ToolResult
from windows_agent import WindowsAgent

# Constants
TITLE = "Claude Windows Computer Control"
DEFAULT_SYSTEM_PROMPT = load_config().get("system_prompt", "")

# Setup state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent" not in st.session_state:
    st.session_state.agent = None
if "in_progress" not in st.session_state:
    st.session_state.in_progress = False

def reset_conversation():
    """Reset the conversation."""
    st.session_state.messages = []

def render_message(role: str, content: Union[str, BetaContentBlockParam, ToolResult]):
    """Render a message in the chat UI."""
    with st.chat_message(role):
        if isinstance(content, str):
            st.markdown(content)
        elif isinstance(content, dict):
            if content.get("type") == "text":
                st.markdown(content.get("text", ""))
            elif content.get("type") == "thinking":
                st.markdown(f"**[Thinking]**\n\n{content.get('thinking', '')}")
            elif content.get("type") == "tool_use":
                st.code(f"Tool: {content.get('name')}\nInput: {content.get('input')}")
            else:
                st.write(content)
        elif hasattr(content, "output") or hasattr(content, "error") or hasattr(content, "base64_image"):
            # It's a ToolResult
            if hasattr(content, "output") and content.output:
                st.markdown(content.output)
            if hasattr(content, "error") and content.error:
                st.error(content.error)
            if hasattr(content, "base64_image") and content.base64_image:
                image_data = base64.b64decode(content.base64_image)
                image = Image.open(BytesIO(image_data))
                st.image(image)
        else:
            st.write(content)

def initialize_agent():
    """Initialize the Windows Agent."""
    if not st.session_state.agent:
        st.session_state.agent = WindowsAgent()
    return st.session_state.agent

async def process_message(human_message: str):
    """Process a message from the human and get a response from Claude."""
    agent = initialize_agent()
    
    # Add user message to history
    text_block = BetaTextBlockParam(type="text", text=human_message)
    st.session_state.messages.append({
        "role": "user",
        "content": [text_block],
    })
    
    # Format messages for the API
    messages = cast(List[BetaMessageParam], st.session_state.messages.copy())
    
    # Define callbacks
    def output_callback(content):
        """Callback for outputs from Claude."""
        render_message("assistant", content)
    
    def tool_output_callback(result, tool_id):
        """Callback for tool outputs."""
        pass  # We'll use the output_callback for rendering
    
    # Mark as in progress
    st.session_state.in_progress = True
    
    # Call the agent
    updated_messages = await agent.start_conversation(
        messages=messages,
        output_callback=output_callback,
        tool_output_callback=tool_output_callback,
    )
    
    # Update messages in state
    st.session_state.messages = updated_messages
    
    # Mark as complete
    st.session_state.in_progress = False

def take_screenshot():
    """Take a screenshot and send it to Claude."""
    # Capture the screen
    screenshot = ImageGrab.grab()
    
    # Convert to base64
    buffered = BytesIO()
    screenshot.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    # Create image block
    image_block = BetaImageBlockParam(
        type="image",
        source={
            "type": "base64",
            "media_type": "image/png",
            "data": img_str,
        }
    )
    
    # Add to messages
    st.session_state.messages.append({
        "role": "user",
        "content": [
            BetaTextBlockParam(type="text", text="Here's a screenshot of my screen:"),
            image_block,
        ],
    })
    
    # Render
    with st.chat_message("user"):
        st.write("Here's a screenshot of my screen:")
        st.image(screenshot)

def main():
    """Main application."""
    st.set_page_config(page_title=TITLE, page_icon="🖥️", layout="wide")
    st.title(TITLE)
    
    # Sidebar configuration
    with st.sidebar:
        st.header("Configuration")
        
        # API Key
        api_key = st.text_input(
            "Anthropic API Key", 
            value=get_api_key(),
            type="password",
            help="Enter your Anthropic API key"
        )
        if api_key != get_api_key():
            save_api_key(api_key)
            # Re-initialize agent if API key changed
            st.session_state.agent = None
        
        # System prompt
        config = load_config()
        system_prompt = st.text_area(
            "System Prompt", 
            value=config.get("system_prompt", DEFAULT_SYSTEM_PROMPT),
            height=300,
            help="Customize Claude's system prompt"
        )
        if system_prompt != config.get("system_prompt"):
            config["system_prompt"] = system_prompt
            save_config(config)
            # Re-initialize agent if system prompt changed
            st.session_state.agent = None
        
        # Model selection
        model = st.selectbox(
            "Model",
            options=["claude-3-7-sonnet-20250219", "claude-3-5-sonnet-20240620"],
            index=0,
            help="Select the Claude model to use"
        )
        if model != config.get("model"):
            config["model"] = model
            save_config(config)
            # Re-initialize agent if model changed
            st.session_state.agent = None
        
        # Max tokens
        max_tokens = st.slider(
            "Max Output Tokens",
            min_value=1024,
            max_value=128000,
            value=config.get("max_output_tokens", 4096),
            step=1024,
            help="Maximum number of tokens in Claude's response"
        )
        if max_tokens != config.get("max_output_tokens"):
            config["max_output_tokens"] = max_tokens
            save_config(config)
        
        # Thinking budget
        enable_thinking = st.checkbox(
            "Enable Thinking",
            value=config.get("thinking_budget", 0) > 0,
            help="Enable Claude's thinking mode"
        )
        thinking_budget = st.slider(
            "Thinking Budget",
            min_value=0,
            max_value=16384,
            value=config.get("thinking_budget", 2048),
            step=1024,
            disabled=not enable_thinking,
            help="Budget for Claude's thinking tokens"
        )
        if enable_thinking and thinking_budget != config.get("thinking_budget"):
            config["thinking_budget"] = thinking_budget
            save_config(config)
        elif not enable_thinking and config.get("thinking_budget", 0) > 0:
            config["thinking_budget"] = 0
            save_config(config)
        
        # Image Management
        st.header("Image Management")
        only_n_most_recent_images = st.number_input(
            "Only send N most recent images",
            min_value=0,
            value=config.get("only_n_most_recent_images", 3),  # Default to 3 images
            key="only_n_most_recent_images",
            help="To decrease the total tokens sent, remove older screenshots from the conversation"
        )
        if only_n_most_recent_images != config.get("only_n_most_recent_images", 3):
            config["only_n_most_recent_images"] = only_n_most_recent_images
            save_config(config)
        
        # Actions
        st.header("Actions")
        if st.button("Take Screenshot", use_container_width=True):
            take_screenshot()
        
        if st.button("Reset Conversation", use_container_width=True):
            reset_conversation()
        
        # Status
        st.header("Status")
        if not api_key:
            st.error("⚠️ Please enter your Anthropic API key")
        elif st.session_state.in_progress:
            st.info("⏳ Claude is thinking...")
        else:
            st.success("✅ Ready")
    
    # Render chat history
    for message in st.session_state.messages:
        role = message["role"]
        content = message["content"]
        
        if isinstance(content, list):
            for item in content:
                if item.get("type") == "text":
                    render_message(role, item)
                elif item.get("type") == "image":
                    with st.chat_message(role):
                        image_data = base64.b64decode(item["source"]["data"])
                        image = Image.open(BytesIO(image_data))
                        st.image(image)
                elif item.get("type") == "tool_result":
                    render_message("system", item)
        else:
            render_message(role, content)
    
    # Chat input
    if not st.session_state.in_progress:
        human_message = st.chat_input("Ask Claude to do something with your computer...")
        if human_message:
            # Show the message immediately
            render_message("user", human_message)
            
            # Process the message asynchronously
            asyncio.run(process_message(human_message))

if __name__ == "__main__":
    main()