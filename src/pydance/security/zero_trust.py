"""
Zero Trust Network implementation for PyDance framework.
Implements never trust, always verify security model.
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import secrets
import json
import asyncio
from enum import Enum


class TrustLevel(Enum):
    """Trust levels for zero trust model"""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class RiskLevel(Enum):
    """Risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DeviceFingerprint:
    """Device fingerprint for identification"""
    user_agent: str
    ip_address: str
    device_id: Optional[str] = None
    browser_fingerprint: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'user_agent': self.user_agent,
            'ip_address': self.ip_address,
            'device_id': self.device_id,
            'browser_fingerprint': self.browser_fingerprint,
            'location': self.location,
            'created_at': self.created_at.isoformat(),
            'last_seen': self.last_seen.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceFingerprint':
        """Create from dictionary"""
        return cls(
            user_agent=data['user_agent'],
            ip_address=data['ip_address'],
            device_id=data.get('device_id'),
            browser_fingerprint=data.get('browser_fingerprint'),
            location=data.get('location'),
            created_at=datetime.fromisoformat(data['created_at']),
            last_seen=datetime.fromisoformat(data['last_seen'])
        )


@dataclass
class TrustContext:
    """Context for trust evaluation"""
    user_id: str
    device_fingerprint: DeviceFingerprint
    resource: str
    action: str
    context_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'user_id': self.user_id,
            'device_fingerprint': self.device_fingerprint.to_dict(),
            'resource': self.resource,
            'action': self.action,
            'context_data': self.context_data,
            'timestamp': self.timestamp.isoformat()
        }


class TrustEngine:
    """Core trust evaluation engine"""

    def __init__(self):
        self.trust_policies: Dict[str, callable] = {}
        self.risk_policies: Dict[str, callable] = {}
        self.device_registry: Dict[str, DeviceFingerprint] = {}

    def register_trust_policy(self, name: str, policy_func: callable):
        """Register a trust evaluation policy"""
        self.trust_policies[name] = policy_func

    def register_risk_policy(self, name: str, policy_func: callable):
        """Register a risk assessment policy"""
        self.risk_policies[name] = policy_func

    async def evaluate_trust(self, context: TrustContext) -> Tuple[TrustLevel, RiskLevel]:
        """Evaluate trust level for a given context"""
        trust_scores = []
        risk_scores = []

        # Evaluate all trust policies
        for policy_name, policy_func in self.trust_policies.items():
            try:
                if asyncio.iscoroutinefunction(policy_func):
                    score = await policy_func(context)
                else:
                    score = policy_func(context)
                trust_scores.append(score)
            except Exception as e:
                # Log error but continue evaluation
                print(f"Trust policy {policy_name} failed: {e}")
                trust_scores.append(TrustLevel.NONE)

        # Evaluate all risk policies
        for policy_name, policy_func in self.risk_policies.items():
            try:
                if asyncio.iscoroutinefunction(policy_func):
                    score = await policy_func(context)
                else:
                    score = policy_func(context)
                risk_scores.append(score)
            except Exception as e:
                print(f"Risk policy {policy_name} failed: {e}")
                risk_scores.append(RiskLevel.HIGH)

        # Calculate final trust level
        avg_trust = sum(t.value for t in trust_scores) / len(trust_scores) if trust_scores else 0
        final_trust = TrustLevel(min(int(avg_trust), TrustLevel.CRITICAL.value))

        # Calculate final risk level
        risk_values = [r.value for r in risk_scores]
        if 'critical' in risk_values:
            final_risk = RiskLevel.CRITICAL
        elif 'high' in risk_values:
            final_risk = RiskLevel.HIGH
        elif 'medium' in risk_values:
            final_risk = RiskLevel.MEDIUM
        else:
            final_risk = RiskLevel.LOW

        return final_trust, final_risk

    def register_device(self, device: DeviceFingerprint) -> str:
        """Register a device in the trust registry"""
        device_id = device.device_id or secrets.token_hex(16)
        device.device_id = device_id
        self.device_registry[device_id] = device
        return device_id

    def get_device(self, device_id: str) -> Optional[DeviceFingerprint]:
        """Get device from registry"""
        return self.device_registry.get(device_id)

    def update_device_last_seen(self, device_id: str):
        """Update device last seen timestamp"""
        if device_id in self.device_registry:
            self.device_registry[device_id].last_seen = datetime.utcnow()


