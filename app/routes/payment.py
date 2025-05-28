"""
Payment routes module.

This module defines routes for payment processing.
"""

import stripe
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user

from db import db
from app.utils.decorators import role_required
from app.services.payment_service import PaymentService
from app.services.booking_service import BookingService
from app.models.booking import Booking
from app.models.payment import Payment

# Create blueprint
payment_bp = Blueprint('payment', __name__)


@payment_bp.route('/webhook', methods=['POST'])
def webhook():
    """Handle Stripe webhook events."""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    payment_service = PaymentService(db.session)

    try:
        event = payment_service.process_webhook_event(payload, sig_header)
        return jsonify(success=True)
    except ValueError as e:
        return jsonify(success=False, error=str(e)), 400
    except Exception as e:
        current_app.logger.error(f"Webhook error: {str(e)}")
        return jsonify(success=False, error=str(e)), 500


@payment_bp.route('/checkout/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def checkout(booking_id):
    """Create a checkout session for a booking."""
    booking_service = BookingService(db.session)
    payment_service = PaymentService(db.session)

    # Get the booking
    booking = booking_service.get_booking_by_id(booking_id)
    if not booking:
        flash("Booking not found.", "danger")
        return redirect(url_for('customer.bookings'))

    # Check if the booking belongs to the current user (for customer role)
    if current_user.role == 'customer' and booking.customer.user_id != current_user.id:
        flash("You don't have permission to access this booking.", "danger")
        return redirect(url_for('customer.bookings'))

    # For GET requests, show the checkout page
    if request.method == 'GET':
        return render_template(
            'payment/checkout.html',
            booking=booking,
            stripe_publishable_key=payment_service.get_publishable_key()
        )

    # For POST requests, create a checkout session
    payment_type = request.form.get('payment_type', 'full_payment')

    try:
        # Create checkout session
        checkout_session = payment_service.create_checkout_session(
            booking_id=booking.id,
            payment_type=payment_type,
            customer_email=booking.customer.user.email if booking.customer and booking.customer.user else None
        )

        # Return the session ID
        return jsonify({
            'success': True,
            'sessionId': checkout_session.id
        })
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except stripe.error.StripeError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Checkout error: {str(e)}")
        return jsonify({
            'success': False,
            'error': "An unexpected error occurred. Please try again."
        }), 500


@payment_bp.route('/success')
@login_required
def payment_success():
    """Handle successful payment."""
    session_id = request.args.get('session_id')

    if not session_id:
        flash("Invalid payment session.", "danger")
        return redirect(url_for('customer.bookings'))

    try:
        # Retrieve the session to get booking details
        session = stripe.checkout.Session.retrieve(session_id)
        booking_id = session.metadata.get('booking_id')

        if not booking_id:
            flash("Booking information not found.", "danger")
            return redirect(url_for('customer.bookings'))

        # Get the booking
        booking = db.session.query(Booking).get(int(booking_id))
        if not booking:
            flash("Booking not found.", "danger")
            return redirect(url_for('customer.bookings'))

        # Show success page
        return render_template(
            'payment/success.html',
            booking=booking,
            payment_intent_id=session.payment_intent
        )
    except stripe.error.StripeError as e:
        flash(f"Error retrieving payment information: {str(e)}", "danger")
        return redirect(url_for('customer.bookings'))
    except Exception as e:
        current_app.logger.error(f"Payment success error: {str(e)}")
        flash("An unexpected error occurred.", "danger")
        return redirect(url_for('customer.bookings'))


@payment_bp.route('/cancel')
@login_required
def payment_cancel():
    """Handle cancelled payment."""
    session_id = request.args.get('session_id')

    if not session_id:
        flash("Invalid payment session.", "danger")
        return redirect(url_for('customer.bookings'))

    try:
        # Retrieve the session to get booking details
        session = stripe.checkout.Session.retrieve(session_id)
        booking_id = session.metadata.get('booking_id')

        if not booking_id:
            flash("Booking information not found.", "danger")
            return redirect(url_for('customer.bookings'))

        # Get the booking
        booking = db.session.query(Booking).get(int(booking_id))
        if not booking:
            flash("Booking not found.", "danger")
            return redirect(url_for('customer.bookings'))

        # Show cancel page
        return render_template(
            'payment/cancel.html',
            booking=booking
        )
    except stripe.error.StripeError as e:
        flash(f"Error retrieving payment information: {str(e)}", "danger")
        return redirect(url_for('customer.bookings'))
    except Exception as e:
        current_app.logger.error(f"Payment cancel error: {str(e)}")
        flash("An unexpected error occurred.", "danger")
        return redirect(url_for('customer.bookings'))


@payment_bp.route('/refund/<int:payment_id>', methods=['POST'])
@login_required
@role_required(['receptionist', 'manager', 'admin'])
def refund_payment(payment_id):
    """Refund a payment."""
    payment = db.session.query(Payment).get(payment_id)
    if not payment:
        flash("Payment not found.", "danger")
        return redirect(url_for('receptionist.dashboard'))

    # Check if payment has a Stripe reference
    if not payment.reference or not payment.reference.startswith('pi_'):
        flash("This payment cannot be refunded through Stripe.", "danger")
        return redirect(url_for('receptionist.view_folio', booking_id=payment.booking_id))

    # Check if payment is already refunded
    if payment.refunded:
        flash("This payment has already been refunded.", "warning")
        return redirect(url_for('receptionist.view_folio', booking_id=payment.booking_id))

    reason = request.form.get('reason', 'Requested by staff')

    try:
        # Create refund in Stripe
        refund = stripe.Refund.create(
            payment_intent=payment.reference,
            reason='requested_by_customer'
        )

        # Update payment record
        payment.refunded = True
        payment.refund_date = datetime.now(timezone.utc)
        payment.refund_reference = refund.id
        payment.refund_reason = reason
        payment.refunded_by = current_user.id

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

        db.session.commit()

        flash(f"Payment of ${payment.amount:.2f} has been refunded successfully.", "success")
    except stripe.error.StripeError as e:
        flash(f"Error processing refund: {str(e)}", "danger")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Refund error: {str(e)}")
        flash("An unexpected error occurred while processing the refund.", "danger")

    return redirect(url_for('receptionist.view_folio', booking_id=payment.booking_id))
