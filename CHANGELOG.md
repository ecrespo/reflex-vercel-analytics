# Changelog

## 0.1.0 - 2026-11-02

First release.

- `VercelAnalytics` component (`vercel_analytics`) wrapping `@vercel/analytics` 2.0.1 (`Analytics` from
  `@vercel/analytics/react`) through a shared JSX bridge.
- `install(app)` mounts the component once in `app.extra_app_wraps`.
- `VercelAnalyticsConfig` and `load_config()`: `vercel_analytics.toml`, `[tool.reflex-vercel-analytics]` in
  `pyproject.toml` or JSON, validated, with `VERCEL_ANALYTICS_*` environment overrides and automatic pick-up of
  `VERCEL_OBSERVABILITY_CLIENT_CONFIG` / `VERCEL_OBSERVABILITY_BASEPATH`.
- `mode = "auto"` resolved from the Reflex run mode (`development` under `reflex run`, `production` with
  `--env prod` / `reflex export`).
- Automatic page views on React Router navigation with the route template (`/post/[pid]`), `exclude_paths`,
  `include_search` and `redact_search_params` enforced through `beforeSend`; the URL fragment is always
  stripped so tokens in `#access_token=...` never reach Vercel.
- Actions: `track` (with feature `flags`), `page_view`, `opt_out`, `opt_in`, `get_status`,
  `validate_event_name`, `validate_properties`.
- `respect_do_not_track`, and the `on_ready`, `on_page_view` and `on_event` triggers.
- Demo app with six pages and a live log of every page view and event.
- pre-commit hooks and `scripts/generate_pyi.py` (replaces `reflex component build`, removed in Reflex 0.10).
- CI: pre-commit, pytest on Python 3.10-3.13, build + `twine check`, smoke tests of the installed wheel and
  sdist (`scripts/smoke_test.py`), `.pyi` drift check and demo `reflex compile`.
- PyPI Trusted Publishing workflow: GitHub pre-releases (`vX.Y.ZrcN`) publish release candidates, releases
  publish final versions, manual runs are dry runs; every upload needs approval and is verified by installing
  it from PyPI. `scripts/check_release.py` validates tag, pre-release flag, changelog and that the version is
  unpublished; `scripts/prepublish.sh` runs the whole gate locally.
