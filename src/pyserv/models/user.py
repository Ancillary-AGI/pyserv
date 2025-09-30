from typing import Optional, Dict, Any, ClassVar
from datetime import datetime, timezone
from enum import Enum
import hashlib
import bcrypt
import re
from email_validator import validate_email, EmailNotValidError

from pyserv.models.base import (
    BaseModel, StringField, EmailField, BooleanField, DateTimeField,
    IntegerField, UUIDField, EnumField, RelationshipType
)

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"
    EDITOR = "editor"
    VIEWER = "viewer"

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"

class BaseUser(BaseModel):
    """Enhanced base user model with comprehensive authentication and profile features"""
    
    _table_name = "users"
    
    id = UUIDField(primary_key=True)
    email = EmailField(unique=True, nullable=False, max_length=255)
    username = StringField(unique=True, nullable=False, max_length=50, pattern=r'^[a-zA-Z0-9_]{3,50}$')
    
    def __post_init__(self):
        super().__post_init__()
        # Ensure USERNAME_FIELD is unique
        if hasattr(self, self.USERNAME_FIELD):
            field = getattr(self.__class__, self.USERNAME_FIELD)
            if hasattr(field, 'unique'):
                field.unique = True
    password_hash = StringField(nullable=False, max_length=255)
    first_name = StringField(max_length=100, nullable=True)
    last_name = StringField(max_length=100, nullable=True)
    display_name = StringField(max_length=150, nullable=True)
    avatar_url = StringField(max_length=500, nullable=True)
    phone_number = StringField(max_length=20, nullable=True)
    date_of_birth = DateTimeField(nullable=True)
    timezone = StringField(max_length=50, default="UTC")
    locale = StringField(max_length=10, default="en-US")
    is_active = BooleanField(default=True)
    is_verified = BooleanField(default=False)
    is_superuser = BooleanField(default=False)
    is_staff = BooleanField(default=False)
    role = EnumField(UserRole, default=UserRole.USER)
    status = EnumField(UserStatus, default=UserStatus.PENDING)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    last_login = DateTimeField(nullable=True)
    last_activity = DateTimeField(nullable=True)
    login_count = IntegerField(default=0)
    failed_login_attempts = IntegerField(default=0)
    password_changed_at = DateTimeField(nullable=True)
    email_verified_at = DateTimeField(nullable=True)
    phone_verified_at = DateTimeField(nullable=True)
    terms_accepted_at = DateTimeField(nullable=True)
    privacy_policy_accepted_at = DateTimeField(nullable=True)
    two_factor_enabled = BooleanField(default=False)
    two_factor_secret = StringField(max_length=255, nullable=True)
    recovery_codes = StringField(max_length=1000, nullable=True)

    # Authentication configuration
    USERNAME_FIELD: ClassVar[str] = 'email'  # Default authentication field
    
    # Add metadata field for storing additional user data
    metadata = StringField(nullable=True)
    
    # Password hashing configuration
    _password_hash_algorithm: ClassVar[str] = "bcrypt"
    _password_hash_rounds: ClassVar[int] = 12
    _min_password_length: ClassVar[int] = 8
    _password_require_special: ClassVar[bool] = True
    _password_require_numbers: ClassVar[bool] = True
    _password_require_uppercase: ClassVar[bool] = True

    @classmethod
    def hash_password(cls, password: str) -> str:
        """Hash password using configured algorithm"""
        if cls._password_hash_algorithm == "bcrypt":
            salt = bcrypt.gensalt(rounds=cls._password_hash_rounds)
            return bcrypt.hashpw(password.encode(), salt).decode()
        elif cls._password_hash_algorithm == "sha3_256":
            return hashlib.sha3_256(password.encode()).hexdigest()
        else:
            from pyserv.exceptions import ConfigurationError
            raise ConfigurationError(f"Unsupported hash algorithm: {cls._password_hash_algorithm}")

    @classmethod
    def verify_password_hash(cls, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        if cls._password_hash_algorithm == "bcrypt":
            return bcrypt.checkpw(password.encode(), password_hash.encode())
        elif cls._password_hash_algorithm == "sha256":
            return hashlib.sha256(password.encode()).hexdigest() == password_hash
        return False

    @classmethod
    def validate_password_strength(cls, password: str) -> Dict[str, bool]:
        """Validate password strength"""
        return {
            'length': len(password) >= cls._min_password_length,
            'special': not cls._password_require_special or bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password)),
            'numbers': not cls._password_require_numbers or bool(re.search(r'\d', password)),
            'uppercase': not cls._password_require_uppercase or bool(re.search(r'[A-Z]', password)),
        }

    @classmethod
    def is_password_strong(cls, password: str) -> bool:
        """Check if password meets all strength requirements"""
        validation = cls.validate_password_strength(password)
        return all(validation.values())

    @classmethod
    async def authenticate(cls, identifier: str, password: str) -> Optional['BaseUser']:
        """Authenticate user using USERNAME_FIELD"""
        # Use the configured USERNAME_FIELD for authentication
        filter_kwargs = {cls.USERNAME_FIELD: identifier, 'is_active': True}
        user = await cls.query().filter(**filter_kwargs).first()
        
        if user and cls.verify_password_hash(password, user.password_hash):
            await user.update_login_info()
            return user
        
        if user:
            await user.increment_failed_login_attempts()
            
        return None

    @classmethod
    async def create_user(
        cls,
        email: str,
        username: str,
        password: str,
        role: UserRole = UserRole.USER,
        status: UserStatus = UserStatus.PENDING,
        **kwargs
    ) -> 'BaseUser':
        """Create a new user with hashed password and validation"""
        
        # Validate email format
        try:
            validate_email(email)
        except EmailNotValidError:
            from pyserv.exceptions import InvalidEmailFormat
            raise InvalidEmailFormat(email)
        
        # Validate username format
        if not re.match(r'^[a-zA-Z0-9_]{3,50}$', username):
            from pyserv.exceptions import InvalidUsernameFormat
            raise InvalidUsernameFormat(username)

        # Validate password strength
        if not cls.is_password_strong(password):
            from pyserv.exceptions import PasswordTooWeak
            raise PasswordTooWeak()

        # Check for existing user
        existing_email = await cls.query().filter(email=email).first()
        if existing_email:
            from pyserv.exceptions import UserAlreadyExists
            raise UserAlreadyExists(email)
        
        existing_username = await cls.query().filter(username=username).first()
        if existing_username:
            from pyserv.exceptions import UserAlreadyExists
            raise UserAlreadyExists(username)
        
        # Hash password
        password_hash = cls.hash_password(password)
        
        # Set timestamps
        now = datetime.now(timezone.utc)
        
        # Create user data
        user_data = {
            'email': email,
            'username': username,
            'password_hash': password_hash,
            'role': role,
            'status': status,
            'created_at': now,
            'updated_at': now,
            'password_changed_at': now,
            **kwargs
        }
        
        return await cls.create(**user_data)
    
    async def update_login_info(self):
        """Update login information"""
        now = datetime.now(timezone.utc)
        self.last_login = now
        self.last_activity = now
        self.login_count += 1
        self.failed_login_attempts = 0
        await self.save()
    
    async def increment_failed_login_attempts(self):
        """Increment failed login attempts"""
        self.failed_login_attempts += 1
        await self.save()
    
    def set_password(self, password: str):
        """Set user password"""
        if not self.is_password_strong(password):
            from pyserv.exceptions import PasswordTooWeak
            raise PasswordTooWeak('Password does not meet strength requirements')
        
        self.password_hash = self.hash_password(password)
        self.password_changed_at = datetime.now(timezone.utc)
    
    def check_password(self, password: str) -> bool:
        """Check if password is correct"""
        return self.verify_password_hash(password, self.password_hash)
    
    def get_full_name(self) -> str:
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.display_name or self.username
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return self.is_active and self.status == UserStatus.ACTIVE
    
    def __str__(self):
        return f"{self.full_name} ({self.email})"
    
    def __repr__(self):
        return f"<User {self.id}: {self.email}>"
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        if self.is_superuser:
            return True
        return False
    
    def can_access_admin(self) -> bool:
        """Check if user can access admin interface"""
        return self.is_staff or self.is_superuser
    
    @classmethod
    async def find(cls, id_value: Any) -> Optional['BaseUser']:
        """Find user by ID"""
        return await cls.query().filter(id=id_value).first()
    
    async def verify_email(self):
        """Mark email as verified"""
        self.is_verified = True
        self.email_verified_at = datetime.now(timezone.utc)
        if self.status == UserStatus.PENDING:
            self.status = UserStatus.ACTIVE
        await self.save()
    
    async def verify_phone(self):
        """Mark phone number as verified"""
        self.phone_verified_at = datetime.now(timezone.utc)
        await self.save()
    
    async def accept_terms(self):
        """Mark terms and conditions as accepted"""
        now = datetime.now(timezone.utc)
        self.terms_accepted_at = now
        self.privacy_policy_accepted_at = now
        await self.save()
    
    async def activate(self):
        """Activate user account"""
        self.is_active = True
        self.status = UserStatus.ACTIVE
        await self.save()
    
    async def deactivate(self):
        """Deactivate user account"""
        self.is_active = False
        self.status = UserStatus.INACTIVE
        await self.save()
    
    @property
    def full_name(self) -> str:
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username or self.email.split('@')[0]
    
    @property
    def initials(self) -> str:
        """Get user's initials"""
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        elif self.username:
            return self.username[:2].upper()
        else:
            return self.email[:2].upper()
    
    @property
    def requires_password_change(self) -> bool:
        """Check if password needs to be changed (e.g., after 90 days)"""
        if not self.password_changed_at:
            return False
        days_since_change = (datetime.now(timezone.utc) - self.password_changed_at).days
        return days_since_change >= 90
    
    @property
    def is_locked_out(self) -> bool:
        """Check if account is locked due to too many failed attempts"""
        return (self.failed_login_attempts or 0) >= 5
    
    async def change_password(self, new_password: str, old_password: Optional[str] = None):
        """Change user password with optional old password verification"""
        if old_password and not self.check_password(old_password):
            from pyserv.exceptions import InvalidCredentials
            raise InvalidCredentials("Current password is incorrect")
        
        if not self.is_password_strong(new_password):
            from pyserv.exceptions import PasswordTooWeak
            raise PasswordTooWeak()
        
        self.password_hash = self.hash_password(new_password)
        self.password_changed_at = datetime.now(timezone.utc)
        self.failed_login_attempts = 0
        await self.save()
    
    async def suspend(self, reason: Optional[str] = None):
        """Suspend user account"""
        self.is_active = False
        self.status = UserStatus.SUSPENDED
        if reason:
            self.metadata = self.metadata or {}
            if isinstance(self.metadata, str):
                import json
                self.metadata = json.loads(self.metadata) if self.metadata else {}
            self.metadata['suspension_reason'] = reason
        await self.save(update_fields=['is_active', 'status', 'metadata', 'updated_at'])
    
    def verify_password(self, password: str) -> bool:
        """Verify if password matches hash"""
        return self.verify_password_hash(password, self.password_hash)
    
    async def get_permissions(self) -> List[str]:
        """Get user permissions (cached)"""
        base_permissions = ["view_profile", "edit_profile"]
        
        if self.role == UserRole.ADMIN:
            base_permissions.extend(["manage_users", "manage_content", "view_reports"])
        elif self.role == UserRole.MODERATOR:
            base_permissions.extend(["moderate_content", "view_reports"])
        elif self.role == UserRole.EDITOR:
            base_permissions.extend(["create_content", "edit_content"])
            
        return base_permissions
    
    def ip(self, request=None) -> Optional[str]:
        """Get user's IP address from request or stored data"""
        if request:
            # Try various headers for IP detection
            ip = (
                request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or
                request.headers.get('X-Real-IP') or
                request.headers.get('CF-Connecting-IP') or
                getattr(request, 'client_ip', None) or
                getattr(request, 'remote_addr', None)
            )
            return ip if ip else None

        # Return stored IP from metadata if available
        if self.metadata and isinstance(self.metadata, dict):
            return self.metadata.get('last_ip')
        return None
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert to dictionary with optional sensitive fields"""
        base_data = {
            "id": str(self.id) if self.id else None,
            "email": self.email,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "display_name": self.display_name,
            "full_name": self.full_name,
            "initials": self.initials,
            "avatar_url": self.avatar_url,
            "phone_number": self.phone_number,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "role": self.role.value if self.role else None,
            "status": self.status.value if self.status else None,
            "timezone": self.timezone,
            "locale": self.locale,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "login_count": self.login_count,
        }
        
        if include_sensitive:
            sensitive_data = {
                "is_superuser": self.is_superuser,
                "is_staff": self.is_staff,
                "two_factor_enabled": self.two_factor_enabled,
                "email_verified_at": self.email_verified_at.isoformat() if self.email_verified_at else None,
                "phone_verified_at": self.phone_verified_at.isoformat() if self.phone_verified_at else None,
                "failed_login_attempts": self.failed_login_attempts,
                "requires_password_change": self.requires_password_change,
                "is_locked_out": self.is_locked_out,
            }
            base_data.update(sensitive_data)
        
        return base_data