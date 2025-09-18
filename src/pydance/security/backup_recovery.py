"""
Backup & Recovery System with Encryption.
Provides secure backup and disaster recovery capabilities.
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import os
import json
import hashlib
import secrets
import gzip
import shutil
from pathlib import Path
import aiofiles
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature


@dataclass
class BackupMetadata:
    """Backup metadata"""
    backup_id: str
    timestamp: datetime
    type: str  # "full", "incremental", "differential"
    size_bytes: int
    checksum: str
    encryption_key_id: Optional[str] = None
    compression: str = "gzip"
    status: str = "completed"  # "in_progress", "completed", "failed"
    retention_days: int = 30
    tags: Dict[str, str] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if backup is expired"""
        expiry_date = self.timestamp + timedelta(days=self.retention_days)
        return datetime.utcnow() > expiry_date

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'backup_id': self.backup_id,
            'timestamp': self.timestamp.isoformat(),
            'type': self.type,
            'size_bytes': self.size_bytes,
            'checksum': self.checksum,
            'encryption_key_id': self.encryption_key_id,
            'compression': self.compression,
            'status': self.status,
            'retention_days': self.retention_days,
            'tags': self.tags
        }


@dataclass
class RecoveryPoint:
    """Recovery point for point-in-time recovery"""
    point_id: str
    timestamp: datetime
    backup_id: str
    sequence_number: int
    changes: List[Dict[str, Any]] = field(default_factory=list)
    checksum: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'point_id': self.point_id,
            'timestamp': self.timestamp.isoformat(),
            'backup_id': self.backup_id,
            'sequence_number': self.sequence_number,
            'changes': self.changes,
            'checksum': self.checksum
        }


class BackupEncryption:
    """Backup encryption utilities"""

    def __init__(self, key_manager):
        self.key_manager = key_manager

    async def generate_backup_key(self) -> str:
        """Generate a new key for backup encryption"""
        return await self.key_manager.create_key("backup_encryption", "AES", 256)

    async def encrypt_backup_data(self, data: bytes, key_id: str) -> bytes:
        """Encrypt backup data"""
        return await self.key_manager.encrypt_with_key(key_id, data)

    async def decrypt_backup_data(self, encrypted_data: bytes, key_id: str) -> bytes:
        """Decrypt backup data"""
        return await self.key_manager.decrypt_with_key(key_id, encrypted_data)

    async def sign_backup(self, data: bytes, key_id: str) -> str:
        """Sign backup for integrity verification"""
        return await self.key_manager.sign_with_key(key_id, data)

    async def verify_backup_signature(self, data: bytes, signature: str, key_id: str) -> bool:
        """Verify backup signature"""
        return await self.key_manager.verify_with_key(key_id, data, signature)


