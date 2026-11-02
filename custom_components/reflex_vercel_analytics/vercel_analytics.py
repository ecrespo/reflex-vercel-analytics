"""Reflex custom component for Vercel Web Analytics, built on @vercel/analytics.

The React side lives in ``vercel_analytics.jsx``, a small bridge shipped with
this package as a shared asset. It renders the ``Analytics`` component from
``@vercel/analytics/react`` (the framework-agnostic adapter; the ``/next``
entry point needs ``next/navigation`` and cannot run in a Reflex app, which is
built with Vite and React Router), feeds it the current route template and
path from React Router, installs a ``beforeSend`` filter for excluded paths,
query strings and opt-out, and exposes ``window.__reflexVA`` for the helpers in
``actions.py``.

Example:
    ```python
    import reflex as rx
    import reflex_vercel_analytics as rva

    app = rx.App()
    rva.install(app)  # reads vercel_analytics.toml next to rxconfig.py, if present

    def index():
        return rx.button("Sign up", on_click=rva.track("Signup", {"method": "email"}))
    ```
"""

from __future__ import annotations

import os
from typing import Any

import reflex as rx
from reflex.components.component import Component
from reflex.event import passthrough_event_spec
from reflex.vars.base import Var

from .config import VercelAnalyticsConfig, load_config
from .constants import APP_WRAP_NAME, APP_WRAP_ORDER, VERCEL_ANALYTICS_VERSION

_JSX_ASSET = rx.asset("vercel_analytics.jsx", shared=True)

ConfigSource = VercelAnalyticsConfig | str | os.PathLike[str] | None


class VercelAnalytics(Component):
    """Injects the Vercel Web Analytics script and tracks page views.

    It renders its children (if any) and nothing else, so it can sit anywhere
    on a page or wrap the whole app through :func:`install`. Mount it once:
    the script is injected once per page load, later instances are no-ops.
    """

    library = _JSX_ASSET.importable_path

    tag = "ReflexVercelAnalytics"

    lib_dependencies: list[str] = [f"@vercel/analytics@{VERCEL_ANALYTICS_VERSION}"]

    # ------------------------------------------------------------- behaviour
    # Master switch. When False nothing is injected and every action is a no-op.
    enabled: Var[bool]

    # ``development`` loads Vercel's debug script (console only, nothing is sent);
    # ``production`` loads the real one. ``auto`` lets the SDK guess from NODE_ENV.
    mode: Var[str]

    # Console logging in development mode.
    debug: Var[bool]

    # Send a page view with the React Router route template on every client-side
    # navigation. When False the injected script tracks pushState on its own.
    track_page_views: Var[bool]

    # Keep ``?query`` in the reported URL. When False ``beforeSend`` strips it.
    include_search: Var[bool]

    # Query parameters whose value is replaced by ``[redacted]`` in reported URLs.
    redact_search_params: Var[list[str]]

    # Routes never reported. ``/admin`` is exact, ``/admin/*`` a prefix.
    exclude_paths: Var[list[str]]

    # Skip injection when the browser sends Do-Not-Track or Global Privacy Control.
    respect_do_not_track: Var[bool]

    # ----------------------------------------------------------------- script
    # Load the analytics script from another URL.
    script_src: Var[str]

    # Project DSN, needed when the script is not served by the Vercel deployment.
    dsn: Var[str]

    # Report events / page views / sessions somewhere else (multi-app domains, proxies).
    event_endpoint: Var[str]
    view_endpoint: Var[str]
    session_endpoint: Var[str]

    # Deprecated single endpoint (@vercel/analytics 1.x), still honoured.
    endpoint: Var[str]

    # Base path for script and endpoints (``<base_path>/insights/...``).
    base_path: Var[str]

    # JSON string with default client options (``VERCEL_OBSERVABILITY_CLIENT_CONFIG``).
    config_string: Var[str]

    # SDK label reported to Vercel (``@vercel/analytics/<framework>``).
    framework: Var[str]

    # -------------------------------------------------------------- events
    # Fired once after mounting with the tracker status:
    # ``{injected, disabled, disabled_reason, mode, opted_out, last_path, last_route, script_src}``.
    on_ready: rx.EventHandler[passthrough_event_spec(dict[str, Any])]

    # Fired after each automatic page view: ``{path, route, url}``.
    on_page_view: rx.EventHandler[passthrough_event_spec(dict[str, Any])]

    # Fired for every call that reaches ``window.va``: ``{type, name, data, url, dropped, timestamp}``.
    # Leave it unset in production: each call is a round trip to the backend.
    on_event: rx.EventHandler[passthrough_event_spec(dict[str, Any])]

    @classmethod
    def create(cls, *children: Any, config: Any = None, **props: Any) -> Component:
        """Create the component, merging in a :class:`VercelAnalyticsConfig`.

        Args:
            *children: Rendered as-is (handy when wrapping the app).
            config: A config object, a path to a ``.toml``/``.json`` file, ``None``
                to auto-discover ``vercel_analytics.toml`` (plus ``VERCEL_ANALYTICS_*``
                env vars), or ``False`` to rely on explicit props only.
            **props: Component props; they win over values from the config.

        Returns:
            The component.
        """
        if config is not False:
            resolved = config if isinstance(config, VercelAnalyticsConfig) else load_config(config)
            props = {**resolved.to_props(), **props}
        return super().create(*children, **props)


vercel_analytics = VercelAnalytics.create


def install(
    app: rx.App,
    config: ConfigSource | bool = None,
    *,
    order: int = APP_WRAP_ORDER,
    **props: Any,
) -> rx.App:
    """Mount Vercel Web Analytics around every page of ``app``.

    The component is added to ``app.extra_app_wraps``, so it is rendered once
    for the whole app and survives navigation (no re-injection per page).

    Args:
        app: The Reflex app.
        config: See :meth:`VercelAnalytics.create`.
        order: Position among the app wraps (lower = closer to the pages).
        **props: Extra component props, including event triggers such as
            ``on_page_view=State.handler``.

    Returns:
        The same app, for chaining.
    """
    resolved: VercelAnalyticsConfig | bool
    resolved = config if config is False or isinstance(config, VercelAnalyticsConfig) else load_config(config)

    def _wrap(_stateful: bool) -> Component:
        return VercelAnalytics.create(config=resolved, **props)

    app.extra_app_wraps[(order, APP_WRAP_NAME)] = _wrap
    return app
