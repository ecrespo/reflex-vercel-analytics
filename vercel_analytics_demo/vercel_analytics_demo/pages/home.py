"""Landing page: how the component is mounted and the page views it records."""

from __future__ import annotations

import reflex as rx

from ..layout import page_shell, section
from ..state import LogState

SNIPPET = """import reflex as rx
import reflex_vercel_analytics as rva

app = rx.App()
# Reads vercel_analytics.toml (+ VERCEL_ANALYTICS_* env vars) and wraps
# every page: one script injection, one page view per navigation.
rva.install(app)
"""


def index() -> rx.Component:
    return page_shell(
        "Vercel Web Analytics in Reflex",
        "@vercel/analytics wrapped as a Reflex component: config file, automatic page views "
        "with route templates, custom events from Python, beforeSend filtering and opt-out.",
        section(
            "One-line setup",
            rx.code_block(SNIPPET, language="python", width="100%"),
            rx.text(
                "Move between the pages in the menu: every route change sends a page view with the ",
                rx.code("path"),
                " and the ",
                rx.code("route"),
                " template. /admin/panel is in exclude_paths and is not reported.",
                size="2",
            ),
            icon="plug",
        ),
        section(
            "Tracker status",
            rx.code_block(LogState.status_json, language="json", width="100%"),
            rx.button("Refresh status", size="2", variant="soft", on_click=LogState.refresh_status),
            icon="activity",
        ),
        section(
            "Recorded page views",
            rx.cond(
                LogState.page_views.length() > 0,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Path"),
                            rx.table.column_header_cell("Route"),
                            rx.table.column_header_cell("Reported URL"),
                        )
                    ),
                    rx.table.body(
                        rx.foreach(
                            LogState.page_views,
                            lambda pv: rx.table.row(
                                rx.table.cell(rx.code(pv["path"])),
                                rx.table.cell(rx.code(pv["route"])),
                                rx.table.cell(pv["url"], word_break="break-all"),
                                class_name="page-view-row",
                            ),
                        )
                    ),
                    width="100%",
                    size="1",
                ),
                rx.text("None yet.", color=rx.color("gray", 10), size="2"),
            ),
            icon="route",
        ),
    )


rx.page(route="/", title="Home | Vercel Analytics demo")(index)
