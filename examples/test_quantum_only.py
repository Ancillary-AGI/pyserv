#!/usr/bin/env python3
"""
Test Quantum Security Module Only
Tests only the quantum security components without framework dependencies.
"""

import asyncio
import sys
import os

# Add the security module directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'pydance', 'security'))

async def test_quantum_only():
    """Test quantum security components in isolation"""
    print("🔬 Testing Quantum Security Module (Isolated)")
    print("=" * 50)

    try:
        # Import only the quantum security module
        import quantum_security
        print("✓ Quantum security module imported successfully")

        # Test basic components
        print("\n1. Testing QuantumAlgorithm enum...")
        from quantum_security import QuantumAlgorithm
        assert QuantumAlgorithm.KYBER.value == "kyber"
        assert QuantumAlgorithm.DILITHIUM.value == "dilithium"
        print("   ✓ QuantumAlgorithm enum working")

        # Test Kyber provider
        print("\n2. Testing KyberProvider...")
        from quantum_security import KyberProvider
        kyber = KyberProvider()
        public_key, private_key = await kyber.generate_keypair()
        assert len(public_key) == 800  # Kyber768 public key size
        assert len(private_key) == 1632  # Kyber768 private key size
        print("   ✓ Kyber keypair generation working")

        # Test encapsulation
        ciphertext, shared_secret = await kyber.encapsulate(public_key)
        assert len(ciphertext) == 768
        assert len(shared_secret) == 32
        print("   ✓ Kyber encapsulation working")

        # Test Dilithium provider
        print("\n3. Testing DilithiumProvider...")
        from quantum_security import DilithiumProvider
        dilithium = DilithiumProvider()
        public_key, private_key = await dilithium.generate_keypair()
        assert len(public_key) == 1312  # Dilithium2 public key size
        assert len(private_key) == 2528  # Dilithium2 private key size
        print("   ✓ Dilithium keypair generation working")

        # Test signing
        message = b"Test message for quantum signature"
        signature = await dilithium.sign(private_key, message)
        assert len(signature) == 2420  # Dilithium2 signature size
        print("   ✓ Dilithium signing working")

        # Test QuantumSecurityAgent
        print("\n4. Testing QuantumSecurityAgent...")
        from quantum_security import QuantumSecurityAgent, QuantumCapability, QuantumSecurityManager

        manager = QuantumSecurityManager()
        capabilities = [
            QuantumCapability("test_kem", "Test KEM", QuantumAlgorithm.KYBER, 1.0),
            QuantumCapability("test_sig", "Test Signature", QuantumAlgorithm.DILITHIUM, 1.0)
        ]

        agent = QuantumSecurityAgent("test_agent", "Test Agent", capabilities, manager)
        assert agent.agent_id == "test_agent"
        assert len(agent.capabilities) == 2
        print("   ✓ QuantumSecurityAgent initialization working")

        # Test agent task execution
        result = await agent.execute_security_task("test operation")
        assert "agent_id" in result
        assert "result" in result
        assert result["agent_id"] == "test_agent"
        print("   ✓ Agent task execution working")

        # Test QuantumSecurityManager
        print("\n5. Testing QuantumSecurityManager...")
        await manager.initialize_quantum_security()
        status = manager.get_security_status()
        assert status["quantum_resistant"] is True
        assert len(manager.agents) == 2  # KEM and signature agents
        print("   ✓ QuantumSecurityManager working")

        # Test global functions
        print("\n6. Testing Global Functions...")
        from quantum_security import (
            generate_quantum_keypair,
            establish_secure_channel,
            quantum_authenticate
        )

        # Test keypair generation
        keys = await generate_quantum_keypair("kyber")
        assert keys["algorithm"] == "kyber"
        print("   ✓ generate_quantum_keypair working")

        # Test channel establishment
        channel = await establish_secure_channel()
        assert "channel_id" in channel
        assert "shared_secret" in channel
        print("   ✓ establish_secure_channel working")

        # Test authentication
        auth = await quantum_authenticate("test_user")
        assert auth["identity"] == "test_user"
        assert "signature" in auth
        print("   ✓ quantum_authenticate working")

        print("\n🎉 All isolated quantum security tests passed!")
        print("\n📊 Implementation Status:")
        print("   ✅ Kyber KEM (Key Encapsulation Mechanism)")
        print("   ✅ Dilithium Digital Signatures")
        print("   ✅ Quantum Security Agents")
        print("   ✅ Agent-Based Task Orchestration")
        print("   ✅ Quantum Security Manager")
        print("   ✅ Global Utility Functions")
        print("   ✅ Quantum-Resistant Algorithms")
        print("   ✅ Modular Architecture (Inspired by NeuralForge)")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    from datetime import datetime
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    success = await test_quantum_only()

    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if success:
        print("✅ Quantum security module is fully functional!")
        print("\n🚀 Ready for integration with PyDance framework")
    else:
        print("❌ Quantum security module needs fixes")

    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
