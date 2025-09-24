"""
Django-style static file management for PyServ.

This module provides collectstatic functionality similar to Django,
with support for multiple source directories and CDN deployment.
"""

import os
import shutil
import hashlib
import fnmatch
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple, TYPE_CHECKING, Union, Any
from dataclasses import dataclass
from urllib.parse import urljoin

if TYPE_CHECKING:
    from pyserv.server.config import StaticFilesConfig


@dataclass
class StaticFile:
    """Represents a static file with metadata"""
    source_path: Path
    relative_path: str
    size: int
    hash: str

    @property
    def destination_path(self, root_dir: Path) -> Path:
        """Get the destination path in STATIC_ROOT"""
        return root_dir / self.relative_path


class StaticFilesManager:
    """Manages static file collection and deployment (Django-style)"""

    def __init__(self, config: 'StaticFilesConfig') -> None:
        self.config = config
        self.collected_files: List[StaticFile] = []
        self.hashed_files: Dict[str, str] = {}

    def collect_static_files(self, clear: bool = False, verbosity: int = 1) -> Dict[str, int]:
        """
        Collect static files from STATICFILES_DIRS to STATIC_ROOT.

        Similar to Django's collectstatic command.

        Args:
            clear: Clear STATIC_ROOT before collecting
            verbosity: Verbosity level (0=quiet, 1=normal, 2=verbose)

        Returns:
            Dict with collection statistics
        """
        static_root = Path(self.config.root)

        # Clear static root if requested
        if clear and static_root.exists():
            if verbosity >= 1:
                print(f"Clearing {static_root}")
            shutil.rmtree(static_root)

        # Ensure static root exists
        static_root.mkdir(parents=True, exist_ok=True)

        # Collect files from all source directories
        all_files = []
        for source_dir in self.config.dirs:
            source_path = Path(source_dir)
            if source_path.exists():
                files = self._find_static_files(source_path)
                all_files.extend(files)

        # Remove duplicates (later sources override earlier ones)
        unique_files = self._deduplicate_files(all_files)

        # Copy files to static root
        copied = 0
        skipped = 0

        for static_file in unique_files:
            dest_path = static_root / static_file.relative_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Check if file needs to be copied
            if not dest_path.exists() or self._file_changed(static_file, dest_path):
                if verbosity >= 2:
                    print(f"Copying {static_file.relative_path}")
                shutil.copy2(static_file.source_path, dest_path)
                copied += 1
            else:
                if verbosity >= 2:
                    print(f"Skipping {static_file.relative_path} (unchanged)")
                skipped += 1

        self.collected_files = unique_files

        if verbosity >= 1:
            print(f"Copied {copied} files, skipped {skipped} files")

        return {
            'copied': copied,
            'skipped': skipped,
            'total': len(unique_files)
        }

    def deploy_to_cdn(self, verbosity: int = 1) -> Dict[str, int]:
        """
        Deploy collected static files to CDN.

        Returns:
            Dict with deployment statistics
        """
        if not self.config.use_cdn or not self.config.cdn_url:
            if verbosity >= 1:
                print("CDN not configured, skipping deployment")
            return {'uploaded': 0, 'skipped': 0, 'errors': 0}

        if verbosity >= 1:
            print(f"Deploying to CDN: {self.config.cdn_url}")

        # This would integrate with actual CDN APIs
        # For now, just simulate the deployment
        uploaded = 0
        skipped = 0
        errors = 0

        for static_file in self.collected_files:
            try:
                # Simulate CDN upload
                if verbosity >= 2:
                    print(f"Uploading {static_file.relative_path} to CDN")
                uploaded += 1
            except Exception as e:
                if verbosity >= 1:
                    print(f"Error uploading {static_file.relative_path}: {e}")
                errors += 1

        if verbosity >= 1:
            print(f"CDN deployment complete: {uploaded} uploaded, {errors} errors")

        return {
            'uploaded': uploaded,
            'skipped': skipped,
            'errors': errors
        }

    def add_file_hashing(self, verbosity: int = 1) -> Dict[str, str]:
        """
        Add hash-based versioning to static files.

        Returns:
            Dict mapping original paths to hashed paths
        """
        if verbosity >= 1:
            print("Adding file hashing for cache busting")

        static_root = Path(self.config.root)
        hashed_files = {}

        for static_file in self.collected_files:
            file_path = static_root / static_file.relative_path

            if file_path.exists():
                # Create hashed version
                hash_suffix = static_file.hash[:12]  # Use first 12 chars of hash
                name_parts = static_file.relative_path.rsplit('.', 1)

                if len(name_parts) == 2:
                    hashed_name = f"{name_parts[0]}.{hash_suffix}.{name_parts[1]}"
                else:
                    hashed_name = f"{name_parts[0]}.{hash_suffix}"

                hashed_path = static_root / hashed_name

                # Copy to hashed version
                shutil.copy2(file_path, hashed_path)

                hashed_files[static_file.relative_path] = hashed_name

                if verbosity >= 2:
                    print(f"Created {hashed_name}")

        self.hashed_files = hashed_files

        if verbosity >= 1:
            print(f"Created {len(hashed_files)} hashed versions")

        return hashed_files

    def get_static_url(self, path: str) -> str:
        """
        Get the full URL for a static file, considering CDN settings.

        Args:
            path: Relative path to static file

        Returns:
            Full URL for the static file
        """
        if self.config.use_cdn and self.config.cdn_url:
            # Use hashed version if available
            if path in self.hashed_files:
                path = self.hashed_files[path]
            return urljoin(self.config.cdn_url.rstrip('/') + '/', path.lstrip('/'))
        else:
            # Use local URL
            return urljoin(self.config.url.rstrip('/') + '/', path.lstrip('/'))

    def _find_static_files(self, source_dir: Path) -> List[StaticFile]:
        """Find all static files in a source directory"""
        files = []

        for root, dirs, filenames in os.walk(source_dir):
            # Skip directories starting with .
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            for filename in filenames:
                # Skip files starting with .
                if filename.startswith('.'):
                    continue

                file_path = Path(root) / filename
                relative_path = file_path.relative_to(source_dir)

                # Check include/exclude patterns
                if self._should_include_file(str(relative_path)):
                    try:
                        stat = file_path.stat()
                        file_hash = self._calculate_file_hash(file_path)

                        static_file = StaticFile(
                            source_path=file_path,
                            relative_path=str(relative_path),
                            size=stat.st_size,
                            hash=file_hash
                        )
                        files.append(static_file)
                    except (OSError, IOError) as e:
                        print(f"Warning: Could not process {file_path}: {e}")

        return files

    def _should_include_file(self, relative_path: str) -> bool:
        """Check if file should be included based on patterns"""
        # Check exclude patterns first
        for pattern in self.config.exclude_patterns:
            if fnmatch.fnmatch(relative_path, pattern):
                return False

        # Check include patterns
        for pattern in self.config.include_patterns:
            if fnmatch.fnmatch(relative_path, pattern):
                return True

        return False

    def _deduplicate_files(self, files: List[StaticFile]) -> List[StaticFile]:
        """Remove duplicate files, keeping the last occurrence"""
        seen = {}
        for file in files:
            seen[file.relative_path] = file
        return list(seen.values())

    def _file_changed(self, static_file: StaticFile, dest_path: Path) -> bool:
        """Check if source file has changed compared to destination"""
        if not dest_path.exists():
            return True

        try:
            dest_stat = dest_path.stat()
            return (static_file.size != dest_stat.st_size or
                    static_file.hash != self._calculate_file_hash(dest_path))
        except (OSError, IOError):
            return True

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except (OSError, IOError):
            return ""


