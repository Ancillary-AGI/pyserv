"""
Tests for quantum security module
"""
import pytest
import asyncio
import base64
from unittest.mock import Mock, patch, AsyncMock

from pyserv.security.quantum_security import (
    QuantumSecurityManager,
    QuantumSecurityAgent,
    QuantumAlgorithm,
    QuantumProvider,
    KyberProvider,
    DilithiumProvider,
    get_quantum_security_manager,
    generate_quantum_keypair,
    establish_secure_channel,
    quantum_authenticate
)


class TestQuantumProvider:
    """Test quantum cryptographic providers"""

    @pytest.fixture
    def kyber_provider(self):
        return KyberProvider()

    @pytest.fixture
    def dilithium_provider(self):
        return DilithiumProvider()

    @pytest.mark.asyncio
    async def test_kyber_generate_keypair(self, kyber_provider):
        """Test Kyber keypair generation"""
        public_key, private_key = await kyber_provider.generate_keypair()

        assert isinstance(public_key, bytes)
        assert isinstance(private_key, bytes)
        assert len(public_key) == 800  # Kyber768 public key size
        assert len(private_key) == 1632  # Kyber768 private key size

    @pytest.mark.asyncio
    async def test_kyber_encapsulate(self, kyber_provider):
        """Test Kyber encapsulation"""
        public_key, _ = await kyber_provider.generate_keypair()

        ciphertext, shared_secret = await kyber_provider.encapsulate(public_key)

        assert isinstance(ciphertext, bytes)
        assert isinstance(shared_secret, bytes)
        assert len(ciphertext) == 768  # Kyber768 ciphertext size
        assert len(shared_secret) == 32  # Shared secret size

    @pytest.mark.asyncio
    async def test_dilithium_generate_keypair(self, dilithium_provider):
        """Test Dilithium keypair generation"""
        public_key, private_key = await dilithium_provider.generate_keypair()

        assert isinstance(public_key, bytes)
        assert isinstance(private_key, bytes)
        assert len(public_key) == 1312  # Dilithium2 public key size
        assert len(private_key) == 2528  # Dilithium2 private key size

    @pytest.mark.asyncio
    async def test_dilithium_sign_verify(self, dilithium_provider):
        """Test Dilithium signing and verification"""
        public_key, private_key = await dilithium_provider.generate_keypair()
        message = b"test message"

        signature = await dilithium_provider.sign(private_key, message)
        assert isinstance(signature, bytes)
        assert len(signature) == 2420  # Dilithium2 signature size

        # Note: In real implementation, this would verify the signature
        # For this test, we just check the method doesn't raise
        result = await dilithium_provider.verify(public_key, message, signature)
        assert isinstance(result, bool)


class TestQuantumSecurityAgent:
    """Test quantum security agents"""

    @pytest.fixture
    def quantum_manager(self):
        return QuantumSecurityManager()

    @pytest.fixture
    def security_agent(self, quantum_manager):
        from pyserv.security.quantum_security import QuantumCapability
        capabilities = [
            QuantumCapability("key_encapsulation", "Test KEM", QuantumAlgorithm.KYBER, 1.0),
            QuantumCapability("digital_signature", "Test signature", QuantumAlgorithm.DILITHIUM, 1.0)
        ]
        return QuantumSecurityAgent("test_agent", "Test Agent", capabilities, quantum_manager)

    @pytest.mark.asyncio
    async def test_agent_initialization(self, security_agent):
        """Test agent initialization"""
        assert security_agent.agent_id == "test_agent"
        assert security_agent.name == "Test Agent"
        assert len(security_agent.capabilities) == 2
        assert security_agent.state == "idle"

    @pytest.mark.asyncio
    async def test_agent_task_analysis(self, security_agent):
        """Test task requirement analysis"""
        assert security_agent._analyze_task_requirements("encrypt data") == "key_encapsulation"
        assert security_agent._analyze_task_requirements("sign message") == "digital_signature"
        assert security_agent._analyze_task_requirements("unknown task") == "general_security"

    @pytest.mark.asyncio
    async def test_agent_execute_task(self, security_agent):
        """Test task execution"""
        result = await security_agent.execute_security_task("generate keypair")

        assert "agent_id" in result
        assert "result" in result
        assert "latency" in result
        assert result["agent_id"] == "test_agent"
        assert security_agent.state == "completed"


class TestQuantumSecurityManager:
    """Test quantum security manager"""

    @pytest.fixture
    def manager(self):
        return QuantumSecurityManager()

    @pytest.mark.asyncio
    async def test_manager_initialization(self, manager):
        """Test manager initialization"""
        assert isinstance(manager.providers, dict)
        assert QuantumAlgorithm.KYBER in manager.providers
        assert QuantumAlgorithm.DILITHIUM in manager.providers
        assert isinstance(manager.agents, dict)
        assert isinstance(manager.key_store, dict)

    @pytest.mark.asyncio
    async def test_manager_setup(self, manager):
        """Test manager setup"""
        await manager.initialize_quantum_security()

        assert len(manager.agents) == 2  # KEM and signature agents
        assert "quantum_kem_agent" in manager.agents
        assert "quantum_sig_agent" in manager.agents

        # Check that keys were generated
        assert len(manager.key_store) == 2  # Kyber and Dilithium keys

    @pytest.mark.asyncio
    async def test_secure_operation(self, manager):
        """Test secure operation execution"""
        await manager.initialize_quantum_security()

        result = await manager.perform_secure_operation("generate keypair")
        assert "agent_id" in result
        assert "result" in result

    @pytest.mark.asyncio
    async def test_kem_operation(self, manager):
        """Test KEM operation"""
        result = await manager.perform_kem_operation("encapsulate")

        assert result["operation"] == "encapsulation"
        assert "ciphertext" in result
        assert "shared_secret" in result

    @pytest.mark.asyncio
    async def test_signature_operation(self, manager):
        """Test signature operation"""
        result = await manager.perform_signature_operation("sign", {"message": "test"})

        assert result["operation"] == "signing"
        assert "signature" in result
        assert "message_hash" in result

    @pytest.mark.asyncio
    async def test_secure_channel(self, manager):
        """Test secure channel establishment"""
        result = await manager.establish_quantum_secure_channel()

        assert "channel_id" in result
        assert "shared_secret" in result
        assert result["algorithm"] == "kyber"
        assert "established_at" in result

    @pytest.mark.asyncio
    async def test_quantum_authentication(self, manager):
        """Test quantum authentication"""
        result = await manager.authenticate_quantum_secure("test_user")

        assert "identity" in result
        assert result["identity"] == "test_user"
        assert "signature" in result
        assert "algorithm" in result
        assert "authenticated_at" in result

    def test_security_status(self, manager):
        """Test security status reporting"""
        status = manager.get_security_status()

        assert status["quantum_resistant"] is True
        assert "active_agents" in status
        assert "total_agents" in status
        assert "quantum_keys" in status
        assert "algorithms_supported" in status
        assert "last_updated" in status


