"""
Advanced Security Framework for PyDance.
Includes IAM, cryptography, zero trust, and Web3 integration.
"""

from .iam import IAM, Role, Permission, Policy, User as IAMUser, get_iam_system
from .cryptography import CryptoManager, ECCManager, HashManager, get_crypto_manager
from .zero_trust import ZeroTrustNetwork, TrustEngine, get_zero_trust_network
from .web3 import Web3Manager, BlockchainClient, SmartContract
from .defense_in_depth import DefenseInDepth, SecurityLayers, get_defense_in_depth

__all__ = [
    'IAM',
    'Role',
    'Permission',
    'Policy',
    'IAMUser',
    'get_iam_system',
    'CryptoManager',
    'ECCManager',
    'HashManager',
    'get_crypto_manager',
    'ZeroTrustNetwork',
    'TrustEngine',
    'get_zero_trust_network',
    'Web3Manager',
    'BlockchainClient',
    'SmartContract',
    'DefenseInDepth',
    'SecurityLayers',
    'get_defense_in_depth'
]
