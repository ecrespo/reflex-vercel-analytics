"""Constants shared by the component, the config loader and the actions."""

from __future__ import annotations

# @vercel/analytics release this package is built and tested against.
VERCEL_ANALYTICS_VERSION = "2.0.1"

# Script the package injects by default on a Vercel deployment (served by the
# platform) and the debug build it uses in development mode.
DEFAULT_SCRIPT_PATH = "/_vercel/insights/script.js"
DEBUG_SCRIPT_URL = "https://va.vercel-scripts.com/v1/script.debug.js"

# Name of the config file looked up next to ``rxconfig.py``.
DEFAULT_CONFIG_FILENAME = "vercel_analytics.toml"

# Environment variables. ``VERCEL_ANALYTICS_CONFIG`` points at a config file;
# the others override single fields of whatever file was loaded.
ENV_PREFIX = "VERCEL_ANALYTICS_"
ENV_CONFIG_PATH = f"{ENV_PREFIX}CONFIG"

# Build-time variables Vercel sets for its own frameworks (Next.js reads them as
# NEXT_PUBLIC_..., CRA as REACT_APP_...). Reflex builds with Vite, which does not
# expose them to the bundle, so the Python side forwards them to the component.
ENV_VERCEL_CLIENT_CONFIG = "VERCEL_OBSERVABILITY_CLIENT_CONFIG"
ENV_VERCEL_BASEPATH = "VERCEL_OBSERVABILITY_BASEPATH"

# Table used inside pyproject.toml / a shared TOML file.
PYPROJECT_TABLE = ("tool", "reflex-vercel-analytics")
TOML_TABLE = "vercel_analytics"

# Order of the app wrap installed by ``install``. Low numbers sit closest to the
# pages, inside every provider Reflex adds, so event triggers can reach State.
APP_WRAP_ORDER = 1
APP_WRAP_NAME = "VercelAnalytics"

# Browser registry populated by the JSX bridge.
BROWSER_API = "window.__reflexVA"

# ``mode`` values accepted by @vercel/analytics. ``auto`` is resolved on the
# Python side from the Reflex run mode (``reflex run`` vs ``--env prod``).
MODES = ("auto", "development", "production")
MODE_AUTO = "auto"
MODE_DEVELOPMENT = "development"
MODE_PRODUCTION = "production"

# Custom event limits documented by Vercel: names, property keys and property
# values are capped at 255 characters; nested values are rejected.
MAX_EVENT_NAME_LENGTH = 255
MAX_PROPERTY_KEY_LENGTH = 255
MAX_PROPERTY_VALUE_LENGTH = 255
