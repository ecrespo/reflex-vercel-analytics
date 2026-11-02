#!/usr/bin/env bash
# Local pre-publication gate: runs the same checks as CI + the publish workflow's
# build stage, without uploading anything. Run it from anywhere before tagging:
#
#   scripts/prepublish.sh            # full gate
#   scripts/prepublish.sh v0.2.0rc1  # also check that the tag matches the version
#
# Steps: lockfile, pre-commit (all files), pytest, .pyi drift, demo compile,
# release metadata, build, twine check, smoke test of the wheel and the sdist in
# isolated environments.
set -euo pipefail

cd "$(dirname "$0")/.."
TAG="${1:-}"

step() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }

step "uv.lock is up to date"
uv lock --check

step "pre-commit (all files, commit stage)"
uv run pre-commit run --all-files --show-diff-on-failure --hook-stage pre-commit

step "pytest"
uv run pytest

step "vercel_analytics.pyi matches the component"
STUB=custom_components/reflex_vercel_analytics/vercel_analytics.pyi
BACKUP="$(mktemp)"
cp "$STUB" "$BACKUP"
uv run --python 3.13 python scripts/generate_pyi.py >/dev/null
if ! cmp -s "$STUB" "$BACKUP"; then
  diff -u "$BACKUP" "$STUB" || true
  echo "error: $STUB is stale; the regenerated version is now in place, review and commit it" >&2
  exit 1
fi

step "demo app compiles"
(cd vercel_analytics_demo && uv run reflex compile --no-rich)

step "release metadata"
if [[ -n "$TAG" ]]; then
  uv run python scripts/check_release.py --tag "$TAG" --check-pypi
else
  uv run python scripts/check_release.py --check-pypi
fi

step "build + twine check"
rm -rf dist
uv build
uvx twine check --strict dist/*

VERSION="$(uv version --short)"
for dist in dist/*.whl dist/*.tar.gz; do
  step "smoke test: $(basename "$dist")"
  uv run --isolated --no-project --with "$dist" python -I scripts/smoke_test.py --version "$VERSION"
done

printf '\n\033[1;32mReady to publish reflex-vercel-analytics %s\033[0m\n' "$VERSION"
