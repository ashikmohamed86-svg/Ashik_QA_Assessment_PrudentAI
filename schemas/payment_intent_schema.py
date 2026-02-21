PAYMENT_INTENT_SCHEMA = {
    "type": "object",
    "required": ["id", "object", "amount", "currency", "status", "created"],
    "properties": {
        "id": {"type": "string", "pattern": "^pi_"},
        "object": {"type": "string", "enum": ["payment_intent"]},
        "amount": {"type": "integer", "minimum": 0},
        "amount_received": {"type": "integer", "minimum": 0},
        "currency": {"type": "string", "minLength": 3, "maxLength": 3},
        "status": {
            "type": "string",
            "enum": [
                "requires_payment_method",
                "requires_confirmation",
                "requires_action",
                "processing",
                "requires_capture",
                "canceled",
                "succeeded",
            ],
        },
        "created": {"type": "integer"},
        "livemode": {"type": "boolean"},
        "receipt_email": {"type": ["string", "null"]},
        "payment_method": {"type": ["string", "null"]},
        "capture_method": {
            "type": "string",
            "enum": ["automatic", "automatic_async", "manual"],
        },
        "confirmation_method": {
            "type": "string",
            "enum": ["automatic", "manual"],
        },
        "metadata": {"type": "object"},
    },
}

PAYMENT_INTENT_LIST_SCHEMA = {
    "type": "object",
    "required": ["object", "data", "has_more", "url"],
    "properties": {
        "object": {"type": "string", "enum": ["list"]},
        "data": {
            "type": "array",
            "items": PAYMENT_INTENT_SCHEMA,
        },
        "has_more": {"type": "boolean"},
        "url": {"type": "string"},
    },
}

CANCEL_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["id", "object", "status"],
    "properties": {
        "id": {"type": "string", "pattern": "^pi_"},
        "object": {"type": "string", "enum": ["payment_intent"]},
        "status": {"type": "string", "enum": ["canceled"]},
        "cancellation_reason": {"type": ["string", "null"]},
    },
}

PAYMENT_INTENT_CONFIRM_SCHEMA = {
    "type": "object",
    "required": ["id", "object", "status"],
    "properties": {
        "id": {"type": "string", "pattern": "^pi_"},
        "object": {"type": "string", "enum": ["payment_intent"]},
        "status": {
            "type": "string",
            "enum": [
                "requires_action",
                "requires_capture",
                "processing",
                "succeeded",
            ],
        },
    },
}
