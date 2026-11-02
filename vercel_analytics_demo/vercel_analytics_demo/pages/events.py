"""Custom events, feature flags, a virtual page view and a tiny shop."""

from __future__ import annotations

import reflex as rx
import reflex_vercel_analytics as rva

from ..layout import page_shell, section
from ..state import PRODUCTS, EventsState

SNIPPET = """rx.button("Sign up", on_click=rva.track("Signup", {"method": "email"}))

class State(rx.State):
    @rx.event
    def pay(self):
        return rva.track("Purchase", {"sku": self.sku, "price": self.price})
"""


def _product(product: dict) -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text(product["name"], weight="bold"),
            rx.text(f"${product['price']:.2f}", size="2", color=rx.color("gray", 11)),
            rx.button("Buy", size="1", on_click=EventsState.buy(product["sku"]), width="100%"),
            spacing="2",
        ),
        flex="1 1 160px",
    )


def events() -> rx.Component:
    return page_shell(
        "Custom events",
        "rva.track() returns an rx.call_script event: use it as a trigger or return it from a handler. "
        "Names, keys and values are validated against Vercel's limits before anything is sent.",
        section(
            "From Python",
            rx.code_block(SNIPPET, language="python", width="100%"),
            rx.hstack(
                rx.button("Signup (trigger)", on_click=rva.track("Signup", {"method": "email"})),
                rx.button(
                    "Play Video",
                    variant="soft",
                    on_click=rva.track("Play Video", {"title": "intro", "seconds": 42, "autoplay": False}),
                ),
                spacing="3",
                wrap="wrap",
            ),
            icon="mouse-pointer-click",
        ),
        section(
            "Your own event",
            rx.hstack(
                rx.input(value=EventsState.name, on_change=EventsState.set_name, placeholder="Event name"),
                rx.input(value=EventsState.param_key, on_change=EventsState.set_param_key, placeholder="key"),
                rx.input(
                    value=EventsState.param_value, on_change=EventsState.set_param_value, placeholder="value"
                ),
                rx.input(
                    value=EventsState.flag, on_change=EventsState.set_flag, placeholder="flag (optional)"
                ),
                width="100%",
                wrap="wrap",
            ),
            rx.button("Track", on_click=EventsState.send_custom, id="track-custom"),
            rx.cond(
                EventsState.error != "",
                rx.callout(EventsState.error, icon="triangle-alert", color_scheme="red"),
            ),
            rx.text(
                "Try an empty name or a 300-character value: the error comes from Python, before the browser.",
                size="1",
                color=rx.color("gray", 10),
            ),
            icon="pencil",
        ),
        section(
            "Virtual page views",
            rx.text(
                "Modals and wizard steps are not navigations. rva.page_view(path, route) reports them "
                "with their own route template.",
                size="2",
            ),
            rx.hstack(
                rx.badge(f"step {EventsState.virtual_step}", variant="surface"),
                rx.button("Next step", variant="soft", on_click=EventsState.next_step),
                align="center",
            ),
            icon="layers",
        ),
        section(
            "Shop",
            rx.flex(*[_product(p) for p in PRODUCTS], gap="1rem", wrap="wrap", width="100%"),
            icon="shopping-cart",
        ),
    )


rx.page(route="/events", title="Events | Vercel Analytics demo")(events)
