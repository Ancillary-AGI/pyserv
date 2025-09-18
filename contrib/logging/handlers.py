"""
Logging handlers for different output destinations.
"""

import logging
import logging.handlers
import sys
from typing import Optional


class ConsoleHandler(logging.StreamHandler):
    """Console logging handler"""

    def __init__(self, stream=None):
        if stream is None:
            stream = sys.stdout
        super().__init__(stream)


class FileHandler(logging.FileHandler):
    """File logging handler"""

    def __init__(self, filename: str, mode: str = 'a', encoding: Optional[str] = None):
        super().__init__(filename, mode, encoding)


class RotatingFileHandler(logging.handlers.RotatingFileHandler):
    """Rotating file handler"""

    def __init__(self, filename: str, mode: str = 'a', maxBytes: int = 0,
                 backupCount: int = 0, encoding: Optional[str] = None):
        super().__init__(filename, mode, maxBytes, backupCount, encoding)


class SyslogHandler(logging.handlers.SysLogHandler):
    """Syslog handler"""

    def __init__(self, address=('localhost', 514), facility=logging.handlers.SysLogHandler.LOG_USER):
        super().__init__(address, facility)
