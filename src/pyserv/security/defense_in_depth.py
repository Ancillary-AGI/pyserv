"""
Defense in Depth implementation for Pyserv  framework.
Multiple layers of security controls and monitoring.
"""

from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import hashlib
import secrets
from enum import Enum


class SecurityLayer(Enum):
    """Security layers in defense in depth model"""
    NETWORK = "network"
    HOST = "host"
    APPLICATION = "application"
    DATA = "data"


class SecurityControl(Enum):
    """Types of security controls"""
    PREVENTION = "prevention"
    DETECTION = "detection"
    RESPONSE = "response"
    RECOVERY = "recovery"


@dataclass
class SecurityEvent:
    """Security event representation"""
    id: str
    timestamp: datetime
    layer: SecurityLayer
    control_type: SecurityControl
    severity: str  # low, medium, high, critical
    source: str
    description: str
    details: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolution_time: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'layer': self.layer.value,
            'control_type': self.control_type.value,
            'severity': self.severity,
            'source': self.source,
            'description': self.description,
            'details': self.details,
            'resolved': self.resolved,
            'resolution_time': self.resolution_time.isoformat() if self.resolution_time else None
        }


@dataclass
class SecurityPolicy:
    """Security policy definition"""
    name: str
    layer: SecurityLayer
    control_type: SecurityControl
    conditions: Dict[str, Any]
    actions: List[Dict[str, Any]]
    enabled: bool = True
    priority: int = 1

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate if policy conditions are met"""
        for key, expected_value in self.conditions.items():
            if key not in context:
                return False

            actual_value = context[key]
            if isinstance(expected_value, dict):
                # Handle operators
                if not self._evaluate_condition(expected_value, actual_value):
                    return False
            else:
                if actual_value != expected_value:
                    return False

        return True

    def _evaluate_condition(self, condition: Dict[str, Any], actual_value: Any) -> bool:
        """Evaluate condition with operators"""
        for operator, expected in condition.items():
            if operator == 'equals' and actual_value != expected:
                return False
            elif operator == 'contains' and expected not in str(actual_value):
                return False
            elif operator == 'greater_than' and actual_value <= expected:
                return False
            elif operator == 'less_than' and actual_value >= expected:
                return False
        return True


class DefenseInDepth:
    """Main defense in depth implementation"""

    def __init__(self):
        self.layers: Dict[SecurityLayer, List[SecurityPolicy]] = {
            layer: [] for layer in SecurityLayer
        }
        self.controls: Dict[SecurityControl, List[Callable]] = {
            control: [] for control in SecurityControl
        }
        self.events: List[SecurityEvent] = []
        self.incident_response_plans: Dict[str, Dict[str, Any]] = {}

    def add_policy(self, policy: SecurityPolicy):
        """Add security policy"""
        self.layers[policy.layer].append(policy)

    def register_control(self, control_type: SecurityControl, control_func: Callable):
        """Register security control"""
        self.controls[control_type].append(control_func)

    def add_incident_response_plan(self, incident_type: str, plan: Dict[str, Any]):
        """Add incident response plan"""
        self.incident_response_plans[incident_type] = plan

    async def process_request(self, request_context: Dict[str, Any]) -> Dict[str, Any]:
        """Process request through all security layers"""
        security_context = {
            'request': request_context,
            'events': [],
            'violations': [],
            'recommendations': []
        }

        # Process each layer
        for layer in SecurityLayer:
            layer_result = await self._process_layer(layer, request_context)
            security_context[layer.value] = layer_result

            if layer_result.get('blocked', False):
                security_context['blocked'] = True
                security_context['blocking_layer'] = layer.value
                break

        # Execute detection controls
        await self._execute_controls(SecurityControl.DETECTION, security_context)

        # Generate security event if violations found
        if security_context['violations']:
            await self._create_security_event(security_context)

        return security_context

    async def _process_layer(self, layer: SecurityLayer, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process a specific security layer"""
        layer_policies = self.layers[layer]
        layer_result = {
            'policies_evaluated': len(layer_policies),
            'violations': [],
            'passed': True,
            'blocked': False
        }

        for policy in sorted(layer_policies, key=lambda p: p.priority, reverse=True):
            if not policy.enabled:
                continue

            if policy.evaluate(context):
                # Policy conditions met, execute actions
                for action in policy.actions:
                    action_result = await self._execute_action(action, context)
                    if action_result.get('block', False):
                        layer_result['blocked'] = True
                        layer_result['blocking_policy'] = policy.name
                        layer_result['passed'] = False
                        break

                    if action_result.get('violation', False):
                        layer_result['violations'].append({
                            'policy': policy.name,
                            'action': action,
                            'result': action_result
                        })

                if layer_result['blocked']:
                    break

        return layer_result

    async def _execute_action(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute security action"""
        action_type = action.get('type')

        if action_type == 'block':
            return {'block': True, 'reason': action.get('reason', 'Policy violation')}
        elif action_type == 'log':
            return await self._log_security_event(action, context)
        elif action_type == 'alert':
            return await self._send_alert(action, context)
        elif action_type == 'redirect':
            return {'redirect': action.get('url'), 'reason': action.get('reason')}
        elif action_type == 'rate_limit':
            return await self._apply_rate_limit(action, context)

        return {}

    async def _execute_controls(self, control_type: SecurityControl, context: Dict[str, Any]):
        """Execute security controls of specific type"""
        for control_func in self.controls[control_type]:
            try:
                if asyncio.iscoroutinefunction(control_func):
                    await control_func(context)
                else:
                    control_func(context)
            except Exception as e:
                print(f"Error executing {control_type.value} control: {e}")

    async def _create_security_event(self, context: Dict[str, Any]):
        """Create security event"""
        violations = context.get('violations', [])
        if not violations:
            return

        # Determine severity based on violations
        severity = 'low'
        if any(v.get('severity') == 'high' for v in violations):
            severity = 'high'
        elif any(v.get('severity') == 'medium' for v in violations):
            severity = 'medium'

        event = SecurityEvent(
            id=f"evt_{secrets.token_hex(8)}",
            timestamp=datetime.utcnow(),
            layer=SecurityLayer.APPLICATION,
            control_type=SecurityControl.DETECTION,
            severity=severity,
            source='defense_in_depth',
            description=f"Security violations detected: {len(violations)}",
            details={
                'violations': violations,
                'request_context': context.get('request', {})
            }
        )

        self.events.append(event)

        # Trigger incident response if critical
        if severity == 'critical':
            await self._trigger_incident_response(event)

    async def _trigger_incident_response(self, event: SecurityEvent):
        """Trigger incident response plan"""
        incident_type = self._classify_incident(event)
        plan = self.incident_response_plans.get(incident_type)

        if plan:
            # Execute automated response actions
            for action in plan.get('automated_actions', []):
                await self._execute_incident_action(action, event)

            # Notify response team
            await self._notify_response_team(plan, event)

    def _classify_incident(self, event: SecurityEvent) -> str:
        """Classify incident type"""
        if 'sql_injection' in event.description.lower():
            return 'sql_injection'
        elif 'xss' in event.description.lower():
            return 'xss_attack'
        elif 'brute_force' in event.description.lower():
            return 'brute_force'
        else:
            return 'general_security_incident'

    async def _execute_incident_action(self, action: Dict[str, Any], event: SecurityEvent):
        """Execute incident response action"""
        action_type = action.get('type')

        if action_type == 'isolate':
            # Isolate affected system/component
            print(f"Isolating system due to incident: {event.id}")
        elif action_type == 'block_ip':
            # Block suspicious IP
            ip = action.get('ip')
            if ip:
                print(f"Blocking IP {ip} due to incident: {event.id}")
        elif action_type == 'disable_user':
            # Disable compromised user account
            user_id = action.get('user_id')
            if user_id:
                print(f"Disabling user {user_id} due to incident: {event.id}")

    async def _notify_response_team(self, plan: Dict[str, Any], event: SecurityEvent):
        """Notify incident response team"""
        notification_config = plan.get('notification', {})
        channels = notification_config.get('channels', ['email'])

        message = f"""
        🚨 SECURITY INCIDENT DETECTED 🚨

        Event ID: {event.id}
        Severity: {event.severity}
        Description: {event.description}
        Timestamp: {event.timestamp}

        Details: {event.details}

        Please investigate immediately.
        """

        for channel in channels:
            if channel == 'email':
                await self._send_email_notification(notification_config.get('email_recipients', []), message)
            elif channel == 'slack':
                await self._send_slack_notification(notification_config.get('slack_webhook'), message)

    async def _log_security_event(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Log security event"""
        print(f"Security Event: {action.get('message', 'Policy violation')} - Context: {context}")
        return {'logged': True}

    async def _send_alert(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Send security alert"""
        alert_message = action.get('message', 'Security alert triggered')
        print(f"🚨 ALERT: {alert_message}")
        return {'alert_sent': True}

    async def _apply_rate_limit(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply rate limiting"""
        duration = action.get('duration', 300)  # 5 minutes default
        print(f"Rate limiting applied for {duration} seconds")
        return {'rate_limited': True, 'duration': duration}

    async def _send_email_notification(self, recipients: List[str], message: str):
        """Send email notification"""
        print(f"Sending email notification to {recipients}: {message[:100]}...")

    async def _send_slack_notification(self, webhook_url: str, message: str):
        """Send Slack notification"""
        print(f"Sending Slack notification to {webhook_url}: {message[:100]}...")

    def get_security_events(self, limit: int = 100, severity: Optional[str] = None) -> List[SecurityEvent]:
        """Get security events"""
        events = self.events

        if severity:
            events = [e for e in events if e.severity == severity]

        return sorted(events, key=lambda e: e.timestamp, reverse=True)[:limit]

    def get_security_metrics(self) -> Dict[str, Any]:
        """Get security metrics"""
        total_events = len(self.events)
        unresolved_events = len([e for e in self.events if not e.resolved])

        severity_counts = {}
        for event in self.events:
            severity_counts[event.severity] = severity_counts.get(event.severity, 0) + 1

        layer_counts = {}
        for event in self.events:
            layer_counts[event.layer.value] = layer_counts.get(event.layer.value, 0) + 1

        return {
            'total_events': total_events,
            'unresolved_events': unresolved_events,
            'severity_distribution': severity_counts,
            'layer_distribution': layer_counts,
            'recent_events': len([e for e in self.events
                                if (datetime.utcnow() - e.timestamp) < timedelta(hours=24)])
        }


# Built-in security policies
def create_default_policies() -> List[SecurityPolicy]:
    """Create default security policies"""
    return [
        # Network layer policies
        SecurityPolicy(
            name="block_suspicious_ips",
            layer=SecurityLayer.NETWORK,
            control_type=SecurityControl.PREVENTION,
            conditions={"ip_risk_score": {"greater_than": 0.8}},
            actions=[{"type": "block", "reason": "High-risk IP address"}]
        ),

        # Host layer policies
        SecurityPolicy(
            name="detect_anomalous_login",
            layer=SecurityLayer.HOST,
            control_type=SecurityControl.DETECTION,
            conditions={"login_attempts": {"greater_than": 5}},
            actions=[{"type": "alert", "message": "Multiple failed login attempts"}]
        ),

        # Application layer policies
        SecurityPolicy(
            name="prevent_sql_injection",
            layer=SecurityLayer.APPLICATION,
            control_type=SecurityControl.PREVENTION,
            conditions={"input_contains": ["SELECT", "UNION", "DROP", "DELETE"]},
            actions=[
                {"type": "block", "reason": "Potential SQL injection detected"},
                {"type": "log", "message": "SQL injection attempt blocked"}
            ]
        ),

        SecurityPolicy(
            name="rate_limit_api",
            layer=SecurityLayer.APPLICATION,
            control_type=SecurityControl.PREVENTION,
            conditions={"request_count": {"greater_than": 100}},
            actions=[{"type": "rate_limit", "duration": 300}]
        ),

        # Data layer policies
        SecurityPolicy(
            name="encrypt_sensitive_data",
            layer=SecurityLayer.DATA,
            control_type=SecurityControl.PREVENTION,
            conditions={"data_type": "sensitive"},
            actions=[{"type": "encrypt"}]
        )
    ]


# Global defense in depth instance
_defense_in_depth = None

def get_defense_in_depth() -> DefenseInDepth:
    """Get global defense in depth instance"""
    global _defense_in_depth
    if _defense_in_depth is None:
        _defense_in_depth = DefenseInDepth()

        # Add default policies
        for policy in create_default_policies():
            _defense_in_depth.add_policy(policy)

    return _defense_in_depth


# Security monitoring functions
async def monitor_failed_logins(context: Dict[str, Any]):
    """Monitor failed login attempts"""
    if context.get('event_type') == 'failed_login':
        user_id = context.get('user_id')
        ip_address = context.get('ip_address')

        # Implement progressive delays, account lockouts, etc.
        print(f"Failed login detected for user {user_id} from IP {ip_address}")

async def monitor_suspicious_traffic(context: Dict[str, Any]):
    """Monitor for suspicious traffic patterns"""
    request_count = context.get('request_count', 0)
    if request_count > 1000:  # per minute
        print("High traffic detected - potential DDoS attack")

async def monitor_data_exfiltration(context: Dict[str, Any]):
    """Monitor for potential data exfiltration"""
    data_size = context.get('response_size', 0)
    if data_size > 1000000:  # 1MB
        print("Large data transfer detected - potential exfiltration")

# Register monitoring functions
defense_system = get_defense_in_depth()
defense_system.register_control(SecurityControl.DETECTION, monitor_failed_logins)
defense_system.register_control(SecurityControl.DETECTION, monitor_suspicious_traffic)
defense_system.register_control(SecurityControl.DETECTION, monitor_data_exfiltration)




