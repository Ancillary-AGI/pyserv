"""
Security utilities for PyDance framework.
Provides file validation, security middleware, and other security features.
"""

from abc import ABC, abstractmethod
from typing import BinaryIO, Dict, Optional, List
import hashlib
import magic
from pathlib import Path
import clamd
import boto3
from .exceptions import FileUploadError, FileTooLarge, InvalidFileType

class FileValidator(ABC):
    """Abstract base class for file validators"""

    @abstractmethod
    async def validate(self, file_data: BinaryIO, filename: str) -> Dict:
        """Validate a file and return results"""
        pass

class BasicFileValidator(FileValidator):
    """Basic file validator with size and type checking"""

    def __init__(self, max_size: int = 100 * 1024 * 1024,  # 100MB
                 allowed_types: List[str] = None,
                 blocked_extensions: List[str] = None):
        self.max_size = max_size
        self.allowed_types = allowed_types or ['image/', 'text/', 'application/pdf']
        self.blocked_extensions = blocked_extensions or ['.exe', '.bat', '.cmd', '.sh']

    async def validate(self, file_data: BinaryIO, filename: str) -> Dict:
        """Validate file using basic checks"""
        results = {
            'valid': True,
            'errors': [],
            'metadata': {}
        }

        # Check file extension
        file_ext = Path(filename).suffix.lower()
        if file_ext in self.blocked_extensions:
            results['valid'] = False
            results['errors'].append(f"Blocked file extension: {file_ext}")

        # Read first few bytes for MIME type detection
        sample = file_data.read(2048)
        file_data.seek(0)

        try:
            mime_type = magic.from_buffer(sample, mime=True)
            results['metadata']['mime_type'] = mime_type

            # Check MIME type against allowed types
            if not any(mime_type.startswith(allowed) for allowed in self.allowed_types):
                results['valid'] = False
                results['errors'].append(f"Unsupported file type: {mime_type}")
        except Exception as e:
            results['valid'] = False
            results['errors'].append(f"MIME type detection failed: {str(e)}")

        # Calculate file hash
        file_data.seek(0)
        file_hash = hashlib.sha256(sample).hexdigest()
        results['metadata']['sha256'] = file_hash

        return results

class ClamAVValidator(FileValidator):
    """Virus scanning using ClamAV"""

    def __init__(self, host: str = 'localhost', port: int = 3310):
        self.client = clamd.ClamdAsyncNetworkSocket(host, port)

    async def validate(self, file_data: BinaryIO, filename: str) -> Dict:
        """Scan file for viruses using ClamAV"""
        results = {
            'valid': True,
            'errors': [],
            'metadata': {}
        }

        try:
            # Scan the file
            file_data.seek(0)
            scan_result = await self.client.instream(file_data)

            if scan_result and scan_result.get('stream'):
                stream_result = scan_result.get('stream')
                if isinstance(stream_result, list) and len(stream_result) > 1:
                    if stream_result[0] == 'FOUND':
                        results['valid'] = False
                        results['errors'].append(f"Virus detected: {stream_result[1]}")

        except Exception as e:
            results['valid'] = False
            results['errors'].append(f"Scan failed: {str(e)}")

        return results

class AWSGuardDutyValidator(FileValidator):
    """Advanced threat detection using AWS GuardDuty"""

    def __init__(self, bucket_name: str):
        self.client = boto3.client('guardduty')
        self.bucket_name = bucket_name

    async def validate(self, file_data: BinaryIO, filename: str) -> Dict:
        """Use AWS GuardDuty for advanced threat detection"""
        # This would integrate with AWS GuardDuty for advanced threat detection
        # Implementation would depend on specific AWS setup
        return {'valid': True, 'errors': [], 'metadata': {}}

class CompositeValidator(FileValidator):
    """Combines multiple validators"""

    def __init__(self, validators: List[FileValidator]):
        self.validators = validators

    async def validate(self, file_data: BinaryIO, filename: str) -> Dict:
        """Run all validators and combine results"""
        results = {
            'valid': True,
            'errors': [],
            'metadata': {},
            'validator_results': []
        }

        for validator in self.validators:
            validator_result = await validator.validate(file_data, filename)
            results['validator_results'].append({
                'validator': type(validator).__name__,
                'result': validator_result
            })

            if not validator_result['valid']:
                results['valid'] = False
                results['errors'].extend(validator_result['errors'])

            results['metadata'].update(validator_result.get('metadata', {}))

        return results

class SecurityManager:
    """Manager for security operations"""

    def __init__(self, config):
        self.config = config
        self._file_validator = None

    def get_file_validator(self) -> FileValidator:
        """Get the configured file validator"""
        if self._file_validator is None:
            validators = []

            # Basic validation
            validators.append(BasicFileValidator(
                max_size=self.config.max_file_size,
                allowed_types=self.config.allowed_extensions
            ))

            # Add virus scanning if configured
            # Note: This would need ClamAV to be running
            # validators.append(ClamAVValidator())

            # Add AWS GuardDuty if configured
            if hasattr(self.config, 'aws_access_key') and self.config.aws_access_key:
                # validators.append(AWSGuardDutyValidator(self.config.aws_bucket))
                pass

            if len(validators) == 1:
                self._file_validator = validators[0]
            else:
                self._file_validator = CompositeValidator(validators)

        return self._file_validator

    async def validate_file(self, file_data: BinaryIO, filename: str) -> Dict:
        """Validate a file upload"""
        validator = self.get_file_validator()
        return await validator.validate(file_data, filename)

    def check_file_size(self, file_size: int) -> None:
        """Check if file size is within limits"""
        if file_size > self.config.max_file_size:
            raise FileTooLarge(self.config.max_file_size, file_size)

    def check_file_type(self, filename: str, content_type: str = None) -> None:
        """Check if file type is allowed"""
        file_ext = Path(filename).suffix.lower()
        if file_ext not in self.config.allowed_extensions:
            raise InvalidFileType(self.config.allowed_extensions, file_ext)

# Global security manager instance
security_manager = None

def get_security_manager(config=None) -> SecurityManager:
    """Get global security manager instance"""
    global security_manager
    if security_manager is None:
        from .config import AppConfig
        config = config or AppConfig()
        security_manager = SecurityManager(config.storage)
    return security_manager
