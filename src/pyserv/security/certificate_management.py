"""
Certificate Management and Automated Rotation.
Provides enterprise-grade certificate lifecycle management.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import secrets
import hashlib
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.hazmat.backends import default_backend
import base64
import json
import os


@dataclass
class CertificateMetadata:
    """Certificate metadata"""
    cert_id: str
    subject: str
    issuer: str
    serial_number: str
    not_before: datetime
    not_after: datetime
    key_size: int
    algorithm: str
    status: str = "active"  # active, expired, revoked
    auto_renew: bool = True
    renewal_days: int = 30
    tags: Dict[str, str] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if certificate is expired"""
        return datetime.utcnow() > self.not_after

    def needs_renewal(self) -> bool:
        """Check if certificate needs renewal"""
        renewal_date = self.not_after - timedelta(days=self.renewal_days)
        return datetime.utcnow() >= renewal_date

    def days_until_expiry(self) -> int:
        """Get days until certificate expires"""
        delta = self.not_after - datetime.utcnow()
        return max(0, delta.days)


@dataclass
class CertificateAuthority:
    """Certificate Authority configuration"""
    name: str
    type: str  # "self_signed", "lets_encrypt", "custom"
    endpoint: Optional[str] = None
    credentials: Dict[str, Any] = field(default_factory=dict)
    root_cert: Optional[str] = None
    intermediate_certs: List[str] = field(default_factory=list)


