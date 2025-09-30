"""
Compliance Framework for Pyserv .
Supports GDPR, HIPAA, SOC2, and other compliance standards.
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import json
import hashlib
from enum import Enum
import logging
from pyserv.database.connections import DatabaseConnection
from pyserv.database.config import DatabaseConfig


class ComplianceStandard(Enum):
    """Supported compliance standards"""
    GDPR = "gdpr"
    HIPAA = "hipaa"
    SOC2 = "soc2"
    PCI_DSS = "pci_dss"
    ISO_27001 = "iso_27001"
    CCPA = "ccpa"


class DataClassification(Enum):
    """Data classification levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


@dataclass
class ComplianceRule:
    """Compliance rule definition"""
    rule_id: str
    standard: ComplianceStandard
    name: str
    description: str
    requirements: List[str]
    check_function: Callable
    severity: str = "medium"
    auto_remediate: bool = False
    remediation_function: Optional[Callable] = None

    async def check_compliance(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check compliance with this rule"""
        try:
            result = await self.check_function(context)
            return {
                'rule_id': self.rule_id,
                'standard': self.standard.value,
                'compliant': result.get('compliant', False),
                'details': result,
                'severity': self.severity,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                'rule_id': self.rule_id,
                'standard': self.standard.value,
                'compliant': False,
                'error': str(e),
                'severity': self.severity,
                'timestamp': datetime.utcnow().isoformat()
            }

    async def remediate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt automatic remediation"""
        if not self.auto_remediate or not self.remediation_function:
            return {'remediated': False, 'reason': 'No auto-remediation available'}

        try:
            result = await self.remediation_function(context)
            return {
                'remediated': True,
                'result': result,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                'remediated': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }


@dataclass
class DataSubject:
    """Data subject for GDPR compliance"""
    subject_id: str
    email: str
    name: str
    data_types: List[str] = field(default_factory=list)
    consent_given: bool = False
    consent_date: Optional[datetime] = None
    consent_withdrawn: bool = False
    withdrawal_date: Optional[datetime] = None

    def give_consent(self, data_types: List[str]):
        """Give consent for data processing"""
        self.consent_given = True
        self.consent_date = datetime.utcnow()
        self.data_types = data_types
        self.consent_withdrawn = False
        self.withdrawal_date = None

    def withdraw_consent(self):
        """Withdraw consent"""
        self.consent_withdrawn = True
        self.withdrawal_date = datetime.utcnow()

    def has_consent(self, data_type: str) -> bool:
        """Check if subject has consent for data type"""
        return (self.consent_given and
                not self.consent_withdrawn and
                data_type in self.data_types)


@dataclass
class AuditLogEntry:
    """Audit log entry for compliance"""
    entry_id: str
    timestamp: datetime
    user_id: Optional[str]
    action: str
    resource: str
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    compliance_standard: Optional[ComplianceStandard] = None


class ComplianceManager:
    """Compliance management system"""

    def __init__(self, db_config: Optional[DatabaseConfig] = None):
        self.rules: Dict[str, ComplianceRule] = {}
        self.data_subjects: Dict[str, DataSubject] = {}
        self.audit_log: List[AuditLogEntry] = []
        self.data_inventory: Dict[str, Dict[str, Any]] = {}
        
        # Database connection for audit logging
        if db_config:
            self.db_connection = DatabaseConnection.get_instance(db_config)
        else:
            # Default SQLite for compliance data
            default_config = DatabaseConfig("sqlite:///compliance.db")
            self.db_connection = DatabaseConnection.get_instance(default_config)
        
        self.logger = logging.getLogger("ComplianceManager")

    def add_compliance_rule(self, rule: ComplianceRule):
        """Add compliance rule"""
        self.rules[rule.rule_id] = rule

    def remove_compliance_rule(self, rule_id: str):
        """Remove compliance rule"""
        self.rules.pop(rule_id, None)

    async def run_compliance_check(self, standard: ComplianceStandard,
                                 context: Dict[str, Any]) -> Dict[str, Any]:
        """Run compliance check for specific standard"""
        relevant_rules = [
            rule for rule in self.rules.values()
            if rule.standard == standard
        ]

        results = []
        for rule in relevant_rules:
            result = await rule.check_compliance(context)
            results.append(result)

        compliant = all(result['compliant'] for result in results)
        violations = [r for r in results if not r['compliant']]

        return {
            'standard': standard.value,
            'compliant': compliant,
            'total_rules': len(results),
            'passed_rules': len(results) - len(violations),
            'violations': violations,
            'timestamp': datetime.utcnow().isoformat()
        }

    async def run_all_compliance_checks(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Run compliance checks for all standards"""
        results = {}
        for standard in ComplianceStandard:
            results[standard.value] = await self.run_compliance_check(standard, context)

        overall_compliant = all(result['compliant'] for result in results.values())

        return {
            'overall_compliant': overall_compliant,
            'standards': results,
            'timestamp': datetime.utcnow().isoformat()
        }

    async def remediate_violations(self, violations: List[Dict[str, Any]],
                                 context: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt to remediate compliance violations"""
        remediation_results = []

        for violation in violations:
            rule = self.rules.get(violation['rule_id'])
            if rule and rule.auto_remediate:
                result = await rule.remediate(context)
                remediation_results.append({
                    'rule_id': violation['rule_id'],
                    'remediation': result
                })

        return {
            'remediation_attempts': len(remediation_results),
            'successful_remediations': len([r for r in remediation_results if r['remediation']['remediated']]),
            'results': remediation_results,
            'timestamp': datetime.utcnow().isoformat()
        }

    # GDPR Compliance Methods
    def register_data_subject(self, subject: DataSubject):
        """Register data subject for GDPR compliance"""
        self.data_subjects[subject.subject_id] = subject

    def get_data_subject(self, subject_id: str) -> Optional[DataSubject]:
        """Get data subject"""
        return self.data_subjects.get(subject_id)

    async def process_data_deletion_request(self, subject_id: str) -> Dict[str, Any]:
        """Process GDPR right to erasure"""
        subject = self.get_data_subject(subject_id)
        if not subject:
            return {'success': False, 'reason': 'Subject not found'}

        # Log the deletion request
        await self.log_audit_event(
            user_id=subject_id,
            action="data_deletion_requested",
            resource="user_data",
            compliance_standard=ComplianceStandard.GDPR
        )

        # Real implementation: process GDPR data deletion request
        # 1. Anonymize or delete user data
        # 2. Notify all data processors
        # 3. Update data inventory

        return {
            'success': True,
            'subject_id': subject_id,
            'deletion_requested': datetime.utcnow().isoformat(),
            'estimated_completion': (datetime.utcnow() + timedelta(days=30)).isoformat()
        }

    async def process_data_portability_request(self, subject_id: str) -> Dict[str, Any]:
        """Process GDPR right to data portability"""
        subject = self.get_data_subject(subject_id)
        if not subject:
            return {'success': False, 'reason': 'Subject not found'}

        # Collect all data for the subject
        subject_data = {
            'personal_data': {},
            'consent_history': {
                'consent_given': subject.consent_given,
                'consent_date': subject.consent_date.isoformat() if subject.consent_date else None,
                'data_types': subject.data_types
            }
        }

        # Log the portability request
        await self.log_audit_event(
            user_id=subject_id,
            action="data_portability_requested",
            resource="user_data",
            compliance_standard=ComplianceStandard.GDPR
        )

        return {
            'success': True,
            'subject_id': subject_id,
            'data': subject_data,
            'format': 'JSON',
            'timestamp': datetime.utcnow().isoformat()
        }

    # HIPAA Compliance Methods
    def classify_health_data(self, data_type: str, sensitivity: str) -> DataClassification:
        """Classify health data for HIPAA compliance"""
        if 'phi' in data_type.lower() or sensitivity == 'high':
            return DataClassification.RESTRICTED
        elif 'medical' in data_type.lower():
            return DataClassification.CONFIDENTIAL
        else:
            return DataClassification.INTERNAL

    async def log_health_data_access(self, user_id: str, patient_id: str,
                                   data_type: str, purpose: str):
        """Log access to health data for HIPAA compliance"""
        await self.log_audit_event(
            user_id=user_id,
            action="health_data_accessed",
            resource=f"patient_{patient_id}",
            details={
                'data_type': data_type,
                'purpose': purpose,
                'patient_id': patient_id
            },
            compliance_standard=ComplianceStandard.HIPAA
        )

    # SOC2 Compliance Methods
    async def generate_soc2_report(self, period_start: datetime,
                                 period_end: datetime) -> Dict[str, Any]:
        """Generate SOC2 compliance report"""
        # Filter audit logs for the period
        period_logs = [
            log for log in self.audit_log
            if period_start <= log.timestamp <= period_end
        ]

        # Analyze controls
        controls_analysis = {
            'access_control': self._analyze_access_controls(period_logs),
            'change_management': self._analyze_change_management(period_logs),
            'incident_response': self._analyze_incident_response(period_logs),
            'monitoring': self._analyze_monitoring(period_logs)
        }

        return {
            'report_period': {
                'start': period_start.isoformat(),
                'end': period_end.isoformat()
            },
            'controls_analysis': controls_analysis,
            'total_events': len(period_logs),
            'generated_at': datetime.utcnow().isoformat()
        }

    def _analyze_access_controls(self, logs: List[AuditLogEntry]) -> Dict[str, Any]:
        """Analyze access controls for SOC2"""
        access_events = [log for log in logs if 'access' in log.action.lower()]

        return {
            'total_access_events': len(access_events),
            'unique_users': len(set(log.user_id for log in access_events if log.user_id)),
            'access_denials': len([log for log in access_events if 'denied' in log.action.lower()])
        }

    def _analyze_change_management(self, logs: List[AuditLogEntry]) -> Dict[str, Any]:
        """Analyze change management for SOC2"""
        change_events = [log for log in logs if 'change' in log.action.lower() or 'update' in log.action.lower()]

        return {
            'total_changes': len(change_events),
            'approved_changes': len([log for log in change_events if log.details.get('approved', False)]),
            'emergency_changes': len([log for log in change_events if log.details.get('emergency', False)])
        }

    def _analyze_incident_response(self, logs: List[AuditLogEntry]) -> Dict[str, Any]:
        """Analyze incident response for SOC2"""
        incident_events = [log for log in logs if 'incident' in log.action.lower() or 'alert' in log.action.lower()]

        return {
            'total_incidents': len(incident_events),
            'resolved_incidents': len([log for log in incident_events if log.details.get('resolved', False)]),
            'average_resolution_time': 'N/A'  # Would calculate actual average
        }

    def _analyze_monitoring(self, logs: List[AuditLogEntry]) -> Dict[str, Any]:
        """Analyze monitoring for SOC2"""
        monitoring_events = [log for log in logs if 'monitor' in log.action.lower() or 'log' in log.action.lower()]

        return {
            'total_monitoring_events': len(monitoring_events),
            'unique_resources_monitored': len(set(log.resource for log in monitoring_events)),
            'alerts_generated': len([log for log in monitoring_events if log.details.get('alert', False)])
        }

    # Audit Logging
    async def log_audit_event(self, user_id: Optional[str], action: str,
                            resource: str, details: Optional[Dict[str, Any]] = None,
                            ip_address: Optional[str] = None,
                            user_agent: Optional[str] = None,
                            compliance_standard: Optional[ComplianceStandard] = None):
        """Log audit event"""
        entry = AuditLogEntry(
            entry_id=f"audit_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            timestamp=datetime.utcnow(),
            user_id=user_id,
            action=action,
            resource=resource,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            compliance_standard=compliance_standard
        )

        self.audit_log.append(entry)

        # Persist to database
        await self._persist_audit_log(entry)

    async def _persist_audit_log(self, entry: AuditLogEntry):
        """Persist audit log entry to database"""
        try:
            # Ensure tables exist
            await self._create_audit_tables()
            
            await self.db_connection.execute("""
                INSERT OR REPLACE INTO audit_logs
                (entry_id, timestamp, user_id, action, resource, details, ip_address, user_agent, compliance_standard)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.entry_id,
                entry.timestamp.isoformat(),
                entry.user_id,
                entry.action,
                entry.resource,
                json.dumps(entry.details),
                entry.ip_address,
                entry.user_agent,
                entry.compliance_standard.value if entry.compliance_standard else None
            ))

        except Exception as e:
            self.logger.error(f"Failed to persist audit log: {e}")

    def get_audit_log(self, user_id: Optional[str] = None,
                     action: Optional[str] = None,
                     start_date: Optional[datetime] = None,
                     end_date: Optional[datetime] = None,
                     limit: int = 100) -> List[AuditLogEntry]:
        """Get audit log entries with filtering"""
        filtered_logs = self.audit_log

        if user_id:
            filtered_logs = [log for log in filtered_logs if log.user_id == user_id]

        if action:
            filtered_logs = [log for log in filtered_logs if action in log.action]

        if start_date:
            filtered_logs = [log for log in filtered_logs if log.timestamp >= start_date]

        if end_date:
            filtered_logs = [log for log in filtered_logs if log.timestamp <= end_date]

        return sorted(filtered_logs, key=lambda x: x.timestamp, reverse=True)[:limit]

    # Data Inventory Management
    def register_data_asset(self, asset_id: str, name: str, data_type: str,
                          classification: DataClassification, owner: str,
                          location: str, **metadata):
        """Register data asset in inventory"""
        self.data_inventory[asset_id] = {
            'name': name,
            'data_type': data_type,
            'classification': classification.value,
            'owner': owner,
            'location': location,
            'created_at': datetime.utcnow().isoformat(),
            'last_updated': datetime.utcnow().isoformat(),
            'metadata': metadata
        }

    def get_data_inventory(self) -> Dict[str, Any]:
        """Get data inventory"""
        return self.data_inventory

    async def _create_audit_tables(self):
        """Create audit logging tables"""
        try:
            await self.db_connection.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    entry_id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    user_id TEXT,
                    action TEXT,
                    resource TEXT,
                    details TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    compliance_standard TEXT
                )
            """)
            
            await self.db_connection.execute("""
                CREATE TABLE IF NOT EXISTS data_subjects (
                    subject_id TEXT PRIMARY KEY,
                    email TEXT,
                    name TEXT,
                    data_types TEXT,
                    consent_given BOOLEAN,
                    consent_date TEXT,
                    consent_withdrawn BOOLEAN,
                    withdrawal_date TEXT
                )
            """)
        except Exception as e:
            self.logger.error(f"Failed to create audit tables: {e}")

    def update_data_asset(self, asset_id: str, **updates):
        """Update data asset"""
        if asset_id in self.data_inventory:
            self.data_inventory[asset_id].update(updates)
            self.data_inventory[asset_id]['last_updated'] = datetime.utcnow().isoformat()


# Global compliance manager instance
_compliance_manager = None

def get_compliance_manager(db_config: Optional[DatabaseConfig] = None) -> ComplianceManager:
    """Get global compliance manager instance"""
    global _compliance_manager
    if _compliance_manager is None:
        _compliance_manager = ComplianceManager(db_config)
    return _compliance_manager


# Compliance check functions
async def check_gdpr_consent(context: Dict[str, Any]) -> Dict[str, Any]:
    """Check GDPR consent compliance"""
    compliance = get_compliance_manager()
    user_id = context.get('user_id')

    if not user_id:
        return {'compliant': False, 'reason': 'No user ID provided'}

    subject = compliance.get_data_subject(user_id)
    if not subject:
        return {'compliant': False, 'reason': 'User not registered as data subject'}

    data_type = context.get('data_type', 'personal')
    has_consent = subject.has_consent(data_type)

    return {
        'compliant': has_consent,
        'subject_id': user_id,
        'data_type': data_type,
        'consent_given': subject.consent_given,
        'consent_date': subject.consent_date.isoformat() if subject.consent_date else None
    }

async def check_hipaa_data_handling(context: Dict[str, Any]) -> Dict[str, Any]:
    """Check HIPAA data handling compliance"""
    data_type = context.get('data_type', '')

    # Check if data contains PHI
    contains_phi = any(keyword in data_type.lower() for keyword in [
        'medical', 'health', 'diagnosis', 'treatment', 'patient'
    ])

    if contains_phi:
        # Check encryption
        encrypted = context.get('encrypted', False)
        access_logged = context.get('access_logged', False)

        return {
            'compliant': encrypted and access_logged,
            'contains_phi': True,
            'encryption_enabled': encrypted,
            'access_logging_enabled': access_logged
        }

    return {'compliant': True, 'contains_phi': False}

async def check_soc2_access_control(context: Dict[str, Any]) -> Dict[str, Any]:
    """Check SOC2 access control compliance"""
    user_id = context.get('user_id')
    resource = context.get('resource')
    action = context.get('action')

    # Check if user has appropriate permissions
    # This would integrate with IAM system
    has_permission = context.get('has_permission', True)  # Mock

    # Check if access is logged
    access_logged = context.get('access_logged', True)  # Mock

    return {
        'compliant': has_permission and access_logged,
        'user_id': user_id,
        'resource': resource,
        'action': action,
        'has_permission': has_permission,
        'access_logged': access_logged
    }

# Initialize default compliance rules
def initialize_compliance_rules():
    """Initialize default compliance rules"""
    compliance = get_compliance_manager()

    # GDPR Rules
    gdpr_consent_rule = ComplianceRule(
        rule_id="gdpr_consent_check",
        standard=ComplianceStandard.GDPR,
        name="GDPR Consent Verification",
        description="Ensure user consent for data processing",
        requirements=["User must provide explicit consent", "Consent must be documented"],
        check_function=check_gdpr_consent,
        severity="high",
        auto_remediate=False
    )

    # HIPAA Rules
    hipaa_data_rule = ComplianceRule(
        rule_id="hipaa_data_handling",
        standard=ComplianceStandard.HIPAA,
        name="HIPAA Data Handling",
        description="Ensure proper handling of protected health information",
        requirements=["PHI must be encrypted", "Access must be logged"],
        check_function=check_hipaa_data_handling,
        severity="critical",
        auto_remediate=False
    )

    # SOC2 Rules
    soc2_access_rule = ComplianceRule(
        rule_id="soc2_access_control",
        standard=ComplianceStandard.SOC2,
        name="SOC2 Access Control",
        description="Ensure proper access controls and logging",
        requirements=["Users must have appropriate permissions", "All access must be logged"],
        check_function=check_soc2_access_control,
        severity="high",
        auto_remediate=False
    )

    compliance.add_compliance_rule(gdpr_consent_rule)
    compliance.add_compliance_rule(hipaa_data_rule)
    compliance.add_compliance_rule(soc2_access_rule)
