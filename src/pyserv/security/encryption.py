"""
Encryption Service for sensitive data protection.
"""

import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import secrets
from typing import Optional, Union

class EncryptionService:
    """
    Enterprise-grade encryption service for data protection.
    """

    def __init__(self, master_key: Optional[str] = None):
        if master_key:
            self.master_key = master_key.encode()
        else:
            self.master_key = Fernet.generate_key()

        self.salt = os.urandom(16)
        self.fernet = self._derive_key()

    def _derive_key(self) -> Fernet:
        """Derive encryption key from master key."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        return Fernet(key)

    def encrypt(self, data: Union[str, bytes]) -> str:
        """Encrypt data."""
        if isinstance(data, str):
            data = data.encode()
        encrypted = self.fernet.encrypt(data)
        return encrypted.decode()

    def decrypt(self, token: str) -> str:
        """Decrypt data."""
        decrypted = self.fernet.decrypt(token.encode())
        return decrypted.decode()

    def encrypt_file(self, file_path: str, output_path: str):
        """Encrypt file contents."""
        with open(file_path, 'rb') as f:
            data = f.read()

        encrypted = self.fernet.encrypt(data)

        with open(output_path, 'wb') as f:
            f.write(encrypted)

    def decrypt_file(self, file_path: str, output_path: str):
        """Decrypt file contents."""
        with open(file_path, 'rb') as f:
            data = f.read()

        decrypted = self.fernet.decrypt(data)

        with open(output_path, 'wb') as f:
            f.write(decrypted)

    def generate_key(self) -> str:
        """Generate a new encryption key."""
        return Fernet.generate_key().decode()

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        import bcrypt
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        import bcrypt
        return bcrypt.checkpw(password.encode(), hashed.encode())

    def encrypt_field(self, value: Union[str, int, float]) -> str:
        """Encrypt a database field value."""
        return self.encrypt(str(value))

    def decrypt_field(self, encrypted_value: str) -> str:
        """Decrypt a database field value."""
        return self.decrypt(encrypted_value)
