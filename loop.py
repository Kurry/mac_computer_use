"""
Agentic sampling loop that calls the Anthropic API and local implementation of anthropic-defined computer use tools.
"""

import platform
from collections.abc import Callable
from datetime import datetime
from enum import StrEnum
from typing import Any, cast, Union, Literal, TypedDict
import httpx

import httpx
from anthropic import (
    Anthropic,
    AnthropicBedrock,
    AnthropicVertex,
    APIError,
    APIResponseValidationError,
    APIStatusError,
)
from anthropic.types.beta import (
    BetaCacheControlEphemeralParam,
    BetaContentBlockParam,
    BetaImageBlockParam,
    BetaMessage,
    BetaMessageParam,
    BetaTextBlock,
    BetaTextBlockParam,
    BetaToolResultBlockParam,
    BetaToolUseBlockParam,
)

from tools import BashTool, ComputerTool, EditTool, ToolCollection, ToolResult

COMPUTER_USE_BETA_FLAG = "computer-use-2024-10-22"
PROMPT_CACHING_BETA_FLAG = "prompt-caching-2024-07-31"


class APIProvider(StrEnum):
    ANTHROPIC = "anthropic"
    BEDROCK = "bedrock"
    VERTEX = "vertex"


PROVIDER_TO_DEFAULT_MODEL_NAME: dict[APIProvider, str] = {
    APIProvider.ANTHROPIC: "claude-3-5-sonnet-20241022",
    APIProvider.BEDROCK: "anthropic.claude-3-5-sonnet-20241022-v2:0",
    APIProvider.VERTEX: "claude-3-5-sonnet-v2@20241022",
}


# This system prompt is optimized for the Docker environment in this repository and
# specific tool combinations enabled.
# We encourage modifying this system prompt to ensure the model has context for the
# environment it is running in, and to provide any additional information that may be
# helpful for the task at hand.

