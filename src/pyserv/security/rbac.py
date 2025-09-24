"""
Role-Based Access Control (RBAC) system.
"""

from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass
from enum import Enum

class Permission:
    """Represents a system permission."""

    def __init__(self, name: str, resource: str, action: str):
        self.name = name
        self.resource = resource
        self.action = action

    def __str__(self):
        return f"{self.resource}:{self.action}"

    def __eq__(self, other):
        if not isinstance(other, Permission):
            return False
        return (self.name == other.name and
                self.resource == other.resource and
                self.action == other.action)

    def __hash__(self):
        return hash((self.name, self.resource, self.action))

@dataclass
class Role:
    name: str
    permissions: Set[Permission]
    parent_roles: Set[str] = None

    def __post_init__(self):
        if self.parent_roles is None:
            self.parent_roles = set()

    def has_permission(self, permission: Permission) -> bool:
        """Check if role has a specific permission."""
        return permission in self.permissions

    def grant_permission(self, permission: Permission):
        """Grant a permission to this role."""
        self.permissions.add(permission)

    def revoke_permission(self, permission: Permission):
        """Revoke a permission from this role."""
        self.permissions.discard(permission)

class RoleBasedAccessControl:
    """
    Role-Based Access Control system for managing permissions.
    """

    def __init__(self):
        self.roles: Dict[str, Role] = {}
        self.users: Dict[str, Set[str]] = {}  # user_id -> set of role names
        self.permissions: Dict[str, Permission] = {}

    def create_role(self, name: str, permissions: List[Permission] = None,
                   parent_roles: List[str] = None) -> Role:
        """Create a new role."""
        if name in self.roles:
            raise ValueError(f"Role {name} already exists")

        role = Role(
            name=name,
            permissions=set(permissions or []),
            parent_roles=set(parent_roles or [])
        )

        self.roles[name] = role
        return role

    def delete_role(self, name: str):
        """Delete a role."""
        if name not in self.roles:
            raise ValueError(f"Role {name} does not exist")

        # Remove role from all users
        for user_roles in self.users.values():
            user_roles.discard(name)

        del self.roles[name]

    def assign_role(self, user_id: str, role_name: str):
        """Assign a role to a user."""
        if role_name not in self.roles:
            raise ValueError(f"Role {role_name} does not exist")

        if user_id not in self.users:
            self.users[user_id] = set()

        self.users[user_id].add(role_name)

    def revoke_role(self, user_id: str, role_name: str):
        """Revoke a role from a user."""
        if user_id not in self.users:
            return

        self.users[user_id].discard(role_name)

    def user_has_permission(self, user_id: str, permission: Permission) -> bool:
        """Check if a user has a specific permission."""
        if user_id not in self.users:
            return False

        user_roles = self.users[user_id]

        for role_name in user_roles:
            role = self.roles.get(role_name)
            if role and role.has_permission(permission):
                return True

            # Check parent roles
            for parent_name in role.parent_roles:
                parent_role = self.roles.get(parent_name)
                if parent_role and parent_role.has_permission(permission):
                    return True

        return False

    def user_has_any_permission(self, user_id: str, permissions: List[Permission]) -> bool:
        """Check if user has any of the specified permissions."""
        return any(self.user_has_permission(user_id, perm) for perm in permissions)

    def user_has_all_permissions(self, user_id: str, permissions: List[Permission]) -> bool:
        """Check if user has all of the specified permissions."""
        return all(self.user_has_permission(user_id, perm) for perm in permissions)

    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """Get all permissions for a user."""
        if user_id not in self.users:
            return set()

        user_permissions = set()
        user_roles = self.users[user_id]

        for role_name in user_roles:
            role = self.roles.get(role_name)
            if role:
                user_permissions.update(role.permissions)

                # Include parent role permissions
                for parent_name in role.parent_roles:
                    parent_role = self.roles.get(parent_name)
                    if parent_role:
                        user_permissions.update(parent_role.permissions)

        return user_permissions

    def get_user_roles(self, user_id: str) -> Set[str]:
        """Get all roles for a user."""
        return self.users.get(user_id, set())

    def create_permission(self, name: str, resource: str, action: str) -> Permission:
        """Create a new permission."""
        permission = Permission(name, resource, action)
        self.permissions[name] = permission
        return permission

    def get_permission(self, name: str) -> Optional[Permission]:
        """Get a permission by name."""
        return self.permissions.get(name)

    def require_permission(self, user_id: str, permission: Permission) -> bool:
        """Require a permission for a user (throws exception if not granted)."""
        if not self.user_has_permission(user_id, permission):
            raise PermissionError(f"User {user_id} does not have permission {permission}")
        return True

    def require_any_permission(self, user_id: str, permissions: List[Permission]) -> bool:
        """Require any of the permissions for a user."""
        if not self.user_has_any_permission(user_id, permissions):
            raise PermissionError(f"User {user_id} does not have any of the required permissions")
        return True

    def require_all_permissions(self, user_id: str, permissions: List[Permission]) -> bool:
        """Require all permissions for a user."""
        if not self.user_has_all_permissions(user_id, permissions):
            raise PermissionError(f"User {user_id} does not have all required permissions")
        return True

class PermissionError(Exception):
    """Exception raised when permission is denied."""
    pass
