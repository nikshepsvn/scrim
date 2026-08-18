"""Public list prices USD / million tokens. Shadow cost only (Max is flat)."""

from __future__ import annotations

# (input, output). Cache read = 10% input. 5m write = 1.25x. 1h write = 2x.
PRICES = {
    "claude-fable-5": (10.0, 50.0),
    "claude-mythos-5": (10.0, 50.0),
    "claude-opus-5": (5.0, 25.0),
    "claude-opus-4": (5.0, 25.0),
    "claude-sonnet-5": (3.0, 15.0),
    "claude-sonnet-4": (3.0, 15.0),
    "claude-haiku-4": (1.0, 5.0),
    # Codex: cached input is 10% of input, same factor as Anthropic cache-read.
    # Order matters — first prefix hit wins, so mini/nano precede bare gpt-5.
    "gpt-5-mini": (0.25, 2.0),
    "gpt-5-nano": (0.05, 0.40),
    "gpt-5": (1.25, 10.0),
}


def price_for(model: str) -> tuple[float, float]:
    m = (model or "").lower()
    for prefix, p in PRICES.items():
        if m.startswith(prefix):
            return p
    if "fable" in m or "mythos" in m:
        return (10.0, 50.0)
    if "opus" in m:
        return (5.0, 25.0)
    if "haiku" in m:
        return (1.0, 5.0)
    if m.startswith("gpt") or m.startswith("o3") or m.startswith("o4"):
        return (1.25, 10.0)  # unknown OpenAI model: bill at gpt-5 base rate
    return (3.0, 15.0)


def cost_usd(model, inp=0, out=0, cr=0, cw=0, cw1h=0) -> float:
    inn, outp = price_for(model)
    write_5m = max(0, (cw or 0) - (cw1h or 0))
    return (
        (inp or 0) * inn
        + (out or 0) * outp
        + (cr or 0) * inn * 0.10
        + write_5m * inn * 1.25
        + (cw1h or 0) * inn * 2.0
    ) / 1_000_000.0
