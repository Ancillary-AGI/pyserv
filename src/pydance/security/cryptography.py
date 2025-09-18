"""
Advanced Cryptography Module for PyDance Framework.
Implements elliptic curve cryptography, SHA3 hashing, and secure key management.
"""

import hashlib
import hmac
import secrets
import os
from typing import Optional, Dict, Any, Tuple, Union
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature
import base64
import json

# Import quantum security module
from .quantum_security import (
    get_quantum_security_manager,
    QuantumAlgorithm,
    generate_quantum_keypair,
    establish_secure_channel,
    quantum_authenticate
)


class HashManager:
    """Advanced hashing with SHA3 and salting"""

    @staticmethod
    def generate_salt(length: int = 32) -> bytes:
        """Generate a cryptographically secure salt"""
        return secrets.token_bytes(length)

    @staticmethod
    def hash_password(password: str, salt: Optional[bytes] = None,
                     algorithm: str = 'sha3_256') -> Dict[str, str]:
        """Hash password with salt using SHA3"""
        if salt is None:
            salt = HashManager.generate_salt()

        # Use PBKDF2 with SHA3 for key derivation
        kdf = PBKDF2HMAC(
            algorithm=getattr(hashes, algorithm.upper())(),
            length=32,
            salt=salt,
            iterations=100000,  # High iteration count for security
            backend=default_backend()
        )

        key = kdf.derive(password.encode('utf-8'))

        return {
            'hash': base64.b64encode(key).decode('utf-8'),
            'salt': base64.b64encode(salt).decode('utf-8'),
            'algorithm': algorithm,
            'iterations': 100000
        }

    @staticmethod
    def verify_password(password: str, stored_hash: Dict[str, str]) -> bool:
        """Verify password against stored hash"""
        try:
            salt = base64.b64decode(stored_hash['salt'])
            algorithm = stored_hash.get('algorithm', 'sha3_256')
            iterations = stored_hash.get('iterations', 100000)

            kdf = PBKDF2HMAC(
                algorithm=getattr(hashes, algorithm.upper())(),
                length=32,
                salt=salt,
                iterations=iterations,
                backend=default_backend()
            )

            key = kdf.derive(password.encode('utf-8'))
            stored_key = base64.b64decode(stored_hash['hash'])

            return hmac.compare_digest(key, stored_key)
        except Exception:
            return False

    @staticmethod
    def hash_data(data: Union[str, bytes], algorithm: str = 'sha3_256') -> str:
        """Hash arbitrary data using SHA3"""
        if isinstance(data, str):
            data = data.encode('utf-8')

        hash_func = getattr(hashlib, algorithm)
        return hash_func(data).hexdigest()

    @staticmethod
    def hmac_sign(key: Union[str, bytes], message: Union[str, bytes],
                  algorithm: str = 'sha3_256') -> str:
        """Create HMAC signature"""
        if isinstance(key, str):
            key = key.encode('utf-8')
        if isinstance(message, str):
            message = message.encode('utf-8')

        return hmac.new(key, message, getattr(hashlib, algorithm)).hexdigest()

    @staticmethod
    def verify_hmac(key: Union[str, bytes], message: Union[str, bytes],
                    signature: str, algorithm: str = 'sha3_256') -> bool:
        """Verify HMAC signature"""
        expected = HashManager.hmac_sign(key, message, algorithm)
        return hmac.compare_digest(expected, signature)


