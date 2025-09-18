#!/usr/bin/env python3
"""
Quantum Security Demo for PyDance Framework
Demonstrates quantum-resistant cryptographic operations and secure communication.
"""

import asyncio
import json
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.pydance.security.quantum_security import (
    get_quantum_security_manager,
    QuantumAlgorithm,
    generate_quantum_keypair,
    establish_secure_channel,
    quantum_authenticate
)
from src.pydance.security.cryptography import get_crypto_manager
from src.pydance.security.key_management import get_key_manager, HSMConfig


async def demo_quantum_keypair_generation():
    """Demonstrate quantum-resistant keypair generation"""
    print("🔐 Quantum Keypair Generation Demo")
    print("=" * 50)

    # Generate Kyber keypair for key exchange
    print("\n1. Generating Kyber keypair (for key exchange)...")
    kyber_keys = await generate_quantum_keypair("kyber")
    print(f"   Algorithm: {kyber_keys['algorithm']}")
    print(f"   Public Key Length: {len(kyber_keys['public_key'])} bytes")
    print(f"   Private Key Length: {len(kyber_keys['private_key'])} bytes")

    # Generate Dilithium keypair for digital signatures
    print("\n2. Generating Dilithium keypair (for digital signatures)...")
    dilithium_keys = await generate_quantum_keypair("dilithium")
    print(f"   Algorithm: {dilithium_keys['algorithm']}")
    print(f"   Public Key Length: {len(dilithium_keys['public_key'])} bytes")
    print(f"   Private Key Length: {len(dilithium_keys['private_key'])} bytes")


async def demo_secure_channel_establishment():
    """Demonstrate quantum-secure channel establishment"""
    print("\n🔒 Quantum-Secure Channel Establishment Demo")
    print("=" * 50)

    print("\n1. Establishing quantum-secure communication channel...")
    channel_info = await establish_secure_channel()

    print(f"   Channel ID: {channel_info['channel_id']}")
    print(f"   Algorithm: {channel_info['algorithm']}")
    print(f"   Shared Secret Length: {len(channel_info['shared_secret'])} bytes")
    print(f"   Established At: {channel_info['established_at']}")

    return channel_info


async def demo_quantum_authentication():
    """Demonstrate quantum-resistant authentication"""
    print("\n🔑 Quantum Authentication Demo")
    print("=" * 50)

    test_users = ["alice", "bob", "charlie"]

    for user in test_users:
        print(f"\n1. Authenticating user: {user}")
        auth_result = await quantum_authenticate(user)

        print(f"   Identity: {auth_result['identity']}")
        print(f"   Algorithm: {auth_result['algorithm']}")
        print(f"   Signature Length: {len(auth_result['signature'])} bytes")
        print(f"   Challenge Length: {len(auth_result['challenge'])} bytes")
        print(f"   Authenticated At: {auth_result['authenticated_at']}")


async def demo_quantum_security_manager():
    """Demonstrate the quantum security manager"""
    print("\n🛡️  Quantum Security Manager Demo")
    print("=" * 50)

    # Get the quantum security manager
    manager = get_quantum_security_manager()

    print("\n1. Initializing quantum security system...")
    await manager.initialize_quantum_security()
    print("   ✓ Security agents initialized")
    print("   ✓ Quantum keys generated")

    # Show security status
    print("\n2. Current security status:")
    status = manager.get_security_status()
    print(f"   Quantum Resistant: {status['quantum_resistant']}")
    print(f"   Active Agents: {status['active_agents']}")
    print(f"   Total Agents: {status['total_agents']}")
    print(f"   Quantum Keys: {status['quantum_keys']}")
    print(f"   Supported Algorithms: {', '.join(status['algorithms_supported'])}")

    # Perform secure operations
    print("\n3. Performing secure operations...")

    # Key encapsulation operation
    kem_result = await manager.perform_secure_operation("encapsulate data")
    print(f"   KEM Operation: {kem_result['result']['operation']}")
    print(f"   Agent: {kem_result['agent_id']}")
    print(f"   Algorithm: {kem_result['algorithm']}")
    print(f"   Latency: {kem_result['latency']:.4f}s")

    # Digital signature operation
    sig_result = await manager.perform_secure_operation("sign message", {"message": "Hello Quantum World!"})
    print(f"   Signature Operation: {sig_result['result']['operation']}")
    print(f"   Agent: {sig_result['agent_id']}")
    print(f"   Algorithm: {sig_result['algorithm']}")
    print(f"   Latency: {sig_result['latency']:.4f}s")


async def demo_integrated_cryptography():
    """Demonstrate integration with existing cryptography module"""
    print("\n🔗 Integrated Cryptography Demo")
    print("=" * 50)

    crypto_manager = get_crypto_manager()

    print("\n1. Testing quantum methods in CryptoManager...")

    # Generate quantum keypair
    quantum_keys = await crypto_manager.generate_quantum_keypair("kyber")
    print(f"   ✓ Generated {quantum_keys['algorithm']} keypair")

    # Establish secure channel
    channel = await crypto_manager.establish_quantum_secure_channel()
    print(f"   ✓ Established secure channel: {channel['channel_id']}")

    # Perform quantum authentication
    auth = await crypto_manager.quantum_authenticate("integrated_user")
    print(f"   ✓ Authenticated user: {auth['identity']}")

    # Get security status
    status = crypto_manager.get_quantum_security_status()
    print(f"   ✓ Security Status - Quantum Resistant: {status['quantum_resistant']}")


