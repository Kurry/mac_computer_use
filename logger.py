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
        # Format timestamp to only show time (no date)
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S.%f')[:-3]

        # Format based on event type
        if hasattr(record, 'event_type'):
            if record.event_type == 'MESSAGE':
                return f"{timestamp} | {record.levelname:<8} | {record.name}:{record.lineno:<4} | {record.event_type:<10} | {record.sender:<10} | {record.content_type}"
            elif record.event_type == 'TOOL_USE':
                return f"{timestamp} | {record.levelname:<8} | {record.name}:{record.lineno:<4} | {record.event_type:<10} | {record.sender:<10} | {record.tool_name:<10} | {record.command}"
            elif record.event_type == 'TOOL_RESULT':
                base = f"{timestamp} | {record.levelname:<8} | {record.name}:{record.lineno:<4} | {record.event_type:<10} | {record.sender:<10} | {record.result_type:<10}"
                if hasattr(record, 'error') and record.error:
                    return f"{base} | Error: {record.error}"
                if hasattr(record, 'output') and record.output:
                    return f"{base} | output: {record.output}"
                return base
        
        # Default format for non-event logs
        return f"{timestamp} | {record.levelname:<8} | {record.name}:{record.lineno:<4} | {record.getMessage()}"

def setup_logger():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Create a daily rotating file handler with date in filename
    file_handler = TimedRotatingFileHandler(
        filename=log_dir / "app.log",
        when="midnight",
        interval=1,
        backupCount=7,  # Keep logs for 7 days
        encoding="utf-8"
    )
    # Customize the suffix to include date
    file_handler.suffix = "%Y-%m-%d.log"
    
    # Set formatter
    formatter = CustomFormatter()
    file_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(file_handler)
    
    return logger

# Create logger instance
logger = setup_logger()

def log_tool_use(sender: str, tool_name: str, command: str):
    logger.debug(
        "",
        extra={
            'event_type': 'TOOL_USE',
            'sender': sender,
            'tool_name': tool_name,
            'command': command
        }
    )

def log_tool_result(sender: str, tool_type: str, output: str = None, error: str = None):
    if error:
        logger.debug(
            "",
            extra={
                'event_type': 'TOOL_RESULT',
                'sender': sender,
                'result_type': tool_type,
                'error': error
            }
        )
    elif output:
        logger.debug(
            "",
            extra={
                'event_type': 'TOOL_RESULT',
                'sender': sender,
                'result_type': tool_type,
                'output': output
            }
        )
    else:
        logger.debug(
            "",
            extra={
                'event_type': 'TOOL_RESULT',
                'sender': sender,
                'result_type': tool_type
            }
        )

def log_message(sender: str, message_type: str, content: str = None):
    if content:
        logger.debug(
            "",
            extra={
                'event_type': 'MESSAGE',
                'sender': sender,
                'content_type': message_type,
                'content': content
            }
        )
    else:
        logger.debug(
            "",
            extra={
                'event_type': 'MESSAGE',
                'sender': sender,
                'content_type': message_type
            }
        )