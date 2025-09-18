"""
Email sending functionality for Pydance framework.
"""

import asyncio
from typing import Optional, Dict, Any, List, Union
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formataddr, make_msgid
import os
from datetime import datetime

from .backends import EmailBackend


class EmailMessage:
    """Represents an email message"""

    def __init__(self,
                 subject: str = "",
                 body: str = "",
                 from_email: Optional[str] = None,
                 to: Optional[List[str]] = None,
                 cc: Optional[List[str]] = None,
                 bcc: Optional[List[str]] = None,
                 reply_to: Optional[str] = None,
                 headers: Optional[Dict[str, str]] = None,
                 attachments: Optional[List[Dict[str, Any]]] = None):
        self.subject = subject
        self.body = body
        self.from_email = from_email
        self.to = to or []
        self.cc = cc or []
        self.bcc = bcc or []
        self.reply_to = reply_to
        self.headers = headers or {}
        self.attachments = attachments or []
        self.html_body = None
        self.alternatives = []

    def set_html_body(self, html_body: str):
        """Set HTML body for the email"""
        self.html_body = html_body

    def add_alternative(self, content: str, content_type: str):
        """Add alternative content (e.g., plain text, HTML)"""
        self.alternatives.append((content, content_type))

    def attach(self, filename: str, content: bytes, mimetype: str = None):
        """Attach a file to the email"""
        attachment = {
            'filename': filename,
            'content': content,
            'mimetype': mimetype
        }
        self.attachments.append(attachment)

    def attach_file(self, filepath: str, mimetype: str = None):
        """Attach a file from filesystem"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File {filepath} does not exist")

        with open(filepath, 'rb') as f:
            content = f.read()

        filename = os.path.basename(filepath)
        self.attach(filename, content, mimetype)

    def get_recipients(self) -> List[str]:
        """Get all recipients (to, cc, bcc)"""
        return self.to + self.cc + self.bcc

    def to_mime_message(self) -> MIMEMultipart:
        """Convert to MIME message"""
        # Create message container
        if self.attachments or self.html_body or self.alternatives:
            msg = MIMEMultipart('mixed' if self.attachments else 'alternative')
        else:
            msg = MIMEMultipart('alternative')

        # Set basic headers
        msg['Subject'] = self.subject
        msg['From'] = self.from_email
        msg['To'] = ', '.join(self.to)
        if self.cc:
            msg['Cc'] = ', '.join(self.cc)
        if self.reply_to:
            msg['Reply-To'] = self.reply_to

        # Add custom headers
        for key, value in self.headers.items():
            msg[key] = value

        # Set Message-ID
        msg['Message-ID'] = make_msgid()

        # Add Date header
        msg['Date'] = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')

        # Create body parts
        body_parts = []

        # Add plain text body
        if self.body:
            text_part = MIMEText(self.body, 'plain', 'utf-8')
            body_parts.append(text_part)

        # Add HTML body
        if self.html_body:
            html_part = MIMEText(self.html_body, 'html', 'utf-8')
            body_parts.append(html_part)

        # Add alternatives
        for content, content_type in self.alternatives:
            subtype = content_type.split('/')[-1] if '/' in content_type else 'plain'
            alt_part = MIMEText(content, subtype, 'utf-8')
            alt_part['Content-Type'] = content_type
            body_parts.append(alt_part)

        # If no body parts, add empty plain text
        if not body_parts:
            text_part = MIMEText('', 'plain', 'utf-8')
            body_parts.append(text_part)

        # Attach body parts
        if len(body_parts) == 1:
            # Single part
            msg.attach(body_parts[0])
        else:
            # Multiple alternatives
            for part in body_parts:
                msg.attach(part)

        # Add attachments
        for attachment in self.attachments:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment['content'])

            if attachment.get('mimetype'):
                part['Content-Type'] = attachment['mimetype']

            encoders.encode_base64(part)
            part.add_header('Content-Disposition',
                          f'attachment; filename="{attachment["filename"]}"')
            msg.attach(part)

        return msg


class EmailTemplate:
    """Email template with subject and body templates"""

    def __init__(self,
                 subject_template: str,
                 body_template: str,
                 html_template: Optional[str] = None):
        self.subject_template = subject_template
        self.body_template = body_template
        self.html_template = html_template

    def render(self, context: Dict[str, Any]) -> EmailMessage:
        """Render template with context"""
        # Simple string formatting for now
        # In production, you might want to use Jinja2 or similar
        subject = self.subject_template.format(**context)
        body = self.body_template.format(**context)

        message = EmailMessage(subject=subject, body=body)

        if self.html_template:
            html_body = self.html_template.format(**context)
            message.set_html_body(html_body)

        return message


class Mail:
    """Main email sending class"""

    def __init__(self,
                 backend: EmailBackend,
                 default_from: Optional[str] = None,
                 fail_silently: bool = False):
        self.backend = backend
        self.default_from = default_from
        self.fail_silently = fail_silently
        self.templates: Dict[str, EmailTemplate] = {}

    def add_template(self, name: str, template: EmailTemplate):
        """Add an email template"""
        self.templates[name] = template

    def get_template(self, name: str) -> Optional[EmailTemplate]:
        """Get an email template by name"""
        return self.templates.get(name)

    async def send(self,
                   subject: str = "",
                   body: str = "",
                   from_email: Optional[str] = None,
                   to: Optional[List[str]] = None,
                   cc: Optional[List[str]] = None,
                   bcc: Optional[List[str]] = None,
                   reply_to: Optional[str] = None,
                   headers: Optional[Dict[str, str]] = None,
                   attachments: Optional[List[Dict[str, Any]]] = None,
                   html_body: Optional[str] = None) -> bool:
        """Send an email message"""
        try:
            # Create message
            message = EmailMessage(
                subject=subject,
                body=body,
                from_email=from_email or self.default_from,
                to=to,
                cc=cc,
                bcc=bcc,
                reply_to=reply_to,
                headers=headers,
                attachments=attachments
            )

            if html_body:
                message.set_html_body(html_body)

            # Send via backend
            return await self.backend.send(message)

        except Exception as e:
            if not self.fail_silently:
                raise
            print(f"Email sending failed: {e}")
            return False

    async def send_template(self,
                           template_name: str,
                           context: Dict[str, Any],
                           from_email: Optional[str] = None,
                           to: Optional[List[str]] = None,
                           cc: Optional[List[str]] = None,
                           bcc: Optional[List[str]] = None,
                           reply_to: Optional[str] = None,
                           headers: Optional[Dict[str, str]] = None,
                           attachments: Optional[List[Dict[str, Any]]] = None) -> bool:
        """Send email using a template"""
        template = self.get_template(template_name)
        if not template:
            if self.fail_silently:
                return False
            raise ValueError(f"Template '{template_name}' not found")

        try:
            # Render template
            message = template.render(context)

            # Override message properties
            if from_email or self.default_from:
                message.from_email = from_email or self.default_from
            if to:
                message.to = to
            if cc:
                message.cc = cc
            if bcc:
                message.bcc = bcc
            if reply_to:
                message.reply_to = reply_to
            if headers:
                message.headers.update(headers)
            if attachments:
                message.attachments.extend(attachments)

            # Send via backend
            return await self.backend.send(message)

        except Exception as e:
            if not self.fail_silently:
                raise
            print(f"Email sending failed: {e}")
            return False

    async def send_bulk(self, messages: List[EmailMessage]) -> List[bool]:
        """Send multiple email messages"""
        results = []
        for message in messages:
            try:
                result = await self.backend.send(message)
                results.append(result)
            except Exception as e:
                if not self.fail_silently:
                    raise
                print(f"Email sending failed: {e}")
                results.append(False)
        return results

    # Convenience methods for common email types

    async def send_welcome_email(self, user_email: str, user_name: str, **kwargs) -> bool:
        """Send welcome email to new user"""
        return await self.send_template(
            'welcome',
            {'user_name': user_name, 'user_email': user_email, **kwargs},
            to=[user_email]
        )

    async def send_password_reset_email(self, user_email: str, reset_token: str, **kwargs) -> bool:
        """Send password reset email"""
        return await self.send_template(
            'password_reset',
            {'reset_token': reset_token, 'user_email': user_email, **kwargs},
            to=[user_email]
        )

    async def send_email_verification(self, user_email: str, verification_token: str, **kwargs) -> bool:
        """Send email verification"""
        return await self.send_template(
            'email_verification',
            {'verification_token': verification_token, 'user_email': user_email, **kwargs},
            to=[user_email]
        )

    async def send_notification(self, user_email: str, subject: str, message: str, **kwargs) -> bool:
        """Send notification email"""
        return await self.send(
            subject=subject,
            body=message,
            to=[user_email],
            **kwargs
        )
