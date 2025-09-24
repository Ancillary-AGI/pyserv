"""
Webhook handler for payment provider notifications.
"""

import asyncio
import hmac
import hashlib
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

class WebhookHandler:
    """
    Handles webhooks from payment providers.
    """

    def __init__(self, webhook_secret: str):
        self.webhook_secret = webhook_secret
        self.logger = logging.getLogger("webhook_handler")

    async def handle_webhook(self, provider: str, payload: Dict[str, Any]) -> bool:
        """Handle webhook from payment provider."""
        try:
            # Verify webhook signature
            if not await self._verify_signature(provider, payload):
                self.logger.warning(f"Invalid webhook signature from {provider}")
                return False

            # Process webhook based on provider
            if provider.lower() == "stripe":
                return await self._handle_stripe_webhook(payload)
            elif provider.lower() == "paypal":
                return await self._handle_paypal_webhook(payload)
            else:
                self.logger.warning(f"Unsupported webhook provider: {provider}")
                return False

        except Exception as e:
            self.logger.error(f"Webhook handling error: {e}")
            return False

    async def _verify_signature(self, provider: str, payload: Dict[str, Any]) -> bool:
        """Verify webhook signature."""
        try:
            if provider.lower() == "stripe":
                # Stripe signature verification
                signature = payload.get("signature", "")
                timestamp = payload.get("timestamp", "")
                body = payload.get("body", "")

                if not all([signature, timestamp, body]):
                    return False

                # Simple signature verification (placeholder)
                expected_signature = hmac.new(
                    self.webhook_secret.encode(),
                    f"{timestamp}.{body}".encode(),
                    hashlib.sha256
                ).hexdigest()

                return hmac.compare_digest(signature, expected_signature)

            return True  # Other providers

        except Exception as e:
            self.logger.error(f"Signature verification error: {e}")
            return False

    async def _handle_stripe_webhook(self, payload: Dict[str, Any]) -> bool:
        """Handle Stripe webhook."""
        try:
            event_type = payload.get("type", "")

            if event_type == "payment_intent.succeeded":
                await self._handle_payment_success(payload)
            elif event_type == "payment_intent.payment_failed":
                await self._handle_payment_failure(payload)
            elif event_type == "charge.dispute.created":
                await self._handle_dispute_created(payload)

            return True

        except Exception as e:
            self.logger.error(f"Stripe webhook error: {e}")
            return False

    async def _handle_paypal_webhook(self, payload: Dict[str, Any]) -> bool:
        """Handle PayPal webhook."""
        try:
            event_type = payload.get("event_type", "")

            if event_type == "PAYMENT.CAPTURE.COMPLETED":
                await self._handle_payment_success(payload)
            elif event_type == "PAYMENT.CAPTURE.DENIED":
                await self._handle_payment_failure(payload)

            return True

        except Exception as e:
            self.logger.error(f"PayPal webhook error: {e}")
            return False

    async def _handle_payment_success(self, payload: Dict[str, Any]):
        """Handle successful payment webhook."""
        self.logger.info(f"Payment succeeded: {payload}")

    async def _handle_payment_failure(self, payload: Dict[str, Any]):
        """Handle failed payment webhook."""
        self.logger.warning(f"Payment failed: {payload}")

    async def _handle_dispute_created(self, payload: Dict[str, Any]):
        """Handle dispute created webhook."""
        self.logger.warning(f"Dispute created: {payload}")

    def get_webhook_status(self) -> Dict[str, Any]:
        """Get webhook handler status."""
        return {
            "webhook_secret_configured": bool(self.webhook_secret),
            "supported_providers": ["stripe", "paypal"],
            "status": "active"
        }
