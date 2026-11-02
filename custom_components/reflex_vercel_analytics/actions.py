"""Send Vercel Web Analytics events from Python.

Every helper returns an ``rx.call_script`` event that talks to the
``window.__reflexVA`` API registered by the component, so it can be used
directly as a trigger or returned/yielded from an event handler::

    rx.button("Buy", on_click=rva.track("Purchase", {"plan": "pro"}))

    class State(rx.State):
        @rx.event
        def checkout(self):
            ...
            return rva.track("Checkout", {"total": self.total, "currency": "USD"})

Calls made before the script is injected are queued by @vercel/analytics
itself (``window.vaq``); when tracking is disabled (``enabled=False``,
Do-Not-Track, opt-out) they are no-ops. Arguments must be plain Python values:
read State values inside a handler and return the helper from there.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import reflex as rx
from reflex.event import EventSpec

from .constants import (
    BROWSER_API,
    MAX_EVENT_NAME_LENGTH,
    MAX_PROPERTY_KEY_LENGTH,
    MAX_PROPERTY_VALUE_LENGTH,
)

PropertyValue = str | int | float | bool | None
Properties = Mapping[str, PropertyValue]


def validate_event_name(name: str) -> str:
    """Return ``name`` if Vercel accepts it as a custom event name, else raise ``ValueError``."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Event name must be a non-empty string")
    if len(name) > MAX_EVENT_NAME_LENGTH:
        raise ValueError(f"Event name {name[:20]!r}... is longer than {MAX_EVENT_NAME_LENGTH} characters")
    return name


def validate_properties(properties: Mapping[str, Any] | None) -> dict[str, PropertyValue]:
    """Return a flat dict of the properties Vercel accepts; raise ``ValueError`` otherwise.

    Only strings, numbers, booleans and ``None`` are allowed (nested objects
    and lists are rejected by the SDK). Keys and string values are capped at
    255 characters. ``None`` values are dropped.
    """
    clean: dict[str, PropertyValue] = {}
    for key, value in (properties or {}).items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"Property keys must be non-empty strings, got {key!r}")
        if len(key) > MAX_PROPERTY_KEY_LENGTH:
            raise ValueError(
                f"Property key {key[:20]!r}... is longer than {MAX_PROPERTY_KEY_LENGTH} characters"
            )
        if value is None:
            continue
        if isinstance(value, bool | int | float):
            clean[key] = value
        elif isinstance(value, str):
            if len(value) > MAX_PROPERTY_VALUE_LENGTH:
                raise ValueError(f"Property {key!r} is longer than {MAX_PROPERTY_VALUE_LENGTH} characters")
            clean[key] = value
        else:
            raise ValueError(
                f"Property {key!r}: nested objects are not supported, "
                f"only strings, numbers, booleans and null (got {type(value).__name__})"
            )
    return clean


def _call(method: str, *args: Any, callback: Any = None) -> EventSpec:
    js_args = ", ".join(json.dumps(arg, default=str) for arg in args)
    script = (
        f"(() => {{ const va = {BROWSER_API};"
        " if (!va) { console.warn('reflex-vercel-analytics: component not mounted'); return null; }"
        f" return va.{method}({js_args}); }})()"
    )
    if callback is not None:
        return rx.call_script(script, callback=callback)
    return rx.call_script(script)


# ------------------------------------------------------------------ events
def track(
    name: str,
    properties: Properties | None = None,
    /,
    *,
    flags: list[str | dict[str, Any]] | dict[str, Any] | None = None,
    **extra: PropertyValue,
) -> EventSpec:
    """A custom event: ``track("Signup")`` or ``track("Play Video", {"title": "intro"})``.

    ``flags`` attaches Vercel feature-flag values to the event (Flags Explorer).
    """
    props = validate_properties({**(properties or {}), **extra})
    return _call("track", validate_event_name(name), props, flags)


def page_view(path: str | None = None, route: str | None = None) -> EventSpec:
    """A manual page view (virtual pages, modals, wizard steps).

    ``path`` defaults to the current location; ``route`` is the route template
    (``/post/[pid]``) shown in the Vercel dashboard and defaults to ``path``.
    """
    return _call("pageView", path, route)


# ----------------------------------------------------------------- privacy
def opt_out() -> EventSpec:
    """Stop reporting from this browser (remembered in localStorage): ``beforeSend`` drops every event."""
    return _call("optOut")


def opt_in() -> EventSpec:
    """Undo :func:`opt_out`."""
    return _call("optIn")


# ----------------------------------------------------------------- reading
def get_status(callback: Any) -> EventSpec:
    """Send the tracker status dict (same shape as ``on_ready``) to ``callback``."""
    return _call("status", callback=callback)
