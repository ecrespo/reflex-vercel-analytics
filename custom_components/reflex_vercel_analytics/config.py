"""Configuration for Vercel Web Analytics, loaded from a file and/or the environment.

The usual setup is a ``vercel_analytics.toml`` next to ``rxconfig.py``::

    mode = "auto"                  # development under `reflex run`, production with --env prod
    debug = true                   # console logging in development mode
    exclude_paths = ["/admin/*"]   # never report these routes
    include_search = false         # strip "?query" from reported URLs
    redact_search_params = ["token", "email"]

The same keys can live under ``[vercel_analytics]`` in that file, under
``[tool.reflex-vercel-analytics]`` in ``pyproject.toml``, or in a JSON file.
Environment variables named ``VERCEL_ANALYTICS_<FIELD>`` override single
fields::

    VERCEL_ANALYTICS_MODE=production reflex run --env prod

Vercel's own build variables are honoured too: ``VERCEL_OBSERVABILITY_CLIENT_CONFIG``
(the JSON with the Resilient Intake paths Vercel passes at build time) and
``VERCEL_OBSERVABILITY_BASEPATH`` fill ``client_config`` and ``base_path`` when
those are not set explicitly, so a Reflex frontend exported on Vercel picks up
the same script and endpoints a Next.js app would.
"""

from __future__ import annotations

import dataclasses
import json
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .constants import (
    DEFAULT_CONFIG_FILENAME,
    ENV_CONFIG_PATH,
    ENV_PREFIX,
    ENV_VERCEL_BASEPATH,
    ENV_VERCEL_CLIENT_CONFIG,
    MODE_AUTO,
    MODE_DEVELOPMENT,
    MODE_PRODUCTION,
    MODES,
    PYPROJECT_TABLE,
    TOML_TABLE,
)

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised on 3.10 only
    import tomli as tomllib


class ConfigError(ValueError):
    """Raised for an invalid Vercel Analytics configuration."""


_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off", ""}

# Fields parsed from environment variables as booleans / comma separated lists.
_BOOL_FIELDS = frozenset({"enabled", "debug", "track_page_views", "include_search", "respect_do_not_track"})
_LIST_FIELDS = frozenset({"exclude_paths", "redact_search_params"})


