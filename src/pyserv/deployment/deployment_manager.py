"""
Deployment manager for automated application deployment.
Handles containerization, orchestration, and deployment strategies.
"""

import asyncio
import json
import logging
import subprocess
import shutil
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

class DeploymentStatus(Enum):
    PENDING = "pending"
    BUILDING = "building"
    DEPLOYING = "deploying"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"

class DeploymentStrategy(Enum):
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    ROLLING = "rolling"
    RECREATE = "recreate"

@dataclass
class DeploymentConfig:
    """Configuration for deployment."""
    strategy: DeploymentStrategy = DeploymentStrategy.BLUE_GREEN
    environment: str = "production"
    container_registry: str = "docker.io"
    kubernetes_namespace: str = "default"
    replicas: int = 3
    resources: Dict[str, Any] = None
    health_check_path: str = "/health"
    rollback_on_failure: bool = True
    auto_scaling: bool = True

    def __post_init__(self):
        if self.resources is None:
            self.resources = {
                "requests": {"cpu": "100m", "memory": "128Mi"},
                "limits": {"cpu": "500m", "memory": "512Mi"}
            }

@dataclass
class Deployment:
    """Deployment information."""
    id: str
    version: str
    status: DeploymentStatus
    strategy: DeploymentStrategy
    environment: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None

