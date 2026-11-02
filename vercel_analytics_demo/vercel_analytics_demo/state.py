"""Demo state: the event log, tracker status, the event form and the opt-out switch."""

from __future__ import annotations

import json
from typing import Any

import reflex as rx
import reflex_vercel_analytics as rva

MAX_LOG = 80

PRODUCTS: list[dict[str, Any]] = [
    {"sku": "SKU-ARE-01", "name": "Arepa reina pepiada", "price": 6.5},
    {"sku": "SKU-CAF-02", "name": "Guayoyo coffee", "price": 2.0},
    {"sku": "SKU-TEQ-03", "name": "Tequenos x12", "price": 9.0},
]


class LogState(rx.State):
    """Everything the component reports back to Python."""

    events: list[dict[str, str]] = []
    page_views: list[dict[str, str]] = []
    status: dict[str, Any] = {}
    event_count: int = 0

    @rx.event
    def on_event(self, payload: dict[str, Any]):
        self.event_count += 1
        kind = str(payload.get("type", ""))
        if kind == "event":
            target = str(payload.get("name", ""))
            detail = json.dumps(payload.get("data") or {}, ensure_ascii=False)
        else:
            target = str(payload.get("route") or payload.get("path") or "")
            detail = str(payload.get("url", ""))
        entry = {
            "n": str(self.event_count),
            "time": str(payload.get("timestamp", ""))[11:19],
            "type": kind,
            "source": str(payload.get("source", "")),
            "target": target,
            "detail": detail,
            "dropped": "yes" if payload.get("dropped") else "",
        }
        self.events = [entry, *self.events][:MAX_LOG]

    @rx.event
    def on_page_view(self, payload: dict[str, Any]):
        entry = {
            "path": str(payload.get("path", "")),
            "route": str(payload.get("route", "")),
            "url": str(payload.get("url", "")),
        }
        self.page_views = [entry, *self.page_views][:MAX_LOG]

    @rx.event
    def on_ready(self, status: dict[str, Any]):
        self.status = status

    @rx.event
    def refresh_status(self):
        return rva.get_status(LogState.on_ready)

    @rx.event
    def clear(self):
        self.events = []
        self.page_views = []
        self.event_count = 0

    @rx.var
    def status_json(self) -> str:
        return json.dumps(self.status, indent=2, ensure_ascii=False)

    @rx.var
    def custom_event_count(self) -> int:
        return sum(1 for entry in self.events if entry["type"] == "event")


class EventsState(rx.State):
    """Custom events typed in the form, validated in Python before they are sent."""

    name: str = "Newsletter Signup"
    param_key: str = "plan"
    param_value: str = "monthly"
    flag: str = ""
    error: str = ""
    virtual_step: int = 1

    @rx.event
    def set_name(self, value: str):
        self.name = value

    @rx.event
    def set_param_key(self, value: str):
        self.param_key = value.strip()

    @rx.event
    def set_param_value(self, value: str):
        self.param_value = value

    @rx.event
    def set_flag(self, value: str):
        self.flag = value.strip()

    @rx.event
    def send_custom(self):
        properties = {self.param_key: self.param_value} if self.param_key else {}
        try:
            rva.validate_event_name(self.name)
            rva.validate_properties(properties)
        except ValueError as error:
            self.error = str(error)
            return rx.toast.error(self.error)
        self.error = ""
        flags = [self.flag] if self.flag else None
        return [
            rva.track(self.name, properties, flags=flags),
            rx.toast.success(f"Event '{self.name}' tracked"),
        ]

    @rx.event
    def next_step(self):
        """A wizard step: a virtual page view with its own route template."""
        self.virtual_step = self.virtual_step % 3 + 1
        return rva.page_view(f"/events/wizard/step-{self.virtual_step}", route="/events/wizard/[step]")

    @rx.event
    def buy(self, sku: str):
        product = next(p for p in PRODUCTS if p["sku"] == sku)
        return rva.track("Purchase", {"sku": sku, "name": product["name"], "price": product["price"]})


class PrivacyState(rx.State):
    """Opt-out switch, remembered by the bridge in localStorage."""

    opted_out: bool = False

    @rx.event
    def toggle_opt_out(self, value: bool):
        self.opted_out = value
        return [rva.opt_out() if value else rva.opt_in(), LogState.refresh_status]

    @rx.event
    def sync_from_status(self):
        return rva.get_status(PrivacyState.receive_status)

    @rx.event
    def receive_status(self, status: dict[str, Any]):
        self.opted_out = bool(status.get("opted_out"))
