"""
Advanced file handling system for PyDance framework.
Provides file validation, processing, resizing, compression, and cloud storage.
"""

from typing import BinaryIO, Dict, Any, Optional, List, Tuple
from pathlib import Path
import asyncio
import hashlib
import mimetypes
from PIL import Image
import io
import gzip
import zipfile
import tempfile
import os

from .storage import get_storage_manager
from .security import get_security_manager
from .exceptions import FileTooLarge, InvalidFileType, FileUploadError


class FileProcessor:
    """File processing utilities"""

    @staticmethod
    def get_file_info(file_data: BinaryIO, filename: str) -> Dict[str, Any]:
        """Get comprehensive file information"""
        file_data.seek(0)
        content = file_data.read()
        file_data.seek(0)

        return {
            'filename': filename,
            'size': len(content),
            'mime_type': mimetypes.guess_type(filename)[0],
            'extension': Path(filename).suffix.lower(),
            'hash_md5': hashlib.md5(content).hexdigest(),
            'hash_sha3_256': hashlib.sha3_256(content).hexdigest(),
        }

    @staticmethod
    def resize_image(file_data: BinaryIO, max_width: int = 1920,
                    max_height: int = 1080, quality: int = 85) -> BinaryIO:
        """Resize image while maintaining aspect ratio"""
        file_data.seek(0)
        image = Image.open(file_data)

        # Calculate new dimensions
        width, height = image.size
        if width > max_width or height > max_height:
            ratio = min(max_width / width, max_height / height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)

            # Resize image
            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Save to buffer
            output_buffer = io.BytesIO()
            if image.format == 'JPEG':
                resized_image.save(output_buffer, format='JPEG', quality=quality, optimize=True)
            elif image.format == 'PNG':
                resized_image.save(output_buffer, format='PNG', optimize=True)
            else:
                resized_image.save(output_buffer, format=image.format)

            output_buffer.seek(0)
            return output_buffer

        # Return original if no resizing needed
        file_data.seek(0)
        return file_data

    @staticmethod
    def compress_file(file_data: BinaryIO, compression_type: str = 'gzip') -> BinaryIO:
        """Compress file data"""
        file_data.seek(0)
        content = file_data.read()

        output_buffer = io.BytesIO()

        if compression_type == 'gzip':
            with gzip.GzipFile(fileobj=output_buffer, mode='wb') as f:
                f.write(content)
        elif compression_type == 'deflate':
            import zlib
            compressed = zlib.compress(content)
            output_buffer.write(compressed)
        else:
            # No compression
            output_buffer.write(content)

        output_buffer.seek(0)
        return output_buffer

    @staticmethod
    def create_thumbnail(file_data: BinaryIO, size: Tuple[int, int] = (200, 200)) -> BinaryIO:
        """Create thumbnail from image"""
        file_data.seek(0)
        image = Image.open(file_data)

        # Create square thumbnail
        image.thumbnail(size, Image.Resampling.LANCZOS)

        # Create new image with white background if needed
        thumb = Image.new('RGB', size, (255, 255, 255))
        # Center the image
        x = (size[0] - image.size[0]) // 2
        y = (size[1] - image.size[1]) // 2
        thumb.paste(image, (x, y))

        output_buffer = io.BytesIO()
        thumb.save(output_buffer, format='JPEG', quality=80)
        output_buffer.seek(0)
        return output_buffer

    @staticmethod
    def convert_format(file_data: BinaryIO, target_format: str) -> BinaryIO:
        """Convert image to different format"""
        file_data.seek(0)
        image = Image.open(file_data)

        output_buffer = io.BytesIO()

        if target_format.upper() == 'WEBP':
            image.save(output_buffer, format='WEBP', quality=80)
        elif target_format.upper() == 'JPEG':
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            image.save(output_buffer, format='JPEG', quality=85)
        elif target_format.upper() == 'PNG':
            image.save(output_buffer, format='PNG', optimize=True)

        output_buffer.seek(0)
        return output_buffer


