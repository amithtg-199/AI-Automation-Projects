# Configurable mapping of provider models to their costs (USD per 1,000 tokens)
# This allows decoupled calculation without hardcoding in SQL queries.

MODEL_PRICING = {
    # OpenAI
    "gpt-4o": {
        "input_per_1k": 0.005,
        "output_per_1k": 0.015,
        "provider": "openai"
    },
    "gpt-4-turbo": {
        "input_per_1k": 0.01,
        "output_per_1k": 0.03,
        "provider": "openai"
    },
    "gpt-3.5-turbo": {
        "input_per_1k": 0.0005,
        "output_per_1k": 0.0015,
        "provider": "openai"
    },
    # Anthropic
    "claude-3-opus-20240229": {
        "input_per_1k": 0.015,
        "output_per_1k": 0.075,
        "provider": "anthropic"
    },
    "claude-3-sonnet-20240229": {
        "input_per_1k": 0.003,
        "output_per_1k": 0.015,
        "provider": "anthropic"
    },
    # Others
    "llama3-70b-8192": {
        "input_per_1k": 0.00059,
        "output_per_1k": 0.00079,
        "provider": "groq"
    }
}

def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculates total cost in USD based on pricing table."""
    rates = MODEL_PRICING.get(model, {"input_per_1k": 0, "output_per_1k": 0})
    cost_in = (input_tokens / 1000) * rates["input_per_1k"]
    cost_out = (output_tokens / 1000) * rates["output_per_1k"]
    return cost_in + cost_out
