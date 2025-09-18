"""
Logging formatters for structured output.
"""

import json
import logging
from typing import Dict, Any
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        # Get structured data from record
        structured_data = getattr(record, 'structured_data', {})

        # Create log entry
        log_entry = {
            'timestamp': structured_data.get('timestamp', datetime.utcnow().isoformat()),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'thread_id': structured_data.get('thread_id'),
            'thread_name': structured_data.get('thread_name'),
        }

        # Add any extra structured data
        for key, value in structured_data.items():
            if key not in log_entry:
                log_entry[key] = value

        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


class StructuredFormatter(logging.Formatter):
    """Human-readable structured formatter"""

    def __init__(self, fmt=None, datefmt=None):
        if fmt is None:
            fmt = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        super().__init__(fmt, datefmt)

    def format(self, record: logging.LogRecord) -> str:
        # Get structured data
        structured_data = getattr(record, 'structured_data', {})

        # Format the basic message
        message = super().format(record)

        # Add structured data as key=value pairs
        extra_parts = []
        for key, value in structured_data.items():
            if key not in ['timestamp', 'logger_name', 'thread_id', 'thread_name']:
                extra_parts.append(f"{key}={value}")

        if extra_parts:
            message += f" {{{', '.join(extra_parts)}}}"

        return message


class ColoredFormatter(logging.Formatter):
    """Colored console formatter"""

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'

    def __init__(self, fmt=None, datefmt=None):
        if fmt is None:
            fmt = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        super().__init__(fmt, datefmt)

    def format(self, record: logging.LogRecord) -> str:
        # Color the level name
        levelname = record.levelname
        if levelname in self.COLORS:
            colored_level = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
            record.levelname = colored_level

        # Format the message
        message = super().format(record)

        # Reset levelname
        record.levelname = levelname

        return message