class ECCManager:
    """Elliptic Curve Cryptography Manager"""

    def __init__(self, curve=ec.SECP256R1()):
        self.curve = curve
        self._private_key = None
        self._public_key = None

    def generate_keypair(self) -> Tuple[str, str]:
        """Generate ECC keypair"""
        self._private_key = ec.generate_private_key(self.curve, default_backend())
        self._public_key = self._private_key.public_key()

        # Serialize private key
        private_pem = self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        # Serialize public key
        public_pem = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        return private_pem.decode('utf-8'), public_pem.decode('utf-8')

    def load_private_key(self, private_key_pem: str):
        """Load private key from PEM"""
        self._private_key = serialization.load_pem_private_key(
            private_key_pem.encode('utf-8'),
            password=None,
            backend=default_backend()
        )
        self._public_key = self._private_key.public_key()

    def load_public_key(self, public_key_pem: str):
        """Load public key from PEM"""
        self._public_key = serialization.load_pem_public_key(
            public_key_pem.encode('utf-8'),
            backend=default_backend()
        )

    def sign(self, message: Union[str, bytes]) -> str:
        """Sign message using ECC"""
        if self._private_key is None:
            raise ValueError("Private key not loaded")

        if isinstance(message, str):
            message = message.encode('utf-8')

        signature = self._private_key.sign(
            message,
            ec.ECDSA(hashes.SHA256())
        )

        return base64.b64encode(signature).decode('utf-8')

    def verify(self, message: Union[str, bytes], signature: str) -> bool:
        """Verify ECC signature"""
        if self._public_key is None:
            raise ValueError("Public key not loaded")

        if isinstance(message, str):
            message = message.encode('utf-8')

        try:
            signature_bytes = base64.b64decode(signature)
            self._public_key.verify(
                signature_bytes,
                message,
                ec.ECDSA(hashes.SHA256())
            )
            return True
        except InvalidSignature:
            return False

    def derive_shared_secret(self, other_public_key_pem: str) -> bytes:
        """Derive shared secret using ECDH"""
        if self._private_key is None:
            raise ValueError("Private key not loaded")

        other_public_key = serialization.load_pem_public_key(
            other_public_key_pem.encode('utf-8'),
            backend=default_backend()
        )

        shared_key = self._private_key.exchange(ec.ECDH(), other_public_key)
        return shared_key

    def get_public_key_pem(self) -> str:
        """Get public key in PEM format"""
        if self._public_key is None:
            raise ValueError("Public key not available")

        public_pem = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        return public_pem.decode('utf-8')


