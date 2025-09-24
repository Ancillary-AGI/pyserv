"""
Security headers middleware for HTTP response protection.
"""

from typing import Dict, List, Optional, Any
import re

class SecurityHeaders:
    """
    Security headers middleware for comprehensive HTTP security.
    """

    def __init__(self):
        self.headers = {
            # Basic security headers
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',

            # Content Security Policy
            'Content-Security-Policy': self._get_default_csp(),

            # Referrer Policy
            'Referrer-Policy': 'strict-origin-when-cross-origin',

            # Permissions Policy (formerly Feature Policy)
            'Permissions-Policy': self._get_default_permissions_policy(),

            # Cross-Origin policies
            'Cross-Origin-Embedder-Policy': 'require-corp',
            'Cross-Origin-Opener-Policy': 'same-origin',
            'Cross-Origin-Resource-Policy': 'same-origin',
        }

    def _get_default_csp(self) -> str:
        """Get default Content Security Policy."""
        return (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "media-src 'none'; "
            "object-src 'none'; "
            "child-src 'none'; "
            "worker-src 'none'; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "base-uri 'self'; "
            "upgrade-insecure-requests;"
        )

    def generate_nonce(self) -> str:
        """Generate a cryptographically secure nonce for CSP."""
        import secrets
        return secrets.token_hex(16)

    def update_csp_with_nonce(self, csp: str, nonce: str) -> str:
        """Update CSP to use nonce instead of unsafe-inline."""
        # Replace unsafe-inline with nonce
        updated_csp = csp.replace("'unsafe-inline'", f"'unsafe-inline' 'nonce-{nonce}'")
        return updated_csp

    def get_csp_with_nonce(self, nonce: str = None) -> str:
        """Get CSP with nonce support."""
        if nonce is None:
            nonce = self.generate_nonce()

        csp = self._get_default_csp()
        return self.update_csp_with_nonce(csp, nonce), nonce

    def _get_default_permissions_policy(self) -> str:
        """Get default Permissions Policy."""
        return (
            "camera=(), microphone=(), geolocation=(), "
            "payment=(), usb=(), magnetometer=(), accelerometer=(), "
            "gyroscope=(), ambient-light-sensor=(), autoplay=(), "
            "encrypted-media=(), fullscreen=(self), picture-in-picture=()"
        )

    def set_header(self, name: str, value: str):
        """Set a security header."""
        self.headers[name] = value

    def remove_header(self, name: str):
        """Remove a security header."""
        if name in self.headers:
            del self.headers[name]

    def update_csp(self, directives: Dict[str, str]):
        """Update Content Security Policy directives."""
        csp_parts = []

        for directive, value in directives.items():
            csp_parts.append(f"{directive} {value}")

        self.headers['Content-Security-Policy'] = '; '.join(csp_parts)

    def update_permissions_policy(self, permissions: Dict[str, str]):
        """Update Permissions Policy."""
        policy_parts = []

        for feature, allowlist in permissions.items():
            policy_parts.append(f"{feature}={allowlist}")

        self.headers['Permissions-Policy'] = ', '.join(policy_parts)

    def add_custom_header(self, name: str, value: str):
        """Add a custom security header."""
        self.headers[name] = value

    def get_headers(self) -> Dict[str, str]:
        """Get all security headers."""
        return self.headers.copy()

    def apply_headers(self, response_headers: Dict[str, str]):
        """Apply security headers to response."""
        response_headers.update(self.headers)

    def configure_for_environment(self, environment: str):
        """Configure headers based on environment."""
        if environment == 'development':
            # Relax CSP for development
            self.update_csp({
                'default-src': "'self' 'unsafe-inline' 'unsafe-eval' http: https: data:",
                'script-src': "'self' 'unsafe-inline' 'unsafe-eval' http: https:",
                'style-src': "'self' 'unsafe-inline' http: https:",
                'img-src': "'self' data: http: https: blob:",
                'connect-src': "'self' http: https: ws: wss:",
                'font-src': "'self' http: https: data:",
                'media-src': "'self' http: https: data:",
                'object-src': "'none'",
                'child-src': "'self' blob:",
                'worker-src': "'self' blob:",
                'frame-ancestors': "'self'",
                'form-action': "'self' http: https:",
                'base-uri': "'self'",
                'upgrade-insecure-requests': ""
            })

            # Relax HSTS for development
            self.headers['Strict-Transport-Security'] = 'max-age=60'

        elif environment == 'production':
            # Strict CSP for production
            self.update_csp({
                'default-src': "'self'",
                'script-src': "'self'",
                'style-src': "'self'",
                'img-src': "'self' data: https:",
                'font-src': "'self'",
                'connect-src': "'self'",
                'media-src': "'none'",
                'object-src': "'none'",
                'child-src': "'none'",
                'worker-src': "'none'",
                'frame-ancestors': "'none'",
                'form-action': "'self'",
                'base-uri': "'self'",
                'upgrade-insecure-requests': ""
            })

            # Strict HSTS for production
            self.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'

    def validate_csp(self, csp: str) -> List[str]:
        """Validate CSP string and return warnings."""
        warnings = []

        # Check for unsafe-inline
        if "'unsafe-inline'" in csp:
            warnings.append("CSP allows unsafe-inline scripts")

        # Check for unsafe-eval
        if "'unsafe-eval'" in csp:
            warnings.append("CSP allows unsafe-eval")

        # Check for wildcards
        if '*' in csp:
            warnings.append("CSP contains wildcards")

        # Check for http: in production
        if 'http:' in csp and 'https:' in csp:
            warnings.append("CSP allows both HTTP and HTTPS")

        return warnings

    def get_security_score(self) -> Dict[str, Any]:
        """Get security score based on headers."""
        score = 0
        max_score = 100
        issues = []

        # Check HSTS
        hsts = self.headers.get('Strict-Transport-Security', '')
        if 'max-age=31536000' in hsts and 'includeSubDomains' in hsts:
            score += 20
        elif 'max-age=' in hsts:
            score += 10
        else:
            issues.append("HSTS not properly configured")

        # Check CSP
        csp = self.headers.get('Content-Security-Policy', '')
        csp_warnings = self.validate_csp(csp)
        if not csp_warnings:
            score += 25
        elif len(csp_warnings) == 1:
            score += 15
        else:
            issues.extend(csp_warnings)

        # Check X-Frame-Options
        if self.headers.get('X-Frame-Options') == 'DENY':
            score += 10
        else:
            issues.append("X-Frame-Options not set to DENY")

        # Check X-Content-Type-Options
        if self.headers.get('X-Content-Type-Options') == 'nosniff':
            score += 10
        else:
            issues.append("X-Content-Type-Options not set to nosniff")

        # Check X-XSS-Protection
        if self.headers.get('X-XSS-Protection') == '1; mode=block':
            score += 10
        else:
            issues.append("X-XSS-Protection not properly configured")

        # Check Permissions Policy
        if 'Permissions-Policy' in self.headers:
            score += 15
        else:
            issues.append("Permissions Policy not set")

        # Check Cross-Origin policies
        cross_origin_headers = [
            'Cross-Origin-Embedder-Policy',
            'Cross-Origin-Opener-Policy',
            'Cross-Origin-Resource-Policy'
        ]

        for header in cross_origin_headers:
            if header in self.headers:
                score += 5
            else:
                issues.append(f"{header} not set")

        return {
            'score': score,
            'max_score': max_score,
            'percentage': (score / max_score) * 100,
            'issues': issues
        }

    def to_middleware(self):
        """Convert to middleware function."""
        def security_middleware(request, call_next):
            response = call_next(request)

            # Apply security headers
            if hasattr(response, 'headers'):
                self.apply_headers(response.headers)

            return response

        return security_middleware
