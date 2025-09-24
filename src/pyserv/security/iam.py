"""
Identity and Access Management (IAM) for Pyserv  framework.
Implements role-based access control (RBAC) with least privilege principles.
"""

from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import secrets
import json


@dataclass
class Permission:
    """Represents a permission in the system"""
    resource: str
    action: str
    conditions: Dict[str, Any] = field(default_factory=dict)

    def __str__(self):
        return f"{self.resource}:{self.action}"

    def matches(self, requested_resource: str, requested_action: str,
               context: Dict[str, Any] = None) -> bool:
        """Check if this permission matches the requested action"""
        if self.resource != requested_resource or self.action != requested_action:
            return False

        # Check conditions if any
        if self.conditions and context:
            for key, expected_value in self.conditions.items():
                if key not in context or context[key] != expected_value:
                    return False

        return True


@dataclass
class Role:
    """Represents a role with associated permissions"""
    name: str
    description: str = ""
    permissions: Set[Permission] = field(default_factory=set)
    parent_roles: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_permission(self, permission: Permission):
        """Add a permission to this role"""
        self.permissions.add(permission)

    def remove_permission(self, permission: Permission):
        """Remove a permission from this role"""
        self.permissions.discard(permission)

    def has_permission(self, resource: str, action: str,
                      context: Dict[str, Any] = None) -> bool:
        """Check if this role has the specified permission"""
        # Check direct permissions
        for permission in self.permissions:
            if permission.matches(resource, action, context):
                return True

        return False

    def get_all_permissions(self, iam_system) -> Set[Permission]:
        """Get all permissions including inherited ones"""
        all_permissions = self.permissions.copy()

        # Add permissions from parent roles
        for parent_name in self.parent_roles:
            parent_role = iam_system.get_role(parent_name)
            if parent_role:
                all_permissions.update(parent_role.get_all_permissions(iam_system))

        return all_permissions


@dataclass
class Policy:
    """Represents an access policy"""
    name: str
    description: str = ""
    statements: List[Dict[str, Any]] = field(default_factory=list)
    version: str = "2012-10-17"

    def evaluate(self, user: 'IAMUser', resource: str, action: str,
                context: Dict[str, Any] = None) -> str:
        """
        Evaluate policy against a request
        Returns: 'Allow', 'Deny', or 'Default'
        """
        context = context or {}

        for statement in self.statements:
            effect = statement.get('Effect', 'Allow')
            principals = statement.get('Principal', [])
            actions = statement.get('Action', [])
            resources = statement.get('Resource', [])
            conditions = statement.get('Condition', {})

            # Check if user matches principals
            if not self._matches_principal(user, principals):
                continue

            # Check if action matches
            if not self._matches_action(action, actions):
                continue

            # Check if resource matches
            if not self._matches_resource(resource, resources):
                continue

            # Check conditions
            if not self._matches_conditions(context, conditions):
                continue

            return effect

        return 'Default'

    def _matches_principal(self, user: 'IAMUser', principals: List[str]) -> bool:
        """Check if user matches any of the principals"""
        if not principals:
            return True

        for principal in principals:
            if principal == '*' or principal == user.id:
                return True

        return False

    def _matches_action(self, action: str, actions: List[str]) -> bool:
        """Check if action matches any of the allowed actions"""
        if not actions:
            return True

        for allowed_action in actions:
            if allowed_action == '*' or allowed_action == action:
                return True
            # Support wildcards like 'user:*'
            if '*' in allowed_action:
                if allowed_action.replace('*', '').replace(':', '') in action.replace(':', ''):
                    return True

        return False

    def _matches_resource(self, resource: str, resources: List[str]) -> bool:
        """Check if resource matches any of the allowed resources"""
        if not resources:
            return True

        for allowed_resource in resources:
            if allowed_resource == '*' or allowed_resource == resource:
                return True

        return False

    def _matches_conditions(self, context: Dict[str, Any],
                           conditions: Dict[str, Any]) -> bool:
        """Check if context matches all conditions"""
        for condition_key, condition_value in conditions.items():
            if condition_key not in context:
                return False

            context_value = context[condition_key]
            if isinstance(condition_value, dict):
                # Handle condition operators like StringEquals, etc.
                for operator, expected in condition_value.items():
                    if not self._evaluate_condition(operator, context_value, expected):
                        return False
            else:
                if context_value != condition_value:
                    return False

        return True

    def _evaluate_condition(self, operator: str, actual: Any, expected: Any) -> bool:
        """Evaluate a condition operator"""
        if operator == 'StringEquals':
            return str(actual) == str(expected)
        elif operator == 'StringLike':
            return expected in str(actual)
        elif operator == 'NumericEquals':
            return float(actual) == float(expected)
        elif operator == 'NumericGreaterThan':
            return float(actual) > float(expected)
        # Add more operators as needed
        return False


