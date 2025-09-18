"""
Authentication forms for login, registration, and password reset.
"""

from typing import Optional, Dict, Any

from ...widgets import TextWidget, PasswordWidget, EmailWidget, ButtonWidget
from ...widgets.forms import Form


class LoginForm(Form):
    """Login form with email/username and password fields"""

    def __init__(self, action: str = "/auth/login", method: str = "POST", **kwargs):
        super().__init__(action=action, method=method, **kwargs)

        # Add fields
        self.add_field("identifier", TextWidget(
            name="identifier",
            label="Email or Username",
            placeholder="Enter your email or username",
            required=True
        ))

        self.add_field("password", PasswordWidget(
            name="password",
            label="Password",
            placeholder="Enter your password",
            required=True
        ))

        self.add_field("remember_me", self.create_checkbox(
            name="remember_me",
            label="Remember me"
        ))

        self.add_field("submit", ButtonWidget(
            name="submit",
            label="Sign In",
            button_type="submit",
            css_class="btn btn-primary"
        ))

    def create_checkbox(self, name: str, label: str, **kwargs) -> 'CheckboxWidget':
        """Create a checkbox widget"""
        from ...widgets import CheckboxWidget
        return CheckboxWidget(name=name, label=label, **kwargs)

    async def validate(self, data: Dict[str, Any]) -> bool:
        """Validate form data"""
        if not await super().validate(data):
            return False

        # Additional validation logic can be added here
        identifier = data.get('identifier', '').strip()
        password = data.get('password', '')

        if not identifier:
            self.add_error('identifier', 'Email or username is required')
            return False

        if not password:
            self.add_error('password', 'Password is required')
            return False

        return True


class RegisterForm(Form):
    """User registration form"""

    def __init__(self, action: str = "/auth/register", method: str = "POST", **kwargs):
        super().__init__(action=action, method=method, **kwargs)

        # Add fields
        self.add_field("email", EmailWidget(
            name="email",
            label="Email Address",
            placeholder="Enter your email address",
            required=True
        ))

        self.add_field("username", TextWidget(
            name="username",
            label="Username",
            placeholder="Choose a username",
            required=True,
            pattern=r'^[a-zA-Z0-9_]{3,50}$',
            title="Username must be 3-50 characters, letters, numbers, and underscores only"
        ))

        self.add_field("first_name", TextWidget(
            name="first_name",
            label="First Name",
            placeholder="Enter your first name",
            required=False
        ))

        self.add_field("last_name", TextWidget(
            name="last_name",
            label="Last Name",
            placeholder="Enter your last name",
            required=False
        ))

        self.add_field("password", PasswordWidget(
            name="password",
            label="Password",
            placeholder="Create a password",
            required=True,
            min_length=8
        ))

        self.add_field("password_confirm", PasswordWidget(
            name="password_confirm",
            label="Confirm Password",
            placeholder="Confirm your password",
            required=True
        ))

        self.add_field("terms_accepted", self.create_checkbox(
            name="terms_accepted",
            label="I accept the Terms and Conditions",
            required=True
        ))

        self.add_field("privacy_accepted", self.create_checkbox(
            name="privacy_accepted",
            label="I accept the Privacy Policy",
            required=True
        ))

        self.add_field("submit", ButtonWidget(
            name="submit",
            label="Create Account",
            button_type="submit",
            css_class="btn btn-success"
        ))

    def create_checkbox(self, name: str, label: str, **kwargs) -> 'CheckboxWidget':
        """Create a checkbox widget"""
        from ...widgets import CheckboxWidget
        return CheckboxWidget(name=name, label=label, **kwargs)

    async def validate(self, data: Dict[str, Any]) -> bool:
        """Validate form data"""
        if not await super().validate(data):
            return False

        # Check password confirmation
        password = data.get('password', '')
        password_confirm = data.get('password_confirm', '')

        if password != password_confirm:
            self.add_error('password_confirm', 'Passwords do not match')
            return False

        # Additional validation can be added here
        return True