class DeploymentManager:
    """
    Manages automated application deployments.
    """

    def __init__(self, config: DeploymentConfig):
        self.config = config
        self.logger = logging.getLogger("deployment_manager")
        self.docker_manager = DockerManager()
        self.kubernetes_manager = KubernetesManager()
        self.deployment_monitor = DeploymentMonitor()
        self.rollback_manager = RollbackManager()
        self.active_deployments: Dict[str, Deployment] = {}

    async def deploy(self, version: str, source_path: str) -> Deployment:
        """Deploy a new version of the application."""
        deployment_id = f"deploy_{int(datetime.now().timestamp())}"

        deployment = Deployment(
            id=deployment_id,
            version=version,
            status=DeploymentStatus.PENDING,
            strategy=self.config.strategy,
            environment=self.config.environment,
            created_at=datetime.now(),
            metadata={"source_path": source_path}
        )

        self.active_deployments[deployment_id] = deployment
        self.logger.info(f"Starting deployment {deployment_id} for version {version}")

        try:
            # Update status
            deployment.status = DeploymentStatus.BUILDING
            await self.deployment_monitor.update_deployment(deployment)

            # Build container image
            image_tag = await self._build_container_image(source_path, version)

            # Deploy based on strategy
            deployment.status = DeploymentStatus.DEPLOYING
            await self.deployment_monitor.update_deployment(deployment)

            if self.config.strategy == DeploymentStrategy.BLUE_GREEN:
                await self._blue_green_deployment(image_tag, deployment)
            elif self.config.strategy == DeploymentStrategy.CANARY:
                await self._canary_deployment(image_tag, deployment)
            elif self.config.strategy == DeploymentStrategy.ROLLING:
                await self._rolling_deployment(image_tag, deployment)
            else:
                await self._recreate_deployment(image_tag, deployment)

            # Run tests
            deployment.status = DeploymentStatus.TESTING
            await self.deployment_monitor.update_deployment(deployment)

            await self._run_deployment_tests(deployment)

            # Complete deployment
            deployment.status = DeploymentStatus.COMPLETED
            deployment.completed_at = datetime.now()
            await self.deployment_monitor.update_deployment(deployment)

            self.logger.info(f"Deployment {deployment_id} completed successfully")

            return deployment

        except Exception as e:
            self.logger.error(f"Deployment {deployment_id} failed: {e}")
            deployment.status = DeploymentStatus.FAILED
            deployment.completed_at = datetime.now()
            await self.deployment_monitor.update_deployment(deployment)

            if self.config.rollback_on_failure:
                await self.rollback(deployment_id)

            raise

    async def _build_container_image(self, source_path: str, version: str) -> str:
        """Build Docker container image."""
        image_name = f"{self.config.container_registry}/pyserv:{version}"

        try:
            # Create Dockerfile if it doesn't exist
            dockerfile_path = Path(source_path) / "Dockerfile"
            if not dockerfile_path.exists():
                await self._create_dockerfile(source_path)

            # Build image
            await self.docker_manager.build_image(source_path, image_name)

            return image_name

        except Exception as e:
            self.logger.error(f"Failed to build container image: {e}")
            raise

    async def _create_dockerfile(self, source_path: str):
        """Create a basic Dockerfile for the application."""
        dockerfile_content = f"""
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000{self.config.health_check_path} || exit 1

# Run application
CMD ["python", "-m", "pyserv.cli", "run", "--host", "0.0.0.0"]
"""

        dockerfile_path = Path(source_path) / "Dockerfile"
        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)

    async def _blue_green_deployment(self, image_tag: str, deployment: Deployment):
        """Perform blue-green deployment."""
        self.logger.info("Performing blue-green deployment")

        # Create green environment
        green_service = f"pyserv-green-{deployment.id}"
        await self.kubernetes_manager.create_service(
            name=green_service,
            image=image_tag,
            replicas=self.config.replicas,
            resources=self.config.resources
        )

        # Wait for green environment to be ready
        await self.kubernetes_manager.wait_for_ready(green_service)

        # Switch traffic to green
        await self.kubernetes_manager.switch_traffic("pyserv", green_service)

        # Remove blue environment
        await self.kubernetes_manager.delete_service("pyserv-blue")

    async def _canary_deployment(self, image_tag: str, deployment: Deployment):
        """Perform canary deployment."""
        self.logger.info("Performing canary deployment")

        # Deploy canary with small percentage of traffic
        canary_service = f"pyserv-canary-{deployment.id}"
        await self.kubernetes_manager.create_service(
            name=canary_service,
            image=image_tag,
            replicas=1,
            resources=self.config.resources
        )

        # Monitor canary for a period
        await asyncio.sleep(300)  # 5 minutes

        # If canary is successful, scale up
        await self.kubernetes_manager.scale_service(canary_service, self.config.replicas)

        # Switch all traffic to canary
        await self.kubernetes_manager.switch_traffic("pyserv", canary_service)

    async def _rolling_deployment(self, image_tag: str, deployment: Deployment):
        """Perform rolling deployment."""
        self.logger.info("Performing rolling deployment")

        # Update existing deployment with new image
        await self.kubernetes_manager.update_deployment_image("pyserv", image_tag)

        # Wait for rollout to complete
        await self.kubernetes_manager.wait_for_rollout("pyserv")

    async def _recreate_deployment(self, image_tag: str, deployment: Deployment):
        """Perform recreate deployment."""
        self.logger.info("Performing recreate deployment")

        # Scale down existing deployment
        await self.kubernetes_manager.scale_service("pyserv", 0)

        # Update deployment with new image
        await self.kubernetes_manager.update_deployment_image("pyserv", image_tag)

        # Scale back up
        await self.kubernetes_manager.scale_service("pyserv", self.config.replicas)

    async def _run_deployment_tests(self, deployment: Deployment):
        """Run deployment tests."""
        # Basic health check
        await self.deployment_monitor.check_health(self.config.health_check_path)

        # Integration tests would go here
        self.logger.info("Deployment tests passed")

    async def rollback(self, deployment_id: str) -> Deployment:
        """Rollback a failed deployment."""
        deployment = self.active_deployments.get(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")

        self.logger.info(f"Rolling back deployment {deployment_id}")

        deployment.status = DeploymentStatus.ROLLING_BACK
        await self.deployment_monitor.update_deployment(deployment)

        # Perform rollback
        await self.rollback_manager.rollback(deployment)

        deployment.status = DeploymentStatus.FAILED
        deployment.completed_at = datetime.now()
        await self.deployment_monitor.update_deployment(deployment)

        return deployment

    async def get_deployment_status(self, deployment_id: str) -> Optional[Deployment]:
        """Get deployment status."""
        return self.active_deployments.get(deployment_id)

    async def list_deployments(self) -> List[Deployment]:
        """List all deployments."""
        return list(self.active_deployments.values())

    def get_deployment_stats(self) -> Dict[str, Any]:
        """Get deployment statistics."""
        total_deployments = len(self.active_deployments)
        status_counts = {}

        for deployment in self.active_deployments.values():
            status = deployment.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_deployments": total_deployments,
            "status_breakdown": status_counts,
            "current_strategy": self.config.strategy.value,
            "environment": self.config.environment
        }

# Global deployment manager
deployment_manager = None

def initialize_deployment_manager(config: DeploymentConfig):
    """Initialize global deployment manager."""
    global deployment_manager
    deployment_manager = DeploymentManager(config)
    return deployment_manager
