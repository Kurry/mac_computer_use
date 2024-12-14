"""
Entrypoint for streamlit, see https://docs.streamlit.io/
"""

import asyncio
import base64
import os
import subprocess
from datetime import datetime, timedelta
from enum import StrEnum
from functools import partial, wraps
from pathlib import PosixPath
from typing import cast, Any
import json
from contextlib import contextmanager
import traceback
from anthropic import RateLimitError

import httpx
import streamlit as st
from streamlit.components.v1 import html
from streamlit.delta_generator import DeltaGenerator
from anthropic import APIResponse
from anthropic.types import Message
from anthropic.types.beta import (
    BetaMessage, 
    BetaToolUseBlock, 
    BetaTextBlock,
    BetaTextBlockParam,
    BetaToolResultBlockParam,
)
from anthropic.types.tool_use_block import ToolUseBlock
from dotenv import load_dotenv

from loop import (
    PROVIDER_TO_DEFAULT_MODEL_NAME,
    APIProvider,
    sampling_loop,
)
from tools import ToolResult
from logger import logger, log_tool_use, log_tool_result, log_message

load_dotenv()

# Rest of the file remains unchanged...

CONFIG_DIR = PosixPath("~/.anthropic").expanduser()
API_KEY_FILE = CONFIG_DIR / "api_key"

# Custom CSS for styling and animations
STREAMLIT_STYLE = """
<style>
    /* Hide chat input while agent loop is running */
    .stApp[data-teststate=running] .stChatInput textarea,
    .stApp[data-test-script-state=running] .stChatInput textarea {
        display: none;
    }
    /* Hide the streamlit deploy button */
    .stDeployButton {
        visibility: hidden;
    }
    /* Mouse tracker styles */
    #mouse-tracker {
        position: fixed;
        width: 20px;
        height: 20px;
        background: rgba(255, 0, 0, 0.3);
        border-radius: 50%;
        pointer-events: none;
        z-index: 9999;
        transition: all 0.1s ease;
        display: none;
    }
    /* Click animation */
    .click-animation {
        position: fixed;
        width: 40px;
        height: 40px;
        border: 2px solid red;
        border-radius: 50%;
        pointer-events: none;
        z-index: 9998;
        animation: clickRipple 0.5s ease-out;
    }
    @keyframes clickRipple {
        0% {
            transform: scale(0.5);
            opacity: 1;
        }
        100% {
            transform: scale(1.5);
            opacity: 0;
        }
    }
    /* Auto scroll container */
    .chat-container {
        height: calc(100vh - 200px);
        overflow-y: auto;
        scroll-behavior: smooth;
    }
</style>

<div id="mouse-tracker"></div>

<script>
    // Mouse tracking
    const tracker = document.getElementById('mouse-tracker');
    let lastX = 0;
    let lastY = 0;
    
    function updateMousePosition(x, y) {
        tracker.style.display = 'block';
        tracker.style.left = x + 'px';
        tracker.style.top = y + 'px';
        lastX = x;
        lastY = y;
    }
    
    // Click animation
    function createClickAnimation(x, y) {
        const clickEffect = document.createElement('div');
        clickEffect.className = 'click-animation';
        clickEffect.style.left = (x - 20) + 'px';
        clickEffect.style.top = (y - 20) + 'px';
        document.body.appendChild(clickEffect);
        
        setTimeout(() => {
            clickEffect.remove();
        }, 500);
    }
    
    // User controls toggle
    let controlsEnabled = true;
    document.addEventListener('keydown', (e) => {
        if (e.key === ' ' && e.metaKey) {  // Space + Cmd
            controlsEnabled = !controlsEnabled;
            const event = new CustomEvent('controlsToggle', { detail: controlsEnabled });
            window.dispatchEvent(event);
        }
    });
    
    // Auto scroll
    function scrollToBottom() {
        const container = document.querySelector('.chat-container');
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    }
    
    // Expose functions to Python
    window.streamlitFunctions = {
        updateMousePosition,
        createClickAnimation,
        scrollToBottom
    };
</script>
"""

