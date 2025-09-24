"""
Stripe payment processor implementation.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime

class StripeProcessor:
    """
    Stripe payment processor implementation.
    """

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger("stripe_processor")
        self.stripe = None

    async def initialize(self):
        """Initialize Stripe client."""
        try:
            import stripe
            stripe.api_key = self.config.api_key
            self.stripe = stripe
            self.logger.info("Stripe processor initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize Stripe: {e}")
            raise

    async def process_payment(self, transaction, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment with Stripe."""
        try:
            # Create payment intent
            intent_data = {
                "amount": int(transaction.amount * 100),  # Convert to cents
                "currency": transaction.currency.lower(),
                "metadata": {
                    "transaction_id": transaction.id,
                    "customer_id": transaction.customer_id
                }
            }

            # Add payment method if provided
            if "payment_method_id" in payment_data:
                intent_data["payment_method"] = payment_data["payment_method_id"]
                intent_data["confirm"] = True
            elif "card_token" in payment_data:
                intent_data["payment_method_data"] = {
                    "type": "card",
                    "card": {"token": payment_data["card_token"]}
                }
                intent_data["confirm"] = True

            payment_intent = self.stripe.PaymentIntent.create(**intent_data)

            return {
                "success": payment_intent.status == "succeeded",
                "provider_id": payment_intent.id,
                "fees": Decimal(str(payment_intent.application_fee_amount or 0)) / 100,
                "error_message": payment_intent.last_payment_error.message if payment_intent.last_payment_error else None
            }

        except Exception as e:
            self.logger.error(f"Stripe payment error: {e}")
            return {
                "success": False,
                "error_message": str(e)
            }

    async def refund_payment(self, transaction, amount: Decimal) -> Dict[str, Any]:
        """Refund payment with Stripe."""
        try:
            refund = self.stripe.Refund.create(
                payment_intent=transaction.provider_transaction_id,
                amount=int(amount * 100)
            )

            return {
                "success": refund.status == "succeeded",
                "refund_id": refund.id
            }

        except Exception as e:
            self.logger.error(f"Stripe refund error: {e}")
            return {
                "success": False,
                "error_message": str(e)
            }
