"""
Structured logging system for Pyserv  framework.
"""

import logging
import json
import sys
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from .formatters import JSONFormatter, StructuredFormatter, ColoredFormatter
from .handlers import ConsoleHandler, FileHandler


class Logger:
    """Structured logger with context support"""

    def __init__(self,
                 name: str,
                 level: int = logging.INFO,
                 handlers: Optional[List[logging.Handler]] = None,
                 context: Optional[Dict[str, Any]] = None):
        self.name = name
        self.level = level
        self.context = context or {}
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)

        # Remove existing handlers to avoid duplicates
        for handler in self._logger.handlers[:]:
            self._logger.removeHandler(handler)

        # Add handlers
        if handlers:
            for handler in handlers:
                self._logger.addHandler(handler)
        else:
            # Default console handler
            console_handler = ConsoleHandler()
            console_handler.setFormatter(StructuredFormatter())
            self._logger.addHandler(console_handler)

    def _log(self, level: int, message: str, extra: Optional[Dict[str, Any]] = None, exc_info=None):
        """Internal logging method"""
        # Merge context with extra data
        log_data = {**self.context}
        if extra:
            log_data.update(extra)

        # Add timestamp and thread info
        log_data.update({
            'timestamp': datetime.utcnow().isoformat(),
            'thread_id': threading.get_ident(),
            'thread_name': threading.current_thread().name,
            'logger_name': self.name,
        })

        self._logger.log(level, message, extra={'structured_data': log_data}, exc_info=exc_info)

    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log debug message"""
        self._log(logging.DEBUG, message, extra)

    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log info message"""
        self._log(logging.INFO, message, extra)

    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log warning message"""
        self._log(logging.WARNING, message, extra)

    def error(self, message: str, extra: Optional[Dict[str, Any]] = None, exc_info=None):
        """Log error message"""
        self._log(logging.ERROR, message, extra, exc_info=exc_info)

    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None, exc_info=None):
        """Log critical message"""
        self._log(logging.CRITICAL, message, extra, exc_info=exc_info)

    def exception(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log exception with traceback"""
        self._log(logging.ERROR, message, extra, exc_info=True)

    def add_context(self, **kwargs):
        """Add context data to all future log messages"""
        self.context.update(kwargs)

    def remove_context(self, *keys):
        """Remove context keys"""
        for key in keys:
            self.context.pop(key, None)

    def bind(self, **kwargs) -> 'Logger':
        """Create a new logger instance with additional context"""
        new_context = {**self.context, **kwargs}
        return Logger(self.name, self.level, self._logger.handlers[:], new_context)


# Global logger registry
_loggers: Dict[str, Logger] = {}
_default_config = {
    'level': 'INFO',
    'format': 'structured',
    'handlers': ['console'],
    'file_path': None,
    'max_file_size': 10 * 1024 * 1024,  # 10MB
    'backup_count': 5,
}


def configure_logging(config: Optional[Dict[str, Any]] = None):
    """Configure global logging settings"""
    global _default_config
    if config:
        _default_config.update(config)

    # Clear existing loggers
    _loggers.clear()

    # Configure Python logging
    logging.basicConfig(level=getattr(logging, _default_config['level']))

    # Create default logger
    get_logger('app')


def get_logger(name: str, context: Optional[Dict[str, Any]] = None) -> Logger:
    """Get or create a logger instance"""
    if name not in _loggers:
        # Create handlers based on config
        handlers = []

        if 'console' in _default_config['handlers']:
            console_handler = ConsoleHandler()

            if _default_config['format'] == 'json':
                console_handler.setFormatter(JSONFormatter())
            elif _default_config['format'] == 'colored':
                console_handler.setFormatter(ColoredFormatter())
            else:
                console_handler.setFormatter(StructuredFormatter())

            handlers.append(console_handler)

        if 'file' in _default_config['handlers'] and _default_config['file_path']:
            from .handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                _default_config['file_path'],
                maxBytes=_default_config['max_file_size'],
                backupCount=_default_config['backup_count']
            )

            if _default_config['format'] == 'json':
                file_handler.setFormatter(JSONFormatter())
            else:
                file_handler.setFormatter(StructuredFormatter())

            handlers.append(file_handler)

        level = getattr(logging, _default_config['level'])
        _loggers[name] = Logger(name, level, handlers, context)

    logger = _loggers[name]
    if context:
        logger = logger.bind(**context)

    return logger


# Convenience functions
def debug(message: str, extra: Optional[Dict[str, Any]] = None, logger_name: str = 'app'):
    """Log debug message"""
    get_logger(logger_name).debug(message, extra)


def info(message: str, extra: Optional[Dict[str, Any]] = None, logger_name: str = 'app'):
    """Log info message"""
    get_logger(logger_name).info(message, extra)


def warning(message: str, extra: Optional[Dict[str, Any]] = None, logger_name: str = 'app'):
    """Log warning message"""
    get_logger(logger_name).warning(message, extra)


def error(message: str, extra: Optional[Dict[str, Any]] = None, logger_name: str = 'app', exc_info=None):
    """Log error message"""
    get_logger(logger_name).error(message, extra, exc_info=exc_info)


def critical(message: str, extra: Optional[Dict[str, Any]] = None, logger_name: str = 'app', exc_info=None):
    """Log critical message"""
    get_logger(logger_name).critical(message, extra, exc_info=exc_info)


def exception(message: str, extra: Optional[Dict[str, Any]] = None, logger_name: str = 'app'):
    """Log exception"""
    get_logger(logger_name).exception(message, extra)




