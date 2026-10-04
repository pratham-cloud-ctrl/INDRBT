"""Generate STEP/STL, local meshes, numerical CAD checks and drawing sheets."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cad/build123d"))
from export_all import main  # noqa: E402

if __name__ == "__main__":
    main()
