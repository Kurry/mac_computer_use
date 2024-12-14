import asyncio
import base64
import os
import shlex
from enum import StrEnum
from pathlib import Path
from typing import Literal, TypedDict
from uuid import uuid4
from io import BytesIO
from PIL import Image

from anthropic.types.beta import BetaToolComputerUse20241022Param

from .base import BaseAnthropicTool, ToolError, ToolResult
from .run import run
from logger import logger, log_tool_use, log_tool_result, log_message

# Constants
OUTPUT_DIR = "/tmp/outputs"
TYPING_DELAY_MS = 12
TYPING_GROUP_SIZE = 50
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB in bytes

# Check if we're running in a codespace environment
IS_CODESPACE = os.environ.get("CODESPACES") == "true"

class Action(StrEnum):
    KEY_DOWN = "kd"      # Key down event
    KEY_PRESS = "kp"     # Key press (down + up)
    KEY_UP = "ku"        # Key up event
    TYPE = "t"           # Type text
    MOUSE_MOVE = "m"     # Move mouse
    LEFT_CLICK = "c"     # Click
    RIGHT_CLICK = "rc"   # Right click
    DOUBLE_CLICK = "dc"  # Double click
    TRIPLE_CLICK = "tc"  # Triple click
    DRAG_DOWN = "dd"     # Start drag
    DRAG_MOVE = "dm"     # Continue drag
    DRAG_UP = "du"      # End drag
    WAIT = "w"          # Wait/pause
    PRINT_POS = "p"     # Print position
    COLOR_PRINT = "cp"  # Print color

# Valid keys for key press (kp) command - only special keys
VALID_KEYS = {
    "arrow-down", "arrow-left", "arrow-right", "arrow-up",
    "brightness-down", "brightness-up", "delete", "end",
    "enter", "esc", "return", "space", "tab",
    "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8",
    "f9", "f10", "f11", "f12", "f13", "f14", "f15", "f16",
    "fwd-delete", "home", "page-down", "page-up"
}

# Valid modifier keys for key down/up (kd/ku) commands
MODIFIER_KEYS = {"alt", "cmd", "ctrl", "fn", "shift"}

class Resolution(TypedDict):
    width: int
    height: int


# sizes above XGA/WXGA are not recommended (see README.md)
# scale down to one of these targets if ComputerTool._scaling_enabled is set
MAX_SCALING_TARGETS: dict[str, Resolution] = {
    "XGA": Resolution(width=1024, height=768),  # 4:3
    "WXGA": Resolution(width=1280, height=800),  # 16:10
    "FWXGA": Resolution(width=1366, height=768),  # ~16:9
}
SCALE_DESTINATION = MAX_SCALING_TARGETS["FWXGA"]


class ScalingSource(StrEnum):
    COMPUTER = "computer"
    API = "api"


class ComputerToolOptions(TypedDict):
    display_height_px: int
    display_width_px: int
    display_number: int | None


def chunks(s: str, chunk_size: int) -> list[str]:
    return [s[i : i + chunk_size] for i in range(0, len(s), chunk_size)]


def compress_image(image_data: bytes, max_size: int = MAX_IMAGE_SIZE) -> bytes:
    """Compress image data until it's under the specified max size."""
    img = Image.open(BytesIO(image_data))
    quality = 95
    output = BytesIO()

    while True:
        output.seek(0)
        output.truncate()
        img.save(output, format="PNG", optimize=True, quality=quality)
        size = output.tell()

        if size <= max_size or quality <= 5:
            break

        quality -= 5

    return output.getvalue()


