"""
Security utilities for Pyserv framework.
Provides file validation, security middleware, and other security features.
"""

from abc import ABC, abstractmethod
from typing import BinaryIO, Dict, Optional, List
import hashlib
import mimetypes
from pathlib import Path
from pyserv.exceptions import FileUploadError, FileTooLarge, InvalidFileType

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

        # Get file size
        file_data.seek(0, 2)  # Seek to end
        file_size = file_data.tell()
        file_data.seek(0)  # Reset to beginning
        
        if file_size > self.max_size:
            results['valid'] = False
            results['errors'].append(f"File too large: {file_size} bytes (max: {self.max_size})")

        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type:
            results['metadata']['mime_type'] = mime_type
            
            # Check MIME type against allowed types
            if not any(mime_type.startswith(allowed) for allowed in self.allowed_types):
                results['valid'] = False
                results['errors'].append(f"Unsupported file type: {mime_type}")

        # Calculate file hash
        file_data.seek(0)
        file_hash = hashlib.sha256(file_data.read()).hexdigest()
        file_data.seek(0)
        results['metadata']['sha256'] = file_hash

        return results

class ClamAVValidator(FileValidator):
    """Virus scanning using ClamAV"""

    def __init__(self, host: str = 'localhost', port: int = 3310):
        self.host = host
        self.port = port

    async def validate(self, file_data: BinaryIO, filename: str) -> Dict:
        """Scan file for viruses using ClamAV"""
        results = {
            'valid': True,
            'errors': [],
            'metadata': {}
        }

        try:
            # Try to import clamd
            import clamd
            client = clamd.ClamdNetworkSocket(self.host, self.port)
            
            # Scan the file
            file_data.seek(0)
            scan_result = client.instream(file_data)
            
            if scan_result and 'stream' in scan_result:
                stream_result = scan_result['stream']
                if isinstance(stream_result, tuple) and len(stream_result) > 1:
                    if stream_result[0] == 'FOUND':
                        results['valid'] = False
                        results['errors'].append(f"Virus detected: {stream_result[1]}")

        except ImportError:
            results['errors'].append("ClamAV not available - install pyclamd")
        except Exception as e:
            results['errors'].append(f"Scan failed: {str(e)}")

        return results

class AWSGuardDutyValidator(FileValidator):
    """Advanced threat detection using AWS GuardDuty"""

    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name

    async def validate(self, file_data: BinaryIO, filename: str) -> Dict:
        """Use AWS GuardDuty for advanced threat detection"""
        results = {
            'valid': True,
            'errors': [],
            'metadata': {}
        }
        
        try:
            import boto3
            # This would integrate with AWS GuardDuty for advanced threat detection
            # Implementation would depend on specific AWS setup
            results['metadata']['aws_guardduty'] = 'not_implemented'
        except ImportError:
            results['errors'].append("AWS SDK not available - install boto3")
        
        return results

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
                max_size=getattr(self.config, 'max_file_size', 100 * 1024 * 1024),
                allowed_types=getattr(self.config, 'allowed_file_types', ['image/', 'text/', 'application/pdf'])
            ))

            # Add virus scanning if configured
            if getattr(self.config, 'enable_virus_scan', False):
                validators.append(ClamAVValidator())

            # Add AWS GuardDuty if configured
            if hasattr(self.config, 'aws_bucket') and self.config.aws_bucket:
                validators.append(AWSGuardDutyValidator(self.config.aws_bucket))

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
        max_size = getattr(self.config, 'max_file_size', 100 * 1024 * 1024)
        if file_size > max_size:
            raise FileTooLarge(filename="", max_size=max_size, actual_size=file_size)

    def check_file_type(self, filename: str, content_type: str = None) -> None:
        """Check if file type is allowed"""
        file_ext = Path(filename).suffix.lower()
        allowed_extensions = getattr(self.config, 'allowed_extensions', ['.jpg', '.png', '.pdf', '.txt'])
        if file_ext not in allowed_extensions:
            raise InvalidFileType(filename=filename, allowed_types=allowed_extensions, actual_type=file_ext)

# Global security manager instance
security_manager = None

def get_security_manager(config=None) -> SecurityManager:
    """Get global security manager instance"""
    global security_manager
    if security_manager is None:
        from pyserv.server.config import AppConfig
        config = config or AppConfig()
        security_manager = SecurityManager(config)
    return security_manager

__all__ = [
    'FileValidator', 'BasicFileValidator', 'ClamAVValidator', 
    'AWSGuardDutyValidator', 'CompositeValidator', 'SecurityManager',
    'get_security_manager'
]