class CertificateManager:
    """Enterprise certificate management system"""

    def __init__(self):
        self.certificates: Dict[str, Dict[str, Any]] = {}
        self.metadata: Dict[str, CertificateMetadata] = {}
        self.authorities: Dict[str, CertificateAuthority] = {}
        self.renewal_tasks: Dict[str, asyncio.Task] = {}

    def add_certificate_authority(self, ca: CertificateAuthority):
        """Add certificate authority"""
        self.authorities[ca.name] = ca

    async def generate_certificate(self, domain: str, ca_name: str = "self_signed",
                                 key_size: int = 2048, validity_days: int = 365) -> str:
        """Generate SSL certificate"""
        ca = self.authorities.get(ca_name)
        if not ca:
            raise ValueError(f"Certificate authority {ca_name} not found")

        cert_id = f"cert_{secrets.token_hex(16)}"

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )

        # Generate certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Pyserv  Framework"),
            x509.NameAttribute(NameOID.COMMON_NAME, domain),
        ])

        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=validity_days)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(domain),
                x509.DNSName(f"*.{domain}"),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256(), default_backend())

        # Serialize certificate and key
        cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()

        # Store certificate
        self.certificates[cert_id] = {
            'certificate': cert_pem,
            'private_key': key_pem,
            'chain': [cert_pem]  # Add CA certificates if available
        }

        # Store metadata
        metadata = CertificateMetadata(
            cert_id=cert_id,
            subject=domain,
            issuer=domain,  # Self-signed
            serial_number=str(cert.serial_number),
            not_before=cert.not_valid_before,
            not_after=cert.not_valid_after,
            key_size=key_size,
            algorithm="RSA",
            tags={"domain": domain, "ca": ca_name}
        )
        self.metadata[cert_id] = metadata

        # Schedule renewal if enabled
        if metadata.auto_renew:
            await self._schedule_renewal(cert_id)

        return cert_id

    async def load_certificate(self, cert_path: str, key_path: str,
                             chain_path: Optional[str] = None) -> str:
        """Load existing certificate"""
        cert_id = f"cert_{secrets.token_hex(16)}"

        with open(cert_path, 'r') as f:
            cert_pem = f.read()

        with open(key_path, 'r') as f:
            key_pem = f.read()

        chain = [cert_pem]
        if chain_path:
            with open(chain_path, 'r') as f:
                chain.extend(f.read().split('-----END CERTIFICATE-----')[:-1])

        # Parse certificate
        cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())

        # Store certificate
        self.certificates[cert_id] = {
            'certificate': cert_pem,
            'private_key': key_pem,
            'chain': chain
        }

        # Store metadata
        metadata = CertificateMetadata(
            cert_id=cert_id,
            subject=cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value,
            issuer=cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value,
            serial_number=str(cert.serial_number),
            not_before=cert.not_valid_before,
            not_after=cert.not_valid_after,
            key_size=2048,  # Assume default
            algorithm="RSA"
        )
        self.metadata[cert_id] = metadata

        return cert_id

    async def get_certificate(self, cert_id: str) -> Optional[Dict[str, Any]]:
        """Get certificate data"""
        return self.certificates.get(cert_id)

    def get_certificate_metadata(self, cert_id: str) -> Optional[CertificateMetadata]:
        """Get certificate metadata"""
        return self.metadata.get(cert_id)

    async def renew_certificate(self, cert_id: str) -> str:
        """Renew certificate"""
        metadata = self.metadata.get(cert_id)
        if not metadata:
            raise ValueError(f"Certificate {cert_id} not found")

        # Generate new certificate with same parameters
        new_cert_id = await self.generate_certificate(
            metadata.subject,
            metadata.tags.get("ca", "self_signed"),
            metadata.key_size,
            365  # 1 year validity
        )

        # Mark old certificate as renewed
        metadata.status = "renewed"
        metadata.not_after = datetime.utcnow()

        return new_cert_id

    async def revoke_certificate(self, cert_id: str):
        """Revoke certificate"""
        metadata = self.metadata.get(cert_id)
        if metadata:
            metadata.status = "revoked"

        # Remove renewal task
        if cert_id in self.renewal_tasks:
            self.renewal_tasks[cert_id].cancel()
            del self.renewal_tasks[cert_id]

    async def _schedule_renewal(self, cert_id: str):
        """Schedule automatic certificate renewal"""
        metadata = self.metadata.get(cert_id)
        if not metadata:
            return

        renewal_seconds = (metadata.not_after - datetime.utcnow() - timedelta(days=metadata.renewal_days)).total_seconds()

        if renewal_seconds > 0:
            async def renewal_task():
                await asyncio.sleep(renewal_seconds)
                try:
                    await self.renew_certificate(cert_id)
                    print(f"Automatically renewed certificate: {cert_id}")
                except Exception as e:
                    print(f"Failed to renew certificate {cert_id}: {e}")

            task = asyncio.create_task(renewal_task())
            self.renewal_tasks[cert_id] = task

    def get_expiring_certificates(self, days: int = 30) -> List[CertificateMetadata]:
        """Get certificates expiring within specified days"""
        expiring = []
        cutoff_date = datetime.utcnow() + timedelta(days=days)

        for metadata in self.metadata.values():
            if metadata.status == "active" and metadata.not_after <= cutoff_date:
                expiring.append(metadata)

        return sorted(expiring, key=lambda x: x.not_after)

    def get_certificate_chain(self, cert_id: str) -> List[str]:
        """Get certificate chain"""
        cert_data = self.certificates.get(cert_id)
        if cert_data:
            return cert_data['chain']
        return []

    async def validate_certificate(self, cert_id: str) -> Dict[str, Any]:
        """Validate certificate"""
        cert_data = self.certificates.get(cert_id)
        metadata = self.metadata.get(cert_id)

        if not cert_data or not metadata:
            return {"valid": False, "reason": "Certificate not found"}

        try:
            # Parse certificate
            cert = x509.load_pem_x509_certificate(
                cert_data['certificate'].encode(), default_backend()
            )

            # Check expiry
            now = datetime.utcnow()
            if now < cert.not_valid_before:
                return {"valid": False, "reason": "Certificate not yet valid"}

            if now > cert.not_valid_after:
                return {"valid": False, "reason": "Certificate expired"}

            # Check key usage
            try:
                key_usage = cert.extensions.get_extension_for_oid(x509.oid.ExtensionOID.KEY_USAGE)
                if not key_usage.value.digital_signature:
                    return {"valid": False, "reason": "Certificate not valid for digital signatures"}
            except x509.ExtensionNotFound:
                pass  # Key usage extension not present

            return {"valid": True}

        except Exception as e:
            return {"valid": False, "reason": f"Certificate parsing error: {str(e)}"}

    async def export_certificate(self, cert_id: str, format: str = "PEM") -> str:
        """Export certificate in specified format"""
        cert_data = self.certificates.get(cert_id)
        if not cert_data:
            raise ValueError(f"Certificate {cert_id} not found")

        if format.upper() == "PEM":
            return cert_data['certificate']
        elif format.upper() == "DER":
            cert = x509.load_pem_x509_certificate(
                cert_data['certificate'].encode(), default_backend()
            )
            return cert.public_bytes(serialization.Encoding.DER).decode('latin-1')
        else:
            raise ValueError(f"Unsupported format: {format}")

    async def import_certificate(self, cert_pem: str, key_pem: str,
                               chain: Optional[List[str]] = None) -> str:
        """Import certificate from PEM data"""
        cert_id = f"cert_{secrets.token_hex(16)}"

        # Parse certificate
        cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())

        # Store certificate
        self.certificates[cert_id] = {
            'certificate': cert_pem,
            'private_key': key_pem,
            'chain': chain or [cert_pem]
        }

        # Store metadata
        metadata = CertificateMetadata(
            cert_id=cert_id,
            subject=cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value,
            issuer=cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value,
            serial_number=str(cert.serial_number),
            not_before=cert.not_valid_before,
            not_after=cert.not_valid_after,
            key_size=2048,  # Assume default
            algorithm="RSA"
        )
        self.metadata[cert_id] = metadata

        return cert_id

    def list_certificates(self) -> List[CertificateMetadata]:
        """List all certificates"""
        return list(self.metadata.values())

    async def cleanup_expired_certificates(self):
        """Clean up expired certificates"""
        expired = []
        for cert_id, metadata in self.metadata.items():
            if metadata.is_expired() and metadata.status == "active":
                metadata.status = "expired"
                expired.append(cert_id)

        # Remove renewal tasks for expired certificates
        for cert_id in expired:
            if cert_id in self.renewal_tasks:
                self.renewal_tasks[cert_id].cancel()
                del self.renewal_tasks[cert_id]

        return expired


# Global certificate manager instance
_cert_manager = None

def get_certificate_manager() -> CertificateManager:
    """Get global certificate manager instance"""
    global _cert_manager
    if _cert_manager is None:
        _cert_manager = CertificateManager()

        # Add default self-signed CA
        _cert_manager.add_certificate_authority(CertificateAuthority(
            name="self_signed",
            type="self_signed"
        ))

    return _cert_manager


# Utility functions
async def generate_ssl_certificate(domain: str, ca: str = "self_signed") -> str:
    """Generate SSL certificate for domain"""
    manager = get_certificate_manager()
    return await manager.generate_certificate(domain, ca)

async def get_certificate_expiry_days(cert_id: str) -> int:
    """Get days until certificate expires"""
    manager = get_certificate_manager()
    metadata = manager.get_certificate_metadata(cert_id)
    return metadata.days_until_expiry() if metadata else 0

async def renew_certificate_if_needed(cert_id: str) -> Optional[str]:
    """Renew certificate if it needs renewal"""
    manager = get_certificate_manager()
    metadata = manager.get_certificate_metadata(cert_id)

    if metadata and metadata.needs_renewal():
        return await manager.renew_certificate(cert_id)

    return None




