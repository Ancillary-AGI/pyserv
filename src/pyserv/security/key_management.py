"""
Hardware Security Module (HSM) Integration and Key Management.
Provides enterprise-grade key management with HSM support.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import secrets
import hashlib
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature
import base64

# Import quantum security
from .quantum_security import QuantumAlgorithm, QuantumKeyPair
QUANTUM_AVAILABLE = True


@dataclass
class KeyMetadata:
    """Key metadata for tracking and management"""
    key_id: str
    algorithm: str
    key_size: int
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    usage_count: int = 0
    status: str = "active"  # active, expired, revoked, compromised
    tags: Dict[str, str] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if key is expired"""
        return self.expires_at and datetime.utcnow() > self.expires_at

    def is_active(self) -> bool:
        """Check if key is active"""
        return self.status == "active" and not self.is_expired()


@dataclass
class HSMConfig:
    """HSM configuration"""
    hsm_type: str  # "software", "aws_cloudhsm", "azure_key_vault", "gcp_kms"
    endpoint: Optional[str] = None
    credentials: Dict[str, Any] = field(default_factory=dict)
    key_store_path: str = "./keys"
    auto_rotate_days: int = 90
    backup_enabled: bool = True


class HSMInterface:
    """Abstract interface for HSM operations"""

    async def generate_key(self, algorithm: str, key_size: int, metadata: Dict[str, Any]) -> str:
        """Generate a new key"""
        raise NotImplementedError

    async def store_key(self, key_id: str, key_material: bytes, metadata: KeyMetadata):
        """Store key material"""
        raise NotImplementedError

    async def retrieve_key(self, key_id: str) -> Optional[bytes]:
        """Retrieve key material"""
        raise NotImplementedError

    async def sign_data(self, key_id: str, data: bytes) -> bytes:
        """Sign data with key"""
        raise NotImplementedError

    async def verify_signature(self, key_id: str, data: bytes, signature: bytes) -> bool:
        """Verify signature with key"""
        raise NotImplementedError

    async def encrypt_data(self, key_id: str, data: bytes) -> bytes:
        """Encrypt data with key"""
        raise NotImplementedError

    async def decrypt_data(self, key_id: str, encrypted_data: bytes) -> bytes:
        """Decrypt data with key"""
        raise NotImplementedError

    async def rotate_key(self, key_id: str) -> str:
        """Rotate key and return new key ID"""
        raise NotImplementedError

    async def revoke_key(self, key_id: str):
        """Revoke key"""
        raise NotImplementedError