async def demo_quantum_key_management():
    """Demonstrate quantum key management"""
    print("\n🔐 Quantum Key Management Demo")
    print("=" * 50)

    # Initialize key manager
    config = HSMConfig(hsm_type="software")
    key_manager = get_key_manager(config)

    print("\n1. Creating quantum keys...")

    # Create Kyber key for encryption
    kyber_key_id = await key_manager.create_quantum_key("encryption", QuantumAlgorithm.KYBER)
    print(f"   ✓ Created Kyber key: {kyber_key_id}")

    # Create Dilithium key for signing
    dilithium_key_id = await key_manager.create_quantum_key("signing", QuantumAlgorithm.DILITHIUM)
    print(f"   ✓ Created Dilithium key: {dilithium_key_id}")

    print("\n2. Retrieving quantum keys...")
    kyber_key = await key_manager.get_quantum_key(kyber_key_id)
    dilithium_key = await key_manager.get_quantum_key(dilithium_key_id)

    print(f"   ✓ Retrieved Kyber key: {kyber_key.algorithm.value}")
    print(f"   ✓ Retrieved Dilithium key: {dilithium_key.algorithm.value}")

    print("\n3. Performing quantum operations...")

    # Test KEM
    kem_result = await key_manager.perform_quantum_kem(kyber_key_id)
    print(f"   ✓ KEM operation completed, shared secret length: {len(kem_result[1])} bytes")

    # Test signing
    test_message = b"This is a test message for quantum signing"
    signature = await key_manager.sign_with_quantum_key(dilithium_key_id, test_message)
    print(f"   ✓ Signed message, signature length: {len(signature)} bytes")

    # Test verification
    is_valid = await key_manager.verify_with_quantum_key(dilithium_key_id, test_message, signature)
    print(f"   ✓ Signature verification: {'✓ Valid' if is_valid else '✗ Invalid'}")


async def demo_middleware_integration():
    """Demonstrate quantum security middleware integration"""
    print("\n🌐 Quantum Security Middleware Demo")
    print("=" * 50)

    try:
        from src.pydance.security.middleware import QuantumSecurityMiddleware

        print("\n1. Testing quantum security middleware availability...")
        print("   ✓ QuantumSecurityMiddleware imported successfully")

        # Create middleware instance
        middleware = QuantumSecurityMiddleware(
            require_quantum_auth=False,  # Optional for demo
            auto_establish_channel=True
        )

        print("   ✓ QuantumSecurityMiddleware instance created")

        # Show middleware configuration
        print("\n2. Middleware configuration:")
        print(f"   Require Quantum Auth: {middleware.options['require_quantum_auth']}")
        print(f"   Auto Establish Channel: {middleware.options['auto_establish_channel']}")
        print(f"   Quantum Header: {middleware.options['quantum_header_name']}")
        print(f"   Channel Header: {middleware.options['channel_header_name']}")

        # Get quantum manager status
        status = middleware.quantum_manager.get_security_status()
        print(f"   Active Security Agents: {status['active_agents']}")

    except ImportError:
        print("   ⚠️  Quantum middleware not available (module not imported)")


async def demo_performance_comparison():
    """Compare performance of quantum vs classical operations"""
    print("\n⚡ Performance Comparison Demo")
    print("=" * 50)

    import time

    # Test quantum operations
    print("\n1. Testing quantum operations performance...")

    start_time = time.time()
    for _ in range(10):
        await generate_quantum_keypair("kyber")
    quantum_time = time.time() - start_time

    print(".4f")

    # Test classical operations
    print("\n2. Testing classical operations performance...")

    crypto_manager = get_crypto_manager()

    start_time = time.time()
    for _ in range(10):
        crypto_manager.generate_ecc_keypair()
    classical_time = time.time() - start_time

    print(".4f")

    # Calculate ratio
    ratio = quantum_time / classical_time if classical_time > 0 else float('inf')
    print(".2f")


async def main():
    """Main demo function"""
    print("🚀 PyDance Quantum Security Framework Demo")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        # Run all demos
        await demo_quantum_keypair_generation()
        await demo_secure_channel_establishment()
        await demo_quantum_authentication()
        await demo_quantum_security_manager()
        await demo_integrated_cryptography()
        await demo_quantum_key_management()
        await demo_middleware_integration()
        await demo_performance_comparison()

        print("\n🎉 All demos completed successfully!")
        print("\n📚 Key Takeaways:")
        print("   • Quantum-resistant algorithms protect against future quantum attacks")
        print("   • Kyber provides secure key exchange (KEM)")
        print("   • Dilithium provides secure digital signatures")
        print("   • Modular agent-based architecture enables flexible security operations")
        print("   • Seamless integration with existing PyDance security modules")
        print("   • Middleware support for quantum-secure web applications")

    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print(f"\n🏁 Demo completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    # Set up asyncio event loop
    asyncio.run(main())
