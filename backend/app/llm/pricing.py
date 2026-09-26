"""What a model call costs, so replayed runs report what they would cost live."""

from decimal import Decimal

from app.config import get_settings

# USD per million tokens, from Anthropic's price list (checked 2026-09-26).
# Add a model here before using it; an unknown model raises rather than costing zero.
USD_PER_MTOK: dict[str, tuple[Decimal, Decimal]] = {
    # model: (input, output)
    "claude-sonnet-5": (Decimal("2.00"), Decimal("10.00")),
}


def cost_gbp(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    try:
        input_price, output_price = USD_PER_MTOK[model]
    except KeyError:
        raise KeyError(f"no price for {model}; add it to app/llm/pricing.py") from None
    usd = (input_tokens * input_price + output_tokens * output_price) / Decimal(1_000_000)
    gbp = usd * Decimal(str(get_settings().gbp_per_usd))
    return gbp.quantize(Decimal("0.00001"))  # llm_calls.cost_gbp is numeric(10, 5)