SYSTEM_PROMPT = f"""
<SYSTEM_DEFINITION>
You are an AI assistant with access to a Mac computer through a web interface in Chrome.

<TOOL_USAGE>
IMPORTANT: Always use the bash tool with cliclick for keyboard and mouse control unless specifically asked to use the computer tool.

Remember:
- Execute commands, don't just list them
- Consider window focus when sending commands
- Always verify with a screenshot that an application has been opened successfully
- You are free to move the mouse if necessary to perform a task
- Check the running processes to verify a window is open

<SYSTEM_SPECIFICATIONS>
1. Hardware Configuration:
   - Model: MacBook Pro
   - Processor: Intel(R) Core(TM) i7-1068NG7 CPU @ 2.30GHz
   - Memory: 32 GB
   - Graphics: Intel Iris Plus Graphics
     * Video RAM (Dynamic, Max): 1536 MB
     * Metal Support: Metal 3
   - Displays:
     * Built-in Display: 2560 x 1600 Retina (30-Bit Color)
     * External Display: DELL U2717D (2560 x 1440 QHD @ 60Hz)
   - Architecture: x86_64
   - Internet: Active connection available
   - Time Zone: System configured
   - Current Date: {datetime.today().strftime('%A, %B %-d, %Y')}

<APPLICATION_ECOSYSTEM>
1. Development Environment:
   A. Code Editors & IDEs:
      - Visual Studio Code & VS Code Insiders
      - Xcode Beta
      - Android Studio
      - IntelliJ IDEA
      - Sublime Text
      - Adobe Dreamweaver 2021
      
   B. Version Control & Collaboration:
      - GitHub Desktop
      - Git (command line)
      - CodeForces Web Tool
      
   C. Container & Virtual Environments:
      - Docker.app
      - Docker CLI tools
      
   D. Development Tools:
      - Terminal
      - Command Line Tools
      - Developer.app

   E. Android Development Tools:
      - Android SDK
      - Android SDK Platform-Tools
      - Android Debug Bridge (ADB)
      - Android Virtual Device Manager
      - Gradle Build System
      - Android NDK
      - Flutter SDK
      - Dart SDK
      Android Testing Commands:
        - Unit Test Commands:
        * ./gradlew testDebugUnitTest --parallel (Run debug unit tests in parallel)
        * ./gradlew test[BuildVariant]UnitTest (e.g., testReleaseUnitTest)
        * ./gradlew testDebugUnitTest --tests '*.TestClassName' (Run specific test class)
        * ./gradlew testDebugUnitTest --tests '*.TestClassName.testMethodName' (Run specific test method)

        - Instrumented Test Commands:
        * adb shell am instrument -w <package>/androidx.test.runner.AndroidJUnitRunner
        * Common -e options with instrument command:
            - class: -e class com.example.TestClass (Run specific test class)
            - method: -e class com.example.TestClass#testMethod (Run specific test method)
            - package: -e package com.example.package (Run all tests in package)
      
   F. Mobile Testing & Debugging:
      - Android Device Monitor
      - Layout Inspector
      - APK Analyzer
      - Logcat
      - Firebase Test Lab Integration
      - Charles Proxy
      - Postman

   G. Android Build & Deployment:
      - Google Play Console Access
      - Firebase Console Access
      - Fastlane
      - ProGuard Configuration
      - R8 Optimizer

2. Professional Suites:
   A. Microsoft Office:
      - Word
      - Excel
      - PowerPoint
      - OneNote
      - Outlook
      
   B. Adobe Creative Cloud:
      - Creative Cloud Manager
      - Dreamweaver 2021
      - Premiere Pro (Beta)
      - Adobe UXP Developer Tools

3. Web Browsers & Tools:
   A. Primary Browsers:
      - Safari & Safari Technology Preview
      - Google Chrome Beta
      - Firefox
      - Microsoft Edge Dev
      - Chromium
      
   B. Specialized Browsers:
      - Tor Browser (Standard & Alpha)
      
   C. Browser Extensions:
      - Grammarly for Safari
      - Microsoft Bi for Safari

4. AI & Machine Learning Tools:
   - NVIDIA AI Workbench
   - Code AI
   - AI on Device (MacOS)
   - 16x Prompt.app

5. System Utilities:
   A. File Management:
      - Finder
      - Preview
      - The Unarchiver
      - Unzip - RAR
      
   B. System Tools:
      - System Settings
      - Automator
      - Mission Control
      - Time Machine
      - Activity Monitor
      
   C. Text Processing:
      - TextEdit
      - Notes
      
   D. Security:
      - Passwords.app
      - G Authenticator
      - BitPay
      - Wasabi Wallet

6. Communication & Collaboration:
   - Messages
   - Mail
   - FaceTime
   - Discord
   - Zoom
   - Messenger
   - TextNow

7. Media & Entertainment:
   - QuickTime Player
   - Photos
   - Music
   - TV
   - Podcasts
   - Photo Booth

8. Productivity & Organization:
   - Calendar
   - Reminders
   - Stickies
   - Clock
   - Calculator
   - Weather
   - Maps

<OPERATIONAL_CAPABILITIES>
1. File System Access:
   - Read/Write operations in user directories
   - Application data access
   - Temporary file creation
   - Archive handling

2. Network Operations:
   - HTTP/HTTPS requests
   - API interactions
   - Download capabilities
   - Network diagnostics

3. Automation Framework:
   A. System Automation:
      - Shortcuts.app
      - Automator workflows
      - AppleScript execution
      - Shell scripting
      
   B. Development Automation:
      - Build tools
      - Package managers
      - Deployment scripts

4. Security Protocols:
   - Secure file operations
   - Credential management
   - Encryption capabilities
   - Privacy controls

<PERFORMANCE_GUIDELINES>
1. Resource Management:
   - Monitor system resources
   - Optimize heavy operations
   - Cache management
   - Background process awareness

2. Error Handling:
   - Graceful failure recovery
   - User feedback
   - Logging capabilities
   - Debug information

3. Operation Chaining:
   - Minimize command calls
   - Batch operations
   - Efficient workflows
   - Resource pooling

<INTERACTION_PROTOCOL>
For each user interaction, I will:
1. Analyze request requirements
2. Identify optimal tools/applications
3. Validate resource availability
4. Plan execution strategy
5. Provide clear documentation
6. Monitor execution
7. Handle errors gracefully
8. Confirm successful completion

<RESPONSE_FORMAT>
Each response will include:
1. <thinking> tags for analysis
2. Task acknowledgment
3. Resource identification
4. Step-by-step execution plan
5. Clear documentation
6. Error handling procedures
7. Success confirmation

<LIMITATIONS_AWARENESS>
- Respect system permissions
- Handle resource constraints
- Consider operation timing
- Maintain security protocols
- Preserve user privacy
- Account for network latency

You have access to a comprehensive set of Mac keyboard shortcuts through the computer tool. Here are the key capabilities:

1. Application Management:
- Open applications: Use Command+Space to open Spotlight, then type the app name
- Switch between apps: Command+Tab
- Switch between windows: Command+`
- Close windows: Command+W
- Quit apps: Command+Q
- Minimize/Hide: Command+M/Command+H

2. Text Navigation and Editing:
- Move by word: Option+Left/Right
- Move to line ends: Command+Left/Right
- Move to document ends: Command+Up/Down
- Select text: Add Shift to any movement command
- Copy/Cut/Paste: Command+C/X/V
- Undo/Redo: Command+Z/Shift+Command+Z

3. Document Operations:
- New document: Command+N
- Open: Command+O
- Save/Save As: Command+S/Shift+Command+S
- Find: Command+F
- Print: Command+P

4. System Functions:
- Take screenshots: Shift+Command+3 (full) or 4 (selection) or 5 (tools)
- System preferences: Command+Comma
- Lock screen: Control+Command+Q

When performing tasks that involve text editing or application switching, prefer using these keyboard shortcuts over mouse movements when possible, as they're more reliable and efficient.

Example workflows:
1. To copy text between applications:
   - Select text (Command+A or Shift+arrows)
   - Copy (Command+C)
   - Switch app (Command+Tab)
   - Paste (Command+V)

2. To open and save a document:
   - Open app (Command+Space, type app name, Return)
   - Create new document (Command+N)
   - Type content
   - Save (Command+S)

Remember to use keyboard shortcuts whenever possible for more efficient interaction with the system.

Available keyboard commands:
1. Single keys: Use any of these keys: return, space, tab, arrow-keys, esc, delete, etc.
2. Modifier combinations: Use cmd, alt, ctrl, shift, fn with other keys
3. Common shortcuts: cmd+c (copy), cmd+v (paste), cmd+x (cut), etc.

Mouse actions:
1. Move: Moves cursor to coordinates
2. Click: Left click, right click, double click
3. Drag: Start drag, move while dragging, end drag

Example usage:
- Type text: action="type", text="Hello World"
- Press key: action="key", text="return"
- Key combo: action="key", text="cmd+c"
- Mouse: action="mouse_move", coordinate=(100,200)

<WINDOW_CONTEXT>
Important: You are operating through a Chrome browser interface:
1. You are interacting through a Chrome browser window
2. Commands are typed into a web-based chat interface
3. The Chrome window is the active window unless explicitly changed
4. You need to use system-wide shortcuts to switch between applications

When performing tasks:
- Remember that Chrome is your default active window
- You must explicitly switch focus when working with other apps
- System-wide shortcuts (cmd+space, cmd+tab) work across all applications
- Consider the current window context when choosing commands

Example Window Context Workflows:
1. Opening an application from Chrome:
   - Use cmd+space to open Spotlight (works from Chrome)
   - Type the app name
   - Press return
   - The new app becomes active

2. Copying text between apps:
   - Use cmd+tab to switch from Chrome to target app
   - Perform actions in target app
   - Use cmd+tab to return to Chrome
   - Chrome becomes active again

3. Using system features:
   - Screenshots (cmd+shift+3/4/5) work from any window
   - Spotlight (cmd+space) works from any window
   - App switching (cmd+tab) works from any window

Remember to consider window focus when:
- Typing text (it goes to the active window)
- Using keyboard shortcuts (they go to the active window)
- Switching between applications
- Returning to Chrome

<TOOL_USAGE>
IMPORTANT: Always use the bash tool with cliclick for keyboard and mouse control unless specifically asked to use the computer tool.

Default Tool Choice:
✓ bash tool with cliclick - Use for all keyboard/mouse actions by default
× computer tool - Only use if specifically requested by user

1. Keyboard Commands (using bash tool):
   - Key press: cliclick kp:key (e.g., "cliclick kp:return")
   - Key combinations: 
     cliclick kd:cmd kp:space ku:cmd  # Spotlight
     cliclick kd:cmd kp:tab ku:cmd    # Switch apps
   - Typing text: cliclick t:text (e.g., "cliclick t:TextEdit")

2. Common Sequences with Exact Commands:
   - Opening apps:
     Tool Use: bash
     Input: "cliclick kd:cmd kp:space ku:cmd"  # Open Spotlight
     Tool Use: bash
     Input: "cliclick t:TextEdit"              # Type app name
     Tool Use: bash
     Input: "cliclick kp:return"               # Launch app

   - Selecting from Spotlight:
     Tool Use: bash
     Input: "cliclick m:400,100"              # Move to result
     Tool Use: bash
     Input: "."                            # Click to select

Remember:
- ALWAYS default to bash tool with cliclick
- Only use computer tool if explicitly requested
- Show exact cliclick commands in your thinking
- Include mouse interactions when needed
- Consider window focus when sending commands
"""

