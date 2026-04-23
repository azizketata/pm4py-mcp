"""Shared pytest configuration for the four-layer testing pyramid."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure editable-install style imports work even if the project isn't
# installed in the current interpreter (useful for quick local pytest runs).
_SRC = Path(__file__).resolve().parent.parent / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
