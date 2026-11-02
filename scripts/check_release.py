"""Pre-publication guard: refuse to build a release whose metadata is inconsistent.

Checks, before anything is uploaded:

* the version in ``pyproject.toml`` is valid PEP 440;
* the git tag (``--tag``) is ``v<version>``;
* the GitHub "pre-release" flag (``--prerelease``) matches the version: ``rcN`` /
  ``bN`` / ``aN`` / ``.devN`` versions must be published as pre-releases (pip only
  installs them when pinned) and final versions must not;
* final versions have a ``## <version>`` entry in ``CHANGELOG.md``;
* the version does not exist on PyPI yet (``--check-pypi``).

Exits non-zero with a GitHub ``::error::`` annotation on the first failure. Run it
locally with::

    uv run python scripts/check_release.py --tag v0.1.0 --check-pypi
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

from packaging.version import InvalidVersion, Version

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = "reflex-vercel-analytics"
PYPI_JSON = "https://pypi.org/pypi/{package}/json"


def fail(message: str) -> None:
    print(f"::error::{message}", file=sys.stderr)
    sys.exit(1)


def published_versions() -> set[str]:
    url = PYPI_JSON.format(package=PACKAGE)
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            releases = json.load(response).get("releases", {})
    except urllib.error.HTTPError as error:
        if error.code == 404:  # project not created on PyPI yet
            return set()
        raise
    # Normalise so that "0.1.0rc1" and "0.1.0-rc.1" compare equal.
    return {str(Version(v)) for v, files in releases.items() if files}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", help="git tag being released, e.g. v0.1.0 or v0.2.0rc1")
    parser.add_argument("--prerelease", choices=["true", "false"], help="GitHub release pre-release flag")
    parser.add_argument("--check-pypi", action="store_true", help="fail if the version is already on PyPI")
    args = parser.parse_args()

    raw = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    try:
        version = Version(raw)
    except InvalidVersion:
        fail(f"pyproject.toml version {raw!r} is not a valid PEP 440 version")
    if str(version) != raw:
        fail(f"pyproject.toml version {raw!r} is not normalised; use {version}")

    if args.tag is not None and args.tag != f"v{version}":
        fail(f"tag {args.tag} does not match pyproject.toml version {version} (expected v{version})")

    if args.prerelease is not None:
        flagged = args.prerelease == "true"
        if version.is_prerelease and not flagged:
            fail(f"{version} is a pre-release version: mark the GitHub release as a pre-release")
        if not version.is_prerelease and flagged:
            fail(f"{version} is a final version: untick 'pre-release' or use an rcN/bN/aN version")

    if not version.is_prerelease:
        changelog = (ROOT / "CHANGELOG.md").read_text()
        if not re.search(rf"^##\s+\[?{re.escape(str(version))}\]?(\s|$)", changelog, re.MULTILINE):
            fail(f"CHANGELOG.md has no '## {version}' entry")

    if args.check_pypi and str(version) in published_versions():
        fail(f"{PACKAGE} {version} is already on PyPI; bump the version")

    kind = "pre-release" if version.is_prerelease else "final release"
    print(f"release check passed: {PACKAGE} {version} ({kind})")


if __name__ == "__main__":
    main()