class PasswordResetForm(Form):
    """Password reset request form"""

    def __init__(self, action: str = "/auth/reset-password", method: str = "POST", **kwargs):
        super().__init__(action=action, method=method, **kwargs)

        # Add fields
        self.add_field("email", EmailWidget(
            name="email",
            label="Email Address",
            placeholder="Enter your email address",
            required=True
        ))

        self.add_field("submit", ButtonWidget(
            name="submit",
            label="Send Reset Link",
            button_type="submit",
            css_class="btn btn-primary"
        ))

    async def validate(self, data: Dict[str, Any]) -> bool:
        """Validate form data"""
        if not await super().validate(data):
            return False

        # Additional validation logic can be added here
        return True


class PasswordChangeForm(Form):
    """Password change form for authenticated users"""

    def __init__(self, action: str = "/auth/change-password", method: str = "POST", **kwargs):
        super().__init__(action=action, method=method, **kwargs)

        # Add fields
        self.add_field("current_password", PasswordWidget(
            name="current_password",
            label="Current Password",
            placeholder="Enter your current password",
            required=True
        ))

        self.add_field("new_password", PasswordWidget(
            name="new_password",
            label="New Password",
            placeholder="Enter your new password",
            required=True,
            min_length=8
        ))

        self.add_field("new_password_confirm", PasswordWidget(
            name="new_password_confirm",
            label="Confirm New Password",
            placeholder="Confirm your new password",
            required=True
        ))

        self.add_field("submit", ButtonWidget(
            name="submit",
            label="Change Password",
            button_type="submit",
            css_class="btn btn-primary"
        ))

    async def validate(self, data: Dict[str, Any]) -> bool:
        """Validate form data"""
        if not await super().validate(data):
            return False

        # Check password confirmation
        new_password = data.get('new_password', '')
        new_password_confirm = data.get('new_password_confirm', '')

        if new_password != new_password_confirm:
            self.add_error('new_password_confirm', 'Passwords do not match')
            return False

        # Additional validation can be added here
        return True


class ProfileUpdateForm(Form):
    """User profile update form"""

    def __init__(self, action: str = "/auth/profile", method: str = "POST", **kwargs):
        super().__init__(action=action, method=method, **kwargs)

        # Add fields
        self.add_field("first_name", TextWidget(
            name="first_name",
            label="First Name",
            placeholder="Enter your first name",
            required=False
        ))

        self.add_field("last_name", TextWidget(
            name="last_name",
            label="Last Name",
            placeholder="Enter your last name",
            required=False
        ))

        self.add_field("display_name", TextWidget(
            name="display_name",
            label="Display Name",
            placeholder="How you want to be displayed",
            required=False
        ))

        self.add_field("phone_number", TextWidget(
            name="phone_number",
            label="Phone Number",
            placeholder="Enter your phone number",
            required=False,
            type="tel"
        ))

        self.add_field("timezone", self.create_select(
            name="timezone",
            label="Timezone",
            options=[
                ("UTC", "UTC"),
                ("America/New_York", "Eastern Time"),
                ("America/Chicago", "Central Time"),
                ("America/Denver", "Mountain Time"),
                ("America/Los_Angeles", "Pacific Time"),
                ("Europe/London", "London"),
                ("Europe/Paris", "Paris"),
                ("Asia/Tokyo", "Tokyo"),
            ],
            required=False
        ))

        self.add_field("locale", self.create_select(
            name="locale",
            label="Language",
            options=[
                ("en-US", "English (US)"),
                ("en-GB", "English (UK)"),
                ("es-ES", "Spanish"),
                ("fr-FR", "French"),
                ("de-DE", "German"),
                ("ja-JP", "Japanese"),
            ],
            required=False
        ))

        self.add_field("submit", ButtonWidget(
            name="submit",
            label="Update Profile",
            button_type="submit",
            css_class="btn btn-primary"
        ))

    def create_select(self, name: str, label: str, options: list, **kwargs) -> 'SelectWidget':
        """Create a select widget"""
        from ...widgets import SelectWidget
        return SelectWidget(name=name, label=label, options=options, **kwargs)

    async def validate(self, data: Dict[str, Any]) -> bool:
        """Validate form data"""
        if not await super().validate(data):
            return False

        # Additional validation can be added here
        return True
