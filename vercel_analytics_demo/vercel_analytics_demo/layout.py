"""Shell shared by every page: navbar and the live event log."""

from __future__ import annotations

import reflex as rx

from .state import LogState

PAGES = [
    ("/", "Home"),
    ("/events", "Events"),
    ("/post/42", "Dynamic route"),
    ("/privacy", "Privacy"),
    ("/configuration", "Configuration"),
    ("/admin/panel", "Admin (excluded)"),
]


def navbar() -> rx.Component:
    return rx.hstack(
        rx.hstack(
            rx.icon("triangle", size=20, color=rx.color("gray", 12)),
            rx.heading("reflex-vercel-analytics", size="4"),
            align="center",
            spacing="2",
        ),
        rx.spacer(),
        rx.hstack(
            *[rx.link(label, href=href, size="2", weight="medium") for href, label in PAGES],
            spacing="5",
            wrap="wrap",
        ),
        rx.color_mode.button(size="1"),
        width="100%",
        align="center",
        spacing="4",
        padding="1rem 1.5rem",
        border_bottom=f"1px solid {rx.color('gray', 5)}",
        background=rx.color("gray", 1),
        position="sticky",
        top="0",
        z_index="50",
    )


def _type_badge(kind: rx.Var[str]) -> rx.Component:
    return rx.badge(
        kind,
        color_scheme=rx.match(kind, ("event", "blue"), ("pageview", "green"), "gray"),
        variant="soft",
    )


def event_log() -> rx.Component:
    """Every page view and custom event the bridge issued, newest first (reported by `on_event`)."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("terminal", size=18),
                rx.heading("Analytics calls", size="3"),
                rx.badge(LogState.event_count.to_string(), variant="surface"),
                rx.spacer(),
                rx.button("Clear", size="1", variant="ghost", on_click=LogState.clear),
                width="100%",
                align="center",
            ),
            rx.text(
                "In development mode the debug script prints each call to the browser console "
                "and nothing is sent to Vercel.",
                size="1",
                color=rx.color("gray", 10),
            ),
            rx.scroll_area(
                rx.vstack(
                    rx.foreach(
                        LogState.events,
                        lambda entry: rx.box(
                            rx.hstack(
                                rx.text(entry["n"], size="1", color=rx.color("gray", 9), width="2rem"),
                                _type_badge(entry["type"]),
                                rx.code(entry["target"], size="1"),
                                rx.cond(
                                    entry["dropped"] != "",
                                    rx.badge("dropped", color_scheme="red", variant="soft"),
                                ),
                                rx.spacer(),
                                rx.text(entry["source"], size="1", color=rx.color("gray", 9)),
                                rx.text(entry["time"], size="1", color=rx.color("gray", 9)),
                                width="100%",
                                align="center",
                                spacing="2",
                            ),
                            rx.cond(
                                entry["detail"] != "",
                                rx.text(
                                    entry["detail"],
                                    size="1",
                                    font_family="ui-monospace, monospace",
                                    color=rx.color("gray", 11),
                                    white_space="pre-wrap",
                                    word_break="break-all",
                                    padding_left="2rem",
                                ),
                            ),
                            padding_y="6px",
                            border_bottom=f"1px dashed {rx.color('gray', 4)}",
                            width="100%",
                            class_name="analytics-call",
                        ),
                    ),
                    spacing="0",
                    width="100%",
                ),
                type="auto",
                scrollbars="vertical",
                style={"height": "calc(100vh - 220px)"},
            ),
            width="100%",
            spacing="2",
        ),
        width="100%",
    )


def page_shell(title: str, description: str, *content: rx.Component) -> rx.Component:
    return rx.box(
        navbar(),
        rx.flex(
            rx.vstack(
                rx.heading(title, size="7"),
                rx.text(description, color=rx.color("gray", 11), size="3"),
                rx.divider(),
                *content,
                spacing="4",
                flex="1 1 520px",
                min_width="0",
            ),
            rx.box(event_log(), flex="0 1 460px", min_width="300px", position="sticky", top="80px"),
            gap="1.5rem",
            padding="1.5rem",
            align="start",
            wrap="wrap",
            max_width="1400px",
            margin="0 auto",
        ),
        min_height="100vh",
        background=rx.color("gray", 2),
    )


def section(title: str, *children: rx.Component, icon: str = "circle") -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon(icon, size=18, color=rx.color("gray", 11)),
                rx.heading(title, size="4"),
                align="center",
            ),
            *children,
            spacing="3",
            width="100%",
        ),
        width="100%",
    )
