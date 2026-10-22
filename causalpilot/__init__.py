"""Check an A/B test export and get a ship / hold / extend call."""

from .analysis import Settings, analyze_csv, analyze_frame

__version__ = "0.2.0"

__all__ = ["Settings", "analyze_csv", "analyze_frame", "__version__"]
