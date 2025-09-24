"""
Transaction manager for payment processing.
Handles transaction storage, retrieval, and lifecycle management.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

class TransactionManager:
    """
    Manages payment transactions with persistence and querying.
    """

    def __init__(self):
        self.transactions: Dict[str, Any] = {}
        self.logger = logging.getLogger("transaction_manager")
        self._lock = asyncio.Lock()

    async def create_transaction(self, transaction) -> bool:
        """Create a new transaction."""
        async with self._lock:
            self.transactions[transaction.id] = {
                "id": transaction.id,
                "amount": str(transaction.amount),
                "currency": transaction.currency,
                "method": transaction.method.value,
                "status": transaction.status.value,
                "customer_id": transaction.customer_id,
                "description": transaction.description,
                "metadata": transaction.metadata,
                "created_at": transaction.created_at.isoformat(),
                "updated_at": transaction.updated_at.isoformat(),
                "provider_transaction_id": transaction.provider_transaction_id,
                "fees": str(transaction.fees) if transaction.fees else None,
                "error_message": transaction.error_message
            }
            return True

    async def update_transaction(self, transaction) -> bool:
        """Update an existing transaction."""
        async with self._lock:
            if transaction.id not in self.transactions:
                return False

            self.transactions[transaction.id].update({
                "status": transaction.status.value,
                "updated_at": transaction.updated_at.isoformat(),
                "provider_transaction_id": transaction.provider_transaction_id,
                "fees": str(transaction.fees) if transaction.fees else None,
                "error_message": transaction.error_message
            })
            return True

    async def get_transaction(self, transaction_id: str) -> Optional[Any]:
        """Get transaction by ID."""
        async with self._lock:
            if transaction_id not in self.transactions:
                return None

            data = self.transactions[transaction_id]
            return self._deserialize_transaction(data)

    async def get_customer_transactions(self, customer_id: str) -> List[Any]:
        """Get all transactions for a customer."""
        async with self._lock:
            customer_transactions = [
                self._deserialize_transaction(data)
                for data in self.transactions.values()
                if data["customer_id"] == customer_id
            ]
            return sorted(customer_transactions, key=lambda t: t.created_at, reverse=True)

    async def get_transactions_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Any]:
        """Get transactions within date range."""
        async with self._lock:
            range_transactions = []
            for data in self.transactions.values():
                created_at = datetime.fromisoformat(data["created_at"])
                if start_date <= created_at <= end_date:
                    range_transactions.append(self._deserialize_transaction(data))
            return sorted(range_transactions, key=lambda t: t.created_at, reverse=True)

    async def get_transactions_by_status(self, status) -> List[Any]:
        """Get transactions by status."""
        async with self._lock:
            status_transactions = [
                self._deserialize_transaction(data)
                for data in self.transactions.values()
                if data["status"] == status.value
            ]
            return sorted(status_transactions, key=lambda t: t.created_at, reverse=True)

    def _deserialize_transaction(self, data: Dict[str, Any]) -> Any:
        """Deserialize transaction data."""
        from ..payment.payment_processor import PaymentTransaction, PaymentStatus, PaymentMethod
        from decimal import Decimal

        return PaymentTransaction(
            id=data["id"],
            amount=Decimal(data["amount"]),
            currency=data["currency"],
            method=PaymentMethod(data["method"]),
            status=PaymentStatus(data["status"]),
            customer_id=data["customer_id"],
            description=data["description"],
            metadata=data["metadata"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            provider_transaction_id=data["provider_transaction_id"],
            fees=Decimal(data["fees"]) if data["fees"] else None,
            error_message=data["error_message"]
        )

    async def get_transaction_stats(self) -> Dict[str, Any]:
        """Get transaction statistics."""
        async with self._lock:
            total_transactions = len(self.transactions)
            status_counts = {}
            total_amount = 0
            total_fees = 0

            for data in self.transactions.values():
                status = data["status"]
                status_counts[status] = status_counts.get(status, 0) + 1

                if data["status"] == "completed":
                    total_amount += float(data["amount"])
                    if data["fees"]:
                        total_fees += float(data["fees"])

            return {
                "total_transactions": total_transactions,
                "status_breakdown": status_counts,
                "total_amount": total_amount,
                "total_fees": total_fees,
                "net_amount": total_amount - total_fees
            }

    async def cleanup_old_transactions(self, days_old: int = 90):
        """Clean up old transactions."""
        async with self._lock:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            to_remove = []

            for transaction_id, data in self.transactions.items():
                created_at = datetime.fromisoformat(data["created_at"])
                if created_at < cutoff_date:
                    to_remove.append(transaction_id)

            for transaction_id in to_remove:
                del self.transactions[transaction_id]

            self.logger.info(f"Cleaned up {len(to_remove)} old transactions")
            return len(to_remove)
