tools = [
    {
        "type": "function",
        "function": {
            "name": "auth_vendor",
            "description": "Authenticate a vendor using their phone number",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone_no": {"type": "string"}
                },
                "required": ["phone_no"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_store",
            "description": "Create a store for the vendor based on business categories",
            "parameters": {
                "type": "object",
                "properties": {
                    "categories": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "token": {"type": "string"}
                },
                "required": ["categories", "token"]
            }
        }
    }
]
