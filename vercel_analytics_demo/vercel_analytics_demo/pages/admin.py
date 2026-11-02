"""An excluded route: no page view is reported here (exclude_paths = ["/admin/*"])."""

from __future__ import annotations

import reflex as rx
import reflex_vercel_analytics as rva

from ..layout import page_shell, section


def admin() -> rx.Component:
    return page_shell(
        "Admin panel (excluded)",
        "/admin/* is in exclude_paths: the navigation shows up in the log as dropped and nothing is queued.",
        section(
            "Events on an excluded route",
            rx.text(
                "Custom events fired here are still handed to the SDK, but beforeSend drops them "
                "because the page URL is excluded.",
                size="2",
            ),
            rx.button(
                "Track 'Admin Action'", variant="soft", on_click=rva.track("Admin Action", {"area": "panel"})
            ),
            icon="lock",
        ),
    )


rx.page(route="/admin/panel", title="Admin | Vercel Analytics demo")(admin)