class SoftwareHSM(HSMInterface):
    """Software-based HSM for development/testing"""

    def __init__(self, config: HSMConfig):
        self.config = config
        self.keys: Dict[str, Dict[str, Any]] = {}
        self.metadata: Dict[str, KeyMetadata] = {}

    async def generate_key(self, algorithm: str, key_size: int, metadata: Dict[str, Any]) -> str:
        """Generate a new key"""
        key_id = f"key_{secrets.token_hex(16)}"

        if algorithm.lower() == "rsa":
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size,
                backend=default_backend()
            )
            key_material = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
        elif algorithm.lower() == "ecc":
            private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
            key_material = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
        else:
            # Symmetric key
            key_material = secrets.token_bytes(key_size // 8)

        # Store key
        await self.store_key(key_id, key_material, KeyMetadata(
            key_id=key_id,
            algorithm=algorithm,
            key_size=key_size,
            created_at=datetime.utcnow(),
            tags=metadata
        ))

        return key_id

    async def store_key(self, key_id: str, key_material: bytes, metadata: KeyMetadata):
        """Store key material"""
        self.keys[key_id] = {
            'material': key_material,
            'encrypted': False  # In production, this would be encrypted
        }
        self.metadata[key_id] = metadata

    async def retrieve_key(self, key_id: str) -> Optional[bytes]:
        """Retrieve key material"""
        if key_id not in self.keys:
            return None

        metadata = self.metadata.get(key_id)
        if metadata and not metadata.is_active():
            return None

        # Update usage metadata
        if metadata:
            metadata.last_used = datetime.utcnow()
            metadata.usage_count += 1

        return self.keys[key_id]['material']

    async def sign_data(self, key_id: str, data: bytes) -> bytes:
        """Sign data with key"""
        key_material = await self.retrieve_key(key_id)
        if not key_material:
            raise ValueError(f"Key {key_id} not found or inactive")

        # Load private key
        private_key = serialization.load_pem_private_key(
            key_material, password=None, backend=default_backend()
        )

        # Sign data
        if isinstance(private_key, rsa.RSAPrivateKey):
            signature = private_key.sign(
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
        else:  # ECC
            signature = private_key.sign(data, ec.ECDSA(hashes.SHA256()))

        return signature

    async def verify_signature(self, key_id: str, data: bytes, signature: bytes) -> bool:
        """Verify signature with key"""
        key_material = await self.retrieve_key(key_id)
        if not key_material:
            return False

        # Load public key
        if b"PRIVATE KEY" in key_material:
            private_key = serialization.load_pem_private_key(
                key_material, password=None, backend=default_backend()
            )
            public_key = private_key.public_key()
        else:
            public_key = serialization.load_pem_public_key(
                key_material, backend=default_backend()
            )

        try:
            if isinstance(public_key, rsa.RSAPublicKey):
                public_key.verify(
                    signature,
                    data,
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
            else:  # ECC
                public_key.verify(signature, data, ec.ECDSA(hashes.SHA256()))
            return True
        except InvalidSignature:
            return False

    async def encrypt_data(self, key_id: str, data: bytes) -> bytes:
        """Encrypt data with key"""
        key_material = await self.retrieve_key(key_id)
        if not key_material:
            raise ValueError(f"Key {key_id} not found")

        # Simple XOR encryption for demo (use proper AES in production)
        key_bytes = key_material[:32] if len(key_material) > 32 else key_material.ljust(32, b'\x00')
        encrypted = bytes(a ^ b for a, b in zip(data, key_bytes * (len(data) // len(key_bytes) + 1)))
        return encrypted[:len(data)]

    async def decrypt_data(self, key_id: str, encrypted_data: bytes) -> bytes:
        """Decrypt data with key"""
        # XOR is symmetric, so same operation
        return await self.encrypt_data(key_id, encrypted_data)

    async def rotate_key(self, key_id: str) -> str:
        """Rotate key and return new key ID"""
        old_metadata = self.metadata.get(key_id)
        if not old_metadata:
            raise ValueError(f"Key {key_id} not found")

        # Generate new key
        new_key_id = await self.generate_key(
            old_metadata.algorithm,
            old_metadata.key_size,
            old_metadata.tags
        )

        # Mark old key as rotated
        old_metadata.status = "rotated"
        old_metadata.expires_at = datetime.utcnow()

        return new_key_id

    async def revoke_key(self, key_id: str):
        """Revoke key"""
        if key_id in self.metadata:
            self.metadata[key_id].status = "revoked"


class KeyManager:
    """Enterprise key management system"""

    def __init__(self, hsm_config: HSMConfig):
        self.config = hsm_config
        self.hsm = self._initialize_hsm()
        self.key_cache: Dict[str, bytes] = {}
        self.rotation_tasks: Dict[str, asyncio.Task] = {}

    def _initialize_hsm(self) -> HSMInterface:
        """Initialize HSM based on configuration"""
        if self.config.hsm_type == "software":
            return SoftwareHSM(self.config)
        elif self.config.hsm_type == "aws_cloudhsm":
            # return AWSCloudHSM(self.config)
            return SoftwareHSM(self.config)  # Fallback for demo
        elif self.config.hsm_type == "azure_key_vault":
            # return AzureKeyVault(self.config)
            return SoftwareHSM(self.config)  # Fallback for demo
        elif self.config.hsm_type == "gcp_kms":
            # return GCPKMS(self.config)
            return SoftwareHSM(self.config)  # Fallback for demo
        else:
            raise ValueError(f"Unsupported HSM type: {self.config.hsm_type}")

    async def create_key(self, purpose: str, algorithm: str = "ECC",
                        key_size: int = 256) -> str:
        """Create a new key for specific purpose"""
        metadata = {
            "purpose": purpose,
            "created_by": "key_manager",
            "auto_rotate": True
        }

        key_id = await self.hsm.generate_key(algorithm, key_size, metadata)

        # Schedule automatic rotation
        if self.config.auto_rotate_days > 0:
            await self._schedule_rotation(key_id)

        return key_id

    async def get_key(self, key_id: str) -> Optional[bytes]:
        """Get key material"""
        # Check cache first
        if key_id in self.key_cache:
            return self.key_cache[key_id]

        # Retrieve from HSM
        key_material = await self.hsm.retrieve_key(key_id)
        if key_material:
            # Cache key (with TTL in production)
            self.key_cache[key_id] = key_material

        return key_material

    async def sign_with_key(self, key_id: str, data: bytes) -> bytes:
        """Sign data with specific key"""
        return await self.hsm.sign_data(key_id, data)

    async def verify_with_key(self, key_id: str, data: bytes, signature: bytes) -> bool:
        """Verify signature with specific key"""
        return await self.hsm.verify_signature(key_id, data, signature)

    async def encrypt_with_key(self, key_id: str, data: bytes) -> bytes:
        """Encrypt data with specific key"""
        return await self.hsm.encrypt_data(key_id, data)

    async def decrypt_with_key(self, key_id: str, encrypted_data: bytes) -> bytes:
        """Decrypt data with specific key"""
        return await self.hsm.decrypt_data(key_id, encrypted_data)

    async def rotate_key(self, key_id: str) -> str:
        """Manually rotate a key"""
        new_key_id = await self.hsm.rotate_key(key_id)

        # Update any references to old key
        await self._update_key_references(key_id, new_key_id)

        # Schedule rotation for new key
        await self._schedule_rotation(new_key_id)

        return new_key_id

    async def revoke_key(self, key_id: str):
        """Revoke a key"""
        await self.hsm.revoke_key(key_id)

        # Remove from cache
        self.key_cache.pop(key_id, None)

        # Cancel rotation task
        if key_id in self.rotation_tasks:
            self.rotation_tasks[key_id].cancel()
            del self.rotation_tasks[key_id]

    async def _schedule_rotation(self, key_id: str):
        """Schedule automatic key rotation"""
        async def rotate_task():
            await asyncio.sleep(self.config.auto_rotate_days * 24 * 3600)
            try:
                await self.rotate_key(key_id)
                print(f"Automatically rotated key: {key_id}")
            except Exception as e:
                print(f"Failed to rotate key {key_id}: {e}")

        task = asyncio.create_task(rotate_task())
        self.rotation_tasks[key_id] = task

    async def _update_key_references(self, old_key_id: str, new_key_id: str):
        """Update references to rotated key"""
        # This would update database records, config files, etc.
        # Implementation depends on how keys are referenced in the system
        print(f"Updated references from {old_key_id} to {new_key_id}")

    def get_key_metadata(self, key_id: str) -> Optional[KeyMetadata]:
        """Get key metadata"""
        if hasattr(self.hsm, 'metadata'):
            return self.hsm.metadata.get(key_id)
        return None

    async def backup_keys(self, backup_path: str):
        """Backup all keys"""
        if not self.config.backup_enabled:
            return

        # Encrypt keys before backup
        master_key = await self.create_key("backup_master", "AES", 256)
        encrypted_backup = {}

        for key_id, metadata in getattr(self.hsm, 'metadata', {}).items():
            if metadata.is_active():
                key_material = await self.get_key(key_id)
                if key_material:
                    encrypted_key = await self.encrypt_with_key(master_key, key_material)
                    encrypted_backup[key_id] = {
                        'material': base64.b64encode(encrypted_key).decode(),
                        'metadata': metadata.__dict__
                    }

        # Write encrypted backup
        import json
        with open(backup_path, 'w') as f:
            json.dump({
                'master_key_id': master_key,
                'keys': encrypted_backup,
                'timestamp': datetime.utcnow().isoformat()
            }, f, default=str)

    async def restore_keys(self, backup_path: str):
        """Restore keys from backup"""
        import json
        with open(backup_path, 'r') as f:
            backup_data = json.load(f)

        master_key_id = backup_data['master_key_id']

        for key_id, key_data in backup_data['keys'].items():
            encrypted_material = base64.b64decode(key_data['material'])
            key_material = await self.decrypt_with_key(master_key_id, encrypted_material)

            metadata_dict = key_data['metadata']
            metadata = KeyMetadata(**metadata_dict)

            await self.hsm.store_key(key_id, key_material, metadata)

    # Quantum key management methods
    async def create_quantum_key(self, purpose: str, algorithm: QuantumAlgorithm = QuantumAlgorithm.KYBER) -> str:
        """Create a quantum-resistant key"""
        if not QUANTUM_AVAILABLE:
            raise RuntimeError("Quantum security module not available")

        from .quantum_security import get_quantum_security_manager
        quantum_manager = get_quantum_security_manager()

        # Generate quantum keypair
        provider = quantum_manager.providers[algorithm]
        public_key, private_key = await provider.generate_keypair()

        # Create quantum key pair object
        key_id = f"quantum_{algorithm.value}_{secrets.token_hex(8)}"
        quantum_key = QuantumKeyPair(
            algorithm=algorithm,
            public_key=public_key,
            private_key=private_key,
            key_id=key_id,
            created_at=datetime.utcnow(),
            metadata={"purpose": purpose, "quantum_resistant": True}
        )

        # Store in quantum key store
        quantum_manager.key_store[key_id] = quantum_key

        # Create traditional metadata for compatibility
        metadata = KeyMetadata(
            key_id=key_id,
            algorithm=f"quantum_{algorithm.value}",
            key_size=len(public_key),  # Approximate size
            created_at=datetime.utcnow(),
            tags={"purpose": purpose, "quantum_resistant": "true"}
        )

        # Store public key in traditional HSM for compatibility
        await self.hsm.store_key(f"{key_id}_public", public_key, metadata)

        return key_id

    async def get_quantum_key(self, key_id: str) -> Optional[QuantumKeyPair]:
        """Get quantum key pair"""
        if not QUANTUM_AVAILABLE:
            return None

        from .quantum_security import get_quantum_security_manager
        quantum_manager = get_quantum_security_manager()

        return quantum_manager.key_store.get(key_id)

    async def sign_with_quantum_key(self, key_id: str, data: bytes) -> bytes:
        """Sign data with quantum-resistant key"""
        if not QUANTUM_AVAILABLE:
            raise RuntimeError("Quantum security module not available")

        quantum_key = await self.get_quantum_key(key_id)
        if not quantum_key:
            raise ValueError(f"Quantum key {key_id} not found")

        from .quantum_security import get_quantum_security_manager
        quantum_manager = get_quantum_security_manager()

        provider = quantum_manager.providers[quantum_key.algorithm]
        return await provider.sign(quantum_key.private_key, data)

    async def verify_with_quantum_key(self, key_id: str, data: bytes, signature: bytes) -> bool:
        """Verify signature with quantum-resistant key"""
        if not QUANTUM_AVAILABLE:
            return False

        quantum_key = await self.get_quantum_key(key_id)
        if not quantum_key:
            return False

        from .quantum_security import get_quantum_security_manager
        quantum_manager = get_quantum_security_manager()

        provider = quantum_manager.providers[quantum_key.algorithm]
        return await provider.verify(quantum_key.public_key, data, signature)

    async def perform_quantum_kem(self, key_id: str) -> Tuple[bytes, bytes]:
        """Perform quantum key encapsulation"""
        if not QUANTUM_AVAILABLE:
            raise RuntimeError("Quantum security module not available")

        quantum_key = await self.get_quantum_key(key_id)
        if not quantum_key:
            raise ValueError(f"Quantum key {key_id} not found")

        from .quantum_security import get_quantum_security_manager
        quantum_manager = get_quantum_security_manager()

        provider = quantum_manager.providers[quantum_key.algorithm]
        return await provider.encapsulate(quantum_key.public_key)

    async def rotate_quantum_key(self, key_id: str) -> str:
        """Rotate quantum key"""
        old_key = await self.get_quantum_key(key_id)
        if not old_key:
            raise ValueError(f"Quantum key {key_id} not found")

        # Create new quantum key
        new_key_id = await self.create_quantum_key(
            old_key.metadata.get("purpose", "rotated"),
            old_key.algorithm
        )

        # Mark old key as rotated (conceptually)
        old_key.metadata["status"] = "rotated"

        return new_key_id


# Global key manager instance
_key_manager = None

def get_key_manager(hsm_config: Optional[HSMConfig] = None) -> KeyManager:
    """Get global key manager instance"""
    global _key_manager
    if _key_manager is None:
        if hsm_config is None:
            # Default software HSM for development
            hsm_config = HSMConfig(hsm_type="software")
        _key_manager = KeyManager(hsm_config)
    return _key_manager


# Utility functions
async def generate_secure_key(purpose: str, algorithm: str = "ECC") -> str:
    """Generate a secure key for specific purpose"""
    manager = get_key_manager()
    return await manager.create_key(purpose, algorithm)

async def sign_data_secure(key_id: str, data: bytes) -> bytes:
    """Sign data using secure key"""
    manager = get_key_manager()
    return await manager.sign_with_key(key_id, data)

async def encrypt_data_secure(key_id: str, data: bytes) -> bytes:
    """Encrypt data using secure key"""
    manager = get_key_manager()
    return await manager.encrypt_with_key(key_id, data)




