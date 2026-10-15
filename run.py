"""Quadton launcher.

Use this as the panel's Startup File.

It ensures the project root is importable, then delegates to
quadton.__main__:main — so `python run.py` and `python -m quadton`
behave identically.
"""
from __future__ import annotations

import asyncio
import os
import sys

# Ensure the project root is on sys.path regardless of the panel's cwd.
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from quadton.__main__ import main  # noqa: E402


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
