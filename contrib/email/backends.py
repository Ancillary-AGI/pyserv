"""
Email backend implementations for different email sending methods.
"""

import asyncio
import smtplib
import ssl
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart

from .mail import EmailMessage


class EmailBackend(ABC):
    """Abstract base class for email backends"""

    @abstractmethod
    async def send(self, message: EmailMessage) -> bool:
        """Send an email message"""
        pass

    @abstractmethod
    async def close(self):
        """Close the backend connection"""
        pass


class SMTPBackend(EmailBackend):
    """SMTP email backend"""

    def __init__(self,
                 host: str = 'localhost',
                 port: int = 587,
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 use_tls: bool = True,
                 use_ssl: bool = False,
                 timeout: int = 30,
                 **kwargs):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.timeout = timeout
        self.connection = None

    async def send(self, message: EmailMessage) -> bool:
        """Send email via SMTP"""
        try:
            # Convert to MIME message
            mime_message = message.to_mime_message()

            # Get recipients
            recipients = message.get_recipients()
            if not recipients:
                return False

            # Create SMTP connection
            if self.use_ssl:
                smtp_class = smtplib.SMTP_SSL
            else:
                smtp_class = smtplib.SMTP

            server = smtp_class(self.host, self.port, timeout=self.timeout)

            try:
                # Start TLS if requested
                if self.use_tls and not self.use_ssl:
                    server.starttls()

                # Login if credentials provided
                if self.username and self.password:
                    server.login(self.username, self.password)

                # Send message
                server.sendmail(
                    message.from_email,
                    recipients,
                    mime_message.as_string()
                )

                return True

            finally:
                server.quit()

        except Exception as e:
            print(f"SMTP sending failed: {e}")
            return False

    async def close(self):
        """Close SMTP connection"""
        if self.connection:
            try:
                self.connection.quit()
            except:
                pass
            self.connection = None


class ConsoleBackend(EmailBackend):
    """Console email backend for development/testing"""

    def __init__(self, output_file: Optional[str] = None, **kwargs):
        self.output_file = output_file

    async def send(self, message: EmailMessage) -> bool:
        """Print email to console or file"""
        try:
            # Format email for display
            output = self._format_email(message)

            if self.output_file:
                # Write to file
                with open(self.output_file, 'a', encoding='utf-8') as f:
                    f.write(output + '\n' + '='*80 + '\n')
            else:
                # Print to console
                print(output)
                print('='*80)

            return True

        except Exception as e:
            print(f"Console backend failed: {e}")
            return False

    def _format_email(self, message: EmailMessage) -> str:
        """Format email message for display"""
        lines = []

        lines.append(f"From: {message.from_email}")
        lines.append(f"To: {', '.join(message.to)}")
        if message.cc:
            lines.append(f"Cc: {', '.join(message.cc)}")
        if message.bcc:
            lines.append(f"Bcc: {', '.join(message.bcc)}")
        if message.reply_to:
            lines.append(f"Reply-To: {message.reply_to}")
        lines.append(f"Subject: {message.subject}")
        lines.append("")

        if message.body:
            lines.append("Body (plain text):")
            lines.append("-" * 40)
            lines.append(message.body)

        if message.html_body:
            lines.append("")
            lines.append("Body (HTML):")
            lines.append("-" * 40)
            lines.append(message.html_body)

        if message.attachments:
            lines.append("")
            lines.append("Attachments:")
            for attachment in message.attachments:
                lines.append(f"  - {attachment['filename']} ({len(attachment['content'])} bytes)")

        return '\n'.join(lines)

    async def close(self):
        """No-op for console backend"""
        pass


class FileBackend(EmailBackend):
    """File-based email backend for testing"""

    def __init__(self, directory: str = 'emails', **kwargs):
        self.directory = directory
        import os
        os.makedirs(directory, exist_ok=True)

    async def send(self, message: EmailMessage) -> bool:
        """Save email to file"""
        try:
            import os
            from datetime import datetime

            # Generate filename
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
            filename = f"{timestamp}_{hash(message.subject) % 10000}.eml"
            filepath = os.path.join(self.directory, filename)

            # Convert to MIME and save
            mime_message = message.to_mime_message()

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(mime_message.as_string())

            return True

        except Exception as e:
            print(f"File backend failed: {e}")
            return False

    async def close(self):
        """No-op for file backend"""
        pass


class AsyncSMTPBackend(SMTPBackend):
    """Async version of SMTP backend using aiosmtplib"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        import aiosmtplib
        self.aiosmtplib = aiosmtplib

    async def send(self, message: EmailMessage) -> bool:
        """Send email asynchronously via SMTP"""
        try:
            # Convert to MIME message
            mime_message = message.to_mime_message()

            # Get recipients
            recipients = message.get_recipients()
            if not recipients:
                return False

            # Send using aiosmtplib
            await self.aiosmtplib.send(
                mime_message,
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                use_tls=self.use_tls,
                start_tls=not self.use_ssl,
                timeout=self.timeout
            )

            return True

        except Exception as e:
            print(f"Async SMTP sending failed: {e}")
            return False
