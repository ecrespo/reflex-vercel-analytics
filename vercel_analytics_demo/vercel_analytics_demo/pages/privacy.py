"""Opt-out, Do-Not-Track and the beforeSend filters."""

from __future__ import annotations

import reflex as rx

from ..layout import page_shell, section
from ..state import PrivacyState

SNIPPET = """# vercel_analytics.toml
exclude_paths = ["/admin/*"]             # never reported
include_search = false                   # or keep it and redact:
redact_search_params = ["token", "email"]
respect_do_not_track = true              # do not inject when DNT / GPC is on
"""


def privacy() -> rx.Component:
    return page_shell(
        "Privacy",
        "A beforeSend hook installed by the bridge drops excluded routes and opted-out visitors, "
        "and strips or redacts query strings before the script sends anything.",
        section(
            "Opt-out",
            rx.hstack(
                rx.switch(
                    checked=PrivacyState.opted_out, on_change=PrivacyState.toggle_opt_out, id="opt-out"
                ),
                rx.text("Stop reporting from this browser (remembered in localStorage)"),
                align="center",
                spacing="3",
            ),
            rx.text(
                "While opted out, page views and events still show up in the log on the right, "
                "flagged as dropped: beforeSend returns null for them.",
                size="2",
                color=rx.color("gray", 11),
            ),
            icon="shield",
        ),
        section(
            "Query strings",
            rx.text(
                "Open ",
                rx.link("/privacy?token=secret&page=2", href="/privacy?token=secret&page=2"),
                ": the reported URL keeps page=2 and replaces token with [redacted].",
                size="2",
            ),
            rx.code_block(SNIPPET, language="toml", width="100%"),
            icon="eye-off",
        ),
    )


rx.page(
    route="/privacy",
    title="Privacy | Vercel Analytics demo",
    on_load=PrivacyState.sync_from_status,
)(privacy)
