"""Smoke-test an *installed* reflex-vercel-analytics distribution.

Runs against a wheel/sdist installed in a throwaway environment (never the source
tree), so it catches packaging mistakes the unit tests cannot see: a missing JSX
bridge or stub, a broken public API, wrong metadata. Used by CI, by the publish
workflow after each upload, and by ``scripts/prepublish.sh``::

    uv run --isolated --no-project --with dist/<wheel>.whl python -I scripts/smoke_test.py --version 0.1.0
"""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import version as dist_version
from pathlib import Path

REPO_PACKAGE_DIR = Path(__file__).resolve().parent.parent / "custom_components"


def check(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}", file=sys.stderr)
        sys.exit(1)
    print(f"ok: {message}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--version", help="expected distribution version (e.g. 0.1.0rc1)")
    args = parser.parse_args()

    import reflex_vercel_analytics as rva

    package_dir = Path(rva.__file__).resolve().parent
    check(
        REPO_PACKAGE_DIR not in package_dir.parents,
        f"imported from the installed distribution ({package_dir})",
    )

    installed = dist_version("reflex-vercel-analytics")
    check(rva.__version__ == installed, f"__version__ matches metadata ({installed})")
    if args.version:
        check(installed == args.version, f"installed version is {args.version}")

    for name in ("vercel_analytics.jsx", "vercel_analytics.pyi", "py.typed"):
        check((package_dir / name).is_file(), f"{name} is shipped")

    missing = [name for name in rva.__all__ if not hasattr(rva, name)]
    check(not missing, f"every name in __all__ resolves ({len(rva.__all__)} names)")

    from reflex_vercel_analytics.constants import VERCEL_ANALYTICS_VERSION

    component = rva.vercel_analytics(mode="development", exclude_paths=["/admin"])
    rendered = str(component)
    check("ReflexVercelAnalytics" in rendered, "component renders the JSX bridge tag")
    check(
        f"@vercel/analytics@{VERCEL_ANALYTICS_VERSION}" in component.lib_dependencies,
        f"pins @vercel/analytics@{VERCEL_ANALYTICS_VERSION}",
    )
    check(
        "__reflexVA" in str(rva.track("Smoke Test", {"ok": True})),
        "track() builds a call to the browser API",
    )

    try:
        rva.track("x" * 300)
    except ValueError:
        check(True, "track() rejects event names over the Vercel limit")
    else:
        check(False, "track() rejects event names over the Vercel limit")

    print(f"smoke test passed for reflex-vercel-analytics {installed}")


if __name__ == "__main__":
    main()
