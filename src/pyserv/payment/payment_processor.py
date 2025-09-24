"""
Core payment processing system for PyServ.
Handles multiple payment providers with security and compliance features.
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from decimal import Decimal

class PaymentStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"

class PaymentMethod(Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    STRIPE = "stripe"
    CRYPTO = "crypto"
    BANK_TRANSFER = "bank_transfer"
    DIGITAL_WALLET = "digital_wallet"

@dataclass
class PaymentConfig:
    """Configuration for payment processing."""
    provider: str = "stripe"
    api_key: str = ""
    webhook_secret: str = ""
    test_mode: bool = True
    currency: str = "USD"
    supported_methods: List[PaymentMethod] = None
    max_amount: Decimal = Decimal('10000.00')
    min_amount: Decimal = Decimal('0.50')
    enable_fraud_detection: bool = True
    enable_idempotency: bool = True

    def __post_init__(self):
        if self.supported_methods is None:
            self.supported_methods = [PaymentMethod.CREDIT_CARD, PaymentMethod.PAYPAL]

@dataclass
class PaymentTransaction:
    """Payment transaction data structure."""
    id: str
    amount: Decimal
    currency: str
    method: PaymentMethod
    status: PaymentStatus
    customer_id: str
    description: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    provider_transaction_id: Optional[str] = None
    fees: Optional[Decimal] = None
    error_message: Optional[str] = None

class PaymentProcessor:
    """
    Core payment processor with multi-provider support.
    """

    def __init__(self, config: PaymentConfig):
        self.config = config
        self.logger = logging.getLogger("payment_processor")
        self.transaction_manager = TransactionManager()
        self.security_manager = PaymentSecurity()
        self.webhook_handler = WebhookHandler(config.webhook_secret)
        self._initialize_provider()

    def _initialize_provider(self):
        """Initialize the appropriate payment provider."""
        if self.config.provider.lower() == "stripe":
            self.provider = StripeProcessor(self.config)
        elif self.config.provider.lower() == "paypal":
            self.provider = PayPalProcessor(self.config)
        elif self.config.provider.lower() == "crypto":
            self.provider = CryptoProcessor(self.config)
        else:
            raise ValueError(f"Unsupported payment provider: {self.config.provider}")

    async def process_payment(self, payment_data: Dict[str, Any]) -> PaymentTransaction:
        """Process a payment transaction."""
        try:
            # Validate payment data
            validated_data = await self._validate_payment_data(payment_data)

            # Create transaction record
            transaction = PaymentTransaction(
                id=str(uuid.uuid4()),
                amount=validated_data["amount"],
                currency=validated_data["currency"],
                method=validated_data["method"],
                status=PaymentStatus.PENDING,
                customer_id=validated_data["customer_id"],
                description=validated_data["description"],
                metadata=validated_data.get("metadata", {}),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

            # Store transaction
            await self.transaction_manager.create_transaction(transaction)

            # Process with provider
            provider_result = await self.provider.process_payment(transaction, validated_data)

            # Update transaction with provider response
            transaction.provider_transaction_id = provider_result.get("provider_id")
            transaction.fees = provider_result.get("fees")
            transaction.status = PaymentStatus.COMPLETED if provider_result["success"] else PaymentStatus.FAILED
            transaction.error_message = provider_result.get("error_message")

            if not provider_result["success"]:
                transaction.status = PaymentStatus.FAILED

            # Update transaction
            await self.transaction_manager.update_transaction(transaction)

            # Log transaction
            self.logger.info(f"Payment {transaction.id} {'completed' if transaction.status == PaymentStatus.COMPLETED else 'failed'}")

            return transaction

        except Exception as e:
            self.logger.error(f"Payment processing error: {e}")
            raise

    async def refund_payment(self, transaction_id: str, amount: Optional[Decimal] = None) -> PaymentTransaction:
        """Refund a payment transaction."""
        try:
            # Get transaction
            transaction = await self.transaction_manager.get_transaction(transaction_id)
            if not transaction:
                raise ValueError(f"Transaction {transaction_id} not found")

            if transaction.status != PaymentStatus.COMPLETED:
                raise ValueError(f"Cannot refund transaction with status {transaction.status.value}")

            # Calculate refund amount
            refund_amount = amount or transaction.amount

            if refund_amount > transaction.amount:
                raise ValueError("Refund amount cannot exceed transaction amount")

            # Process refund with provider
            refund_result = await self.provider.refund_payment(transaction, refund_amount)

            # Update transaction
            transaction.status = PaymentStatus.REFUNDED if refund_amount == transaction.amount else PaymentStatus.PARTIALLY_REFUNDED
            transaction.updated_at = datetime.now()

            await self.transaction_manager.update_transaction(transaction)

            self.logger.info(f"Payment {transaction_id} refunded: {refund_amount}")

            return transaction

        except Exception as e:
            self.logger.error(f"Payment refund error: {e}")
            raise

    async def _validate_payment_data(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate payment data."""
        required_fields = ["amount", "currency", "customer_id", "description"]
        validated_data = {}

        # Check required fields
        for field in required_fields:
            if field not in payment_data:
                raise ValueError(f"Missing required field: {field}")
            validated_data[field] = payment_data[field]

        # Validate amount
        try:
            amount = Decimal(str(validated_data["amount"]))
            if amount < self.config.min_amount or amount > self.config.max_amount:
                raise ValueError(f"Amount must be between {self.config.min_amount} and {self.config.max_amount}")
            validated_data["amount"] = amount
        except:
            raise ValueError("Invalid amount format")

        # Validate currency
        if validated_data["currency"] != self.config.currency:
            self.logger.warning(f"Currency mismatch: {validated_data['currency']} vs {self.config.currency}")

        # Validate payment method
        method_str = payment_data.get("method", "credit_card")
        try:
            method = PaymentMethod(method_str)
            if method not in self.config.supported_methods:
                raise ValueError(f"Unsupported payment method: {method_str}")
            validated_data["method"] = method
        except ValueError:
            raise ValueError(f"Invalid payment method: {method_str}")

        return validated_data

    async def get_transaction(self, transaction_id: str) -> Optional[PaymentTransaction]:
        """Get transaction by ID."""
        return await self.transaction_manager.get_transaction(transaction_id)

    async def get_customer_transactions(self, customer_id: str) -> List[PaymentTransaction]:
        """Get all transactions for a customer."""
        return await self.transaction_manager.get_customer_transactions(customer_id)

    async def get_transaction_stats(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get transaction statistics for date range."""
        transactions = await self.transaction_manager.get_transactions_by_date_range(start_date, end_date)

        total_amount = sum(t.amount for t in transactions if t.status == PaymentStatus.COMPLETED)
        total_fees = sum(t.fees or 0 for t in transactions if t.fees)
        success_count = sum(1 for t in transactions if t.status == PaymentStatus.COMPLETED)
        failed_count = sum(1 for t in transactions if t.status == PaymentStatus.FAILED)

        return {
            "total_transactions": len(transactions),
            "successful_transactions": success_count,
            "failed_transactions": failed_count,
            "success_rate": success_count / len(transactions) if transactions else 0,
            "total_amount": float(total_amount),
            "total_fees": float(total_fees),
            "net_amount": float(total_amount - total_fees)
        }

    async def handle_webhook(self, provider: str, payload: Dict[str, Any]) -> bool:
        """Handle payment provider webhook."""
        return await self.webhook_handler.handle_webhook(provider, payload)

# Global payment processor
payment_processor = None

def initialize_payment_processor(config: PaymentConfig):
    """Initialize global payment processor."""
    global payment_processor
    payment_processor = PaymentProcessor(config)
    return payment_processor