class ZeroTrustNetwork:
    """Zero Trust Network implementation"""

    def __init__(self, trust_engine: TrustEngine):
        self.trust_engine = trust_engine
        self.access_policies: Dict[str, Dict[str, Any]] = {}
        self.session_registry: Dict[str, Dict[str, Any]] = {}

    def define_access_policy(self, resource: str, policy: Dict[str, Any]):
        """Define access policy for a resource"""
        self.access_policies[resource] = policy

    async def authorize_request(self, user_id: str, resource: str, action: str,
                              device_fingerprint: DeviceFingerprint,
                              context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Authorize a request using zero trust principles"""

        # Create trust context
        context = TrustContext(
            user_id=user_id,
            device_fingerprint=device_fingerprint,
            resource=resource,
            action=action,
            context_data=context_data or {}
        )

        # Evaluate trust
        trust_level, risk_level = await self.trust_engine.evaluate_trust(context)

        # Check access policy
        policy = self.access_policies.get(resource, {})
        min_trust_required = policy.get('min_trust_level', TrustLevel.LOW)
        max_risk_allowed = policy.get('max_risk_level', RiskLevel.HIGH)

        # Determine authorization
        authorized = (trust_level.value >= min_trust_required.value and
                     self._risk_level_value(risk_level) <= self._risk_level_value(max_risk_allowed))

        # Additional checks based on risk level
        if risk_level == RiskLevel.CRITICAL:
            authorized = False
        elif risk_level == RiskLevel.HIGH:
            # Require additional authentication
            authorized = authorized and self._requires_step_up_auth(context)

        result = {
            'authorized': authorized,
            'trust_level': trust_level,
            'risk_level': risk_level,
            'context': context.to_dict(),
            'additional_requirements': []
        }

        if not authorized:
            result['denial_reason'] = self._get_denial_reason(trust_level, risk_level, policy)

        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            result['additional_requirements'].append('mfa_required')

        if trust_level == TrustLevel.NONE:
            result['additional_requirements'].append('device_verification')

        return result

    def _risk_level_value(self, risk_level: RiskLevel) -> int:
        """Convert risk level to numeric value"""
        return ['low', 'medium', 'high', 'critical'].index(risk_level.value)

    def _requires_step_up_auth(self, context: TrustContext) -> bool:
        """Check if step-up authentication is required"""
        # Check for suspicious patterns
        device = context.device_fingerprint

        # Check if IP address is from high-risk location
        if device.location and device.location.get('risk_score', 0) > 0.7:
            return True

        # Check if device is new or hasn't been seen recently
        if (datetime.utcnow() - device.created_at) < timedelta(hours=24):
            return True

        return False

    def _get_denial_reason(self, trust_level: TrustLevel, risk_level: RiskLevel,
                          policy: Dict[str, Any]) -> str:
        """Get reason for access denial"""
        if trust_level.value < policy.get('min_trust_level', TrustLevel.LOW).value:
            return f"Insufficient trust level. Required: {policy.get('min_trust_level')}, Current: {trust_level}"

        if self._risk_level_value(risk_level) > self._risk_level_value(policy.get('max_risk_level', RiskLevel.HIGH)):
            return f"Risk level too high. Maximum allowed: {policy.get('max_risk_level')}, Current: {risk_level}"

        return "Access denied by policy"

    def create_trust_session(self, user_id: str, device_id: str,
                           trust_level: TrustLevel) -> str:
        """Create a trust session"""
        session_id = secrets.token_hex(32)
        self.session_registry[session_id] = {
            'user_id': user_id,
            'device_id': device_id,
            'trust_level': trust_level,
            'created_at': datetime.utcnow(),
            'last_activity': datetime.utcnow(),
            'is_active': True
        }
        return session_id

    def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Validate a trust session"""
        session = self.session_registry.get(session_id)
        if not session or not session['is_active']:
            return None

        # Check session expiry (8 hours)
        if datetime.utcnow() - session['created_at'] > timedelta(hours=8):
            session['is_active'] = False
            return None

        # Update last activity
        session['last_activity'] = datetime.utcnow()

        return session

    def revoke_session(self, session_id: str):
        """Revoke a trust session"""
        if session_id in self.session_registry:
            self.session_registry[session_id]['is_active'] = False

    def get_active_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all active sessions for a user"""
        return [
            session for session in self.session_registry.values()
            if session['user_id'] == user_id and session['is_active']
        ]


# Built-in trust policies
async def device_trust_policy(context: TrustContext) -> TrustLevel:
    """Evaluate trust based on device characteristics"""
    device = context.device_fingerprint

    trust_score = TrustLevel.NONE

    # Check if device is registered
    if device.device_id:
        trust_score = TrustLevel.LOW

    # Check device age
    device_age = datetime.utcnow() - device.created_at
    if device_age > timedelta(days=30):
        trust_score = TrustLevel(max(trust_score.value, TrustLevel.MEDIUM.value))
    elif device_age > timedelta(days=7):
        trust_score = TrustLevel(max(trust_score.value, TrustLevel.LOW.value))

    # Check recent activity
    time_since_last_seen = datetime.utcnow() - device.last_seen
    if time_since_last_seen < timedelta(hours=24):
        trust_score = TrustLevel(max(trust_score.value, TrustLevel.MEDIUM.value))

    return TrustLevel(trust_score.value)


async def location_trust_policy(context: TrustContext) -> TrustLevel:
    """Evaluate trust based on location"""
    device = context.device_fingerprint

    if not device.location:
        return TrustLevel.LOW

    # Check location consistency
    # In a real implementation, you'd check against user's known locations
    risk_score = device.location.get('risk_score', 0.5)

    if risk_score < 0.3:
        return TrustLevel.HIGH
    elif risk_score < 0.7:
        return TrustLevel.MEDIUM
    else:
        return TrustLevel.LOW


async def behavior_trust_policy(context: TrustContext) -> TrustLevel:
    """Evaluate trust based on user behavior"""
    # Analyze patterns like time of access, frequency, etc.
    # This is a simplified implementation
    current_hour = datetime.utcnow().hour

    # Assume business hours are more trustworthy
    if 9 <= current_hour <= 17:
        return TrustLevel.HIGH
    elif 7 <= current_hour <= 21:
        return TrustLevel.MEDIUM
    else:
        return TrustLevel.LOW


# Built-in risk policies
async def ip_risk_policy(context: TrustContext) -> RiskLevel:
    """Assess risk based on IP address"""
    device = context.device_fingerprint

    # Check if IP is from known VPN/proxy services
    # This is a simplified check
    suspicious_patterns = ['vpn', 'proxy', 'tor']
    ip_str = device.ip_address.lower()

    for pattern in suspicious_patterns:
        if pattern in ip_str:
            return RiskLevel.HIGH

    # Check location risk
    if device.location and device.location.get('risk_score', 0) > 0.8:
        return RiskLevel.CRITICAL
    elif device.location and device.location.get('risk_score', 0) > 0.6:
        return RiskLevel.HIGH

    return RiskLevel.LOW


async def time_risk_policy(context: TrustContext) -> RiskLevel:
    """Assess risk based on access time"""
    current_time = datetime.utcnow()

    # High risk during unusual hours
    if current_time.hour < 5 or current_time.hour > 22:
        return RiskLevel.MEDIUM

    # Very high risk during maintenance windows
    if current_time.weekday() >= 5:  # Weekend
        return RiskLevel.MEDIUM

    return RiskLevel.LOW


async def action_risk_policy(context: TrustContext) -> RiskLevel:
    """Assess risk based on the action being performed"""
    high_risk_actions = ['delete', 'admin', 'financial', 'security']
    medium_risk_actions = ['update', 'create', 'modify']

    if any(action in context.action.lower() for action in high_risk_actions):
        return RiskLevel.HIGH
    elif any(action in context.action.lower() for action in medium_risk_actions):
        return RiskLevel.MEDIUM

    return RiskLevel.LOW


# Global zero trust network instance
_zero_trust_network = None

def get_zero_trust_network() -> ZeroTrustNetwork:
    """Get global zero trust network instance"""
    global _zero_trust_network
    if _zero_trust_network is None:
        trust_engine = TrustEngine()

        # Register built-in policies
        trust_engine.register_trust_policy('device_trust', device_trust_policy)
        trust_engine.register_trust_policy('location_trust', location_trust_policy)
        trust_engine.register_trust_policy('behavior_trust', behavior_trust_policy)

        trust_engine.register_risk_policy('ip_risk', ip_risk_policy)
        trust_engine.register_risk_policy('time_risk', time_risk_policy)
        trust_engine.register_risk_policy('action_risk', action_risk_policy)

        _zero_trust_network = ZeroTrustNetwork(trust_engine)

    return _zero_trust_network
