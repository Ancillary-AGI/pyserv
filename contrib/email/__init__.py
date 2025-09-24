"""
Email sending functionality for Pyserv  framework.
"""

from .mail import Mail, EmailMessage, EmailTemplate
from .backends import SMTPBackend, ConsoleBackend, FileBackend
from .templates import EmailTemplateEngine

__all__ = [
    'Mail',
    'EmailMessage',
    'EmailTemplate',
    'SMTPBackend',
    'ConsoleBackend',
    'FileBackend',
    'EmailTemplateEngine',
]