WARNING_TEXT = ""

INTERRUPT_TEXT = "(user stopped or interrupted and wrote the following)"
INTERRUPT_TOOL_ERROR = "human stopped or interrupted tool execution"


class Sender(StrEnum):
    USER = "user"
    BOT = "assistant"
    TOOL = "tool"


def setup_state():
    """Initialize session state variables"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "api_key" not in st.session_state:
        st.session_state.api_key = load_from_storage("api_key") or os.getenv(
            "ANTHROPIC_API_KEY", ""
        )
    if "provider" not in st.session_state:
        st.session_state.provider = (
            os.getenv("API_PROVIDER", "anthropic") or APIProvider.ANTHROPIC
        )
    if "provider_radio" not in st.session_state:
        st.session_state.provider_radio = st.session_state.provider
    if "model" not in st.session_state:
        _reset_model()
    if "auth_validated" not in st.session_state:
        st.session_state.auth_validated = False
    if "responses" not in st.session_state:
        st.session_state.responses = {}
    if "tools" not in st.session_state:
        st.session_state.tools = {}
    if "only_n_most_recent_images" not in st.session_state:
        st.session_state.only_n_most_recent_images = 10
    if "custom_system_prompt" not in st.session_state:
        st.session_state.custom_system_prompt = load_from_storage("system_prompt") or ""
    if "hide_images" not in st.session_state:
        st.session_state.hide_images = False
    if "controls_enabled" not in st.session_state:
        st.session_state.controls_enabled = True
    if "in_sampling_loop" not in st.session_state:
        st.session_state.in_sampling_loop = False


def _reset_model():
    st.session_state.model = PROVIDER_TO_DEFAULT_MODEL_NAME[
        cast(APIProvider, st.session_state.provider)
    ]


def toggle_controls():
    st.session_state.controls_enabled = not st.session_state.controls_enabled


async def main():
    """Render loop for streamlit"""
    setup_state()

    st.markdown(STREAMLIT_STYLE, unsafe_allow_html=True)

    st.title("Claude Computer Use for Mac")

    # User controls toggle button (only visible to users)
    col1, col2 = st.columns([3, 1])
    with col2:
        st.button("Toggle Controls (⌘ + Space)", on_click=toggle_controls)
        if st.session_state.controls_enabled:
            st.success("Controls Enabled")
        else:
            st.error("Controls Disabled")

    st.markdown(
        """This is from [Mac Computer Use](https://github.com/deedy/mac_computer_use), a fork of [Anthropic Computer Use](https://github.com/anthropics/anthropic-quickstarts/blob/main/computer-use-demo/README.md) to work natively on Mac."""
    )

    with st.sidebar:

        def _reset_api_provider():
            if st.session_state.provider_radio != st.session_state.provider:
                _reset_model()
                st.session_state.provider = st.session_state.provider_radio
                st.session_state.auth_validated = False

        provider_options = [option.value for option in APIProvider]
        st.radio(
            "API Provider",
            options=provider_options,
            key="provider_radio",
            format_func=lambda x: x.title(),
            on_change=_reset_api_provider,
        )

        st.text_input("Model", key="model")

        if st.session_state.provider == APIProvider.ANTHROPIC:
            api_key_label = "Anthropic API Key"
            st.text_input(
                api_key_label,
                type="password",
                key="api_key",
                on_change=lambda: save_to_storage("api_key", st.session_state.api_key),
            )

        st.number_input(
            "Only send N most recent images",
            min_value=0,
            key="only_n_most_recent_images",
            help="To decrease the total tokens sent, remove older screenshots from the conversation",
        )
        st.text_area(
            "Custom System Prompt Suffix",
            key="custom_system_prompt",
            help="Additional instructions to append to the system prompt. see computer_use_demo/loop.py for the base system prompt.",
            on_change=lambda: save_to_storage(
                "system_prompt", st.session_state.custom_system_prompt
            ),
        )
        st.checkbox("Hide screenshots", key="hide_images")

        if st.button("Reset", type="primary"):
            with st.spinner("Resetting..."):
                st.session_state.clear()
                setup_state()

                subprocess.run("pkill Xvfb; pkill tint2", shell=True, check=True)  # noqa: ASYNC221
                await asyncio.sleep(1)
                subprocess.run("./start_all.sh", shell=True)  # noqa: ASYNC221

    if not st.session_state.auth_validated:
        if auth_error := validate_auth(
            st.session_state.provider, st.session_state.api_key
        ):
            st.warning(f"Please resolve the following auth issue:\\n\\n{auth_error}")
            return
        else:
            st.session_state.auth_validated = True

    chat, http_logs = st.tabs(["Chat", "HTTP Exchange Logs"])
    new_message = st.chat_input(
        "Type a message to send to Claude to control the computer..."
    )

    with chat:
        # Create a container for auto-scrolling
        chat_container = st.container()
        with chat_container:
            # render past chats
            for message in st.session_state.messages:
                if isinstance(message["content"], str):
                    _render_message(message["role"], message["content"])
                elif isinstance(message["content"], list):
                    for block in message["content"]:
                        if isinstance(block, dict) and block["type"] == "tool_result":
                            _render_message(
                                Sender.TOOL,
                                st.session_state.tools[block["tool_use_id"]],
                            )
                        else:
                            _render_message(
                                message["role"],
                                block,
                            )

            # render past http exchanges
            for identity, response in st.session_state.responses.items():
                if isinstance(response, httpx.Response):
                    _render_api_response(response.request, response, identity, http_logs)

            # render new message
            if new_message:
                st.session_state.messages.append(
                    {
                        "role": Sender.USER,
                        "content": [
                            *maybe_add_interruption_blocks(),
                            BetaTextBlockParam(type="text", text=new_message),
                        ],
                    }
                )
                _render_message(Sender.USER, new_message)

            try:
                most_recent_message = st.session_state["messages"][-1]
            except IndexError:
                return

            if most_recent_message["role"] is not Sender.USER:
                return

            with st.spinner("Running Agent..."):
                with track_sampling_loop():
                    st.session_state.messages = await sampling_loop(
                        system_prompt_suffix=st.session_state.custom_system_prompt,
                        model=st.session_state.model,
                        provider=st.session_state.provider,
                        messages=st.session_state.messages,
                        output_callback=partial(_render_message, Sender.BOT),
                        tool_output_callback=partial(
                            _tool_output_callback, tool_state=st.session_state.tools
                        ),
                        api_response_callback=partial(
                            _api_response_callback,
                            tab=http_logs,
                            response_state=st.session_state.responses,
                        ),
                        api_key=st.session_state.api_key,
                        only_n_most_recent_images=st.session_state.only_n_most_recent_images,
                    )

        # Auto scroll after rendering
        html("""
            <script>
                window.streamlitFunctions.scrollToBottom();
            </script>
        """)


