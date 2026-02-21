CUSTOMER_SCHEMA = {
    "type": "object",
    "required": ["id", "object", "created", "email", "livemode"],
    "properties": {
        "id": {"type": "string", "pattern": "^cus_"},
        "object": {"type": "string", "enum": ["customer"]},
        "name": {"type": ["string", "null"]},
        "email": {"type": ["string", "null"]},
        "phone": {"type": ["string", "null"]},
        "created": {"type": "integer"},
        "livemode": {"type": "boolean"},
        "description": {"type": ["string", "null"]},
        "currency": {"type": ["string", "null"]},
        "default_source": {"type": ["string", "null"]},
        "metadata": {"type": "object"},
    },
}

CUSTOMER_LIST_SCHEMA = {
    "type": "object",
    "required": ["object", "data", "has_more", "url"],
    "properties": {
        "object": {"type": "string", "enum": ["list"]},
        "data": {
            "type": "array",
            "items": CUSTOMER_SCHEMA,
        },
        "has_more": {"type": "boolean"},
        "url": {"type": "string"},
    },
}

CUSTOMER_DELETE_SCHEMA = {
    "type": "object",
    "required": ["id", "object", "deleted"],
    "properties": {
        "id": {"type": "string", "pattern": "^cus_"},
        "object": {"type": "string", "enum": ["customer"]},
        "deleted": {"type": "boolean", "enum": [True]},
    },
}

STRIPE_ERROR_SCHEMA = {
    "type": "object",
    "required": ["error"],
    "properties": {
        "error": {
            "type": "object",
            "required": ["type", "message"],
            "properties": {
                "type": {"type": "string"},
                "message": {"type": "string"},
                "code": {"type": "string"},
                "param": {"type": "string"},
            },
        }
    },
}
