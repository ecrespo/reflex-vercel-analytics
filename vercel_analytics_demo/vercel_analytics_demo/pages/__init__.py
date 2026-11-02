"""Importing the page modules registers their @rx.page routes."""

from . import admin, configuration, events, home, post, privacy

__all__ = ["admin", "configuration", "events", "home", "post", "privacy"]
