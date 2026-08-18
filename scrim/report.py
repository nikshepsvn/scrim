"""Human-readable Scrim report."""

from __future__ import annotations


def render(usage: dict, tools: dict) -> str:
    lines = ["Scrim"]
    tot = (usage or {}).get("total") or {}
    if tot.get("turns"):
        cr_pct = (usage.get("cache_read_share") or 0) * 100
        lines.append("Usage  (list prices, not Stripe)")
        lines.append(
            f"  ${tot['cost']:,.0f} API-eq   turns {tot['turns']:,}   "
            f"cache-read {tot['cr']:,} ({cr_pct:.0f}%)   "
            f"cache-write {tot['cw']:,}   out {tot['out']:,}"
        )
        models = usage.get("models") or {}
        for model, m in sorted(models.items(), key=lambda kv: -kv[1]["cost"])[:8]:
            lines.append(f"    {model:<32} ${m['cost']:,.0f}   {m['turns']:,} turns")
    else:
        lines.append("Usage  (no transcript turns in range)")

    lines.append("Tools  (this plugin)")
    if tools.get("n"):
        lines.append(
            f"  {tools['n']:,} calls   {tools['bytes_in']/1e6:.2f} MB in → "
            f"{tools['bytes_out']/1e6:.2f} MB out   "
            f"{tools['saved']/1e6:.2f} MB thinned  ({tools['shrunk']:,} calls)"
        )
        for name, v in list((tools.get("by_tool") or {}).items())[:8]:
            lines.append(f"    {name:<40} n={v['n']:<5} {v['in']/1e6:6.2f} MB")
        kinds = [
            f"{k} {v['in']/1e6:.2f} MB"
            for k, v in list((tools.get("by_kind") or {}).items())[:4]
            if v["in"] >= 10_000
        ]
        if kinds:
            lines.append("  kinds  " + " · ".join(kinds))
        if tools.get("stashes"):
            lines.append(f"  stashed originals  {tools['stashes']:,}  (scrim get <id>)")
        if tools.get("swarms"):
            lines.append(f"  subagents spawned  {tools['swarms']:,}")
    else:
        lines.append("  no hook metrics yet — install the plugin and run a tool")
    return "\n".join(lines) + "\n"