def _parse_bool(name: str, raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    text = str(raw).strip().lower()
    if text in _TRUE:
        return True
    if text in _FALSE:
        return False
    raise ConfigError(f"{name}: expected a boolean, got {raw!r}")


def _parse_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [item.strip() for item in raw.split(",") if item.strip()]
    return [str(item) for item in raw]


def _optional_str(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


@dataclass
class VercelAnalyticsConfig:
    """Everything the ``vercel_analytics`` component needs to inject the script."""

    # Master switch. When False nothing is injected and every action is a no-op.
    enabled: bool = True
    # ``auto`` (resolved from the Reflex run mode), ``development`` or ``production``.
    # In development mode the package loads Vercel's debug script, which only logs
    # events to the browser console and never sends anything.
    mode: str = MODE_AUTO
    # Console logging in development mode (None: the package default, which is on).
    debug: bool | None = None
    # Load the analytics script from another URL (proxy, Resilient Intake path).
    script_src: str | None = None
    # Project DSN. Only needed when the script is not served by the Vercel deployment itself.
    dsn: str | None = None
    # Report custom events / page views / sessions to other URLs (multi-app domains, proxies).
    event_endpoint: str | None = None
    view_endpoint: str | None = None
    session_endpoint: str | None = None
    # Deprecated in @vercel/analytics 2.x, still honoured: single endpoint for everything.
    endpoint: str | None = None
    # Base path for the script and endpoints (``<base_path>/insights/...``).
    base_path: str | None = None
    # JSON with default client options, the shape of VERCEL_OBSERVABILITY_CLIENT_CONFIG:
    # ``{"analytics": {"scriptSrc": "...", "eventEndpoint": "...", "viewEndpoint": "..."}}``.
    client_config: str | None = None
    # Send a page view with the route template on every client-side navigation.
    # When False the injected script tracks pushState changes on its own.
    track_page_views: bool = True
    # Keep ``?query`` in the reported URL (``beforeSend`` strips it when False).
    include_search: bool = True
    # Query parameters removed from every reported URL (``?token=...`` -> ``?token=[redacted]``).
    redact_search_params: list[str] = field(default_factory=list)
    # Routes never reported. ``/admin`` is exact, ``/admin/*`` is a prefix.
    exclude_paths: list[str] = field(default_factory=list)
    # Do not inject when the browser sends Do-Not-Track or Global Privacy Control.
    respect_do_not_track: bool = False
    # Where the values came from (for diagnostics; not a config field).
    source: str | None = field(default=None, compare=False)

    def __post_init__(self) -> None:
        self.exclude_paths = _parse_list(self.exclude_paths)
        self.redact_search_params = _parse_list(self.redact_search_params)
        for name in ("script_src", "dsn", "event_endpoint", "view_endpoint", "session_endpoint", "endpoint"):
            setattr(self, name, _optional_str(getattr(self, name)))
        self.base_path = _optional_str(self.base_path)
        self.client_config = _optional_str(self.client_config)
        self.mode = str(self.mode).strip().lower() or MODE_AUTO
        self.validate()

    # ------------------------------------------------------------ validation
    def validate(self) -> None:
        """Raise :class:`ConfigError` on malformed values."""
        if self.mode not in MODES:
            raise ConfigError(f"mode: expected one of {list(MODES)}, got {self.mode!r}")
        for path in self.exclude_paths:
            if not path.startswith("/"):
                raise ConfigError(f"exclude_paths: {path!r} must start with '/'")
        if self.client_config is not None:
            try:
                parsed = json.loads(self.client_config)
            except json.JSONDecodeError as error:
                raise ConfigError(f"client_config: expected JSON ({error})") from error
            if not isinstance(parsed, Mapping):
                raise ConfigError("client_config: expected a JSON object")

    # --------------------------------------------------------------- loaders
    @classmethod
    def field_names(cls) -> set[str]:
        return {f.name for f in dataclasses.fields(cls)} - {"source"}

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any], *, source: str | None = None) -> VercelAnalyticsConfig:
        """Build a config from a plain dict, rejecting unknown keys (typos)."""
        unknown = sorted(set(data) - cls.field_names())
        if unknown:
            raise ConfigError(
                f"{source or 'config'}: unknown keys {unknown}; valid keys are {sorted(cls.field_names())}"
            )
        return cls(**dict(data), source=source)

    @classmethod
    def from_file(cls, path: str | os.PathLike[str]) -> VercelAnalyticsConfig:
        """Load a ``.toml`` or ``.json`` file.

        For TOML the keys may be top level or under ``[vercel_analytics]``; a
        ``pyproject.toml`` uses ``[tool.reflex-vercel-analytics]``.
        """
        file = Path(path)
        if not file.is_file():
            raise ConfigError(f"Vercel Analytics config file not found: {file}")
        if file.suffix.lower() == ".json":
            data = json.loads(file.read_text(encoding="utf-8"))
        else:
            data = tomllib.loads(file.read_text(encoding="utf-8"))
            if file.name == "pyproject.toml":
                for key in PYPROJECT_TABLE:
                    data = data.get(key, {})
            elif TOML_TABLE in data and isinstance(data[TOML_TABLE], dict):
                data = data[TOML_TABLE]
        if not isinstance(data, Mapping):
            raise ConfigError(f"{file}: expected a table/object at the top level")
        return cls.from_mapping(data, source=str(file))

    def with_env(self, environ: Mapping[str, str] | None = None) -> VercelAnalyticsConfig:
        """Return a copy with ``VERCEL_ANALYTICS_<FIELD>`` and Vercel build variables applied."""
        environ = os.environ if environ is None else environ
        changes: dict[str, Any] = {}
        for name in sorted(self.field_names()):
            raw = environ.get(ENV_PREFIX + name.upper())
            if raw is None:
                continue
            if name in _BOOL_FIELDS:
                changes[name] = _parse_bool(ENV_PREFIX + name.upper(), raw)
            elif name in _LIST_FIELDS:
                changes[name] = _parse_list(raw)
            else:
                changes[name] = raw.strip() or None
        # Vercel's own build-time configuration, unless the file/env already set it.
        if (
            "client_config" not in changes
            and self.client_config is None
            and environ.get(ENV_VERCEL_CLIENT_CONFIG)
        ):
            changes["client_config"] = environ[ENV_VERCEL_CLIENT_CONFIG]
        if "base_path" not in changes and self.base_path is None and environ.get(ENV_VERCEL_BASEPATH):
            changes["base_path"] = environ[ENV_VERCEL_BASEPATH]
        if not changes:
            return self
        source = f"{self.source or 'defaults'} + env"
        merged = {f: getattr(self, f) for f in self.field_names()}
        merged.update(changes)
        return type(self)(**merged, source=source)

    # ------------------------------------------------------------ rendering
    def effective_mode(self, prod: bool | None = None) -> str:
        """``mode`` with ``auto`` resolved from the Reflex run mode."""
        if self.mode != MODE_AUTO:
            return self.mode
        return MODE_PRODUCTION if (_is_prod_mode() if prod is None else prod) else MODE_DEVELOPMENT

    def to_props(self, *, prod: bool | None = None) -> dict[str, Any]:
        """Props for :func:`reflex_vercel_analytics.vercel_analytics`."""
        props: dict[str, Any] = {
            "enabled": self.enabled,
            "mode": self.effective_mode(prod),
            "track_page_views": self.track_page_views,
            "include_search": self.include_search,
            "respect_do_not_track": self.respect_do_not_track,
        }
        if self.debug is not None:
            props["debug"] = self.debug
        for name in ("script_src", "dsn", "event_endpoint", "view_endpoint", "session_endpoint", "endpoint"):
            value = getattr(self, name)
            if value:
                props[name] = value
        if self.base_path:
            props["base_path"] = self.base_path
        if self.client_config:
            props["config_string"] = self.client_config
        if self.exclude_paths:
            props["exclude_paths"] = list(self.exclude_paths)
        if self.redact_search_params:
            props["redact_search_params"] = list(self.redact_search_params)
        return props


