"""
Maintenance mode middleware for Pyserv framework.
Provides site maintenance functionality similar to Laravel/Django.
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from pyserv.http.request import Request
from pyserv.http.response import Response
from pyserv.exceptions import HTTPException


class MaintenanceStatus(str, Enum):
    """Maintenance mode status"""
    ACTIVE = "active"
    SCHEDULED = "scheduled"
    INACTIVE = "inactive"


@dataclass
class MaintenanceConfig:
    """Configuration for maintenance mode"""
    enabled: bool = False
    status: MaintenanceStatus = MaintenanceStatus.INACTIVE
    message: str = "Site is temporarily under maintenance. Please check back soon."
    title: str = "Maintenance Mode"
    retry_after: int = 3600  # 1 hour in seconds
    allowed_ips: List[str] = None
    allowed_paths: List[str] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    bypass_token: Optional[str] = None

    def __post_init__(self):
        if self.allowed_ips is None:
            self.allowed_ips = ['127.0.0.1', 'localhost', '::1']
        if self.allowed_paths is None:
            self.allowed_paths = ['/health', '/status', '/api/health', '/api/status']


@dataclass
class MaintenanceRecord:
    """Record of maintenance periods"""
    id: str
    start_time: datetime
    end_time: Optional[datetime]
    reason: str
    message: str
    performed_by: str
    affected_paths: List[str]
    allowed_ips: List[str]
    created_at: datetime


class MaintenanceManager:
    """Manager for maintenance mode functionality"""

    def __init__(self, config_file: str = "maintenance.json"):
        self.config_file = Path(config_file)
        self.logger = logging.getLogger("maintenance_manager")
        self.config = MaintenanceConfig()
        self.maintenance_history: List[MaintenanceRecord] = []
        self._lock = asyncio.Lock()

        # Load existing configuration
        self.load_config()

    def load_config(self):
        """Load maintenance configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.config = MaintenanceConfig(**data)
                    self.logger.info("Maintenance configuration loaded")
        except Exception as e:
            self.logger.warning(f"Could not load maintenance config: {e}")

    def save_config(self):
        """Save maintenance configuration to file"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config.__dict__, f, indent=2, default=str)
            self.logger.info("Maintenance configuration saved")
        except Exception as e:
            self.logger.error(f"Could not save maintenance config: {e}")

    def is_maintenance_active(self) -> bool:
        """Check if maintenance mode is currently active"""
        if not self.config.enabled:
            return False

        now = datetime.now()

        # Check scheduled maintenance
        if (self.config.scheduled_start and
            self.config.scheduled_end and
            self.config.scheduled_start <= now <= self.config.scheduled_end):
            return True

        return self.config.status == MaintenanceStatus.ACTIVE

    def is_ip_allowed(self, ip: str) -> bool:
        """Check if IP address is allowed during maintenance"""
        if not self.is_maintenance_active():
            return True

        return ip in self.config.allowed_ips

    def is_path_allowed(self, path: str) -> bool:
        """Check if path is allowed during maintenance"""
        if not self.is_maintenance_active():
            return True

        return any(path.startswith(allowed_path) for allowed_path in self.config.allowed_paths)

    def should_bypass_maintenance(self, request: Request) -> bool:
        """Check if request should bypass maintenance mode"""
        # Check bypass token
        if self.config.bypass_token:
            token = request.headers.get('X-Maintenance-Bypass')
            if token == self.config.bypass_token:
                return True

        # Check if IP is allowed
        client_ip = self._get_client_ip(request)
        if self.is_ip_allowed(client_ip):
            return True

        # Check if path is allowed
        if self.is_path_allowed(request.path):
            return True

        return False

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request"""
        # Check X-Forwarded-For header
        forwarded_for = request.headers.get('X-Forwarded-For', '')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get('X-Real-IP', '')
        if real_ip:
            return real_ip

        # Fall back to remote address
        return getattr(request, 'remote_addr', 'unknown')

    async def enable_maintenance(
        self,
        message: str = None,
        title: str = None,
        retry_after: int = None,
        allowed_ips: List[str] = None,
        allowed_paths: List[str] = None,
        scheduled_start: Optional[datetime] = None,
        scheduled_end: Optional[datetime] = None,
        performed_by: str = "system"
    ) -> MaintenanceRecord:
        """Enable maintenance mode"""
        async with self._lock:
            now = datetime.now()

            # Create maintenance record
            record = MaintenanceRecord(
                id=f"maintenance_{int(now.timestamp())}",
                start_time=now,
                end_time=None,
                reason="Scheduled maintenance",
                message=message or self.config.message,
                performed_by=performed_by,
                affected_paths=["*"],
                allowed_ips=allowed_ips or self.config.allowed_ips,
                created_at=now
            )

            # Update configuration
            self.config.enabled = True
            self.config.status = MaintenanceStatus.ACTIVE
            if message:
                self.config.message = message
            if title:
                self.config.title = title
            if retry_after:
                self.config.retry_after = retry_after
            if allowed_ips:
                self.config.allowed_ips = allowed_ips
            if allowed_paths:
                self.config.allowed_paths = allowed_paths
            if scheduled_start:
                self.config.scheduled_start = scheduled_start
            if scheduled_end:
                self.config.scheduled_end = scheduled_end

            # Save configuration
            self.save_config()

            # Add to history
            self.maintenance_history.append(record)

            self.logger.info(f"Maintenance mode enabled by {performed_by}")
            return record

    async def disable_maintenance(self, performed_by: str = "system") -> Optional[MaintenanceRecord]:
        """Disable maintenance mode"""
        async with self._lock:
            if not self.config.enabled:
                return None

            now = datetime.now()

            # Update active maintenance record
            for record in reversed(self.maintenance_history):
                if record.end_time is None:
                    record.end_time = now
                    break

            # Update configuration
            self.config.enabled = False
            self.config.status = MaintenanceStatus.INACTIVE
            self.config.scheduled_start = None
            self.config.scheduled_end = None

            # Save configuration
            self.save_config()

            self.logger.info(f"Maintenance mode disabled by {performed_by}")
            return record

    async def schedule_maintenance(
        self,
        start_time: datetime,
        end_time: datetime,
        message: str = None,
        title: str = None,
        allowed_ips: List[str] = None,
        allowed_paths: List[str] = None,
        performed_by: str = "system"
    ) -> MaintenanceRecord:
        """Schedule maintenance for a future time"""
        async with self._lock:
            # Create maintenance record
            record = MaintenanceRecord(
                id=f"scheduled_{int(start_time.timestamp())}",
                start_time=start_time,
                end_time=end_time,
                reason="Scheduled maintenance",
                message=message or self.config.message,
                performed_by=performed_by,
                affected_paths=["*"],
                allowed_ips=allowed_ips or self.config.allowed_ips,
                created_at=datetime.now()
            )

            # Update configuration
            self.config.status = MaintenanceStatus.SCHEDULED
            self.config.scheduled_start = start_time
            self.config.scheduled_end = end_time
            if message:
                self.config.message = message
            if title:
                self.config.title = title
            if allowed_ips:
                self.config.allowed_ips = allowed_ips
            if allowed_paths:
                self.config.allowed_paths = allowed_paths

            # Save configuration
            self.save_config()

            # Add to history
            self.maintenance_history.append(record)

            self.logger.info(f"Maintenance scheduled from {start_time} to {end_time} by {performed_by}")
            return record

    def get_maintenance_status(self) -> Dict[str, Any]:
        """Get current maintenance status"""
        return {
            "enabled": self.config.enabled,
            "status": self.config.status.value,
            "message": self.config.message,
            "title": self.config.title,
            "retry_after": self.config.retry_after,
            "allowed_ips": self.config.allowed_ips,
            "allowed_paths": self.config.allowed_paths,
            "scheduled_start": self.config.scheduled_start.isoformat() if self.config.scheduled_start else None,
            "scheduled_end": self.config.scheduled_end.isoformat() if self.config.scheduled_end else None,
            "is_active": self.is_maintenance_active()
        }

    def get_maintenance_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get maintenance history"""
        return [
            {
                "id": record.id,
                "start_time": record.start_time.isoformat(),
                "end_time": record.end_time.isoformat() if record.end_time else None,
                "reason": record.reason,
                "message": record.message,
                "performed_by": record.performed_by,
                "affected_paths": record.affected_paths,
                "allowed_ips": record.allowed_ips,
                "created_at": record.created_at.isoformat()
            }
            for record in self.maintenance_history[-limit:]
        ]


class MaintenanceMiddleware:
    """Middleware for handling maintenance mode"""

    def __init__(self, maintenance_manager: MaintenanceManager):
        self.maintenance_manager = maintenance_manager
        self.logger = logging.getLogger("maintenance_middleware")

    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Handle maintenance mode for requests"""

        # Check if maintenance mode should be bypassed
        if self.maintenance_manager.should_bypass_maintenance(request):
            response = await call_next(request)
            return response

        # Check if maintenance is active
        if self.maintenance_manager.is_maintenance_active():
            return await self._handle_maintenance_request(request)

        # Continue normal request processing
        response = await call_next(request)
        return response

    async def _handle_maintenance_request(self, request: Request) -> Response:
        """Handle request during maintenance mode"""
        status = self.maintenance_manager.get_maintenance_status()

        # Create maintenance response
        if request.headers.get('Accept', '').startswith('application/json'):
            # JSON response for API requests
            response_data = {
                "error": "Service Unavailable",
                "message": status["message"],
                "title": status["title"],
                "retry_after": status["retry_after"],
                "maintenance_mode": True
            }
            response = Response(
                json.dumps(response_data),
                status_code=503,
                headers={
                    "Content-Type": "application/json",
                    "Retry-After": str(status["retry_after"])
                }
            )
        else:
            # HTML response for web requests
            html_content = self._generate_maintenance_html(status)
            response = Response(
                html_content,
                status_code=503,
                headers={
                    "Content-Type": "text/html",
                    "Retry-After": str(status["retry_after"])
                }
            )

        self.logger.info(f"Maintenance mode response served to {request.remote_addr} for {request.path}")
        return response

    def _generate_maintenance_html(self, status: Dict[str, Any]) -> str:
        """Generate HTML page for maintenance mode"""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{status["title"]}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .container {{
            text-align: center;
            max-width: 600px;
            padding: 2rem;
        }}
        .maintenance-icon {{
            font-size: 4rem;
            margin-bottom: 1rem;
            opacity: 0.8;
        }}
        h1 {{
            font-size: 2.5rem;
            margin-bottom: 1rem;
            font-weight: 300;
        }}
        p {{
            font-size: 1.1rem;
            line-height: 1.6;
            margin-bottom: 2rem;
            opacity: 0.9;
        }}
        .retry-info {{
            background: rgba(255, 255, 255, 0.1);
            padding: 1rem;
            border-radius: 8px;
            margin-top: 2rem;
        }}
        .countdown {{
            font-size: 1.5rem;
            font-weight: bold;
            margin-top: 1rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="maintenance-icon">🔧</div>
        <h1>{status["title"]}</h1>
        <p>{status["message"]}</p>

        <div class="retry-info">
            <p>This site is temporarily under maintenance.</p>
            <p>We expect to be back online in approximately <span class="countdown" id="countdown">{status["retry_after"]}</span> seconds.</p>
        </div>
    </div>

    <script>
        // Simple countdown timer
        let countdown = {status["retry_after"]};
        const countdownElement = document.getElementById('countdown');

        const timer = setInterval(() => {{
            countdown--;
            countdownElement.textContent = countdown;

            if (countdown <= 0) {{
                clearInterval(timer);
                countdownElement.textContent = '0';
                // Optionally refresh the page
                // window.location.reload();
            }}
        }}, 1000);
    </script>
</body>
</html>
        """.strip()


# Global maintenance manager instance
maintenance_manager = MaintenanceManager()

def get_maintenance_manager() -> MaintenanceManager:
    """Get global maintenance manager instance"""
    return maintenance_manager

def enable_maintenance(
    message: str = None,
    title: str = None,
    retry_after: int = 3600,
    allowed_ips: List[str] = None,
    allowed_paths: List[str] = None,
    performed_by: str = "system"
) -> MaintenanceRecord:
    """Enable maintenance mode"""
    return asyncio.run(maintenance_manager.enable_maintenance(
        message=message,
        title=title,
        retry_after=retry_after,
        allowed_ips=allowed_ips,
        allowed_paths=allowed_paths,
        performed_by=performed_by
    ))

def disable_maintenance(performed_by: str = "system") -> Optional[MaintenanceRecord]:
    """Disable maintenance mode"""
    return asyncio.run(maintenance_manager.disable_maintenance(performed_by))

def schedule_maintenance(
    start_time: datetime,
    end_time: datetime,
    message: str = None,
    title: str = None,
    allowed_ips: List[str] = None,
    allowed_paths: List[str] = None,
    performed_by: str = "system"
) -> MaintenanceRecord:
    """Schedule maintenance for a future time"""
    return asyncio.run(maintenance_manager.schedule_maintenance(
        start_time=start_time,
        end_time=end_time,
        message=message,
        title=title,
        allowed_ips=allowed_ips,
        allowed_paths=allowed_paths,
        performed_by=performed_by
    ))

def get_maintenance_status() -> Dict[str, Any]:
    """Get current maintenance status"""
    return maintenance_manager.get_maintenance_status()

def get_maintenance_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Get maintenance history"""
    return maintenance_manager.get_maintenance_history(limit)

__all__ = [
    'MaintenanceManager', 'MaintenanceMiddleware', 'MaintenanceStatus',
    'MaintenanceConfig', 'MaintenanceRecord', 'maintenance_manager',
    'get_maintenance_manager', 'enable_maintenance', 'disable_maintenance',
    'schedule_maintenance', 'get_maintenance_status', 'get_maintenance_history'
]
