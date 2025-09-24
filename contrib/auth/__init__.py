"""
Authentication and authorization system for Pyserv  framework.
"""
from typing import List

from .auth import Auth, UserSession, AuthToken
from .backends import SessionBackend, TokenBackend, DatabaseBackend
from .decorators import login_required, permission_required, role_required
from .forms import LoginForm, RegisterForm, PasswordResetForm

__all__: List[str] = [
    'Auth',
    'UserSession',
    'AuthToken',
    'SessionBackend',
    'TokenBackend',
    'DatabaseBackend',
    'login_required',
    'permission_required',
    'role_required',
    'LoginForm',
    'RegisterForm',
    'PasswordResetForm',
]
