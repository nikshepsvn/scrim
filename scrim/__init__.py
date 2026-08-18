"""A scrim between the tool and the model. Local, fail-open."""

from .config import load_config, data_dir
from .metrics import append_metric, summarize
from .prices import cost_usd, price_for
from .classify import classify
from .shrink import shrink_tool
from .constrain import constrain
from .observe import parse_transcript, parse_projects

__all__ = [
    "load_config",
    "data_dir",
    "append_metric",
    "summarize",
    "cost_usd",
    "price_for",
    "classify",
    "shrink_tool",
    "constrain",
    "parse_transcript",
    "parse_projects",
]
