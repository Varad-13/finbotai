functions_schema = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Perform mathematical calculations including basic arithmetic, trigonometry, logarithms, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate (e.g., '2+2', 'sqrt(16)', 'sin(pi/2)', '(5*3)+2')"
                    }
                },
                "required": ["expression"]
            }
        }
    }
]
