import uuid
from typing import Optional, List, Dict, Any, Type, ClassVar, Union
from datetime import datetime, timezone
from enum import Enum
import hashlib
import bcrypt
import re
from email_validator import validate_email, EmailNotValidError

from .base import BaseModel, ModelFactory
from ..utils.types import (
    Field, StringField, EmailField, BooleanField, DateTimeField, 
    IntegerField, UUIDField, PasswordField, EnumField, Relationship,
    ForeignKeyField
)
from ..utils.types import FieldType, RelationshipType

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
    _columns: ClassVar[Dict[str, Field]] = {
        'id': UUIDField(primary_key=True),
        'email': EmailField(unique=True, nullable=False, index=True, max_length=255),
        'username': StringField(unique=True, nullable=False, index=True, max_length=50, 
                               pattern=r'^[a-zA-Z0-9_]{3,50}$'),
        'password_hash': StringField(nullable=False, max_length=255),
        'first_name': StringField(max_length=100, nullable=True),
        'last_name': StringField(max_length=100, nullable=True),
        'display_name': StringField(max_length=150, nullable=True),
        'avatar_url': StringField(max_length=500, nullable=True),
        'phone_number': StringField(max_length=20, nullable=True),
        'date_of_birth': DateTimeField(nullable=True),
        'timezone': StringField(max_length=50, default="UTC"),
        'locale': StringField(max_length=10, default="en-US"),
        'is_active': BooleanField(default=True),
        'is_verified': BooleanField(default=False),
        'is_superuser': BooleanField(default=False),
        'is_staff': BooleanField(default=False),
        'role': EnumField(UserRole, default=UserRole.USER),
        'status': EnumField(UserStatus, default=UserStatus.PENDING),
        'created_at': DateTimeField(auto_now_add=True),
        'updated_at': DateTimeField(auto_now=True),
        'last_login': DateTimeField(nullable=True),
        'last_activity': DateTimeField(nullable=True),
        'login_count': IntegerField(default=0),
        'failed_login_attempts': IntegerField(default=0),
        'password_changed_at': DateTimeField(nullable=True),
        'email_verified_at': DateTimeField(nullable=True),
        'phone_verified_at': DateTimeField(nullable=True),
        'terms_accepted_at': DateTimeField(nullable=True),
        'privacy_policy_accepted_at': DateTimeField(nullable=True),
        'two_factor_enabled': BooleanField(default=False),
        'two_factor_secret': StringField(max_length=255, nullable=True),
        'recovery_codes': StringField(max_length=1000, nullable=True),
        'metadata': StringField(field_type=FieldType.JSON, nullable=True),
    }

    _relationships: ClassVar[Dict[str, Relationship]] = {
        'sessions': Relationship('UserSession', RelationshipType.ONE_TO_MANY, 
                                foreign_key='user_id', backref='user', lazy=True),
        'tokens': Relationship('AuthToken', RelationshipType.ONE_TO_MANY, 
                              foreign_key='user_id', backref='user', lazy=True),
        'permissions': Relationship('UserPermission', RelationshipType.ONE_TO_MANY, 
                                   foreign_key='user_id', backref='user', lazy=True),
        'notifications': Relationship('Notification', RelationshipType.ONE_TO_MANY, 
                                     foreign_key='user_id', backref='user', lazy=True),
    }

    _indexes: ClassVar[List[Dict]] = [
        {'columns': ['email'], 'unique': True},
        {'columns': ['username'], 'unique': True},
        {'columns': ['phone_number'], 'unique': True, 'where': 'phone_number IS NOT NULL'},
        {'columns': ['role']},
        {'columns': ['status']},
        {'columns': ['created_at']},
        {'columns': ['last_login']},
        {'columns': ['is_active', 'status']},
    ]

    # Password hashing configuration
    _password_hash_algorithm: ClassVar[str] = "bcrypt"  # Options: "sha256", "bcrypt"
    _password_hash_rounds: ClassVar[int] = 12  # For bcrypt
    _min_password_length: ClassVar[int] = 8
    _password_require_special: ClassVar[bool] = True
    _password_require_numbers: ClassVar[bool] = True
    _password_require_uppercase: ClassVar[bool] = True

    def __init__(self, **kwargs):
        # Set timestamps before initialization
        now = datetime.now(timezone.utc)
        if 'created_at' not in kwargs:
            kwargs['created_at'] = now
        if 'updated_at' not in kwargs:
            kwargs['updated_at'] = now
            
        super().__init__(**kwargs)
        
        # Initialize virtual fields
        self._permissions_cache = None
        self._roles_cache = None

    @classmethod
    def hash_password(cls, password: str) -> str:
        """Hash password using configured algorithm"""
        if cls._password_hash_algorithm == "bcrypt":
            salt = bcrypt.gensalt(rounds=cls._password_hash_rounds)
            return bcrypt.hashpw(password.encode(), salt).decode()
        elif cls._password_hash_algorithm == "sha3_256":
            return hashlib.sha3_256(password.encode()).hexdigest()
        else:
            from ..core.exceptions import ConfigurationError
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
        """Authenticate user with email/username and password"""
        # Check if identifier is email or username
        is_email = '@' in identifier
        
        query = cls.query().filter(
            cls.email == identifier if is_email else cls.username == identifier,
            cls.is_active == True
        )
        
        user = await query.first()
        
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
            from ..core.exceptions import InvalidEmailFormat
            from ..core.i18n import _
            raise InvalidEmailFormat(_('invalid_email_format'))
        
        # Validate username format
        if not re.match(r'^[a-zA-Z0-9_]{3,50}$', username):
            from ..core.exceptions import InvalidUsernameFormat
            raise InvalidUsernameFormat()

        # Validate password strength
        if not cls.is_password_strong(password):
            from ..core.exceptions import PasswordTooWeak
            raise PasswordTooWeak()

        # Check for existing user
        existing_email = await cls.query().filter(cls.email == email).first()
        if existing_email:
            from ..core.exceptions import EmailAlreadyExists
            raise EmailAlreadyExists()

        existing_username = await cls.query().filter(cls.username == username).first()
        if existing_username:
            from ..core.exceptions import UsernameAlreadyExists
            raise UsernameAlreadyExists()
        
        password_hash = cls.hash_password(password)
        now = datetime.now(timezone.utc)
        
        return await cls.create(
            email=email,
            username=username,
            password_hash=password_hash,
            role=role,
            status=status,
            password_changed_at=now,
            **kwargs
        )

    async def update_login_info(self):
        """Update login information and activity"""
        now = datetime.now(timezone.utc)
        self.last_login = now
        self.last_activity = now
        self.login_count = (self.login_count or 0) + 1
        self.failed_login_attempts = 0  # Reset failed attempts on successful login
        await self.save()

    async def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now(timezone.utc)
        await self.save(update_fields=['last_activity', 'updated_at'])

    async def increment_failed_login_attempts(self):
        """Increment failed login attempts counter"""
        self.failed_login_attempts = (self.failed_login_attempts or 0) + 1
        await self.save(update_fields=['failed_login_attempts', 'updated_at'])

    async def change_password(self, new_password: str, old_password: Optional[str] = None):
        """Change user password with optional old password verification"""
        if old_password and not self.verify_password(old_password):
            from ..core.exceptions import InvalidCredentials
            raise InvalidCredentials("Current password is incorrect")

        if not self.is_password_strong(new_password):
            from ..core.exceptions import PasswordTooWeak
            raise PasswordTooWeak()

        self.password_hash = self.hash_password(new_password)
        self.password_changed_at = datetime.now(timezone.utc)
        self.failed_login_attempts = 0  # Reset failed attempts

        await self.save(update_fields=['password_hash', 'password_changed_at', 'failed_login_attempts', 'updated_at'])

    async def verify_email(self):
        """Mark email as verified"""
        self.is_verified = True
        self.email_verified_at = datetime.now(timezone.utc)
        if self.status == UserStatus.PENDING:
            self.status = UserStatus.ACTIVE
        await self.save(update_fields=['is_verified', 'email_verified_at', 'status', 'updated_at'])

    async def verify_phone(self):
        """Mark phone number as verified"""
        self.phone_verified_at = datetime.now(timezone.utc)
        await self.save(update_fields=['phone_verified_at', 'updated_at'])

    async def accept_terms(self):
        """Mark terms and conditions as accepted"""
        now = datetime.now(timezone.utc)
        self.terms_accepted_at = now
        self.privacy_policy_accepted_at = now
        await self.save(update_fields=['terms_accepted_at', 'privacy_policy_accepted_at', 'updated_at'])

    async def activate(self):
        """Activate user account"""
        self.is_active = True
        self.status = UserStatus.ACTIVE
        await self.save(update_fields=['is_active', 'status', 'updated_at'])

    async def deactivate(self):
        """Deactivate user account"""
        self.is_active = False
        self.status = UserStatus.INACTIVE
        await self.save(update_fields=['is_active', 'status', 'updated_at'])

    async def suspend(self, reason: Optional[str] = None):
        """Suspend user account"""
        self.is_active = False
        self.status = UserStatus.SUSPENDED
        if reason:
            self.metadata = self.metadata or {}
            self.metadata['suspension_reason'] = reason
        await self.save(update_fields=['is_active', 'status', 'metadata', 'updated_at'])

    def verify_password(self, password: str) -> bool:
        """Verify if password matches hash"""
        return self.verify_password_hash(password, self.password_hash)

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
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return self.is_active and self.is_verified

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
        return (self.failed_login_attempts or 0) >= 5  # Lock after 5 failed attempts

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert to dictionary with optional sensitive fields"""
        base_data = {
            "id": str(self.id),
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
            "role": self.role,
            "status": self.status,
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

    async def get_permissions(self) -> List[str]:
        """Get user permissions (cached)"""
        if self._permissions_cache is None:
            # Load permissions from database or role-based system
            self._permissions_cache = await self._load_permissions()
        return self._permissions_cache

    async def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        permissions = await self.get_permissions()
        return permission in permissions

    async def _load_permissions(self) -> List[str]:
        """Load user permissions from database"""
        # This would typically query a permissions table or use role-based permissions
        # For now, return basic permissions based on role
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

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    def __repr__(self):
        return f"<User {self.id}: {self.email}>"

# Timestamp mixin for automatic created_at/updated_at management
class TimestampMixin:
    """Mixin for automatic timestamp management"""
    
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    
    async def save(self, *args, **kwargs):
        """Override save to update timestamps"""
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        await super().save(*args, **kwargs)

# Factory method to create extended user models
def create_extended_user_model(
    name: str,
    additional_fields: Optional[Dict[str, Field]] = None,
    additional_relationships: Optional[Dict[str, Relationship]] = None,
    table_name: Optional[str] = None,
    mixins: Optional[List[Type]] = None
) -> Type[BaseUser]:
    """
    Create an extended user model with additional fields, relationships, and mixins
    
    Args:
        name: Name of the new user model class
        additional_fields: Additional field definitions
        additional_relationships: Additional relationship definitions
        table_name: Optional table name (defaults to 'users')
        mixins: List of mixin classes to include
    
    Returns:
        A new user model class that extends BaseUser
    """
    
    # Include TimestampMixin by default if not already present
    if mixins is None:
        mixins = [TimestampMixin]
    elif TimestampMixin not in mixins:
        mixins.append(TimestampMixin)
    
    return ModelFactory.extend_model(
        BaseUser,
        name,
        additional_fields or {},
        additional_relationships or {},
        table_name,
        mixins
    )

# Example usage: Create a Student user model
Student = create_extended_user_model(
    "Student",
    additional_fields={
        'student_id': StringField(unique=True, max_length=20),
        'grade_level': IntegerField(min_value=1, max_value=12),
        'gpa': StringField(max_length=4, nullable=True),
        'major': StringField(max_length=100, nullable=True),
        'enrollment_date': DateTimeField(),
    },
    additional_relationships={
        'courses': Relationship('Course', RelationshipType.MANY_TO_MANY, 
                               through_table='student_courses',
                               through_local_key='student_id',
                               through_foreign_key='course_id'),
    },
    table_name='students'
)
