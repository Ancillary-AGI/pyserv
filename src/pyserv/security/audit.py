"""
Comprehensive audit logging for compliance and security monitoring.
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging
from pathlib import Path

class AuditEvent(Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    FAILED_LOGIN = "failed_login"
    PASSWORD_CHANGE = "password_change"
    PERMISSION_CHANGE = "permission_change"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    ADMIN_ACTION = "admin_action"
    SECURITY_EVENT = "security_event"

@dataclass
class AuditEntry:
    timestamp: datetime
    event_type: AuditEvent
    user_id: Optional[str]
    session_id: Optional[str]
    resource: str
    action: str
    details: Dict[str, Any]
    ip_address: str
    user_agent: str
    success: bool
    correlation_id: Optional[str] = None

class AuditLogger:
    """
    Comprehensive audit logging system for compliance.
    """

    def __init__(self, log_file: str = "audit.log", max_file_size: int = 100 * 1024 * 1024):
        self.log_file = Path(log_file)
        self.max_file_size = max_file_size
        self._queue: asyncio.Queue[AuditEntry] = asyncio.Queue()
        self._running = False
        self.correlation_id = None

    async def start(self):
        """Start audit logging service."""
        if not self._running:
            self._running = True
            asyncio.create_task(self._process_queue())

    async def stop(self):
        """Stop audit logging service."""
        self._running = False
        # Process remaining entries
        while not self._queue.empty():
            await asyncio.sleep(0.1)

    async def log_event(self, event_type: AuditEvent, user_id: Optional[str],
                       session_id: Optional[str], resource: str, action: str,
                       details: Dict[str, Any], ip_address: str,
                       user_agent: str, success: bool = True):
        """Log an audit event."""
        entry = AuditEntry(
            timestamp=datetime.now(),
            event_type=event_type,
            user_id=user_id,
            session_id=session_id,
            resource=resource,
            action=action,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            correlation_id=self.correlation_id
        )

        await self._queue.put(entry)

    async def _process_queue(self):
        """Process audit log queue."""
        while self._running:
            try:
                if not self._queue.empty():
                    entry = await self._queue.get()
                    await self._write_entry(entry)
                    self._queue.task_done()
                else:
                    await asyncio.sleep(0.1)
            except Exception as e:
                logging.error(f"Audit logging error: {e}")

    async def _write_entry(self, entry: AuditEntry):
        """Write audit entry to file."""
        # Check file size and rotate if necessary
        if self.log_file.exists() and self.log_file.stat().st_size > self.max_file_size:
            await self._rotate_log()

        log_data = {
            'timestamp': entry.timestamp.isoformat(),
            'event_type': entry.event_type.value,
            'user_id': entry.user_id,
            'session_id': entry.session_id,
            'resource': entry.resource,
            'action': entry.action,
            'details': entry.details,
            'ip_address': entry.ip_address,
            'user_agent': entry.user_agent,
            'success': entry.success,
            'correlation_id': entry.correlation_id
        }

        log_line = json.dumps(log_data, default=str) + '\n'

        with open(self.log_file, 'a') as f:
            f.write(log_line)

    async def _rotate_log(self):
        """Rotate audit log file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.log_file.with_suffix(f'.{timestamp}.bak')
        self.log_file.rename(backup_file)

    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for audit entries."""
        self.correlation_id = correlation_id

    def get_recent_entries(self, limit: int = 100) -> List[AuditEntry]:
        """Get recent audit entries."""
        entries = []
        try:
            if self.log_file.exists():
                with open(self.log_file, 'r') as f:
                    for line in f.readlines()[-limit:]:
                        try:
                            data = json.loads(line.strip())
                            entry = AuditEntry(
                                timestamp=datetime.fromisoformat(data['timestamp']),
                                event_type=AuditEvent(data['event_type']),
                                user_id=data['user_id'],
                                session_id=data['session_id'],
                                resource=data['resource'],
                                action=data['action'],
                                details=data['details'],
                                ip_address=data['ip_address'],
                                user_agent=data['user_agent'],
                                success=data['success'],
                                correlation_id=data.get('correlation_id')
                            )
                            entries.append(entry)
                        except (json.JSONDecodeError, KeyError, ValueError):
                            continue
        except Exception as e:
            logging.error(f"Error reading audit log: {e}")

        return entries

    def search_entries(self, **filters) -> List[AuditEntry]:
        """Search audit entries with filters."""
        entries = []
        try:
            if self.log_file.exists():
                with open(self.log_file, 'r') as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())

                            # Apply filters
                            match = True
                            for key, value in filters.items():
                                if key not in data or data[key] != value:
                                    match = False
                                    break

                            if match:
                                entry = AuditEntry(
                                    timestamp=datetime.fromisoformat(data['timestamp']),
                                    event_type=AuditEvent(data['event_type']),
                                    user_id=data['user_id'],
                                    session_id=data['session_id'],
                                    resource=data['resource'],
                                    action=data['action'],
                                    details=data['details'],
                                    ip_address=data['ip_address'],
                                    user_agent=data['user_agent'],
                                    success=data['success'],
                                    correlation_id=data.get('correlation_id')
                                )
                                entries.append(entry)
                        except (json.JSONDecodeError, KeyError, ValueError):
                            continue
        except Exception as e:
            logging.error(f"Error searching audit log: {e}")

        return entries
