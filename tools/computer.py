import asyncio
import base64
import io
import time
from enum import Enum
from typing import Literal, Optional, Tuple, Union, cast

import pyautogui
import pygetwindow as gw
from PIL import Image, ImageGrab

from .base import BaseAnthropicTool, ToolError, ToolResult

# Configure pyautogui safety
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1  # Add small delay between pyautogui commands

# Define action types
Action = Literal[
    "key",
    "type",
    "mouse_move",
    "left_click",
    "left_click_drag",
    "right_click",
    "middle_click", 
    "double_click",
    "screenshot",
    "cursor_position",
    "left_mouse_down",
    "left_mouse_up",
    "scroll",
    "hold_key",
    "wait",
    "triple_click",
]

ScrollDirection = Literal["up", "down", "left", "right"]

class ComputerTool(BaseAnthropicTool):
    """
    A tool that allows Claude to interact with the Windows desktop environment 
    through screenshots and input control.
    """
    
    name = "computer"
    api_type = "computer_20250124"
    _screenshot_delay = 0.5
    
    def __init__(self):
        super().__init__()
        # Get screen dimensions
        self.width, self.height = pyautogui.size()
        
    def to_params(self) -> dict:
        """Returns the tool parameters for the Anthropic API."""
        return {
            "type": self.api_type,
            "name": self.name,
            "display_width_px": self.width,
            "display_height_px": self.height,
            "display_number": None,
        }
    
    async def __call__(
        self,
        *,
        action: Action,
        text: Optional[str] = None,
        coordinate: Optional[Tuple[int, int]] = None,
        scroll_direction: Optional[ScrollDirection] = None,
        scroll_amount: Optional[int] = None,
        duration: Optional[Union[int, float]] = None,
        key: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        """Execute the requested computer action."""
        try:
            # Mouse movement actions
            if action == "mouse_move":
                if coordinate is None:
                    raise ToolError("Coordinate is required for mouse_move")
                x, y = self._validate_coordinates(coordinate)
                pyautogui.moveTo(x, y)
                return await self._with_screenshot(f"Mouse moved to {x}, {y}")
                
            elif action == "left_click_drag":
                if coordinate is None:
                    raise ToolError("Coordinate is required for left_click_drag")
                x, y = self._validate_coordinates(coordinate)
                pyautogui.dragTo(x, y, button='left')
                return await self._with_screenshot(f"Mouse dragged to {x}, {y}")
            
            # Keyboard actions
            elif action == "key":
                if text is None:
                    raise ToolError("Text is required for key action")
                if coordinate is not None:
                    raise ToolError("Coordinate is not accepted for key action")
                
                pyautogui.press(text)
                return await self._with_screenshot(f"Key pressed: {text}")
                
            elif action == "type":
                if text is None:
                    raise ToolError("Text is required for type action")
                if coordinate is not None:
                    raise ToolError("Coordinate is not accepted for type action")
                
                pyautogui.write(text, interval=0.01)
                return await self._with_screenshot(f"Text typed: {text}")
                
            # Click actions
            elif action == "left_click":
                x, y = None, None
                if coordinate is not None:
                    x, y = self._validate_coordinates(coordinate)
                    pyautogui.click(x, y, button='left')
                else:
                    pyautogui.click(button='left')
                
                location = f" at {x}, {y}" if x is not None else ""
                return await self._with_screenshot(f"Left click{location}")
                
            elif action == "right_click":
                x, y = None, None
                if coordinate is not None:
                    x, y = self._validate_coordinates(coordinate)
                    pyautogui.click(x, y, button='right')
                else:
                    pyautogui.click(button='right')
                    
                location = f" at {x}, {y}" if x is not None else ""
                return await self._with_screenshot(f"Right click{location}")
                
            elif action == "middle_click":
                x, y = None, None
                if coordinate is not None:
                    x, y = self._validate_coordinates(coordinate)
                    pyautogui.click(x, y, button='middle')
                else:
                    pyautogui.click(button='middle')
                    
                location = f" at {x}, {y}" if x is not None else ""
                return await self._with_screenshot(f"Middle click{location}")
                
            elif action == "double_click":
                x, y = None, None
                if coordinate is not None:
                    x, y = self._validate_coordinates(coordinate)
                    pyautogui.doubleClick(x, y)
                else:
                    pyautogui.doubleClick()
                    
                location = f" at {x}, {y}" if x is not None else ""
                return await self._with_screenshot(f"Double click{location}")
                
            elif action == "triple_click":
                x, y = None, None
                if coordinate is not None:
                    x, y = self._validate_coordinates(coordinate)
                    pyautogui.tripleClick(x, y)
                else:
                    pyautogui.tripleClick()
                    
                location = f" at {x}, {y}" if x is not None else ""
                return await self._with_screenshot(f"Triple click{location}")
                
            # Advanced mouse actions
            elif action == "left_mouse_down":
                pyautogui.mouseDown(button='left')
                return await self._with_screenshot("Left mouse button pressed down")
                
            elif action == "left_mouse_up":
                pyautogui.mouseUp(button='left')
                return await self._with_screenshot("Left mouse button released")
                
            elif action == "scroll":
                if scroll_direction is None:
                    raise ToolError("Scroll direction is required for scroll action")
                if scroll_amount is None:
                    raise ToolError("Scroll amount is required for scroll action")
                
                if coordinate is not None:
                    x, y = self._validate_coordinates(coordinate)
                    pyautogui.moveTo(x, y)
                    
                clicks = scroll_amount
                if scroll_direction == "up":
                    pyautogui.scroll(clicks)
                elif scroll_direction == "down":
                    pyautogui.scroll(-clicks)
                elif scroll_direction == "left":
                    pyautogui.hscroll(-clicks)
                elif scroll_direction == "right":
                    pyautogui.hscroll(clicks)
                    
                return await self._with_screenshot(f"Scrolled {scroll_direction} by {scroll_amount}")
                
            # Timing and special actions
            elif action == "hold_key":
                if text is None:
                    raise ToolError("Text is required for hold_key action")
                if duration is None:
                    raise ToolError("Duration is required for hold_key action")
                    
                if duration > 30:
                    raise ToolError("Duration must be 30 seconds or less")
                    
                pyautogui.keyDown(text)
                await asyncio.sleep(duration)
                pyautogui.keyUp(text)
                
                return await self._with_screenshot(f"Held key {text} for {duration} seconds")
                
            elif action == "wait":
                if duration is None:
                    raise ToolError("Duration is required for wait action")
                    
                if duration > 30:
                    raise ToolError("Duration must be 30 seconds or less")
                    
                await asyncio.sleep(duration)
                return await self._with_screenshot(f"Waited for {duration} seconds")
                
            # Information actions
            elif action == "screenshot":
                return await self._take_screenshot()
                
            elif action == "cursor_position":
                x, y = pyautogui.position()
                return ToolResult(
                    output=f"Cursor position: X={x}, Y={y}",
                    base64_image=(await self._take_screenshot()).base64_image
                )
                
            else:
                raise ToolError(f"Invalid action: {action}")
                
        except ToolError as e:
            return ToolResult(error=e.message)
        except Exception as e:
            return ToolResult(error=f"An error occurred: {str(e)}")
    
    def scale_coordinates(self, source_type, x, y):
        """
        Scale coordinates between full resolution and target resolution.
        
        Args:
            source_type: 'api' (from Claude) or 'computer' (from screen)
            x, y: The coordinates to scale
            
        Returns:
            Tuple of scaled (x, y) coordinates
        """
        # Target resolution is XGA (1024x768)
        target_width, target_height = 1024, 768
        
        # Get actual screen dimensions
        actual_width, actual_height = self.width, self.height
        
        if source_type == 'api':
            # Scale from API coordinates (target resolution) to computer coordinates (actual resolution)
            # Avoid division by zero if target dimensions are 0
            scaled_x = int(x * (actual_width / target_width)) if target_width > 0 else 0
            scaled_y = int(y * (actual_height / target_height)) if target_height > 0 else 0
        else: # source_type == 'computer'
            # Scale from computer coordinates (actual resolution) to API coordinates (target resolution)
            # Avoid division by zero if actual dimensions are 0
            scaled_x = int(x * (target_width / actual_width)) if actual_width > 0 else 0
            scaled_y = int(y * (target_height / actual_height)) if actual_height > 0 else 0
            
        return scaled_x, scaled_y
        
    def _validate_coordinates(self, coordinate: Tuple[int, int]) -> Tuple[int, int]:
        """Validate coordinates and scale them to the actual screen resolution."""
        if not isinstance(coordinate, (list, tuple)) or len(coordinate) != 2:
            raise ToolError(f"{coordinate} must be a tuple of length 2")
            
        # Ensure coordinates are non-negative integers before scaling
        if not all(isinstance(i, int) and i >= 0 for i in coordinate):
            raise ToolError(f"{coordinate} must be a tuple of non-negative integers")
            
        # Scale from API coordinates (assuming 1024x768) to actual screen coordinates
        x, y = self.scale_coordinates('api', coordinate[0], coordinate[1])
        
        # Check if the scaled coordinates are within screen bounds
        # Use >= 0 check as well, although scale_coordinates should handle this implicitly
        if not (0 <= x <= self.width and 0 <= y <= self.height):
            raise ToolError(f"Scaled coordinates {x}, {y} are outside screen bounds ({self.width}x{self.height})")
            
        return x, y
    
    async def _take_screenshot(self) -> ToolResult:
        """Take a screenshot and scale it to target resolution."""
        try:
            # Take the screenshot
            screenshot = ImageGrab.grab()
            
            # Scale down to XGA resolution (1024x768) using LANCZOS resampling
            target_width, target_height = 1024, 768
            scaled_screenshot = screenshot.resize((target_width, target_height), Image.LANCZOS)
            
            # Convert scaled image to base64
            buffered = io.BytesIO()
            scaled_screenshot.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            return ToolResult(base64_image=img_str)
        except Exception as e:
            return ToolResult(error=f"Failed to take screenshot: {str(e)}")
    
    async def _with_screenshot(self, output: str) -> ToolResult:
        """Add a screenshot to the specified output."""
        # Add a small delay to allow UI to update
        await asyncio.sleep(self._screenshot_delay)
        screenshot = await self._take_screenshot()
        return ToolResult(
            output=output,
            base64_image=screenshot.base64_image,
            error=screenshot.error
        )