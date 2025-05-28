"""
Stripe configuration module.

This module provides configuration settings for Stripe payment integration.
"""

import os

# Stripe API keys
# In production, these would be set as environment variables
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_51OxXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', 'pk_test_51OxXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX')

# Stripe webhook secret
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', 'whsec_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX')

# Currency configuration
CURRENCY = 'usd'  # Default currency
CURRENCY_SYMBOL = '$'  # Default currency symbol

# Payment options
PAYMENT_METHODS = ['card']  # Supported payment methods

# Deposit percentage (e.g., 0.2 for 20%)
DEPOSIT_PERCENTAGE = 0.2

# Minimum deposit amount
MIN_DEPOSIT_AMOUNT = 10.00

# Stripe checkout settings
CHECKOUT_SUCCESS_URL = '/payment/success?session_id={CHECKOUT_SESSION_ID}'
CHECKOUT_CANCEL_URL = '/payment/cancel?session_id={CHECKOUT_SESSION_ID}'

# Payment description templates
PAYMENT_DESCRIPTIONS = {
    'deposit': 'Deposit for booking #{booking_id}',
    'full_payment': 'Full payment for booking #{booking_id}',
    'balance': 'Balance payment for booking #{booking_id}',
    'additional_charge': 'Additional charge for booking #{booking_id}'
}