def validate_auth(provider: APIProvider, api_key: str | None):
    if provider == APIProvider.ANTHROPIC:
        if not api_key:
            key_type = "Anthropic API Key"
            return f"Enter your {key_type} in the sidebar to continue."
    if provider == APIProvider.BEDROCK:
        import boto3

        if not boto3.Session().get_credentials():
            return "You must have AWS credentials set up to use the Bedrock API."
    if provider == APIProvider.VERTEX:
        import google.auth
        from google.auth.exceptions import DefaultCredentialsError

        if not os.environ.get("CLOUD_ML_REGION"):
            return "Set the CLOUD_ML_REGION environment variable to use the Vertex API."
        try:
            google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
        except DefaultCredentialsError:
            return "Your google cloud credentials are not set up correctly."


def load_from_storage(filename: str) -> str | None:
    """Load data from a file in the storage directory."""
    try:
        file_path = CONFIG_DIR / filename
        if file_path.exists():
            data = file_path.read_text().strip()
            if data:
                return data
    except Exception as e:
        st.write(f"Debug: Error loading {filename}: {e}")
    return None


def save_to_storage(filename: str, data: str) -> None:
    """Save data to a file in the storage directory."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        file_path = CONFIG_DIR / filename
        file_path.write_text(data)
        # Ensure only user can read/write the file
        file_path.chmod(0o600)
    except Exception as e:
        st.write(f"Debug: Error saving {filename}: {e}")


def _api_response_callback(
    request: httpx.Request,
    response: httpx.Response | object | None,
    error: Exception | None,
    *,  # Force keyword arguments
    tab: DeltaGenerator,
    response_state: dict[str, Any],  # Changed type hint to be more flexible
):
    """Handle an API response by storing it to state and rendering it."""
    response_id = datetime.now().isoformat()
    if isinstance(response, httpx.Response):
        response_state[response_id] = response
        _render_api_response(request, response, response_id, tab)
    elif error:
        with tab:
            st.error(f"API Error: {error}")


def _tool_output_callback(
    tool_output: ToolResult, tool_id: str, tool_state: dict[str, ToolResult]
):
    """Handle a tool output by storing it to state and rendering it."""
    tool_state[tool_id] = tool_output
    _render_message(Sender.TOOL, tool_output)

    # Update mouse tracker for mouse movements
    if hasattr(tool_output, "output") and "cliclick m:" in str(tool_output.output):
        coords = str(tool_output.output).split("m:")[1].strip().split(",")
        if len(coords) == 2:
            html(f"""
                <script>
                    window.streamlitFunctions.updateMousePosition({coords[0]}, {coords[1]});
                </script>
            """)

    # Show click animation for clicks
    if hasattr(tool_output, "output") and any(
        cmd in str(tool_output.output) for cmd in ["c:", "rc:", "dc:", "mc:"]
    ):
        # Get current mouse position from tracker
        html("""
            <script>
                const tracker = document.getElementById('mouse-tracker');
                if (tracker) {
                    window.streamlitFunctions.createClickAnimation(
                        parseInt(tracker.style.left),
                        parseInt(tracker.style.top)
                    );
                }
            </script>
        """)


def _render_api_response(
    request: httpx.Request,
    response: httpx.Response,
    response_id: str,
    tab: DeltaGenerator,
):
    """Render an API response to a streamlit tab"""
    with tab:
        with st.expander(f"Request/Response ({response_id})"):
            newline = "\\n\\n"
            st.markdown(
                f"`{request.method} {request.url}`{newline}{newline.join(f'`{k}: {v}`' for k, v in request.headers.items())}"
            )
            st.json(request.read().decode())
            st.markdown(
                f"`{response.status_code}`{newline}{newline.join(f'`{k}: {v}`' for k, v in response.headers.items())}"
            )
            st.json(response.text)


def _render_message(
    sender: Sender,
    message: str | dict | BetaToolUseBlock | ToolResult | BetaTextBlock,
):
    """Convert input from the user or output from the agent to a streamlit message."""
    # Log messages but remove print statements
    if isinstance(message, dict) and message.get("type") == "tool_use" and message.get("name") == "bash":
        cmd = message.get("input", {}).get("command", "")
        log_tool_use(sender, "bash", cmd)
    elif isinstance(message, ToolResult):
        if message.error:
            log_tool_result(sender, type(message).__name__, error=message.error)
        elif message.output and not message.base64_image:
            output = message.output[:50] + "..." if len(message.output) > 50 else message.output
            log_tool_result(sender, type(message).__name__, output=message.output)
        else:
            log_tool_result(sender, type(message).__name__)
    else:
        log_message(sender, type(message).__name__)

    if not message:
        return

    is_tool_result = not isinstance(message, str) and (
        isinstance(message, ToolResult)
        or message.__class__.__name__ == "ToolResult"
        or message.__class__.__name__ == "CLIResult"
        or message.__class__.__name__ == "ToolFailure"
    )

    with st.chat_message(sender):
        if is_tool_result:
            message = cast(ToolResult, message)
            if message.output:
                if message.__class__.__name__ == "CLIResult":
                    # Truncate long CLI output to first line
                    output = message.output.split('\n')[0] + "..." if '\n' in message.output else message.output
                    st.code(output)
                else:
                    st.markdown(message.output)
            if message.error:
                st.error(message.error)
            if message.base64_image and not st.session_state.hide_images:
                try:
                    st.image(base64.b64decode(message.base64_image))
                except Exception:
                    st.error("Failed to load image")
        elif isinstance(message, BetaToolUseBlock) or isinstance(message, ToolUseBlock):
            st.code(f"Tool Use: {message.name}\nInput: {message.input}")
        elif isinstance(message, dict):
            if message.get("type") == "text":
                text = message.get("text", "")
                if "<thinking>" in text and "</thinking>" in text:
                    parts = text.split("<thinking>")
                    pre_thinking = parts[0]
                    thinking_and_post = parts[1].split("</thinking>")
                    thinking = thinking_and_post[0]
                    post_thinking = thinking_and_post[1] if len(thinking_and_post) > 1 else ""
                    
                    if pre_thinking.strip():
                        st.markdown(pre_thinking)
                    with st.expander("Thinking...", expanded=True):
                        st.markdown(thinking)
                    if post_thinking.strip():
                        st.markdown(post_thinking)
                else:
                    st.markdown(text)
            elif message.get("type") == "tool_use":
                if message.get("name") == "bash":
                    command = message.get("input", {}).get("command", "")
                    st.code(f"Tool Use: bash\nInput: {command}")
                elif message.get("name") == "computer":
                    input_data = message.get("input", {})
                    action = input_data.get("action", "")
                    text = input_data.get("text", "")
                    coordinate = input_data.get("coordinate", "")
                    
                    input_str = f"action: {action}"
                    if text:
                        input_str += f", text: {text}"
                    if coordinate:
                        input_str += f", coordinate: {coordinate}"
                    
                    st.code(f"Tool Use: computer\nInput: {input_str}")
                elif message.get("name") == "str_replace_editor":
                    input_data = message.get("input", {})
                    params = []
                    if 'command' in input_data:
                        params.append(f"command: {input_data['command']}")
                    if 'path' in input_data:
                        params.append(f"path: {input_data['path']}")
                    if 'file_text' in input_data:
                        params.append(f"text: {input_data['file_text']}")
                    
                    input_str = ", ".join(params) if params else "{}"
                    st.code(f"Tool Use: str_replace_editor\nInput: {input_str}")
                else:
                    st.code(f"Tool Use: {message.get('name')}\nInput: {json.dumps(message.get('input', {}), indent=2)}")
            else:
                text_content = message.get("text", "")
                if text_content:
                    st.markdown(text_content)
                else:
                    st.markdown(str(message))
        elif isinstance(message, BetaTextBlock):
            st.markdown(message.text)
        else:
            st.markdown(str(message))


def maybe_add_interruption_blocks():
    if not st.session_state.in_sampling_loop:
        return []
    result = []
    last_message = st.session_state.messages[-1]
    previous_tool_use_ids = [
        block["id"] for block in last_message["content"] if block["type"] == "tool_use"
    ]
    for tool_use_id in previous_tool_use_ids:
        st.session_state.tools[tool_use_id] = ToolResult(error=INTERRUPT_TOOL_ERROR)
        result.append(
            BetaToolResultBlockParam(
                tool_use_id=tool_use_id,
                type="tool_result",
                content=INTERRUPT_TOOL_ERROR,
                is_error=True,
            )
        )
    result.append(BetaTextBlockParam(type="text", text=INTERRUPT_TEXT))
    return result


@contextmanager
def track_sampling_loop():
    st.session_state.in_sampling_loop = True
    yield
    st.session_state.in_sampling_loop = False


def _render_error(error: Exception):
    if isinstance(error, RateLimitError):
        body = "You have been rate limited."
        if retry_after := error.response.headers.get("retry-after"):
            body += f" **Retry after {str(timedelta(seconds=int(retry_after)))} (HH:MM:SS).**"
        body += f"\n\n{error.message}"
    else:
        body = str(error)
        body += "\n\n**Traceback:**"
        lines = "\n".join(traceback.format_exception(error))
        body += f"\n\n```{lines}```"
    save_to_storage(f"error_{datetime.now().timestamp()}.md", body)
    st.error(f"**{error.__class__.__name__}**\n\n{body}", icon=":material/error:")


MAX_STORED_RESPONSES = 50  # Limit number of stored responses

def _cleanup_old_responses(response_state: dict):
    """Remove old responses if we have too many stored"""
    if len(response_state) > MAX_STORED_RESPONSES:
        sorted_keys = sorted(response_state.keys())
        for key in sorted_keys[:-MAX_STORED_RESPONSES]:
            del response_state[key]
        logger.debug(f"Cleaned up responses from {before_count} to {len(response_state)}")


MAX_MESSAGES = 100

def _cleanup_old_messages():
    if len(st.session_state.messages) > MAX_MESSAGES:
        before_count = len(st.session_state.messages)
        st.session_state.messages = st.session_state.messages[-MAX_MESSAGES:]
        logger.debug(f"Cleaned up messages from {before_count} to {len(st.session_state.messages)}")


def render_chat_history(messages):
    """
    Render chat history with virtualization for better performance
    """
    # Only render visible messages
    VISIBLE_MESSAGES = 10
    
    js_code = """
        // Implement intersection observer for lazy loading
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    // Load more messages when user scrolls
                    loadMoreMessages();
                }
            });
        });
        
        const chatContainer = document.getElementById('chat-messages');
        observer.observe(chatContainer);
    """
    
    html_string = f"""
    <div class="chat-container">
        <div class="virtualized-list" id="chat-messages">
            {render_visible_messages(messages[-VISIBLE_MESSAGES:])}
        </div>
    </div>
    
    <script>
        {js_code}
    </script>
    """
    
    return html(html_string)


def debounce(wait):
    """
    Decorator to debounce rapid UI updates
    """
    def decorator(fn):
        last_timestamp = 0
        
        @wraps(fn)
        def debounced(*args, **kwargs):
            nonlocal last_timestamp
            current_time = time.time()
            
            if current_time - last_timestamp > wait:
                last_timestamp = current_time
                return fn(*args, **kwargs)
        return debounced
    return decorator

@debounce(0.1)  # 100ms debounce
def update_chat_ui(messages):
    # Update UI logic here
    pass


from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ChatMessage:
    """Optimized message storage"""
    content: str
    role: str
    timestamp: float
    rendered: bool = False
    
    # Only store essential data
    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "role": self.role,
            "timestamp": self.timestamp
        }

class ChatHistory:
    def __init__(self):
        self.messages: List[ChatMessage] = []
        self.max_messages = 100  # Limit total messages
        
    def add_message(self, message: ChatMessage):
        if len(self.messages) >= self.max_messages:
            # Remove oldest messages when limit reached
            self.messages = self.messages[-(self.max_messages-1):]
        self.messages.append(message)


class MessageBatcher:
    """Batch message updates to reduce UI refreshes"""
    def __init__(self, batch_size=5):
        self.pending_messages = []
        self.batch_size = batch_size
        
    def add(self, message: ChatMessage):
        self.pending_messages.append(message)
        if len(self.pending_messages) >= self.batch_size:
            self.flush()
            
    def flush(self):
        if self.pending_messages:
            st.session_state.messages.extend(self.pending_messages)
            self.pending_messages = []
            st.experimental_rerun()


def load_optimized_css():
    return """
    <style>
        /* Use CSS containment for better performance */
        .chat-container {
            contain: content;
            overflow-y: auto;
            height: 600px;
        }
        
        /* Use CSS will-change for smoother animations */
        .message-animation {
            will-change: transform, opacity;
        }
        
        /* Reduce repaints */
        .chat-message {
            transform: translateZ(0);
            backface-visibility: hidden;
        }
    </style>
    """

st.markdown(load_optimized_css(), unsafe_allow_html=True)


if __name__ == "__main__":
    asyncio.run(main())