class FileUploadHandler:
    """Advanced file upload handler with validation and processing"""

    def __init__(self, config=None):
        self.config = config
        self.storage = get_storage_manager(config)
        self.security = get_security_manager(config)

    async def upload_file(self, file_data: BinaryIO, filename: str,
                         options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Upload file with comprehensive processing"""
        options = options or {}

        # Validate file
        validation_result = await self.security.validate_file(file_data, filename)
        if not validation_result['valid']:
            raise FileUploadError(f"File validation failed: {', '.join(validation_result['errors'])}")

        # Get file info
        file_info = FileProcessor.get_file_info(file_data, filename)

        # Check size limits
        if file_info['size'] > self.config.max_file_size:
            raise FileTooLarge(self.config.max_file_size, file_info['size'])

        # Process file based on type and options
        processed_data = await self._process_file(file_data, filename, options)

        # Generate unique filename
        unique_filename = self._generate_unique_filename(filename, file_info)

        # Upload to storage
        storage_key = await self.storage.put(unique_filename, processed_data)

        # Create thumbnails if image
        thumbnails = {}
        if file_info['mime_type'] and file_info['mime_type'].startswith('image/'):
            thumbnails = await self._create_thumbnails(processed_data, unique_filename, options)

        return {
            'original_filename': filename,
            'filename': unique_filename,
            'storage_key': storage_key,
            'size': file_info['size'],
            'mime_type': file_info['mime_type'],
            'hash_sha256': file_info['hash_sha256'],
            'url': await self.storage.get_url(unique_filename),
            'thumbnails': thumbnails,
            'metadata': validation_result.get('metadata', {})
        }

    async def _process_file(self, file_data: BinaryIO, filename: str,
                           options: Dict[str, Any]) -> BinaryIO:
        """Process file based on options"""
        processed_data = file_data

        # Resize images
        if options.get('resize') and filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            max_width = options['resize'].get('max_width', 1920)
            max_height = options['resize'].get('max_height', 1080)
            quality = options['resize'].get('quality', 85)
            processed_data = FileProcessor.resize_image(processed_data, max_width, max_height, quality)

        # Convert format
        if options.get('convert_format'):
            processed_data = FileProcessor.convert_format(processed_data, options['convert_format'])

        # Compress
        if options.get('compress'):
            compression_type = options['compress'].get('type', 'gzip')
            processed_data = FileProcessor.compress_file(processed_data, compression_type)

        return processed_data

    async def _create_thumbnails(self, file_data: BinaryIO, filename: str,
                                options: Dict[str, Any]) -> Dict[str, str]:
        """Create thumbnails for image files"""
        thumbnails = {}

        if options.get('thumbnails'):
            for thumb_name, thumb_config in options['thumbnails'].items():
                size = thumb_config.get('size', (200, 200))
                thumb_data = FileProcessor.create_thumbnail(file_data, size)

                thumb_filename = f"thumb_{thumb_name}_{filename}"
                thumb_key = await self.storage.put(thumb_filename, thumb_data)
                thumbnails[thumb_name] = {
                    'key': thumb_key,
                    'url': await self.storage.get_url(thumb_filename),
                    'size': size
                }

        return thumbnails

    def _generate_unique_filename(self, filename: str, file_info: Dict[str, Any]) -> str:
        """Generate unique filename"""
        import uuid
        import time

        name, ext = os.path.splitext(filename)
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]

        return f"{name}_{timestamp}_{unique_id}{ext}"

    async def delete_file(self, filename: str) -> bool:
        """Delete file from storage"""
        return await self.storage.delete(filename)

    async def get_file_url(self, filename: str, expires_in: int = 3600) -> str:
        """Get signed URL for file access"""
        return await self.storage.get_url(filename, expires_in)

    async def batch_upload(self, files: List[Tuple[BinaryIO, str]],
                          options: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Upload multiple files"""
        results = []
        for file_data, filename in files:
            try:
                result = await self.upload_file(file_data, filename, options)
                results.append(result)
            except Exception as e:
                results.append({
                    'filename': filename,
                    'error': str(e),
                    'success': False
                })

        return results


class FileValidator:
    """Customizable file validation system"""

    def __init__(self, config=None):
        self.config = config or {}
        self._custom_validators = []

    def add_validator(self, validator_func):
        """Add custom validation function"""
        self._custom_validators.append(validator_func)

    async def validate(self, file_data: BinaryIO, filename: str) -> Dict[str, Any]:
        """Run all validations"""
        results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        # Built-in validations
        await self._validate_size(file_data, results)
        await self._validate_type(filename, results)
        await self._validate_content(file_data, filename, results)

        # Custom validations
        for validator in self._custom_validators:
            try:
                if asyncio.iscoroutinefunction(validator):
                    await validator(file_data, filename, results)
                else:
                    validator(file_data, filename, results)
            except Exception as e:
                results['errors'].append(f"Validation error: {str(e)}")
                results['valid'] = False

        return results

    async def _validate_size(self, file_data: BinaryIO, results: Dict):
        """Validate file size"""
        file_data.seek(0, 2)  # Seek to end
        size = file_data.tell()
        file_data.seek(0)  # Reset position

        max_size = self.config.get('max_size', 10 * 1024 * 1024)  # 10MB default
        if size > max_size:
            results['valid'] = False
            results['errors'].append(f"File too large: {size} bytes (max: {max_size} bytes)")

    async def _validate_type(self, filename: str, results: Dict):
        """Validate file type"""
        allowed_types = self.config.get('allowed_types', [])
        if allowed_types:
            mime_type, _ = mimetypes.guess_type(filename)
            if mime_type not in allowed_types:
                results['valid'] = False
                results['errors'].append(f"File type not allowed: {mime_type}")

    async def _validate_content(self, file_data: BinaryIO, filename: str, results: Dict):
        """Validate file content"""
        # This could include virus scanning, content analysis, etc.
        pass


# Global instances
file_handler = None
file_validator = None

def get_file_handler(config=None):
    """Get global file handler instance"""
    global file_handler
    if file_handler is None:
        file_handler = FileUploadHandler(config)
    return file_handler

def get_file_validator(config=None):
    """Get global file validator instance"""
    global file_validator
    if file_validator is None:
        file_validator = FileValidator(config)
    return file_validator
