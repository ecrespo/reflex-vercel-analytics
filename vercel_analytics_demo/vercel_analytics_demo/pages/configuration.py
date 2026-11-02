"""The configuration the demo loaded, and where it came from."""

from __future__ import annotations

import dataclasses
import json

import reflex as rx
import reflex_vercel_analytics as rva

from ..layout import page_shell, section

ENV_SNIPPET = """VERCEL_ANALYTICS_MODE=production reflex run --env prod
VERCEL_ANALYTICS_EXCLUDE_PATHS="/admin/*,/preview" reflex run
"""


class ConfigState(rx.State):
    @rx.var
    def loaded(self) -> str:
        config = rva.load_config()
        data = {f.name: getattr(config, f.name) for f in dataclasses.fields(config)}
        return json.dumps(data, indent=2, default=str)

    @rx.var
    def props(self) -> str:
        return json.dumps(rva.load_config().to_props(), indent=2, default=str)

    @rx.var
    def source(self) -> str:
        return str(rva.find_config_file() or "(defaults)")


def configuration() -> rx.Component:
    return page_shell(
        "Configuration",
        "rva.load_config() merges vercel_analytics.toml (or pyproject.toml / JSON) with "
        "VERCEL_ANALYTICS_* environment variables and validates the result at startup.",
        section(
            "Loaded config",
            rx.text("Source: ", rx.code(ConfigState.source), size="2"),
            rx.code_block(ConfigState.loaded, language="json", width="100%"),
            icon="file-cog",
        ),
        section(
            "Component props",
            rx.text("What the bridge receives (mode already resolved from the Reflex run mode):", size="2"),
            rx.code_block(ConfigState.props, language="json", width="100%"),
            icon="braces",
        ),
        section(
            "Environment overrides",
            rx.code_block(ENV_SNIPPET, language="bash", width="100%"),
            rx.text(
                "On Vercel, VERCEL_OBSERVABILITY_CLIENT_CONFIG and VERCEL_OBSERVABILITY_BASEPATH "
                "are picked up automatically at build time.",
                size="2",
                color=rx.color("gray", 11),
            ),
            icon="terminal",
        ),
    )


rx.page(route="/configuration", title="Configuration | Vercel Analytics demo")(configuration)
