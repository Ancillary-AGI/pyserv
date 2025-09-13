# server_framework/core/security.py
import hashlib
import hmac
import secrets
import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class CryptoUtils:
    """Cryptography utilities"""
    
    @staticmethod
    def generate_salt(length: int = 16) -> bytes:
        """Generate a cryptographically secure salt"""
        return secrets.token_bytes(length)
        
    @staticmethod
    def hash_password(password: str, salt: Optional[bytes] = None) -> tuple:
        """Hash a password using PBKDF2"""
        if salt is None:
            salt = CryptoUtils.generate_salt()
            
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt
        
    @staticmethod
    def verify_password(password: str, hashed: bytes, salt: bytes) -> bool:
        """Verify a password against a hash"""
        new_hash, _ = CryptoUtils.hash_password(password, salt)
        return hmac.compare_digest(new_hash, hashed)
        
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate a secure token"""
        return secrets.token_urlsafe(length)

class Security:
    """Security middleware and utilities"""
    
    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or Fernet.generate_key().decode()
        self.fernet = Fernet(self.secret_key.encode())
        
    def encrypt(self, data: str) -> str:
        """Encrypt data"""
        return self.fernet.encrypt(data.encode()).decode()
        
    def decrypt(self, token: str) -> str:
        """Decrypt data"""
        return self.fernet.decrypt(token.encode()).decode()
        
    def create_hmac(self, data: str) -> str:
        """Create HMAC signature for data"""
        return hmac.new(
            self.secret_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        
    def verify_hmac(self, data: str, signature: str) -> bool:
        """Verify HMAC signature"""
        expected_signature = self.create_hmac(data)
        return hmac.compare_digest(expected_signature, signature)