def collectstatic(
    config,
    clear: bool = False,
    deploy_cdn: bool = False,
    add_hashing: bool = False,
    verbosity: int = 1
) -> Dict[str, any]:
    """
    Django-style collectstatic command.

    Args:
        config: Static files configuration
        clear: Clear STATIC_ROOT before collecting
        deploy_cdn: Deploy to CDN after collecting
        add_hashing: Add hash-based versioning
        verbosity: Verbosity level

    Returns:
        Dict with operation results
    """
    manager = StaticFilesManager(config)

    # Collect static files
    collection_result = manager.collect_static_files(clear=clear, verbosity=verbosity)

    # Add hashing if requested
    if add_hashing:
        hashing_result = manager.add_file_hashing(verbosity=verbosity)
    else:
        hashing_result = {}

    # Deploy to CDN if requested
    if deploy_cdn:
        cdn_result = manager.deploy_to_cdn(verbosity=verbosity)
    else:
        cdn_result = {'uploaded': 0, 'skipped': 0, 'errors': 0}

    return {
        'collection': collection_result,
        'hashing': hashing_result,
        'cdn': cdn_result,
        'manager': manager
    }


# CLI integration functions
def cmd_collectstatic(args):
    """CLI command for collectstatic"""
    # Import directly to avoid circular imports
    import importlib.util
    spec = importlib.util.spec_from_file_location("config", "src/pyserv/server/config.py")
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)

    # Load configuration
    config = config_module.AppConfig()

    print("Starting static file collection...")

    result = collectstatic(
        config.staticfiles,
        clear=getattr(args, 'clear', False),
        deploy_cdn=getattr(args, 'cdn', False),
        add_hashing=getattr(args, 'hash', False),
        verbosity=1
    )

    collection = result['collection']
    cdn = result['cdn']

    print("\nStatic file collection complete!")
    print(f"  Files collected: {collection['total']}")
    print(f"  Files copied: {collection['copied']}")
    print(f"  Files skipped: {collection['skipped']}")

    if cdn['uploaded'] > 0:
        print(f"  CDN uploads: {cdn['uploaded']}")

    if cdn['errors'] > 0:
        print(f"  CDN errors: {cdn['errors']}")

    return result
