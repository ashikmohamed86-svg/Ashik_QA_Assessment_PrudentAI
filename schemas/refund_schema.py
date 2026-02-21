REFUND_SCHEMA = {
    "type": "object",
    "required": ["id", "object", "amount", "currency", "payment_intent", "status"],
    "properties": {
        "id": {"type": "string", "pattern": "^re_"},
        "object": {"type": "string", "enum": ["refund"]},
        "amount": {"type": "integer", "minimum": 0},
        "currency": {"type": "string", "minLength": 3, "maxLength": 3},
        "payment_intent": {"type": "string", "pattern": "^pi_"},
        "status": {
            "type": "string",
            "enum": ["succeeded", "pending", "failed", "canceled"],
        },
        "reason": {"type": ["string", "null"]},
        "created": {"type": "integer"},
    },
}
