import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from datetime import datetime
import time

class CustomFormatter(logging.Formatter):
    def __init__(self):
        # Tell formatter to extract caller info
        super().__init__(style='{')
        self._fmt = "%(asctime)s | %(levelname)-8s | %(module)s:%(lineno)-4d | %(message)s"
        self.datefmt = '%H:%M:%S.%f'

    def formatTime(self, record, datefmt=None):
        # Only show time, not date
        ct = self.converter(record.created)
        if datefmt:
            s = time.strftime(datefmt, ct)
            return s[:-3]  # Trim microseconds to 3 digits
        else:
            return time.strftime('%H:%M:%S', ct)

    def format(self, record):
        # Get the original caller's info
        if record.name == "logger":
            # Walk up the stack to find the real caller
            frame = logging.currentframe()
            while frame and frame.f_code.co_filename.endswith("logger.py"):
                frame = frame.f_back
            if frame:
                record.lineno = frame.f_lineno
                record.module = frame.f_code.co_filename.split("/")[-1].split(".")[0]

        # Format based on event type
        if hasattr(record, 'event_type'):
            message_parts = [
                f"{self.formatTime(record, self.datefmt)}",
                f"{record.levelname:<8}",
                f"{record.module}:{record.lineno:<4}",
                f"{record.event_type:<10}",
                f"{record.sender:<10}"
            ]

            if record.event_type == 'MESSAGE':
                message_parts.append(f"{record.content_type}")
                if hasattr(record, 'content'):
                    message_parts.append(f"| {record.content}")
            elif record.event_type == 'TOOL_USE':
                message_parts.extend([f"{record.tool_name:<10}", f"| {record.command}"])
            elif record.event_type == 'TOOL_RESULT':
                message_parts.append(f"{record.result_type:<10}")
                if hasattr(record, 'error'):
                    message_parts.append(f"| Error: {record.error}")
                elif hasattr(record, 'output'):
                    message_parts.append(f"| output: {record.output}")

            return " | ".join(message_parts)

        return super().format(record)

def setup_logger():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Create a daily rotating file handler with date in filename
    file_handler = TimedRotatingFileHandler(
        filename=log_dir / "mac_computer_use.log",
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