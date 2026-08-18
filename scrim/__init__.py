"""A scrim between the tool and the model. Local, fail-open."""

__version__ = "0.7.0"

from .config import load_config, load_config_report, data_dir
from .metrics import append_metric, summarize
from .prices import cost_usd, price_for
from .classify import classify
from .shrink import shrink_tool
from .constrain import constrain
from .observe import parse_transcript, parse_projects
from .timeutil import local_day, today_local

__all__ = [
    "__version__",
    "load_config",
    "load_config_report",
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
    "local_day",
    "today_local",
]
