"""Regenerate ``vercel_analytics.pyi`` from the component definition.

``reflex component build`` was removed in Reflex 0.10, so this script drives
Reflex's stub generator directly. Run it from the repository root after
changing a component prop or event trigger::

    uv run python scripts/generate_pyi.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from reflex.utils.pyi_generator import PyiGenerator

ROOT = Path(__file__).resolve().parent.parent
# Relative to the repository root: the generator imports the module from the cwd.
TARGETS = [Path("custom_components") / "reflex_vercel_analytics" / "vercel_analytics.py"]


# Python 3.13 strips the common indentation from ``__doc__``, which changes the docstrings the
# generator copies into the stub; pin one version so the committed stub is reproducible (CI too).
STUB_PYTHON = (3, 13)


def main() -> None:
    if sys.version_info[:2] != STUB_PYTHON:
        version = ".".join(map(str, STUB_PYTHON))
        sys.exit(
            f"generate_pyi.py must run on Python {version} so the stub is reproducible; "
            f"use: uv run --python {version} python scripts/generate_pyi.py"
        )
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))  # ``custom_components.reflex_vercel_analytics`` must be importable
    PyiGenerator().scan_all([str(path) for path in TARGETS])
    for path in TARGETS:
        stub = path.with_suffix(".pyi")
        print(f"{'wrote' if stub.exists() else 'MISSING'}: {stub}")


if __name__ == "__main__":
    main()