class ComputerTool(BaseAnthropicTool):
    """
    A tool that allows the agent to interact with the screen, keyboard, and mouse.
    The tool parameters are defined by Anthropic and are not editable.
    """

    name: Literal["computer"] = "computer"
    api_type: Literal["computer_20241022"] = "computer_20241022"
    width: int
    height: int
    display_num: int | None

    _screenshot_delay = 1.0
    _scaling_enabled = True

    # Common key combinations mapped to cliclick commands
    KEY_COMBINATIONS = {
        # Copy/Paste
        "cmd+c": ["kd:cmd", "kp:c", "ku:cmd"],           # Copy
        "cmd+v": ["kd:cmd", "kp:v", "ku:cmd"],           # Paste
        "cmd+x": ["kd:cmd", "kp:x", "ku:cmd"],           # Cut
        
        # Undo/Redo
        "cmd+z": ["kd:cmd", "kp:z", "ku:cmd"],           # Undo
        "cmd+shift+z": ["kd:cmd,shift", "kp:z", "ku:cmd,shift"],  # Redo
        
        # Text Editing
        "cmd+a": ["kd:cmd", "kp:a", "ku:cmd"],           # Select All
        "cmd+f": ["kd:cmd", "kp:f", "ku:cmd"],           # Find
        
        # File Operations
        "cmd+s": ["kd:cmd", "kp:s", "ku:cmd"],           # Save
        "cmd+o": ["kd:cmd", "kp:o", "ku:cmd"],           # Open
        "cmd+w": ["kd:cmd", "kp:w", "ku:cmd"],           # Close Window
        "cmd+q": ["kd:cmd", "kp:q", "ku:cmd"],           # Quit App
        
        # App Management
        "cmd+space": ["kd:cmd", "kp:space", "ku:cmd"],   # Spotlight
        "cmd+tab": ["kd:cmd", "kp:tab", "ku:cmd"],       # Switch Apps
        "cmd+m": ["kd:cmd", "kp:m", "ku:cmd"],           # Minimize
        "cmd+h": ["kd:cmd", "kp:h", "ku:cmd"],           # Hide
        
        # Screenshots
        "cmd+shift+3": ["kd:cmd,shift", "kp:3", "ku:cmd,shift"],  # Full Screenshot
        "cmd+shift+4": ["kd:cmd,shift", "kp:4", "ku:cmd,shift"],  # Selection Screenshot
        "cmd+shift+5": ["kd:cmd,shift", "kp:5", "ku:cmd,shift"],  # Screenshot Tools
        
        # Navigation
        "cmd+left": ["kd:cmd", "kp:arrow-left", "ku:cmd"],        # Start of Line
        "cmd+right": ["kd:cmd", "kp:arrow-right", "ku:cmd"],      # End of Line
        "alt+left": ["kd:alt", "kp:arrow-left", "ku:alt"],        # Previous Word
        "alt+right": ["kd:alt", "kp:arrow-right", "ku:alt"],      # Next Word
        
        # Text Selection
        "cmd+shift+left": ["kd:cmd,shift", "kp:arrow-left", "ku:cmd,shift"],    # Select to Line Start
        "cmd+shift+right": ["kd:cmd,shift", "kp:arrow-right", "ku:cmd,shift"],  # Select to Line End
        "shift+left": ["kd:shift", "kp:arrow-left", "ku:shift"],                # Select Left
        "shift+right": ["kd:shift", "kp:arrow-right", "ku:shift"],              # Select Right
    }

    @property
    def options(self) -> ComputerToolOptions:
        return {
            "display_width_px": self.width,
            "display_height_px": self.height,
            "display_number": self.display_num,
        }

    def to_params(self) -> BetaToolComputerUse20241022Param:
        return {"name": self.name, "type": self.api_type, **self.options}

    def __init__(self):
        super().__init__()

        # Set default dimensions
        self.width = int(os.environ.get("WIDTH", 1366))
        self.height = int(os.environ.get("HEIGHT", 768))
        self.display_num = None

        if IS_CODESPACE:
            logger.warning("Running in codespace environment - some features may be limited")

    async def __call__(
        self,
        *,
        action: Action,
        text: str | None = None,
        coordinate: tuple[int, int] | None = None,
        **kwargs,
    ):
        logger.debug(
            "",
            extra={
                'event_type': 'TOOL_USE',
                'sender': 'computer',
                'tool_name': 'computer',
                'command': f"action={action} text={text} coordinate={coordinate}"
            }
        )

        if IS_CODESPACE:
            return ToolResult(
                error="This action is not supported in codespace environment."
            )

        try:
            if action == "key":
                if not text:
                    raise ToolError("Text required for key action")
                
                # Convert to lowercase for consistency
                text = text.lower()
                
                # Handle key combinations
                if "+" in text:
                    keys = text.split("+")
                    cmd_parts = []
                    
                    # Handle modifier keys
                    modifiers = [k for k in keys[:-1] if k in MODIFIER_KEYS]
                    if modifiers:
                        cmd_parts.append(f"kd:{','.join(modifiers)}")
                    
                    # Handle the main key
                    main_key = keys[-1]
                    if main_key in VALID_KEYS:
                        # Use kp: for special keys
                        cmd_parts.append(f"kp:{main_key}")
                    else:
                        # Use t: for regular characters
                        cmd_parts.append(f"t:{main_key}")
                    
                    # Release modifier keys
                    if modifiers:
                        cmd_parts.append(f"ku:{','.join(modifiers)}")
                    
                    # Execute commands in sequence
                    results = []
                    for cmd in cmd_parts:
                        results.append(await self.shell(f"cliclick {cmd}"))
                    return ToolResult(
                        output="\n".join(r.output for r in results if r.output),
                        error="\n".join(r.error for r in results if r.error)
                    )
                
                # Handle single keys
                if text in VALID_KEYS:
                    return await self.shell(f"cliclick kp:{text}")
                else:
                    # Use t: for typing single characters
                    return await self.shell(f"cliclick t:{text}")

            elif action == "type":
                if not text:
                    raise ToolError("Text required for type action")
                results: list[ToolResult] = []
                for chunk in chunks(text, TYPING_GROUP_SIZE):
                    cmd = f"cliclick w:{TYPING_DELAY_MS} t:{shlex.quote(chunk)}"
                    results.append(await self.shell(cmd, take_screenshot=False))
                screenshot_base64 = (await self.screenshot()).base64_image
                return ToolResult(
                    output="".join(result.output or "" for result in results),
                    error="".join(result.error or "" for result in results),
                    base64_image=screenshot_base64,
                )

            elif action in ("mouse_move", "left_click", "right_click", "double_click"):
                if not coordinate:
                    raise ToolError(f"Coordinates required for {action}")
                
                x, y = self.scale_coordinates(ScalingSource.API, coordinate[0], coordinate[1])
                
                cmd_map = {
                    "mouse_move": "m",
                    "left_click": "c",
                    "right_click": "rc",
                    "double_click": "dc"
                }
                
                return await self.shell(f"cliclick {cmd_map[action]}:{x},{y}")

            elif action == "screenshot":
                return await self.screenshot()

            else:
                raise ToolError(f"Invalid action: {action}")

        except Exception as e:
            return ToolResult(error=str(e))

    async def screenshot(self):
        """Take a screenshot of the current screen and return the base64 encoded image."""
        if IS_CODESPACE:
            return ToolResult(
                error="Screenshot functionality is not available in codespace environment"
            )

        output_dir = Path(OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"screenshot_{uuid4().hex}.png"

        try:
            # Use screencapture on macOS
            result = await self.shell(f"screencapture -x {path}")
            if result.error:
                return result

            if path.exists():
                # Read the image and compress if necessary
                image_data = path.read_bytes()
                if len(image_data) > MAX_IMAGE_SIZE:
                    image_data = compress_image(image_data)

                return ToolResult(base64_image=base64.b64encode(image_data).decode())
            return ToolResult(error="Screenshot file was not created")
        except Exception as e:
            return ToolResult(error=f"Failed to take screenshot: {str(e)}")
        finally:
            # Clean up the temporary file
            if path.exists():
                path.unlink()

    async def shell(self, command: str, take_screenshot=False) -> ToolResult:
        """Run a shell command and return the output, error, and optionally a screenshot."""
        _, stdout, stderr = await run(command)
        base64_image = None

        if take_screenshot:
            # delay to let things settle before taking a screenshot
            await asyncio.sleep(self._screenshot_delay)
            base64_image = (await self.screenshot()).base64_image

        return ToolResult(output=stdout, error=stderr, base64_image=base64_image)

    def scale_coordinates(
        self, source: ScalingSource, x: int, y: int
    ) -> tuple[int, int]:
        """
        Scale coordinates between original resolution and target resolution (SCALE_DESTINATION).

        Args:
            source: ScalingSource.API for scaling up from SCALE_DESTINATION to original resolution
                   or ScalingSource.COMPUTER for scaling down from original to SCALE_DESTINATION
            x, y: Coordinates to scale

        Returns:
            Tuple of scaled (x, y) coordinates
        """
        if not self._scaling_enabled:
            return x, y

        # Calculate scaling factors
        x_scaling_factor = SCALE_DESTINATION["width"] / self.width
        y_scaling_factor = SCALE_DESTINATION["height"] / self.height

        if source == ScalingSource.API:
            # Scale up from SCALE_DESTINATION to original resolution
            if x > SCALE_DESTINATION["width"] or y > SCALE_DESTINATION["height"]:
                raise ToolError(
                    f"Coordinates {x}, {y} are out of bounds for {SCALE_DESTINATION['width']}x{SCALE_DESTINATION['height']}"
                )
            return round(x / x_scaling_factor), round(y / y_scaling_factor)
        else:
            # Scale down from original resolution to SCALE_DESTINATION
            return round(x * x_scaling_factor), round(y * y_scaling_factor)