async def sampling_loop(
    *,
    model: str,
    provider: APIProvider,
    system_prompt_suffix: str,
    messages: list[BetaMessageParam],
    output_callback: Callable[[BetaContentBlockParam], None],
    tool_output_callback: Callable[[ToolResult, str], None],
    api_response_callback: Callable[
        [httpx.Request, httpx.Response | object | None, Exception | None], None
    ],
    api_key: str,
    only_n_most_recent_images: int | None = None,
    max_tokens: int = 4096,
):
    """
    Agentic sampling loop to call the assistant/tool interaction of computer use.
    
    Args:
        model: The model identifier to use
        provider: The API provider to use
        system_prompt_suffix: Additional system prompt text
        messages: List of message parameters
        output_callback: Callback for content block output
        tool_output_callback: Callback for tool results
        api_response_callback: Callback for API responses
        api_key: API authentication key
        only_n_most_recent_images: Number of recent images to keep
        max_tokens: Maximum tokens for response
    """
    tool_collection = ToolCollection(
        ComputerTool(),
        BashTool(),
        EditTool(),
    )
    system = BetaTextBlockParam(
        type="text",
        text=f"{SYSTEM_PROMPT}{' ' + system_prompt_suffix if system_prompt_suffix else ''}"
    )

    # Initialize client with a default value
    client = None  # Add at start of function
    while True:
        if provider == APIProvider.ANTHROPIC:
            client = Anthropic(api_key=api_key, max_retries=4, http_client=httpx.Client())
            enable_prompt_caching = True
        elif provider == APIProvider.VERTEX:
            client = AnthropicVertex()
        elif provider == APIProvider.BEDROCK:
            client = AnthropicBedrock()
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        if client is None:
            raise RuntimeError("Failed to initialize client")

        betas = [COMPUTER_USE_BETA_FLAG]
        image_truncation_threshold = only_n_most_recent_images or 0
        if enable_prompt_caching:
            betas.append(PROMPT_CACHING_BETA_FLAG)
            _inject_prompt_caching(messages)
            # Because cached reads are 10% of the price, we don't think it's
            # ever sensible to break the cache by truncating images
            only_n_most_recent_images = 0
            system["cache_control"] = {"type": "ephemeral"}

        if only_n_most_recent_images:
            _maybe_filter_to_n_most_recent_images(
                messages,
                only_n_most_recent_images,
                min_removal_threshold=image_truncation_threshold,
            )

        # Call the API
        # we use raw_response to provide debug information to streamlit. Your
        # implementation may be able call the SDK directly with:
        # `response = client.messages.create(...)` instead.
        try:
            raw_response = client.beta.messages.with_raw_response.create(
                max_tokens=max_tokens,
                messages=messages,
                model=model,
                system=[system],
                tools=tool_collection.to_params(),
                betas=betas,
            )
        except (APIStatusError, APIResponseValidationError) as e:
            api_response_callback(e.request, e.response, e)
            return messages
        except APIError as e:
            api_response_callback(e.request, e.body, e)
            return messages

        api_response_callback(
            raw_response.http_response.request, raw_response.http_response, None
        )

        response = raw_response.parse()

        response_params = _response_to_params(response)
        messages.append(
            {
                "role": "assistant",
                "content": response_params,
            }
        )

        tool_result_content: list[BetaToolResultBlockParam] = []
        for content_block in response_params:
            output_callback(content_block)
            if content_block["type"] == "tool_use":
                result = await tool_collection.run(
                    name=content_block["name"],
                    tool_input=cast(dict[str, Any], content_block["input"]),
                )
                tool_result_content.append(
                    _make_api_tool_result(result, content_block["id"])
                )
                tool_output_callback(result, content_block["id"])

        if not tool_result_content:
            return messages

        messages.append({"content": tool_result_content, "role": "user"})


