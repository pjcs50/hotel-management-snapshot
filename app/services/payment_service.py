"""
Payment service module.

This module provides services for processing payments through Stripe.
"""

import stripe
from datetime import datetime, timezone
from flask import current_app, url_for

from app.config.stripe_config import (
    CURRENCY,
    PAYMENT_METHODS,
    PAYMENT_DESCRIPTIONS,
    DEPOSIT_PERCENTAGE,
    MIN_DEPOSIT_AMOUNT
)
from app.models.payment import Payment
from app.models.booking import Booking


class PaymentService:
    """Service for processing payments through Stripe."""

    def __init__(self, db_session):
        """Initialize the service with a database session."""
        self.db_session = db_session
        # Initialize Stripe with the secret key from config
        stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')

    def create_checkout_session(self, booking_id, payment_type='full_payment', customer_email=None, success_url=None, cancel_url=None):
        """
        Create a Stripe checkout session for a booking.

        Args:
            booking_id: ID of the booking to pay for
            payment_type: Type of payment ('deposit', 'full_payment', 'balance')
            customer_email: Customer's email address
            success_url: URL to redirect to after successful payment
            cancel_url: URL to redirect to after cancelled payment

        Returns:
            Stripe checkout session
        """
        # Get the booking
        booking = self.db_session.query(Booking).get(booking_id)
        if not booking:
            raise ValueError(f"Booking with ID {booking_id} not found")

        # Determine payment amount based on payment type
        if payment_type == 'deposit':
            amount = max(booking.total_price * DEPOSIT_PERCENTAGE, MIN_DEPOSIT_AMOUNT)
        elif payment_type == 'balance':
            amount = booking.balance_due
        else:  # full_payment
            amount = booking.total_price

        # Ensure amount is valid
        if amount <= 0:
            raise ValueError("Payment amount must be greater than zero")

        # Convert amount to cents (Stripe uses smallest currency unit)
        amount_cents = int(amount * 100)

        # Get customer email if not provided
        if not customer_email and booking.customer and booking.customer.user:
            customer_email = booking.customer.user.email

        # Create line item for checkout
        line_items = [{
            'price_data': {
                'currency': CURRENCY,
                'product_data': {
                    'name': f"Room {booking.room.number} - {booking.room.room_type.name}",
                    'description': PAYMENT_DESCRIPTIONS.get(payment_type, '').format(booking_id=booking.id),
                    'metadata': {
                        'booking_id': booking.id,
                        'payment_type': payment_type
                    }
                },
                'unit_amount': amount_cents,
            },
            'quantity': 1,
        }]

        # Set metadata for the session
        metadata = {
            'booking_id': booking.id,
            'payment_type': payment_type,
            'room_number': booking.room.number,
            'check_in_date': booking.check_in_date.isoformat(),
            'check_out_date': booking.check_out_date.isoformat()
        }

        # Set success and cancel URLs
        if not success_url:
            success_url = url_for('customer.payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}'
        if not cancel_url:
            cancel_url = url_for('customer.payment_cancel', _external=True) + '?session_id={CHECKOUT_SESSION_ID}'

        # Create checkout session
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=PAYMENT_METHODS,
                line_items=line_items,
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=customer_email,
                metadata=metadata
            )
            return checkout_session
        except stripe.error.StripeError as e:
            # Log the error
            current_app.logger.error(f"Stripe error: {str(e)}")
            raise

    def process_webhook_event(self, payload, sig_header):
        """
        Process a webhook event from Stripe.

        Args:
            payload: The webhook payload
            sig_header: The Stripe signature header

        Returns:
            The processed event
        """
        webhook_secret = current_app.config.get('STRIPE_WEBHOOK_SECRET')

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError as e:
            # Invalid payload
            raise ValueError('Invalid payload')
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            raise ValueError('Invalid signature')

        # Handle the event
        if event['type'] == 'checkout.session.completed':
            self._handle_checkout_session_completed(event['data']['object'])
        elif event['type'] == 'payment_intent.succeeded':
            self._handle_payment_intent_succeeded(event['data']['object'])
        elif event['type'] == 'charge.refunded':
            self._handle_charge_refunded(event['data']['object'])

        return event

    def _handle_checkout_session_completed(self, session):
        """
        Handle a completed checkout session.

        Args:
            session: The Stripe checkout session
        """
        # Get booking ID from metadata
        booking_id = session.get('metadata', {}).get('booking_id')
        if not booking_id:
            current_app.logger.error("No booking ID in session metadata")
            return

        # Get payment details
        payment_intent_id = session.get('payment_intent')
        if not payment_intent_id:
            current_app.logger.error("No payment intent ID in session")
            return

        try:
            # Get payment intent for additional details
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            # Get booking
            booking = self.db_session.query(Booking).get(int(booking_id))
            if not booking:
                current_app.logger.error(f"Booking with ID {booking_id} not found")
                return

            # Create payment record
            amount = payment_intent.amount / 100  # Convert from cents
            payment = Payment(
                booking_id=booking.id,
                amount=amount,
                payment_date=datetime.now(timezone.utc),
                payment_type='Credit Card',  # Default to credit card
                reference=payment_intent_id
            )
            self.db_session.add(payment)

            # Update booking payment amount and status
            booking.payment_amount += amount
            if booking.is_fully_paid:
                booking.payment_status = booking.PAYMENT_FULL
            elif booking.payment_amount > 0:
                booking.payment_status = booking.PAYMENT_DEPOSIT

            self.db_session.commit()

            # Log successful payment
            current_app.logger.info(f"Payment of {amount} processed for booking {booking_id}")

        except Exception as e:
            self.db_session.rollback()
            current_app.logger.error(f"Error processing payment: {str(e)}")
            raise

    def _handle_payment_intent_succeeded(self, payment_intent_obj):
        """
        Handle a succeeded payment intent.

        Args:
            payment_intent_obj: The Stripe payment intent
        """
        # This is a backup handler in case the checkout.session.completed event fails
        # In most cases, we'll handle payments through checkout.session.completed
        pass

    def _handle_charge_refunded(self, charge):
        """
        Handle a refunded charge.

        Args:
            charge: The Stripe charge
        """
        # Find the payment by reference (payment_intent_id)
        payment_intent_id = charge.get('payment_intent')
        if not payment_intent_id:
            current_app.logger.error("No payment intent ID in charge")
            return

        try:
            # Find payment by reference
            payment = self.db_session.query(Payment).filter_by(reference=payment_intent_id).first()
            if not payment:
                current_app.logger.error(f"Payment with reference {payment_intent_id} not found")
                return

            # Mark payment as refunded
            payment.refunded = True
            payment.refund_date = datetime.now(timezone.utc)
            payment.refund_reference = charge.get('id')
            payment.refund_reason = "Refunded via Stripe"

            # Update booking payment amount and status
            booking = payment.booking
            if booking:
                booking.payment_amount -= payment.amount
                if booking.payment_amount <= 0:
                    booking.payment_status = booking.PAYMENT_NOT_PAID
                elif booking.is_fully_paid:
                    booking.payment_status = booking.PAYMENT_FULL
                else:
                    booking.payment_status = booking.PAYMENT_DEPOSIT

            self.db_session.commit()

            # Log successful refund
            current_app.logger.info(f"Refund of {payment.amount} processed for payment {payment.id}")

        except Exception as e:
            self.db_session.rollback()
            current_app.logger.error(f"Error processing refund: {str(e)}")
            raise

    def get_publishable_key(self):
        """
        Get the Stripe publishable key.

        Returns:
            Stripe publishable key
        """
        return current_app.config.get('STRIPE_PUBLISHABLE_KEY')
