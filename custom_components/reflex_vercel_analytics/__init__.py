"""reflex-vercel-analytics: Vercel Web Analytics for Reflex, powered by @vercel/analytics."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _package_version

from . import actions
from .actions import (
    Properties,
    PropertyValue,
    get_status,
    opt_in,
    opt_out,
    page_view,
    track,
    validate_event_name,
    validate_properties,
)
from .config import (
    ConfigError,
    VercelAnalyticsConfig,
    find_config_file,
    load_config,
)
from .constants import (
    DEFAULT_CONFIG_FILENAME,
    MODE_AUTO,
    MODE_DEVELOPMENT,
    MODE_PRODUCTION,
    MODES,
    VERCEL_ANALYTICS_VERSION,
)
from .vercel_analytics import VercelAnalytics, install, vercel_analytics

# pyproject.toml is the single source of truth for the version.
try:
    __version__ = _package_version("reflex-vercel-analytics")
except PackageNotFoundError:  # pragma: no cover - source tree without an install
    __version__ = "0.0.0.dev0"

__all__ = [
    "DEFAULT_CONFIG_FILENAME",
    "MODES",
    "MODE_AUTO",
    "MODE_DEVELOPMENT",
    "MODE_PRODUCTION",
    "VERCEL_ANALYTICS_VERSION",
    "ConfigError",
    "Properties",
    "PropertyValue",
    "VercelAnalytics",
    "VercelAnalyticsConfig",
    "actions",
    "find_config_file",
    "get_status",
    "install",
    "load_config",
    "opt_in",
    "opt_out",
    "page_view",
    "track",
    "validate_event_name",
    "validate_properties",
    "vercel_analytics",
]