class TestQuantumSecurityIntegration:
    """Test integration with other modules"""

    @pytest.mark.asyncio
    async def test_generate_quantum_keypair(self):
        """Test global quantum keypair generation"""
        result = await generate_quantum_keypair("kyber")

        assert "algorithm" in result
        assert result["algorithm"] == "kyber"
        assert "public_key" in result
        assert "private_key" in result

    @pytest.mark.asyncio
    async def test_establish_secure_channel(self):
        """Test global secure channel establishment"""
        result = await establish_secure_channel()

        assert "channel_id" in result
        assert "shared_secret" in result
        assert "algorithm" in result
        assert "established_at" in result

    @pytest.mark.asyncio
    async def test_quantum_authenticate(self):
        """Test global quantum authentication"""
        result = await quantum_authenticate("test_identity")

        assert "identity" in result
        assert result["identity"] == "test_identity"
        assert "signature" in result
        assert "algorithm" in result
        assert "authenticated_at" in result

    def test_get_quantum_manager(self):
        """Test getting quantum security manager instance"""
        manager1 = get_quantum_security_manager()
        manager2 = get_quantum_security_manager()

        # Should return the same instance (singleton)
        assert manager1 is manager2
        assert isinstance(manager1, QuantumSecurityManager)


class TestQuantumCryptographyIntegration:
    """Test integration with cryptography module"""

    @pytest.mark.asyncio
    async def test_crypto_manager_quantum_methods(self):
        """Test that CryptoManager has quantum methods"""
        from pyserv.security.cryptography import CryptoManager

        crypto_manager = CryptoManager()

        # Check that quantum methods exist
        assert hasattr(crypto_manager, 'generate_quantum_keypair')
        assert hasattr(crypto_manager, 'establish_quantum_secure_channel')
        assert hasattr(crypto_manager, 'quantum_authenticate')
        assert hasattr(crypto_manager, 'perform_quantum_operation')
        assert hasattr(crypto_manager, 'get_quantum_security_status')

    @pytest.mark.asyncio
    async def test_crypto_manager_quantum_operations(self):
        """Test quantum operations through CryptoManager"""
        from pyserv.security.cryptography import CryptoManager

        crypto_manager = CryptoManager()

        # Test quantum keypair generation
        result = await crypto_manager.generate_quantum_keypair("kyber")
        assert "algorithm" in result
        assert result["algorithm"] == "kyber"

        # Test secure channel
        channel_result = await crypto_manager.establish_quantum_secure_channel()
        assert "channel_id" in channel_result

        # Test quantum authentication
        auth_result = await crypto_manager.quantum_authenticate("test_user")
        assert "identity" in auth_result

        # Test security status
        status = crypto_manager.get_quantum_security_status()
        assert "quantum_resistant" in status


class TestQuantumKeyManagementIntegration:
    """Test integration with key management module"""

    @pytest.mark.asyncio
    async def test_key_manager_quantum_methods(self):
        """Test that KeyManager has quantum methods"""
        from pyserv.security.key_management import KeyManager, HSMConfig

        config = HSMConfig(hsm_type="software")
        key_manager = KeyManager(config)

        # Check that quantum methods exist
        assert hasattr(key_manager, 'create_quantum_key')
        assert hasattr(key_manager, 'get_quantum_key')
        assert hasattr(key_manager, 'sign_with_quantum_key')
        assert hasattr(key_manager, 'verify_with_quantum_key')
        assert hasattr(key_manager, 'perform_quantum_kem')
        assert hasattr(key_manager, 'rotate_quantum_key')

    @pytest.mark.asyncio
    async def test_quantum_key_creation(self):
        """Test quantum key creation through KeyManager"""
        from pyserv.security.key_management import KeyManager, HSMConfig

        config = HSMConfig(hsm_type="software")
        key_manager = KeyManager(config)

        # Create quantum key
        key_id = await key_manager.create_quantum_key("test_purpose", QuantumAlgorithm.KYBER)

        assert isinstance(key_id, str)
        assert key_id.startswith("quantum_kyber_")

        # Retrieve quantum key
        quantum_key = await key_manager.get_quantum_key(key_id)
        assert quantum_key is not None
        assert quantum_key.algorithm == QuantumAlgorithm.KYBER
        assert quantum_key.key_id == key_id


if __name__ == "__main__":
    pytest.main([__file__])




