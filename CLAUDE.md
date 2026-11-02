# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`reflex-vercel-analytics` is a Reflex custom component (published to PyPI) that wraps **@vercel/analytics 2.0.1** to add Vercel Web Analytics to Reflex apps. The importable package is `reflex_vercel_analytics` under `custom_components/` (setuptools `packages.find where = ["custom_components"]`). `vercel_analytics_demo/` is a separate Reflex app that exercises it.

## Commands

```bash
uv sync && uv pip install -e .          # dev setup (package must be installed editable for the demo/tests)
uv run pre-commit install --install-hooks   # hooks: file checks, ruff, uv-lock on commit; pytest on pre-push
uv run pre-commit run --all-files
uv run pytest                            # all tests (testpaths = tests, -q --strict-markers)
uv run pytest tests/test_config.py::test_name   # single test
uv run ruff check .                      # lint (line-length 110, py310 target; .pyi excluded)
uv run ruff format .
uv run --python 3.13 python scripts/generate_pyi.py    # regenerates vercel_analytics.pyi (`reflex component build` is gone in Reflex 0.10)
uv build                                 # sdist/wheel into dist/
scripts/prepublish.sh [vX.Y.Z]           # local pre-publication gate: CI checks + build + smoke tests, no upload
uv run python scripts/check_release.py --tag vX.Y.Z --check-pypi  # release metadata guard used by publish.yml

cd vercel_analytics_demo && uv run reflex run   # demo; must run from this dir (config discovery is cwd-relative)
VERCEL_ANALYTICS_MODE=production uv run reflex run --env prod   # production script
```

## Architecture

Three layers that must stay in sync:

1. **Config (`config.py`)** — `VercelAnalyticsConfig` dataclass, validated in `__post_init__` (`mode` in `MODES`, `exclude_paths` must start with `/`, `client_config` must be a JSON object, unknown keys rejected). `load_config()` / `find_config_file()` resolve in order: `$VERCEL_ANALYTICS_CONFIG` → `vercel_analytics.toml` in the app dir → `[tool.reflex-vercel-analytics]` in `pyproject.toml` (JSON also supported). `with_env()` then overlays `VERCEL_ANALYTICS_<FIELD>` env vars (bools/lists parsed) and, if not set otherwise, Vercel's `VERCEL_OBSERVABILITY_CLIENT_CONFIG` → `client_config` and `VERCEL_OBSERVABILITY_BASEPATH` → `base_path`. `to_props()` converts to component props; `effective_mode()` resolves `auto` from Reflex's prod mode so the bridge never depends on `NODE_ENV`.

2. **Component (`vercel_analytics.py`)** — `VercelAnalytics` points `library` at the bundled `vercel_analytics.jsx` via `rx.asset(..., shared=True)` and pins `@vercel/analytics@{VERCEL_ANALYTICS_VERSION}` in `lib_dependencies`. `create(config=...)` merges config props under explicit props (explicit wins; `config=False` disables loading). `install(app)` registers it in `app.extra_app_wraps` so it mounts once above all pages and survives navigation.

3. **JSX bridge (`vercel_analytics.jsx`)** — `ReflexVercelAnalytics` renders `<Analytics>` from `@vercel/analytics/react` (not `/next`: that needs `next/navigation`; Reflex uses Vite + React Router) with `route={null}` so the script's own pushState tracking is disabled, computes `route`/`path` from `useLocation()`/`useParams()` + `computeRoute()` and calls `pageview()` once per navigation, installs a stable `beforeSend` (opt-out, `excludePaths`, `includeSearch`, `redactSearchParams`), and exposes an imperative API at `window.__reflexVA` (`track`, `pageView`, `optOut`, `optIn`, `status`). It reports to the `onReady`, `onPageView` and `onEvent` triggers.

**Actions (`actions.py`)** don't touch State: every helper returns an `rx.call_script` built by `_call(method, *args)` that JSON-encodes args and invokes `window.__reflexVA.<method>(...)`. Adding a new action means adding the matching method in the JSX bridge. `track` runs `validate_event_name()` and `validate_properties()` (255-char limits, flat scalar values) before anything is sent.

Shared constants (SDK version, `BROWSER_API`, env prefix, modes, limits, app-wrap order) live in `constants.py`.

## Conventions

- Adding/changing a component prop: update the `Var` in `vercel_analytics.py`, the JSX destructuring/handling, `VercelAnalyticsConfig` + `to_props()` if it's configurable from file, then regenerate `vercel_analytics.pyi` with `uv run --python 3.13 python scripts/generate_pyi.py` (the `.pyi` is generated, don't hand-edit). `tests/test_component.py` asserts props compile to the camelCase names the bridge expects.
- Public API is re-exported explicitly in `__init__.py` (`__all__`); keep both lists updated.
- Bumping @vercel/analytics requires changing `VERCEL_ANALYTICS_VERSION` (tests assert the pinned value) and re-checking the `/react` adapter's props in `node_modules/@vercel/analytics/dist/react/index.d.ts`.
- Version lives only in `pyproject.toml` (`__version__` reads installed metadata); record releases in `CHANGELOG.md`.
- Everything (library, demo UI, docs) is in English. README images use absolute `raw.githubusercontent.com/.../main/docs/screenshots/...` URLs so they render on PyPI too; relative paths break there.
- Releases go to PyPI only (`.github/workflows/publish.yml`, Trusted Publishing, `pypi` environment with approval); no TestPyPI. Pre-publication = GitHub pre-release `vX.Y.ZrcN` → `X.Y.ZrcN` on PyPI (pip only installs it when pinned); release `vX.Y.Z` → final; manual run = dry run (no upload). After each upload `verify-pypi` installs it from PyPI and runs `scripts/smoke_test.py`. `scripts/check_release.py` enforces tag == `v<version>`, pre-release flag ↔ PEP 440 pre-release, a `## X.Y.Z` CHANGELOG entry for finals, and version not on PyPI (`--check-pypi`). `ci.yml` is reused via `workflow_call`; its concurrency group includes `github.workflow` so pushes don't cancel a publication. Keep `UV_VERSION` in the workflows and the `uv-pre-commit` rev in `.pre-commit-config.yaml` aligned.