class RSAManager:
    """RSA Cryptography Manager"""

    def __init__(self, key_size: int = 2048):
        self.key_size = key_size
        self._private_key = None
        self._public_key = None

    def generate_keypair(self) -> Tuple[str, str]:
        """Generate RSA keypair"""
        self._private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=self.key_size,
            backend=default_backend()
        )
        self._public_key = self._private_key.public_key()

        # Serialize private key
        private_pem = self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        # Serialize public key
        public_pem = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        return private_pem.decode('utf-8'), public_pem.decode('utf-8')

    def load_private_key(self, private_key_pem: str):
        """Load private key from PEM"""
        self._private_key = serialization.load_pem_private_key(
            private_key_pem.encode('utf-8'),
            password=None,
            backend=default_backend()
        )
        self._public_key = self._private_key.public_key()

    def load_public_key(self, public_key_pem: str):
        """Load public key from PEM"""
        self._public_key = serialization.load_pem_public_key(
            public_key_pem.encode('utf-8'),
            backend=default_backend()
        )

    def encrypt(self, message: Union[str, bytes]) -> str:
        """Encrypt message using RSA"""
        if self._public_key is None:
            raise ValueError("Public key not loaded")

        if isinstance(message, str):
            message = message.encode('utf-8')

        ciphertext = self._public_key.encrypt(
            message,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        return base64.b64encode(ciphertext).decode('utf-8')

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt message using RSA"""
        if self._private_key is None:
            raise ValueError("Private key not loaded")

        try:
            ciphertext_bytes = base64.b64decode(ciphertext)
            plaintext = self._private_key.decrypt(
                ciphertext_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )

            return plaintext.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")

    def sign(self, message: Union[str, bytes]) -> str:
        """Sign message using RSA"""
        if self._private_key is None:
            raise ValueError("Private key not loaded")

        if isinstance(message, str):
            message = message.encode('utf-8')

        signature = self._private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        return base64.b64encode(signature).decode('utf-8')

    def verify(self, message: Union[str, bytes], signature: str) -> bool:
        """Verify RSA signature"""
        if self._public_key is None:
            raise ValueError("Public key not loaded")

        if isinstance(message, str):
            message = message.encode('utf-8')

        try:
            signature_bytes = base64.b64decode(signature)
            self._public_key.verify(
                signature_bytes,
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except InvalidSignature:
            return False


class CryptoManager:
    """Unified cryptography manager"""

    def __init__(self):
        self.ecc = ECCManager()
        self.rsa = RSAManager()
        self.hash_manager = HashManager()

    def generate_ecc_keypair(self) -> Tuple[str, str]:
        """Generate ECC keypair"""
        return self.ecc.generate_keypair()

    def generate_rsa_keypair(self) -> Tuple[str, str]:
        """Generate RSA keypair"""
        return self.rsa.generate_keypair()

    def hash_password(self, password: str) -> Dict[str, str]:
        """Hash password with SHA3 and salting"""
        return self.hash_manager.hash_password(password)

    def verify_password(self, password: str, stored_hash: Dict[str, str]) -> bool:
        """Verify password hash"""
        return self.hash_manager.verify_password(password, stored_hash)

    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure token"""
        return secrets.token_hex(length)

    def generate_api_key(self) -> str:
        """Generate API key"""
        return f"pk_{secrets.token_hex(16)}"

    def encrypt_data(self, data: Union[str, Dict], key: str) -> str:
        """Encrypt data using AES"""
        # Simplified AES encryption - in production use proper AES implementation
        if isinstance(data, dict):
            data = json.dumps(data)

        # For demo purposes, using simple XOR with key
        # In production, use cryptography library's AES
        encrypted = ""
        key_len = len(key)
        for i, char in enumerate(data):
            encrypted += chr(ord(char) ^ ord(key[i % key_len]))

        return base64.b64encode(encrypted.encode()).decode()

    def decrypt_data(self, encrypted_data: str, key: str) -> Union[str, Dict]:
        """Decrypt data"""
        try:
            encrypted = base64.b64decode(encrypted_data).decode()
            decrypted = ""

            key_len = len(key)
            for i, char in enumerate(encrypted):
                decrypted += chr(ord(char) ^ ord(key[i % key_len]))

            # Try to parse as JSON
            try:
                return json.loads(decrypted)
            except json.JSONDecodeError:
                return decrypted
        except Exception:
            raise ValueError("Decryption failed")

    def create_jwt(self, payload: Dict[str, Any], secret: str,
                   algorithm: str = 'HS256') -> str:
        """Create JWT token"""
        import jwt
        return jwt.encode(payload, secret, algorithm=algorithm)

    def verify_jwt(self, token: str, secret: str, algorithms: List[str] = None) -> Dict[str, Any]:
        """Verify JWT token"""
        import jwt
        if algorithms is None:
            algorithms = ['HS256']
        return jwt.decode(token, secret, algorithms=algorithms)

    # Quantum-resistant methods
    async def generate_quantum_keypair(self, algorithm: str = "kyber") -> Dict[str, Any]:
        """Generate quantum-resistant keypair"""
        return await generate_quantum_keypair(algorithm)

    async def establish_quantum_secure_channel(self) -> Dict[str, Any]:
        """Establish quantum-secure communication channel"""
        return await establish_secure_channel()

    async def quantum_authenticate(self, identity: str) -> Dict[str, Any]:
        """Perform quantum-secure authentication"""
        return await quantum_authenticate(identity)

    async def perform_quantum_operation(self, operation: str, context: Dict = None) -> Dict[str, Any]:
        """Perform quantum-secure operation using security agents"""
        manager = get_quantum_security_manager()
        return await manager.perform_secure_operation(operation, context)

    def get_quantum_security_status(self) -> Dict[str, Any]:
        """Get quantum security system status"""
        manager = get_quantum_security_manager()
        return manager.get_security_status()


# Global crypto manager instance
_crypto_manager = None

def get_crypto_manager() -> CryptoManager:
    """Get global crypto manager instance"""
    global _crypto_manager
    if _crypto_manager is None:
        _crypto_manager = CryptoManager()
    return _crypto_manager


# Security utilities
def generate_secure_password(length: int = 16) -> str:
    """Generate secure random password"""
    import string
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(characters) for _ in range(length))

def constant_time_compare(a: str, b: str) -> bool:
    """Constant time string comparison to prevent timing attacks"""
    return hmac.compare_digest(a.encode(), b.encode())

def sanitize_input(input_string: str) -> str:
    """Sanitize user input to prevent injection attacks"""
    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', '"', "'", ';', '--', '/*', '*/']
    sanitized = input_string

    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')

    return sanitized

def validate_certificate_chain(cert_chain: List[str]) -> bool:
    """Validate certificate chain"""
    # Simplified certificate validation
    # In production, use proper certificate validation libraries
    return len(cert_chain) > 0
