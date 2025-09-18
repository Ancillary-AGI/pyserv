# Quantum Security for PyDance Framework

## Overview

The PyDance Quantum Security module provides quantum-resistant cryptographic operations and secure communication protocols. Inspired by the NeuralForge framework's modular architecture, it implements post-quantum cryptography (PQC) algorithms that protect against both classical and quantum computing threats.

## Features

### 🔐 Quantum-Resistant Algorithms
- **Kyber**: Lattice-based key encapsulation mechanism (KEM) for secure key exchange
- **Dilithium**: Lattice-based digital signatures for authentication
- **Future Support**: Falcon, SPHINCS+ for additional quantum-resistant operations

### 🤖 Agent-Based Security Architecture
- **Security Agents**: Specialized agents for different cryptographic operations
- **Task Orchestration**: Intelligent routing of security tasks to appropriate agents
- **Performance Monitoring**: Real-time metrics and latency tracking

### 🔗 Seamless Integration
- **Cryptography Module**: Extended with quantum-resistant methods
- **Key Management**: Quantum key lifecycle management
- **Middleware**: HTTP and WebSocket quantum security middleware
- **Backward Compatibility**: Classical crypto still available as fallback

### 🌐 Web Framework Integration
- **HTTP Middleware**: Quantum authentication and channel establishment
- **WebSocket Support**: Quantum-secure real-time communication
- **Header-Based Signaling**: Quantum security status in HTTP headers

## Quick Start

### Installation

The quantum security module is included with PyDance. Ensure you have the framework installed:

```bash
pip install -e .
```

### Basic Usage

```python
import asyncio
from src.pydance.security.quantum_security import (
    generate_quantum_keypair,
    establish_secure_channel,
    quantum_authenticate
)

async def main():
    # Generate quantum-resistant keypair
    keys = await generate_quantum_keypair("kyber")
    print(f"Generated {keys['algorithm']} keypair")

    # Establish quantum-secure channel
    channel = await establish_secure_channel()
    print(f"Channel established: {channel['channel_id']}")

    # Perform quantum authentication
    auth = await quantum_authenticate("user123")
    print(f"Authenticated: {auth['identity']}")

asyncio.run(main())
```

### Integration with Existing Code

```python
from src.pydance.security.cryptography import get_crypto_manager

crypto = get_crypto_manager()

# Use quantum methods alongside classical ones
quantum_keys = await crypto.generate_quantum_keypair("dilithium")
channel = await crypto.establish_quantum_secure_channel()
status = crypto.get_quantum_security_status()
```

## Architecture

### Core Components

#### QuantumSecurityManager
Central orchestrator that manages security agents, key stores, and operations.

```python
from src.pydance.security.quantum_security import get_quantum_security_manager

manager = get_quantum_security_manager()
await manager.initialize_quantum_security()

# Perform secure operations
result = await manager.perform_secure_operation("encrypt data")
```

#### QuantumSecurityAgent
Specialized agents for different security tasks:

- **KEM Agent**: Handles key encapsulation operations
- **Signature Agent**: Manages digital signatures
- **Custom Agents**: Extensible for additional operations

#### Quantum Providers
Algorithm implementations:

- **KyberProvider**: NIST Round 3 finalist for key exchange
- **DilithiumProvider**: NIST Round 3 finalist for signatures

### Middleware Integration

#### HTTP Middleware

```python
from src.pydance.security.middleware import QuantumSecurityMiddleware

# Add to your application
app.add_middleware(QuantumSecurityMiddleware(
    require_quantum_auth=False,  # Optional quantum auth
    auto_establish_channel=True  # Auto-establish secure channels
))
```

#### WebSocket Middleware

```python
from src.pydance.security.middleware import QuantumWebSocketMiddleware

# Add to WebSocket routes
app.add_websocket_middleware(QuantumWebSocketMiddleware(
    require_quantum_auth=True,  # Require quantum auth for WebSockets
    channel_timeout=300  # 5 minute channel timeout
))
```

## API Reference

### Quantum Security Manager

#### `initialize_quantum_security()`
Initialize the quantum security system with default agents and keys.

#### `perform_secure_operation(operation: str, context: Dict = None)`
Execute a security operation using the appropriate agent.