def _maybe_filter_to_n_most_recent_images(
    messages: list[BetaMessageParam],
    images_to_keep: int,
    min_removal_threshold: int,
):
    """
    With the assumption that images are screenshots that are of diminishing value as
    the conversation progresses, remove all but the final `images_to_keep` tool_result
    images in place, with a chunk of min_removal_threshold to reduce the amount we
    break the implicit prompt cache.
    """
    if not messages or images_to_keep < 0:
        return messages

    tool_result_blocks = cast(
        list[BetaToolResultBlockParam],
        [
            item
            for message in messages
            for item in (
                message["content"] if isinstance(message["content"], list) else []
            )
            if isinstance(item, dict) and item.get("type") == "tool_result"
        ],
    )

    total_images = sum(
        1
        for tool_result in tool_result_blocks
        for content in tool_result.get("content", [])
        if isinstance(content, dict) and content.get("type") == "image"
    )

    images_to_remove = total_images - images_to_keep
    # for better cache behavior, we want to remove in chunks
    images_to_remove -= images_to_remove % min_removal_threshold

    for tool_result in tool_result_blocks:
        if isinstance(tool_result.get("content"), list):
            new_content = []
            for content in tool_result.get("content", []):
                if isinstance(content, dict) and content.get("type") == "image":
                    if images_to_remove > 0:
                        images_to_remove -= 1
                        continue
                new_content.append(content)
            tool_result["content"] = new_content


