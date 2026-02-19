"""Reusable test data and Stripe test card tokens."""


# ── Customer payloads ───────────────────────────────────────────────
VALID_CUSTOMER = {
    "name": "Jane Doe",
    "email": "jane.doe@example.com",
    "phone": "+14155551234",
    "description": "Automation test customer",
}

CUSTOMER_MINIMAL = {
    "email": "minimal@example.com",
}

CUSTOMER_MISSING_EMAIL = {
    "name": "No Email User",
    "phone": "+14155559999",
}

CUSTOMER_INVALID_EMAIL = {
    "name": "Bad Email",
    "email": "not-an-email",
}


# ── Payment Intent payloads ─────────────────────────────────────────
VALID_PAYMENT_INTENT = {
    "amount": 2000,
    "currency": "usd",
    "payment_method_types[]": "card",
}

PAYMENT_INTENT_WITH_RECEIPT = {
    "amount": 5000,
    "currency": "usd",
    "receipt_email": "receipt@example.com",
    "payment_method_types[]": "card",
}

PAYMENT_INTENT_MANUAL_CAPTURE = {
    "amount": 3000,
    "currency": "usd",
    "capture_method": "manual",
    "payment_method_types[]": "card",
}

PAYMENT_INTENT_INVALID_CURRENCY = {
    "amount": 1000,
    "currency": "zzz",
    "payment_method_types[]": "card",
}

PAYMENT_INTENT_ZERO_AMOUNT = {
    "amount": 0,
    "currency": "usd",
    "payment_method_types[]": "card",
}

PAYMENT_INTENT_NEGATIVE_AMOUNT = {
    "amount": -500,
    "currency": "usd",
    "payment_method_types[]": "card",
}


# ── Stripe test payment method tokens ──────────────────────────────
# https://docs.stripe.com/testing#cards
CARD_VISA_SUCCESS = "pm_card_visa"
CARD_MASTERCARD_SUCCESS = "pm_card_mastercard"
CARD_DECLINED = "pm_card_chargeDeclined"
CARD_INSUFFICIENT_FUNDS = "pm_card_chargeDeclinedInsufficientFunds"
CARD_EXPIRED = "pm_card_chargeDeclinedExpiredCard"
CARD_INCORRECT_CVC = "pm_card_chargeDeclinedIncorrectCvc"
CARD_PROCESSING_ERROR = "pm_card_chargeDeclinedProcessingError"