def _is_prod_mode() -> bool:
    try:
        from reflex.utils.exec import is_prod_mode
    except ImportError:  # pragma: no cover - very old/new Reflex
        return os.environ.get("REFLEX_ENV_MODE", "dev").lower() == "prod"
    return is_prod_mode()


def find_config_file(start: str | os.PathLike[str] | None = None) -> Path | None:
    """The config file that :func:`load_config` would use, if any.

    Order: ``$VERCEL_ANALYTICS_CONFIG``, ``vercel_analytics.toml`` in the app
    directory, then ``pyproject.toml`` if it has ``[tool.reflex-vercel-analytics]``.
    """
    env_path = os.environ.get(ENV_CONFIG_PATH)
    if env_path:
        return Path(env_path)
    base = Path(start) if start is not None else Path.cwd()
    candidate = base / DEFAULT_CONFIG_FILENAME
    if candidate.is_file():
        return candidate
    pyproject = base / "pyproject.toml"
    if pyproject.is_file():
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError:
            return None
        if data.get(PYPROJECT_TABLE[0], {}).get(PYPROJECT_TABLE[1]) is not None:
            return pyproject
    return None


def load_config(
    path: str | os.PathLike[str] | None = None,
    *,
    env: bool = True,
    environ: Mapping[str, str] | None = None,
) -> VercelAnalyticsConfig:
    """Load the Vercel Analytics config for the current Reflex app.

    Args:
        path: An explicit file. Defaults to :func:`find_config_file`.
        env: Apply ``VERCEL_ANALYTICS_*`` (and Vercel build) overrides on top of the file.
        environ: Mapping used instead of ``os.environ`` (tests).

    Returns:
        The merged, validated configuration (the defaults if nothing is set).
    """
    file = Path(path) if path is not None else find_config_file()
    config = VercelAnalyticsConfig.from_file(file) if file is not None else VercelAnalyticsConfig()
    return config.with_env(environ) if env else config