@dataclass
class IAMUser:
    """Represents a user in the IAM system"""
    id: str
    username: str
    email: str
    roles: Set[str] = field(default_factory=set)
    policies: List[Policy] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    last_login: Optional[datetime] = None
    mfa_enabled: bool = False

    def add_role(self, role_name: str):
        """Add a role to the user"""
        self.roles.add(role_name)

    def remove_role(self, role_name: str):
        """Remove a role from the user"""
        self.roles.discard(role_name)

    def add_policy(self, policy: Policy):
        """Add a policy to the user"""
        self.policies.append(policy)

    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role"""
        return role_name in self.roles

    def get_effective_permissions(self, iam_system) -> Set[Permission]:
        """Get all effective permissions for this user"""
        permissions = set()

        # Get permissions from roles
        for role_name in self.roles:
            role = iam_system.get_role(role_name)
            if role:
                permissions.update(role.get_all_permissions(iam_system))

        return permissions

    def is_authorized(self, iam_system, resource: str, action: str,
                     context: Dict[str, Any] = None) -> bool:
        """Check if user is authorized for an action"""
        context = context or {}

        # Check explicit deny in policies first
        for policy in self.policies:
            result = policy.evaluate(self, resource, action, context)
            if result == 'Deny':
                return False

        # Check allow in policies
        for policy in self.policies:
            result = policy.evaluate(self, resource, action, context)
            if result == 'Allow':
                return True

        # Check role-based permissions
        for role_name in self.roles:
            role = iam_system.get_role(role_name)
            if role and role.has_permission(resource, action, context):
                return True

        return False


class IAM:
    """Identity and Access Management system"""

    def __init__(self):
        self.users: Dict[str, IAMUser] = {}
        self.roles: Dict[str, Role] = {}
        self.policies: Dict[str, Policy] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def create_user(self, username: str, email: str, **kwargs) -> IAMUser:
        """Create a new user"""
        user_id = f"user_{secrets.token_hex(8)}"
        user = IAMUser(
            id=user_id,
            username=username,
            email=email,
            **kwargs
        )
        self.users[user_id] = user
        return user

    def get_user(self, user_id: str) -> Optional[IAMUser]:
        """Get user by ID"""
        return self.users.get(user_id)

    def create_role(self, name: str, description: str = "",
                   permissions: Set[Permission] = None) -> Role:
        """Create a new role"""
        role = Role(
            name=name,
            description=description,
            permissions=permissions or set()
        )
        self.roles[name] = role
        return role

    def get_role(self, name: str) -> Optional[Role]:
        """Get role by name"""
        return self.roles.get(name)

    def create_policy(self, name: str, statements: List[Dict[str, Any]],
                     description: str = "") -> Policy:
        """Create a new policy"""
        policy = Policy(
            name=name,
            description=description,
            statements=statements
        )
        self.policies[name] = policy
        return policy

    def get_policy(self, name: str) -> Optional[Policy]:
        """Get policy by name"""
        return self.policies.get(name)

    def assign_role_to_user(self, user_id: str, role_name: str):
        """Assign a role to a user"""
        user = self.get_user(user_id)
        if user:
            user.add_role(role_name)

    def revoke_role_from_user(self, user_id: str, role_name: str):
        """Revoke a role from a user"""
        user = self.get_user(user_id)
        if user:
            user.remove_role(role_name)

    def attach_policy_to_user(self, user_id: str, policy_name: str):
        """Attach a policy to a user"""
        user = self.get_user(user_id)
        policy = self.get_policy(policy_name)
        if user and policy:
            user.add_policy(policy)

    def check_permission(self, user_id: str, resource: str, action: str,
                        context: Dict[str, Any] = None) -> bool:
        """Check if user has permission for an action"""
        user = self.get_user(user_id)
        if not user or not user.is_active:
            return False

        return user.is_authorized(self, resource, action, context)

    def create_session(self, user_id: str, metadata: Dict[str, Any] = None) -> str:
        """Create a session for a user"""
        session_id = secrets.token_hex(32)
        self.sessions[session_id] = {
            'user_id': user_id,
            'created_at': datetime.utcnow(),
            'metadata': metadata or {},
            'is_active': True
        }
        return session_id

    def validate_session(self, session_id: str) -> Optional[IAMUser]:
        """Validate a session and return the associated user"""
        session = self.sessions.get(session_id)
        if not session or not session['is_active']:
            return None

        # Check session expiry (24 hours)
        if datetime.utcnow() - session['created_at'] > timedelta(hours=24):
            session['is_active'] = False
            return None

        user = self.get_user(session['user_id'])
        if user:
            user.last_login = datetime.utcnow()

        return user

    def invalidate_session(self, session_id: str):
        """Invalidate a session"""
        if session_id in self.sessions:
            self.sessions[session_id]['is_active'] = False

    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """Get all effective permissions for a user"""
        user = self.get_user(user_id)
        if not user:
            return set()

        return user.get_effective_permissions(self)

    def list_users(self) -> List[IAMUser]:
        """List all users"""
        return list(self.users.values())

    def list_roles(self) -> List[Role]:
        """List all roles"""
        return list(self.roles.values())

    def list_policies(self) -> List[Policy]:
        """List all policies"""
        return list(self.policies.values())


# Predefined roles and permissions
ADMIN_ROLE = Role(
    name="admin",
    description="Administrator with full access",
    permissions={
        Permission("*", "*"),  # All resources, all actions
    }
)

USER_ROLE = Role(
    name="user",
    description="Regular user with basic access",
    permissions={
        Permission("user", "read"),
        Permission("user", "update", {"user_id": "self"}),
        Permission("post", "create"),
        Permission("post", "read"),
        Permission("post", "update", {"author_id": "self"}),
        Permission("post", "delete", {"author_id": "self"}),
    }
)

MODERATOR_ROLE = Role(
    name="moderator",
    description="Content moderator",
    permissions={
        Permission("post", "read"),
        Permission("post", "update"),
        Permission("post", "delete"),
        Permission("comment", "delete"),
        Permission("user", "read"),
    }
)

# Global IAM instance
_iam_instance = None

def get_iam_system() -> IAM:
    """Get global IAM system instance"""
    global _iam_instance
    if _iam_instance is None:
        _iam_instance = IAM()
        # Initialize with default roles
        _iam_instance.roles.update({
            'admin': ADMIN_ROLE,
            'user': USER_ROLE,
            'moderator': MODERATOR_ROLE
        })
    return _iam_instance




