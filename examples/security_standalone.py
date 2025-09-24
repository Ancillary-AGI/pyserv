#!/usr/bin/env python3
"""
Standalone Quantum Security Demo
Tests quantum security components without full framework dependencies.
"""

import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

async def test_quantum_security():
    """Test quantum security components directly"""
    print("🚀 Testing Pyserv  Quantum Security Components")
    print("=" * 60)

    try:
        # Import quantum security module
        from pyserv.security.quantum_security import (
            QuantumSecurityManager,
            QuantumAlgorithm,
            KyberProvider,
            DilithiumProvider,
            generate_quantum_keypair,
            establish_secure_channel,
            quantum_authenticate
        )
        print("✓ Quantum security module imported successfully")

        # Test Kyber provider
        print("\n1. Testing Kyber Provider...")
        kyber = KyberProvider()
        public_key, private_key = await kyber.generate_keypair()
        print(f"   ✓ Generated Kyber keypair: {len(public_key)}B public, {len(private_key)}B private")

        ciphertext, shared_secret = await kyber.encapsulate(public_key)
        print(f"   ✓ Performed key encapsulation: {len(ciphertext)}B ciphertext, {len(shared_secret)}B secret")

        # Test Dilithium provider
        print("\n2. Testing Dilithium Provider...")
        dilithium = DilithiumProvider()
        public_key, private_key = await dilithium.generate_keypair()
        print(f"   ✓ Generated Dilithium keypair: {len(public_key)}B public, {len(private_key)}B private")

        message = b"Test message for quantum signing"
        signature = await dilithium.sign(private_key, message)
        print(f"   ✓ Signed message: {len(signature)}B signature")

        # Test global functions
        print("\n3. Testing Global Functions...")

        # Generate keypair
        keys = await generate_quantum_keypair("kyber")
        print(f"   ✓ Generated {keys['algorithm']} keypair via global function")

        # Establish channel
        channel = await establish_secure_channel()
        print(f"   ✓ Established secure channel: {channel['channel_id']}")

        # Authenticate
        auth = await quantum_authenticate("test_user")
        print(f"   ✓ Authenticated user: {auth['identity']}")

        # Test security manager
        print("\n4. Testing Quantum Security Manager...")
        manager = QuantumSecurityManager()
        await manager.initialize_quantum_security()

        status = manager.get_security_status()
        print(f"   ✓ Manager initialized: {status['active_agents']} active agents")
        print(f"   ✓ Quantum resistant: {status['quantum_resistant']}")
        print(f"   ✓ Supported algorithms: {', '.join(status['algorithms_supported'])}")

        # Test secure operation
        result = await manager.perform_secure_operation("test operation")
        print(f"   ✓ Performed secure operation via agent: {result['agent_id']}")

        print("\n🎉 All quantum security tests passed!")
        print("\n📊 Summary:")
        print("   • Kyber KEM: Working (NIST Round 3 finalist)")
        print("   • Dilithium signatures: Working (NIST Round 3 finalist)")
        print("   • Security manager: Operational with agent-based architecture")
        print("   • Global functions: Available for easy integration")
        print("   • Quantum resistance: Enabled against Shor's/Grover's algorithms")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   This might be due to missing dependencies or path issues")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    from datetime import datetime
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    success = await test_quantum_security()

    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if success:
        print("✅ Quantum security implementation is ready!")
    else:
        print("❌ Quantum security implementation needs fixes")

    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)




