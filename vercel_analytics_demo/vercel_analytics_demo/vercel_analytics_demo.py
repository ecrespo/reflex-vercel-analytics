"""reflex-vercel-analytics demo app.

Six pages (home, events, a dynamic route, privacy, configuration and an
excluded admin route) plus a live log of every page view and custom event the
component issues.

    cd vercel_analytics_demo && uv run reflex run

The tracker is configured by vercel_analytics.toml in this directory. It ships
with mode = "development", so the debug script only logs to the browser
console; run with VERCEL_ANALYTICS_MODE=production on a Vercel deployment to
send real data.
"""

from __future__ import annotations

import reflex as rx
import reflex_vercel_analytics as rva

from . import pages  # noqa: F401  - importing the modules registers their @rx.page
from .state import LogState

app = rx.App(
    style={"font_family": "Inter, ui-sans-serif, system-ui, sans-serif"},
)

# One component around every page. The event triggers feed the log panel.
rva.install(
    app,
    on_ready=LogState.on_ready,
    on_page_view=LogState.on_page_view,
    on_event=LogState.on_event,
)
