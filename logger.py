import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from datetime import datetime

class CustomFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[41m'  # Red background
    }
    RESET = '\033[0m'
    INDENT = ' ' * 4  # Indentation for multiline outputs

    def format(self, record):
        # Add color to log level
        level_color = self.COLORS.get(record.levelname, '')
        reset = self.RESET

        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

        # Format the basic message header
        header = f"{timestamp} | {level_color}{record.levelname:<8}{reset} | {record.name}:{record.lineno:<4}"

        # Format based on event type
        if hasattr(record, 'event_type'):
            if record.event_type == 'MESSAGE':
                content = getattr(record, 'content', '')
                return f"{header} | {record.event_type:<10} | {record.sender:<10} | {record.content_type} | {content[:100]}..."
            elif record.event_type == 'TOOL_USE':
                return f"{header} | {record.event_type:<10} | {record.sender:<10} | {record.tool_name:<10} | {record.command}"
            elif record.event_type == 'TOOL_RESULT':
                base = f"{header} | {record.event_type:<10} | {record.sender:<10} | {record.result_type:<10}"
                if hasattr(record, 'error') and record.error:
                    error = record.error.strip().replace('\n', '\n' + self.INDENT)
                    return f"{base} | Error:\n{self.INDENT}{error}"
                if hasattr(record, 'output') and record.output:
                    output = record.output.strip().replace('\n', '\n' + self.INDENT)
                    return f"{base} |\n{self.INDENT}{output}"
                return base
        # Default format for other log types
        return f"{header} | {record.getMessage()}"

# Create logs directory
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Configure logging
logger = logging.getLogger("mac_computer_use")
logger.setLevel(logging.DEBUG)

# Create formatters
detailed_formatter = logging.Formatter(
    '%(asctime)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

custom_formatter = CustomFormatter()

# Create daily rotating file handler
file_handler = TimedRotatingFileHandler(
    filename=LOG_DIR / "mac_computer_use.log",
    when="midnight",
    interval=1,
    backupCount=7,  # Keep a week of logs
    encoding="utf-8"
)
file_handler.setFormatter(detailed_formatter)
file_handler.setLevel(logging.DEBUG)
logger.addHandler(file_handler)

# Create console handler with CustomFormatter
console_handler = logging.StreamHandler()
console_handler.setFormatter(custom_formatter)
console_handler.setLevel(logging.DEBUG)
logger.addHandler(console_handler)

# Helper functions
def log_tool_use(sender: str, tool: str, command: str):
    logger.debug(
        '',
        extra={
            'event_type': 'TOOL_USE',
            'sender': sender,
            'tool_name': tool,
            'command': command
        }
    )

def log_tool_result(sender: str, tool_type: str, output: str = None, error: str = None):
    if error:
        logger.debug(
            '',
            extra={
                'event_type': 'TOOL_RESULT',
                'sender': sender,
                'result_type': tool_type,
                'error': error
            }
        )
    elif output:
        logger.debug(
            '',
            extra={
                'event_type': 'TOOL_RESULT',
                'sender': sender,
                'result_type': tool_type,
                'output': output
            }
        )
    else:
        logger.debug(
            '',
            extra={
                'event_type': 'TOOL_RESULT',
                'sender': sender,
                'result_type': tool_type
            }
        )

def log_message(sender: str, message_type: str, content: str = None):
    if content:
        logger.debug(
            '',
            extra={
                'event_type': 'MESSAGE',
                'sender': sender,
                'content_type': message_type,
                'content': content
            }
        )
    else:
        logger.debug(
            '',
            extra={
                'event_type': 'MESSAGE',
                'sender': sender,
                'content_type': message_type
            }
        )