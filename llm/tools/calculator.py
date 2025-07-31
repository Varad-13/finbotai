import math


def calculate(expression: str) -> str:
    """Safe calculator function"""
    try:
        safe_dict = {
            "__builtins__": {},
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "pow": pow,
            "sqrt": math.sqrt,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "log": math.log,
            "log10": math.log10,
            "exp": math.exp,
            "pi": math.pi,
            "e": math.e,
            "ceil": math.ceil,
            "floor": math.floor,
            "factorial": math.factorial
        }

        expression = expression.replace("^", "**")  # Replace ^ with **

        result = eval(expression, safe_dict)
        return str(result)

    except Exception as e:
        return f"Error: {str(e)}"