#### `establish_quantum_secure_channel(peer_key: bytes = None)`
Establish a quantum-secure communication channel.

#### `authenticate_quantum_secure(identity: str, challenge: bytes = None)`
Perform quantum-resistant authentication.

#### `get_security_status()`
Get current quantum security system status.

### Key Management Integration

#### `create_quantum_key(purpose: str, algorithm: QuantumAlgorithm)`
Create a quantum-resistant key for specific purpose.

#### `sign_with_quantum_key(key_id: str, data: bytes)`
Sign data with quantum-resistant key.

#### `verify_with_quantum_key(key_id: str, data: bytes, signature: bytes)`
Verify quantum signature.

#### `perform_quantum_kem(key_id: str)`
Perform key encapsulation with quantum key.

### Cryptography Module Extensions

#### `generate_quantum_keypair(algorithm: str)`
Generate quantum-resistant keypair.

#### `establish_quantum_secure_channel()`
Establish quantum-secure channel.

#### `quantum_authenticate(identity: str)`
Perform quantum authentication.

#### `perform_quantum_operation(operation: str, context: Dict = None)`
Execute quantum security operation.

#### `get_quantum_security_status()`
Get quantum security status.

## Security Considerations

### Quantum Threats Addressed
- **Shor's Algorithm**: Breaks RSA/ECC - mitigated by lattice-based crypto
- **Grover's Algorithm**: Reduces symmetric key strength - addressed by increased key sizes
- **Harvest Now, Decrypt Later**: Quantum-resistant algorithms prevent future decryption

### Best Practices
1. **Hybrid Approach**: Use quantum-resistant algorithms alongside classical ones during transition
2. **Key Rotation**: Regularly rotate quantum keys as with classical keys
3. **Algorithm Diversity**: Use different algorithms for different purposes (Kyber for KEM, Dilithium for signatures)
4. **Performance Monitoring**: Monitor operation latency and resource usage
5. **Fallback Mechanisms**: Ensure graceful degradation if quantum operations fail

### Performance Characteristics
- **Kyber**: ~2-3x slower than ECDH for key exchange
- **Dilithium**: ~10-20x slower than ECDSA for signatures
- **Key Sizes**: Larger than classical equivalents (Kyber: 800B public, Dilithium: 1312B public)

## Testing

Run the quantum security test suite:

```bash
pytest tests/security/test_quantum_security.py -v
```

Run the interactive demo:

```python
python examples/quantum_security_demo.py
```

## Future Enhancements

### Planned Features
- **Hardware Acceleration**: GPU/FPGA acceleration for quantum operations
- **Additional Algorithms**: Support for Falcon, SPHINCS+ algorithms
- **Quantum TLS**: Integration with quantum-resistant TLS 1.3
- **Distributed Operations**: Multi-party quantum computations
- **Zero-Knowledge Proofs**: Quantum-resistant ZKP protocols

### Research Integration
- **NIST Standardization**: Tracking ongoing PQC standardization
- **Algorithm Updates**: Easy migration path for algorithm improvements
- **Security Analysis**: Integration with formal verification tools

## Contributing

### Adding New Algorithms
1. Implement `QuantumProvider` subclass
2. Add to `QuantumAlgorithm` enum
3. Register in `QuantumSecurityManager.providers`
4. Add comprehensive tests
5. Update documentation

### Adding Security Agents
1. Extend `QuantumSecurityAgent` class
2. Define capabilities with `QuantumCapability`
3. Implement task execution logic
4. Register with security manager
5. Add integration tests

## License

This quantum security module is part of the PyDance framework and follows the same license terms.

## References

- [NIST Post-Quantum Cryptography](https://csrc.nist.gov/projects/post-quantum-cryptography)
- [Kyber Specification](https://pq-crystals.org/kyber/)
- [Dilithium Specification](https://pq-crystals.org/dilithium/)
- [NeuralForge Framework](https://github.com/ancillary-ai/neuralforge)

## Support

For questions and support:
- Documentation: [PyDance Docs](https://pydance.readthedocs.io/)
- Issues: [GitHub Issues](https://github.com/ancillary-ai/pydance/issues)
- Security: [Security Policy](https://github.com/ancillary-ai/pydance/security)
