"""
Type definitions for PyDance routing system.
"""

from enum import Enum


class RouteType(Enum):
    """Types of routes"""
    NORMAL = "normal"
    REDIRECT = "redirect"
    VIEW = "view"
    FALLBACK = "fallback"
    INTENDED = "intended"