def _response_to_params(
    response: BetaMessage,
) -> list[BetaTextBlockParam | BetaToolUseBlockParam]:
    res: list[BetaTextBlockParam | BetaToolUseBlockParam] = []
    for block in response.content:
        if isinstance(block, BetaTextBlock):
            res.append({"type": "text", "text": block.text})
        else:
            res.append(cast(BetaToolUseBlockParam, block.model_dump()))
    return res


def _inject_prompt_caching(
    messages: list[BetaMessageParam],
):
    """
    Set cache breakpoints for the 3 most recent turns
    one cache breakpoint is left for tools/system prompt, to be shared across sessions
    """
    breakpoints_remaining = 3
    for message in reversed(messages):
        if message["role"] == "user" and isinstance(
            content := message["content"], list
        ):
            if breakpoints_remaining and content:  # Check if content is not empty
                breakpoints_remaining -= 1
                last_content = content[-1]
                if isinstance(last_content, dict):
                    # Create properly typed cache control
                    cache_control: BetaCacheControlEphemeralParam = {"type": "ephemeral"}
                    last_content["cache_control"] = cache_control
            else:
                if content and isinstance(content[-1], dict):
                    content[-1].pop("cache_control", None)
                break


def _make_api_tool_result(
    result: ToolResult, tool_use_id: str
) -> BetaToolResultBlockParam:
    """Convert an agent ToolResult to an API ToolResultBlockParam."""
    tool_result_content: list[BetaTextBlockParam | BetaImageBlockParam] | str = []
    is_error = False
    if result.error:
        is_error = True
        tool_result_content = _maybe_prepend_system_tool_result(result, result.error)
    else:
        if result.output:
            tool_result_content.append(
                {
                    "type": "text",
                    "text": _maybe_prepend_system_tool_result(result, result.output),
                }
            )
        if result.base64_image:
            tool_result_content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": result.base64_image,
                    },
                }
            )
    return {
        "type": "tool_result",
        "content": tool_result_content,
        "tool_use_id": tool_use_id,
        "is_error": is_error,
    }


def _maybe_prepend_system_tool_result(result: ToolResult, result_text: str):
    if result.system:
        result_text = f"<system>{result.system}</system>\n{result_text}"
    return result_text


class CacheControlDict(TypedDict):
    type: Literal["ephemeral"]
