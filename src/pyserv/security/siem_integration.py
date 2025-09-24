"""
SIEM (Security Information and Event Management) Integration.
Provides centralized security monitoring and alerting.
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import json
import aiohttp
from enum import Enum


class SIEMProvider(Enum):
    """Supported SIEM providers"""
    SPLUNK = "splunk"
    ELASTICSEARCH = "elasticsearch"
    SUMOLOGIC = "sumologic"
    DATADOG = "datadog"
    CUSTOM = "custom"


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    """Security event for SIEM"""
    event_id: str
    timestamp: datetime
    source: str
    event_type: str
    severity: AlertSeverity
    description: str
    details: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'event_type': self.event_type,
            'severity': self.severity.value,
            'description': self.description,
            'details': self.details,
            'user_id': self.user_id,
            'ip_address': self.ip_address,
            'resource': self.resource,
            'action': self.action,
            'tags': self.tags
        }


@dataclass
class AlertRule:
    """Alert rule configuration"""
    rule_id: str
    name: str
    description: str
    conditions: Dict[str, Any]
    severity: AlertSeverity
    enabled: bool = True
    cooldown_minutes: int = 5
    last_triggered: Optional[datetime] = None

    def evaluate(self, event: SecurityEvent) -> bool:
        """Evaluate if rule conditions match event"""
        for key, expected_value in self.conditions.items():
            if key not in event.__dict__:
                return False

            actual_value = getattr(event, key)
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
            elif operator == 'in' and actual_value not in expected:
                return False
        return True

    def can_trigger(self) -> bool:
        """Check if rule can trigger (cooldown check)"""
        if not self.last_triggered:
            return True

        cooldown_end = self.last_triggered + timedelta(minutes=self.cooldown_minutes)
        return datetime.utcnow() >= cooldown_end


class SIEMIntegration:
    """SIEM integration system"""

    def __init__(self, provider: SIEMProvider, config: Dict[str, Any]):
        self.provider = provider
        self.config = config
        self.alert_rules: Dict[str, AlertRule] = {}
        self.event_buffer: List[SecurityEvent] = []
        self.buffer_size = config.get('buffer_size', 100)
        self.flush_interval = config.get('flush_interval', 30)
        self.session = None
        self.flush_task = None

    async def initialize(self):
        """Initialize SIEM connection"""
        if self.provider == SIEMProvider.SPLUNK:
            self.session = aiohttp.ClientSession(
                headers={'Authorization': f'Bearer {self.config["token"]}'}
            )
        elif self.provider == SIEMProvider.ELASTICSEARCH:
            self.session = aiohttp.ClientSession(
                auth=aiohttp.BasicAuth(
                    self.config['username'],
                    self.config['password']
                )
            )
        else:
            self.session = aiohttp.ClientSession()

        # Start background flush task
        self.flush_task = asyncio.create_task(self._background_flush())

    async def shutdown(self):
        """Shutdown SIEM connection"""
        if self.flush_task:
            self.flush_task.cancel()
            try:
                await self.flush_task
            except asyncio.CancelledError:
                pass

        if self.session:
            await self.session.close()

        # Final flush
        if self.event_buffer:
            await self._flush_events()

    async def log_event(self, event: SecurityEvent):
        """Log security event"""
        self.event_buffer.append(event)

        # Check alert rules
        await self._check_alert_rules(event)

        # Flush if buffer is full
        if len(self.event_buffer) >= self.buffer_size:
            await self._flush_events()

    async def _check_alert_rules(self, event: SecurityEvent):
        """Check alert rules against event"""
        for rule in self.alert_rules.values():
            if rule.enabled and rule.can_trigger() and rule.evaluate(event):
                await self._trigger_alert(rule, event)
                rule.last_triggered = datetime.utcnow()

    async def _trigger_alert(self, rule: AlertRule, event: SecurityEvent):
        """Trigger alert for rule"""
        alert_event = SecurityEvent(
            event_id=f"alert_{event.event_id}",
            timestamp=datetime.utcnow(),
            source="siem_alert",
            event_type="alert_triggered",
            severity=rule.severity,
            description=f"Alert triggered: {rule.name}",
            details={
                'rule_id': rule.rule_id,
                'rule_name': rule.name,
                'triggered_by': event.event_id,
                'original_event': event.to_dict()
            },
            user_id=event.user_id,
            ip_address=event.ip_address,
            resource=event.resource,
            action=event.action,
            tags=['alert', rule.rule_id]
        )

        await self.log_event(alert_event)

        # Send external alert notification
        await self._send_external_alert(rule, event)

    async def _send_external_alert(self, rule: AlertRule, event: SecurityEvent):
        """Send alert to external systems"""
        alert_data = {
            'rule': rule.name,
            'severity': rule.severity.value,
            'description': rule.description,
            'event': event.to_dict(),
            'timestamp': datetime.utcnow().isoformat()
        }

        # Send to configured endpoints
        for endpoint in self.config.get('alert_endpoints', []):
            try:
                async with self.session.post(endpoint, json=alert_data) as response:
                    if response.status != 200:
                        print(f"Failed to send alert to {endpoint}: {response.status}")
            except Exception as e:
                print(f"Error sending alert to {endpoint}: {e}")

    async def _flush_events(self):
        """Flush events to SIEM"""
        if not self.event_buffer:
            return

        events_data = [event.to_dict() for event in self.event_buffer]

        try:
            if self.provider == SIEMProvider.SPLUNK:
                await self._send_to_splunk(events_data)
            elif self.provider == SIEMProvider.ELASTICSEARCH:
                await self._send_to_elasticsearch(events_data)
            elif self.provider == SIEMProvider.SUMOLOGIC:
                await self._send_to_sumologic(events_data)
            elif self.provider == SIEMProvider.DATADOG:
                await self._send_to_datadog(events_data)
            else:
                await self._send_to_custom(events_data)

            self.event_buffer.clear()

        except Exception as e:
            print(f"Failed to flush events to SIEM: {e}")

    async def _send_to_splunk(self, events: List[Dict[str, Any]]):
        """Send events to Splunk"""
        url = f"{self.config['endpoint']}/services/collector"
        headers = {'Authorization': f'Splunk {self.config["token"]}'}

        for event in events:
            payload = {
                'event': event,
                'sourcetype': 'pyserv _security',
                'index': self.config.get('index', 'security')
            }

            async with self.session.post(url, json=payload, headers=headers) as response:
                response.raise_for_status()

    async def _send_to_elasticsearch(self, events: List[Dict[str, Any]]):
        """Send events to Elasticsearch"""
        url = f"{self.config['endpoint']}/_bulk"

        bulk_data = []
        for event in events:
            bulk_data.extend([
                {'index': {'_index': self.config.get('index', 'security-events')}},
                event
            ])

        bulk_body = '\n'.join(json.dumps(item) for item in bulk_data) + '\n'

        async with self.session.post(url, data=bulk_body,
                                   headers={'Content-Type': 'application/x-ndjson'}) as response:
            response.raise_for_status()

    async def _send_to_sumologic(self, events: List[Dict[str, Any]]):
        """Send events to Sumo Logic"""
        url = self.config['endpoint']

        for event in events:
            async with self.session.post(url, json=event) as response:
                response.raise_for_status()

    async def _send_to_datadog(self, events: List[Dict[str, Any]]):
        """Send events to Datadog"""
        url = f"{self.config['endpoint']}/v1/input/{self.config['api_key']}"

        for event in events:
            payload = {
                'message': event['description'],
                'severity': event['severity'],
                'tags': event.get('tags', []),
                'attributes': event
            }

            async with self.session.post(url, json=payload) as response:
                response.raise_for_status()

    async def _send_to_custom(self, events: List[Dict[str, Any]]):
        """Send events to custom endpoint"""
        url = self.config['endpoint']

        for event in events:
            async with self.session.post(url, json=event) as response:
                response.raise_for_status()

    async def _background_flush(self):
        """Background task to periodically flush events"""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                await self._flush_events()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in background flush: {e}")

    def add_alert_rule(self, rule: AlertRule):
        """Add alert rule"""
        self.alert_rules[rule.rule_id] = rule

    def remove_alert_rule(self, rule_id: str):
        """Remove alert rule"""
        self.alert_rules.pop(rule_id, None)

    def get_alert_rules(self) -> List[AlertRule]:
        """Get all alert rules"""
        return list(self.alert_rules.values())

    def get_recent_events(self, limit: int = 100) -> List[SecurityEvent]:
        """Get recent security events"""
        return self.event_buffer[-limit:] if self.event_buffer else []

    async def query_events(self, query: Dict[str, Any], limit: int = 100) -> List[SecurityEvent]:
        """Query events from SIEM"""
        # This would query the actual SIEM system
        # For demo purposes, filter from buffer
        matching_events = []

        for event in self.event_buffer:
            matches = True
            for key, value in query.items():
                if getattr(event, key, None) != value:
                    matches = False
                    break

            if matches:
                matching_events.append(event)

        return matching_events[-limit:]


# Global SIEM instance
_siem_instance = None

def get_siem_integration(provider: SIEMProvider = SIEMProvider.CUSTOM,
                        config: Optional[Dict[str, Any]] = None) -> SIEMIntegration:
    """Get global SIEM integration instance"""
    global _siem_instance
    if _siem_instance is None:
        if config is None:
            # Default configuration for development
            config = {
                'endpoint': 'http://localhost:8080/api/events',
                'buffer_size': 50,
                'flush_interval': 15
            }
        _siem_instance = SIEMIntegration(provider, config)
    return _siem_instance


# Utility functions
async def log_security_event(event_type: str, severity: AlertSeverity,
                           description: str, **kwargs):
    """Log security event to SIEM"""
    siem = get_siem_integration()

    event = SecurityEvent(
        event_id=f"evt_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        timestamp=datetime.utcnow(),
        source="pyserv _framework",
        event_type=event_type,
        severity=severity,
        description=description,
        **kwargs
    )

    await siem.log_event(event)

async def create_alert_rule(rule_id: str, name: str, conditions: Dict[str, Any],
                          severity: AlertSeverity, description: str = ""):
    """Create alert rule"""
    siem = get_siem_integration()

    rule = AlertRule(
        rule_id=rule_id,
        name=name,
        description=description,
        conditions=conditions,
        severity=severity
    )

    siem.add_alert_rule(rule)

# Pre-configured alert rules
default_alert_rules = [
    AlertRule(
        rule_id="failed_login_attempts",
        name="Multiple Failed Login Attempts",
        description="Alert when multiple failed login attempts detected",
        conditions={"event_type": "failed_login", "severity": {"greater_than": "medium"}},
        severity=AlertSeverity.HIGH
    ),

    AlertRule(
        rule_id="suspicious_ip",
        name="Suspicious IP Activity",
        description="Alert for suspicious IP addresses",
        conditions={"event_type": "suspicious_traffic", "severity": "high"},
        severity=AlertSeverity.CRITICAL
    ),

    AlertRule(
        rule_id="privilege_escalation",
        name="Privilege Escalation Attempt",
        description="Alert for privilege escalation attempts",
        conditions={"event_type": "privilege_escalation"},
        severity=AlertSeverity.CRITICAL
    ),

    AlertRule(
        rule_id="data_exfiltration",
        name="Data Exfiltration Detected",
        description="Alert for potential data exfiltration",
        conditions={"event_type": "data_exfiltration"},
        severity=AlertSeverity.HIGH
    )
]

def initialize_default_alerts():
    """Initialize default alert rules"""
    siem = get_siem_integration()
    for rule in default_alert_rules:
        siem.add_alert_rule(rule)