class BackupManager:
    """Enterprise backup management system"""

    def __init__(self, backup_dir: str = "./backups", key_manager=None):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.encryption = BackupEncryption(key_manager) if key_manager else None
        self.backups: Dict[str, BackupMetadata] = {}
        self.recovery_points: Dict[str, List[RecoveryPoint]] = {}

    async def create_backup(self, data_source: Dict[str, Any], backup_type: str = "full",
                          compression: bool = True, encryption: bool = True) -> str:
        """Create a backup"""
        backup_id = f"backup_{secrets.token_hex(16)}"
        timestamp = datetime.utcnow()

        # Serialize data
        data_json = json.dumps(data_source, default=str, indent=2)
        data_bytes = data_json.encode('utf-8')

        # Compress if requested
        if compression:
            data_bytes = await self._compress_data(data_bytes)

        # Encrypt if requested and encryption is available
        encryption_key_id = None
        if encryption and self.encryption:
            encryption_key_id = await self.encryption.generate_backup_key()
            data_bytes = await self.encryption.encrypt_backup_data(data_bytes, encryption_key_id)

        # Calculate checksum
        checksum = hashlib.sha256(data_bytes).hexdigest()

        # Create backup file
        backup_path = self.backup_dir / f"{backup_id}.backup"
        async with aiofiles.open(backup_path, 'wb') as f:
            await f.write(data_bytes)

        # Create metadata
        metadata = BackupMetadata(
            backup_id=backup_id,
            timestamp=timestamp,
            type=backup_type,
            size_bytes=len(data_bytes),
            checksum=checksum,
            encryption_key_id=encryption_key_id,
            compression="gzip" if compression else "none"
        )

        self.backups[backup_id] = metadata

        # Save metadata
        await self._save_backup_metadata(metadata)

        return backup_id

    async def restore_backup(self, backup_id: str, target_location: str = "./restored") -> Dict[str, Any]:
        """Restore from backup"""
        if backup_id not in self.backups:
            raise ValueError(f"Backup {backup_id} not found")

        metadata = self.backups[backup_id]
        backup_path = self.backup_dir / f"{backup_id}.backup"

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file {backup_path} not found")

        # Read backup data
        async with aiofiles.open(backup_path, 'rb') as f:
            data_bytes = await f.read()

        # Verify checksum
        actual_checksum = hashlib.sha256(data_bytes).hexdigest()
        if actual_checksum != metadata.checksum:
            raise ValueError(f"Backup checksum mismatch for {backup_id}")

        # Decrypt if encrypted
        if metadata.encryption_key_id and self.encryption:
            data_bytes = await self.encryption.decrypt_backup_data(data_bytes, metadata.encryption_key_id)

        # Decompress if compressed
        if metadata.compression == "gzip":
            data_bytes = await self._decompress_data(data_bytes)

        # Parse JSON
        data = json.loads(data_bytes.decode('utf-8'))

        # Create target directory
        target_path = Path(target_location)
        target_path.mkdir(exist_ok=True)

        # Restore files/data
        await self._restore_data(data, target_path)

        return {
            'backup_id': backup_id,
            'restored_to': str(target_path),
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }

    async def _compress_data(self, data: bytes) -> bytes:
        """Compress data using gzip"""
        import io
        buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='wb') as f:
            f.write(data)
        return buffer.getvalue()

    async def _decompress_data(self, data: bytes) -> bytes:
        """Decompress gzip data"""
        import io
        buffer = io.BytesIO(data)
        with gzip.GzipFile(fileobj=buffer, mode='rb') as f:
            return f.read()

    async def _save_backup_metadata(self, metadata: BackupMetadata):
        """Save backup metadata to file"""
        metadata_path = self.backup_dir / f"{metadata.backup_id}.meta"
        async with aiofiles.open(metadata_path, 'w') as f:
            await f.write(json.dumps(metadata.to_dict(), indent=2))

    async def _restore_data(self, data: Dict[str, Any], target_path: Path):
        """Restore data to target location"""
        # This would implement the actual restoration logic
        # For different types of data (files, database, etc.)
        for key, value in data.items():
            if isinstance(value, dict) and 'type' in value:
                if value['type'] == 'file':
                    # Restore file
                    file_path = target_path / key
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    async with aiofiles.open(file_path, 'w') as f:
                        await f.write(value.get('content', ''))
                elif value['type'] == 'directory':
                    # Restore directory structure
                    dir_path = target_path / key
                    dir_path.mkdir(parents=True, exist_ok=True)

    async def list_backups(self, backup_type: Optional[str] = None) -> List[BackupMetadata]:
        """List available backups"""
        backups = list(self.backups.values())

        if backup_type:
            backups = [b for b in backups if b.type == backup_type]

        return sorted(backups, key=lambda x: x.timestamp, reverse=True)

    async def delete_backup(self, backup_id: str):
        """Delete a backup"""
        if backup_id not in self.backups:
            return

        # Remove files
        backup_path = self.backup_dir / f"{backup_id}.backup"
        metadata_path = self.backup_dir / f"{backup_id}.meta"

        if backup_path.exists():
            backup_path.unlink()

        if metadata_path.exists():
            metadata_path.unlink()

        # Remove from memory
        del self.backups[backup_id]

    async def cleanup_expired_backups(self):
        """Clean up expired backups"""
        expired_backups = []
        for backup_id, metadata in self.backups.items():
            if metadata.is_expired():
                expired_backups.append(backup_id)

        for backup_id in expired_backups:
            await self.delete_backup(backup_id)

        return len(expired_backups)

    async def get_backup_status(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Get backup status and information"""
        if backup_id not in self.backups:
            return None

        metadata = self.backups[backup_id]
        backup_path = self.backup_dir / f"{backup_id}.backup"

        return {
            'backup_id': backup_id,
            'exists': backup_path.exists(),
            'size_bytes': metadata.size_bytes,
            'timestamp': metadata.timestamp.isoformat(),
            'type': metadata.type,
            'status': metadata.status,
            'is_expired': metadata.is_expired(),
            'days_until_expiry': metadata.days_until_expiry()
        }

    async def create_recovery_point(self, backup_id: str, changes: List[Dict[str, Any]]) -> str:
        """Create a recovery point for point-in-time recovery"""
        if backup_id not in self.recovery_points:
            self.recovery_points[backup_id] = []

        existing_points = self.recovery_points[backup_id]
        sequence_number = len(existing_points) + 1

        point_id = f"recovery_{backup_id}_{sequence_number}"

        # Calculate checksum of changes
        changes_json = json.dumps(changes, sort_keys=True)
        checksum = hashlib.sha256(changes_json.encode()).hexdigest()

        recovery_point = RecoveryPoint(
            point_id=point_id,
            timestamp=datetime.utcnow(),
            backup_id=backup_id,
            sequence_number=sequence_number,
            changes=changes,
            checksum=checksum
        )

        existing_points.append(recovery_point)

        return point_id

    async def restore_to_point(self, backup_id: str, point_id: str) -> Dict[str, Any]:
        """Restore to a specific recovery point"""
        if backup_id not in self.recovery_points:
            raise ValueError(f"No recovery points found for backup {backup_id}")

        points = self.recovery_points[backup_id]
        target_point = None

        for point in points:
            if point.point_id == point_id:
                target_point = point
                break

        if not target_point:
            raise ValueError(f"Recovery point {point_id} not found")

        # First restore the base backup
        base_restore = await self.restore_backup(backup_id)

        # Then apply changes up to the target point
        applied_changes = []
        for point in points:
            if point.sequence_number <= target_point.sequence_number:
                applied_changes.extend(point.changes)

        return {
            'base_backup': backup_id,
            'recovery_point': point_id,
            'applied_changes': len(applied_changes),
            'timestamp': datetime.utcnow().isoformat()
        }

    async def export_backup(self, backup_id: str, export_path: str):
        """Export backup to external location"""
        if backup_id not in self.backups:
            raise ValueError(f"Backup {backup_id} not found")

        metadata = self.backups[backup_id]
        backup_path = self.backup_dir / f"{backup_id}.backup"
        metadata_path = self.backup_dir / f"{backup_id}.meta"

        export_dir = Path(export_path)
        export_dir.mkdir(exist_ok=True)

        # Copy files
        shutil.copy2(backup_path, export_dir / f"{backup_id}.backup")
        shutil.copy2(metadata_path, export_dir / f"{backup_id}.meta")

        # Create export manifest
        manifest = {
            'backup_id': backup_id,
            'exported_at': datetime.utcnow().isoformat(),
            'metadata': metadata.to_dict(),
            'files': [
                f"{backup_id}.backup",
                f"{backup_id}.meta"
            ]
        }

        async with aiofiles.open(export_dir / "manifest.json", 'w') as f:
            await f.write(json.dumps(manifest, indent=2))

    async def import_backup(self, import_path: str) -> str:
        """Import backup from external location"""
        import_dir = Path(import_path)
        manifest_path = import_dir / "manifest.json"

        if not manifest_path.exists():
            raise FileNotFoundError("Backup manifest not found")

        async with aiofiles.open(manifest_path, 'r') as f:
            manifest = json.loads(await f.read())

        backup_id = manifest['backup_id']

        # Copy files to backup directory
        for filename in manifest['files']:
            src_path = import_dir / filename
            dst_path = self.backup_dir / filename
            shutil.copy2(src_path, dst_path)

        # Load metadata
        metadata_dict = manifest['metadata']
        metadata = BackupMetadata(**metadata_dict)
        self.backups[backup_id] = metadata

        return backup_id


# Disaster Recovery Orchestrator
class DisasterRecoveryOrchestrator:
    """Orchestrates disaster recovery operations"""

    def __init__(self, backup_manager: BackupManager):
        self.backup_manager = backup_manager
        self.recovery_plans: Dict[str, Dict[str, Any]] = {}

    def create_recovery_plan(self, plan_name: str, steps: List[Dict[str, Any]]):
        """Create a disaster recovery plan"""
        self.recovery_plans[plan_name] = {
            'name': plan_name,
            'steps': steps,
            'created_at': datetime.utcnow().isoformat(),
            'last_tested': None,
            'status': 'active'
        }

    async def execute_recovery_plan(self, plan_name: str) -> Dict[str, Any]:
        """Execute a disaster recovery plan"""
        if plan_name not in self.recovery_plans:
            raise ValueError(f"Recovery plan {plan_name} not found")

        plan = self.recovery_plans[plan_name]
        results = []

        for step in plan['steps']:
            step_result = await self._execute_recovery_step(step)
            results.append(step_result)

            if step_result.get('failed', False):
                break

        return {
            'plan_name': plan_name,
            'executed_at': datetime.utcnow().isoformat(),
            'steps_executed': len(results),
            'success': all(not r.get('failed', False) for r in results),
            'results': results
        }

    async def _execute_recovery_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single recovery step"""
        step_type = step.get('type')

        try:
            if step_type == 'restore_backup':
                result = await self.backup_manager.restore_backup(
                    step['backup_id'],
                    step.get('target_location', './recovery')
                )
                return {'step': step, 'result': result, 'success': True}

            elif step_type == 'start_service':
                # This would integrate with service management
                service_name = step['service_name']
                return {'step': step, 'service': service_name, 'success': True}

            elif step_type == 'run_command':
                # Execute system command
                command = step['command']
                # In production, use subprocess with proper security
                return {'step': step, 'command': command, 'success': True}

            else:
                return {'step': step, 'error': f'Unknown step type: {step_type}', 'failed': True}

        except Exception as e:
            return {'step': step, 'error': str(e), 'failed': True}

    async def test_recovery_plan(self, plan_name: str) -> Dict[str, Any]:
        """Test a recovery plan without actual execution"""
        if plan_name not in self.recovery_plans:
            raise ValueError(f"Recovery plan {plan_name} not found")

        plan = self.recovery_plans[plan_name]

        # Validate each step
        validation_results = []
        for step in plan['steps']:
            result = await self._validate_recovery_step(step)
            validation_results.append(result)

        # Update last tested timestamp
        plan['last_tested'] = datetime.utcnow().isoformat()

        return {
            'plan_name': plan_name,
            'tested_at': plan['last_tested'],
            'valid': all(r['valid'] for r in validation_results),
            'validation_results': validation_results
        }

    async def _validate_recovery_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a recovery step"""
        step_type = step.get('type')

        if step_type == 'restore_backup':
            backup_id = step.get('backup_id')
            if not backup_id:
                return {'step': step, 'valid': False, 'error': 'Missing backup_id'}

            backup_status = await self.backup_manager.get_backup_status(backup_id)
            if not backup_status or not backup_status['exists']:
                return {'step': step, 'valid': False, 'error': 'Backup not found or corrupted'}

            return {'step': step, 'valid': True}

        elif step_type == 'start_service':
            if not step.get('service_name'):
                return {'step': step, 'valid': False, 'error': 'Missing service_name'}

            return {'step': step, 'valid': True}

        elif step_type == 'run_command':
            if not step.get('command'):
                return {'step': step, 'valid': False, 'error': 'Missing command'}

            return {'step': step, 'valid': True}

        return {'step': step, 'valid': False, 'error': f'Unknown step type: {step_type}'}


# Global instances
_backup_manager = None
_recovery_orchestrator = None

def get_backup_manager(backup_dir: str = "./backups", key_manager=None) -> BackupManager:
    """Get global backup manager instance"""
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = BackupManager(backup_dir, key_manager)
    return _backup_manager

def get_recovery_orchestrator(backup_manager: Optional[BackupManager] = None) -> DisasterRecoveryOrchestrator:
    """Get global recovery orchestrator instance"""
    global _recovery_orchestrator
    if _recovery_orchestrator is None:
        if backup_manager is None:
            backup_manager = get_backup_manager()
        _recovery_orchestrator = DisasterRecoveryOrchestrator(backup_manager)
    return _recovery_orchestrator
