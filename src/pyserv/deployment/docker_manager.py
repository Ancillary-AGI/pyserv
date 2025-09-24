"""
Docker container management for deployment.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

class DockerManager:
    """
    Manages Docker containers and images for deployment.
    """

    def __init__(self):
        self.logger = logging.getLogger("docker_manager")

    async def build_image(self, source_path: str, image_name: str) -> bool:
        """Build Docker image from source."""
        try:
            import subprocess
            import os

            # Change to source directory
            original_cwd = os.getcwd()
            os.chdir(source_path)

            # Build Docker image
            cmd = [
                "docker", "build",
                "-t", image_name,
                "."
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            # Restore original directory
            os.chdir(original_cwd)

            if result.returncode == 0:
                self.logger.info(f"Successfully built image: {image_name}")
                return True
            else:
                self.logger.error(f"Failed to build image: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Docker build error: {e}")
            return False

    async def push_image(self, image_name: str) -> bool:
        """Push Docker image to registry."""
        try:
            import subprocess

            cmd = ["docker", "push", image_name]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                self.logger.info(f"Successfully pushed image: {image_name}")
                return True
            else:
                self.logger.error(f"Failed to push image: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Docker push error: {e}")
            return False

    async def pull_image(self, image_name: str) -> bool:
        """Pull Docker image from registry."""
        try:
            import subprocess

            cmd = ["docker", "pull", image_name]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                self.logger.info(f"Successfully pulled image: {image_name}")
                return True
            else:
                self.logger.error(f"Failed to pull image: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Docker pull error: {e}")
            return False
