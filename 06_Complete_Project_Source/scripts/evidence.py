"""Bind recorded checks to the actual package and engineering source bytes."""

import hashlib
import json
import math
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path):
    def reject_constant(token):
        raise ValueError(f"Non-finite evidence value: {token}")

    def finite_float(token):
        value = float(token)
        if not math.isfinite(value):
            reject_constant(token)
        return value

    return json.loads(
        path.read_text(encoding="utf-8"), parse_constant=reject_constant, parse_float=finite_float
    )


def package_sources(root: Path) -> dict[str, str]:
    paths = [
        *sorted((root / "src/robotarm").rglob("*.py")),
        *(
            root / name
            for name in ("config/robot.yaml", "pyproject.toml", "setup.py", "MANIFEST.in")
        ),
    ]
    return {path.relative_to(root).as_posix(): sha256(path) for path in paths}


def validation_sources(root: Path) -> dict[str, str]:
    paths = set()
    for folder in ("src", "analysis", "cad", "electronics", "scripts", "tests", "simulations"):
        for pattern in ("*.py", "*.js", "*.cjs", "*.ps1"):
            paths.update((root / folder).rglob(pattern))
    paths.update(
        root / name
        for name in (
            "config/robot.yaml",
            "pyproject.toml",
            "requirements-lock.txt",
            "setup.py",
            "MANIFEST.in",
        )
    )
    for pattern in (
        "*.kicad_sch",
        "*.kicad_pcb",
        "*.kicad_pro",
        "*.kicad_dru",
        "*.kicad_mod",
        "*.kicad_sym",
    ):
        paths.update((root / "electronics").rglob(pattern))
    paths.update(
        root / "electronics" / name
        for name in ("electrical_assumptions.json", "fuse_selection.json", "fp-lib-table")
    )
    return {path.relative_to(root).as_posix(): sha256(path) for path in sorted(paths)}


def verify_packaging(root: Path, report: dict) -> None:
    if report.get("status") != "PASS" or report.get("source_sha256") != package_sources(root):
        raise ValueError("Isolated wheel evidence is missing or stale for current package sources")
