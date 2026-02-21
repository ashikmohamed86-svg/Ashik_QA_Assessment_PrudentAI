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


# ── Boundary / limit payloads ──────────────────────────────────────
PAYMENT_INTENT_MIN_AMOUNT = {
    "amount": 50,
    "currency": "usd",
    "payment_method_types[]": "card",
}

PAYMENT_INTENT_LARGE_AMOUNT = {
    "amount": 99999999,
    "currency": "usd",
    "payment_method_types[]": "card",
}

PAYMENT_INTENT_EUR = {
    "amount": 1500,
    "currency": "eur",
    "payment_method_types[]": "card",
}

PAYMENT_INTENT_GBP = {
    "amount": 2500,
    "currency": "gbp",
    "payment_method_types[]": "card",
}

PAYMENT_INTENT_FLOAT_AMOUNT = {
    "amount": 20.50,
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
CARD_AMEX_SUCCESS = "pm_card_amex"
CARD_DISCOVER_SUCCESS = "pm_card_discover"

# Additional decline test cards
CARD_STOLEN = "pm_card_chargeDeclinedFraudulent"
CARD_LOST = "pm_card_chargeDeclinedLostCard"
CARD_RADAR_BLOCK = "pm_card_radarBlock"


# ── Security injection payloads ──────────────────────────────────
SQL_INJECTION_NAME = "'; DROP TABLE customers;--"
XSS_PAYLOAD_NAME = "<script>alert('xss')</script>"
PATH_TRAVERSAL_ID = "../../etc/passwd"
NULL_BYTE_NAME = "test\x00name"
HTML_ENTITY_DESCRIPTION = '&lt;b&gt;bold&lt;/b&gt; <img src=x onerror=alert(1)>'


# ── Zero-decimal currency payloads ───────────────────────────────
PAYMENT_INTENT_JPY = {
    "amount": 500,
    "currency": "jpy",
    "payment_method_types[]": "card",
}

PAYMENT_INTENT_WITH_DESCRIPTION = {
    "amount": 2000,
    "currency": "usd",
    "description": "Test payment for order #12345",
    "payment_method_types[]": "card",
}

PAYMENT_INTENT_WITH_METADATA = {
    "amount": 3000,
    "currency": "usd",
    "payment_method_types[]": "card",
    "metadata[order_id]": "ord_12345",
    "metadata[source]": "automation",
}
