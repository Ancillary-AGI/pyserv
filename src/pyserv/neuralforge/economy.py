"""
Economy System Module for NeuralForge

Provides a sandbox economy system for managing agent balances, transactions, and economic activities.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import logging
from decimal import Decimal, ROUND_DOWN

logger = logging.getLogger(__name__)


class Transaction:
    """
    Represents a single economic transaction
    """

    def __init__(self, agent_id: str, transaction_type: str, amount: float,
                 reason: str, service: str = None, metadata: Dict = None):
        self.agent_id = agent_id
        self.transaction_type = transaction_type  # "credit", "debit", "transfer"
        self.amount = Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
        self.reason = reason
        self.service = service
        self.metadata = metadata or {}
        self.timestamp = datetime.now().isoformat()
        self.transaction_id = f"txn_{hash(str(self.timestamp) + agent_id)[:16]}"

    def to_dict(self) -> Dict:
        """
        Convert transaction to dictionary

        Returns:
            Dictionary representation
        """
        return {
            "transaction_id": self.transaction_id,
            "agent_id": self.agent_id,
            "type": self.transaction_type,
            "amount": float(self.amount),
            "reason": self.reason,
            "service": self.service,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Transaction':
        """
        Create transaction from dictionary

        Args:
            data: Dictionary representation

        Returns:
            Transaction instance
        """
        txn = cls(
            agent_id=data["agent_id"],
            transaction_type=data["type"],
            amount=data["amount"],
            reason=data["reason"],
            service=data.get("service"),
            metadata=data.get("metadata", {})
        )
        txn.timestamp = data["timestamp"]
        txn.transaction_id = data["transaction_id"]
        return txn


class ServiceDefinition:
    """
    Defines a service with its pricing structure
    """

    def __init__(self, name: str, description: str, base_cost: float,
                 cost_unit: str = None, cost_per_unit: float = None,
                 max_cost: float = None, min_cost: float = None):
        self.name = name
        self.description = description
        self.base_cost = Decimal(str(base_cost))
        self.cost_unit = cost_unit  # e.g., "token", "kb", "second"
        self.cost_per_unit = Decimal(str(cost_per_unit)) if cost_per_unit else None
        self.max_cost = Decimal(str(max_cost)) if max_cost else None
        self.min_cost = Decimal(str(min_cost)) if min_cost else None

    def calculate_cost(self, **kwargs) -> Decimal:
        """
        Calculate cost for this service

        Args:
            **kwargs: Parameters for cost calculation

        Returns:
            Calculated cost
        """
        cost = self.base_cost

        if self.cost_per_unit and self.cost_unit:
            unit_count = kwargs.get(self.cost_unit, 0)
            cost += self.cost_per_unit * Decimal(str(unit_count))

        if self.max_cost and cost > self.max_cost:
            cost = self.max_cost

        if self.min_cost and cost < self.min_cost:
            cost = self.min_cost

        return cost.quantize(Decimal('0.01'), rounding=ROUND_DOWN)

    def to_dict(self) -> Dict:
        """
        Convert service definition to dictionary

        Returns:
            Dictionary representation
        """
        return {
            "name": self.name,
            "description": self.description,
            "base_cost": float(self.base_cost),
            "cost_unit": self.cost_unit,
            "cost_per_unit": float(self.cost_per_unit) if self.cost_per_unit else None,
            "max_cost": float(self.max_cost) if self.max_cost else None,
            "min_cost": float(self.min_cost) if self.min_cost else None
        }


class EconomySystem:
    """
    Main economy system for managing agent balances and transactions
    """

    def __init__(self):
        self.agent_balances: Dict[str, Decimal] = {}
        self.transaction_history: List[Transaction] = []
        self.services: Dict[str, ServiceDefinition] = {}
        self.max_history_size = 10000
        self.daily_transaction_limits: Dict[str, Dict] = {}  # agent_id -> {"date": date, "count": int, "amount": Decimal}
        self.max_daily_transactions = 1000
        self.max_daily_amount = Decimal("1000.00")

        # Initialize default services
        self._initialize_default_services()

    def _initialize_default_services(self):
        """
        Initialize default services with their pricing
        """
        self.services["llm_inference"] = ServiceDefinition(
            name="llm_inference",
            description="LLM text generation service",
            base_cost=0.1,
            cost_unit="tokens",
            cost_per_unit=0.01,
            max_cost=10.0
        )

        self.services["memory_storage"] = ServiceDefinition(
            name="memory_storage",
            description="Agent memory storage",
            base_cost=0.01,
            cost_unit="kb",
            cost_per_unit=0.001,
            max_cost=5.0
        )

        self.services["api_call"] = ServiceDefinition(
            name="api_call",
            description="External API call",
            base_cost=0.5,
            max_cost=20.0
        )

        self.services["agent_communication"] = ServiceDefinition(
            name="agent_communication",
            description="Agent-to-agent communication",
            base_cost=0.05,
            cost_unit="messages",
            cost_per_unit=0.01,
            max_cost=2.0
        )

        self.services["resource_access"] = ServiceDefinition(
            name="resource_access",
            description="MCP resource access",
            base_cost=1.0,
            max_cost=50.0
        )

        self.services["tool_execution"] = ServiceDefinition(
            name="tool_execution",
            description="MCP tool execution",
            base_cost=5.0,
            max_cost=100.0
        )

    def register_agent(self, agent_id: str, initial_balance: float = 100.0):
        """
        Register an agent with the economy system

        Args:
            agent_id: Unique agent identifier
            initial_balance: Initial balance for the agent
        """
        if agent_id not in self.agent_balances:
            self.agent_balances[agent_id] = Decimal(str(initial_balance))
            logger.info(f"Registered agent {agent_id} with balance {initial_balance}")

    def unregister_agent(self, agent_id: str):
        """
        Unregister an agent from the economy system

        Args:
            agent_id: Agent identifier to unregister
        """
        if agent_id in self.agent_balances:
            final_balance = self.agent_balances[agent_id]
            del self.agent_balances[agent_id]
            logger.info(f"Unregistered agent {agent_id} with final balance {final_balance}")

    def get_balance(self, agent_id: str) -> float:
        """
        Get an agent's current balance

        Args:
            agent_id: Agent identifier

        Returns:
            Current balance
        """
        return float(self.agent_balances.get(agent_id, Decimal("0")))

    async def charge_service(self, agent_id: str, service_name: str, **kwargs) -> bool:
        """
        Charge an agent for using a service

        Args:
            agent_id: Agent identifier
            service_name: Name of the service
            **kwargs: Parameters for cost calculation

        Returns:
            True if charge was successful
        """
        if agent_id not in self.agent_balances:
            logger.warning(f"Agent {agent_id} not registered in economy system")
            return False

        if service_name not in self.services:
            logger.warning(f"Service {service_name} not found")
            return False

        # Check daily limits
        if not self._check_daily_limits(agent_id):
            logger.warning(f"Daily transaction limit exceeded for agent {agent_id}")
            return False

        service = self.services[service_name]
        cost = service.calculate_cost(**kwargs)

        if self.agent_balances[agent_id] >= cost:
            self.agent_balances[agent_id] -= cost

            # Record transaction
            transaction = Transaction(
                agent_id=agent_id,
                transaction_type="debit",
                amount=float(cost),
                reason=f"Service charge: {service_name}",
                service=service_name,
                metadata=kwargs
            )
            self._record_transaction(transaction)

            logger.info(f"Charged agent {agent_id} {cost} for {service_name}")
            return True
        else:
            logger.warning(f"Insufficient balance for agent {agent_id}: has {self.agent_balances[agent_id]}, needs {cost}")
            return False

    def add_funds(self, agent_id: str, amount: float, reason: str = "funds_added",
                  admin_override: bool = False):
        """
        Add funds to an agent's balance

        Args:
            agent_id: Agent identifier
            amount: Amount to add
            reason: Reason for adding funds
            admin_override: Whether this is an administrative action
        """
        if agent_id not in self.agent_balances:
            self.register_agent(agent_id, 0.0)

        decimal_amount = Decimal(str(amount))
        self.agent_balances[agent_id] += decimal_amount

        # Record transaction
        transaction = Transaction(
            agent_id=agent_id,
            transaction_type="credit",
            amount=float(decimal_amount),
            reason=reason,
            metadata={"admin_override": admin_override}
        )
        self._record_transaction(transaction)

        logger.info(f"Added {decimal_amount} to agent {agent_id} balance")

    def transfer_funds(self, from_agent: str, to_agent: str, amount: float,
                      reason: str = "transfer") -> bool:
        """
        Transfer funds between agents

        Args:
            from_agent: Sender agent ID
            to_agent: Receiver agent ID
            amount: Amount to transfer
            reason: Reason for transfer

        Returns:
            True if transfer was successful
        """
        if from_agent not in self.agent_balances or to_agent not in self.agent_balances:
            logger.warning("One or both agents not registered in economy system")
            return False

        decimal_amount = Decimal(str(amount))

        if self.agent_balances[from_agent] >= decimal_amount:
            # Perform transfer
            self.agent_balances[from_agent] -= decimal_amount
            self.agent_balances[to_agent] += decimal_amount

            # Record transactions
            debit_txn = Transaction(
                agent_id=from_agent,
                transaction_type="transfer",
                amount=float(decimal_amount),
                reason=f"Transfer to {to_agent}: {reason}",
                metadata={"to_agent": to_agent}
            )
            self._record_transaction(debit_txn)

            credit_txn = Transaction(
                agent_id=to_agent,
                transaction_type="transfer",
                amount=float(decimal_amount),
                reason=f"Transfer from {from_agent}: {reason}",
                metadata={"from_agent": from_agent}
            )
            self._record_transaction(credit_txn)

            logger.info(f"Transferred {decimal_amount} from {from_agent} to {to_agent}")
            return True
        else:
            logger.warning(f"Insufficient balance for transfer from {from_agent}")
            return False

    def add_service(self, service: ServiceDefinition):
        """
        Add a new service to the economy system

        Args:
            service: Service definition to add
        """
        self.services[service.name] = service
        logger.info(f"Added service: {service.name}")

    def remove_service(self, service_name: str):
        """
        Remove a service from the economy system

        Args:
            service_name: Name of service to remove
        """
        if service_name in self.services:
            del self.services[service_name]
            logger.info(f"Removed service: {service_name}")

    def get_service_cost(self, service_name: str, **kwargs) -> Optional[float]:
        """
        Get the cost of a service

        Args:
            service_name: Name of the service
            **kwargs: Parameters for cost calculation

        Returns:
            Service cost or None if service not found
        """
        if service_name not in self.services:
            return None

        service = self.services[service_name]
        return float(service.calculate_cost(**kwargs))

    def get_transaction_history(self, agent_id: str = None, limit: int = 100) -> List[Dict]:
        """
        Get transaction history

        Args:
            agent_id: Specific agent ID (None for all transactions)
            limit: Maximum number of transactions to return

        Returns:
            List of transaction dictionaries
        """
        if agent_id:
            transactions = [t for t in self.transaction_history if t.agent_id == agent_id]
        else:
            transactions = self.transaction_history

        # Return most recent transactions
        return [t.to_dict() for t in transactions[-limit:]]

    def get_agent_stats(self, agent_id: str) -> Dict:
        """
        Get economic statistics for an agent

        Args:
            agent_id: Agent identifier

        Returns:
            Statistics dictionary
        """
        if agent_id not in self.agent_balances:
            return {"error": "Agent not registered"}

        # Get agent's transactions
        agent_transactions = [t for t in self.transaction_history if t.agent_id == agent_id]

        total_credits = sum(float(t.amount) for t in agent_transactions if t.transaction_type == "credit")
        total_debits = sum(float(t.amount) for t in agent_transactions if t.transaction_type == "debit")
        total_transfers_sent = sum(float(t.amount) for t in agent_transactions
                                  if t.transaction_type == "transfer" and "to_agent" in t.metadata)
        total_transfers_received = sum(float(t.amount) for t in agent_transactions
                                      if t.transaction_type == "transfer" and "from_agent" in t.metadata)

        return {
            "agent_id": agent_id,
            "current_balance": float(self.agent_balances[agent_id]),
            "total_credits": total_credits,
            "total_debits": total_debits,
            "total_transfers_sent": total_transfers_sent,
            "total_transfers_received": total_transfers_received,
            "transaction_count": len(agent_transactions),
            "net_flow": total_credits - total_debits
        }

    def get_system_stats(self) -> Dict:
        """
        Get system-wide economic statistics

        Returns:
            Statistics dictionary
        """
        total_balance = sum(self.agent_balances.values())
        total_transactions = len(self.transaction_history)

        service_usage = {}
        for txn in self.transaction_history:
            if txn.service:
                service_usage[txn.service] = service_usage.get(txn.service, 0) + 1

        return {
            "total_agents": len(self.agent_balances),
            "total_balance_in_system": float(total_balance),
            "average_balance": float(total_balance / max(1, len(self.agent_balances))),
            "total_transactions": total_transactions,
            "service_usage": service_usage,
            "registered_services": len(self.services)
        }

    def _record_transaction(self, transaction: Transaction):
        """
        Record a transaction in history

        Args:
            transaction: Transaction to record
        """
        self.transaction_history.append(transaction)

        # Maintain history size limit
        if len(self.transaction_history) > self.max_history_size:
            self.transaction_history = self.transaction_history[-self.max_history_size:]

    def _check_daily_limits(self, agent_id: str) -> bool:
        """
        Check if agent has exceeded daily transaction limits

        Args:
            agent_id: Agent identifier

        Returns:
            True if within limits
        """
        today = datetime.now().date().isoformat()

        if agent_id not in self.daily_transaction_limits:
            self.daily_transaction_limits[agent_id] = {
                "date": today,
                "count": 0,
                "amount": Decimal("0")
            }

        limits = self.daily_transaction_limits[agent_id]

        # Reset if it's a new day
        if limits["date"] != today:
            limits["date"] = today
            limits["count"] = 0
            limits["amount"] = Decimal("0")

        # Check limits
        if limits["count"] >= self.max_daily_transactions:
            return False

        return True

    def reset_daily_limits(self):
        """
        Reset daily transaction limits (typically called daily)
        """
        self.daily_transaction_limits.clear()
        logger.info("Reset daily transaction limits")




