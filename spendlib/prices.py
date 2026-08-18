"""Public list prices USD / million tokens. Shadow cost only (Max is flat)."""

from __future__ import annotations

# (input, output). Cache read = 10% input. 5m write = 1.25x. 1h write = 2x.
PRICES = {
    "claude-opus-5": (5.0, 25.0),
    "claude-opus-4": (5.0, 25.0),
    "claude-sonnet-5": (3.0, 15.0),
    "claude-sonnet-4": (3.0, 15.0),
    "claude-haiku-4": (1.0, 5.0),
    "claude-fable-5": (3.0, 15.0),
}


def price_for(model: str) -> tuple[float, float]:
    m = (model or "").lower()
    for prefix, p in PRICES.items():
        if m.startswith(prefix):
            return p
    if "opus" in m:
        return (5.0, 25.0)
    if "haiku" in m:
        return (1.0, 5.0)
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
