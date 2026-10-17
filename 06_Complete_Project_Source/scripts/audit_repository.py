"""Audit tracked deliverables for credential patterns, personal paths and junk."""

from pathlib import Path
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TEXT = {
    ".py",
    ".md",
    ".yaml",
    ".yml",
    ".toml",
    ".json",
    ".xml",
    ".txt",
    ".js",
    ".cjs",
    ".html",
    ".mmd",
    ".cff",
    ".svg",
    ".csv",
    ".kicad_sch",
    ".kicad_pro",
    ".kicad_pcb",
    ".kicad_mod",
    ".kicad_dru",
    ".gbr",
    ".pos",
    ".step",
    ".ps1",
    ".cmd",
}
PATTERNS = {
    "credential": re.compile(
        r"(?:gh[pousr]_[A-Za-z0-9]{32,}|github_pat_[A-Za-z0-9_]{40,}|sk-[A-Za-z0-9]{32,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)"
    ),
    "personal_absolute_path": re.compile(
        r"(?:C:(?:\\+|/)Users(?:\\+|/)|E:(?:\\+|/)(?:project workspace assests|gripper projects))",
        re.I,
    ),
}


def audit():
    repository = Path(
        subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], cwd=ROOT, text=True
        ).strip()
    )
    listing = subprocess.run(
        ["git", "ls-files", "-z"], cwd=repository, capture_output=True, check=True
    ).stdout
    names = [name for name in listing.decode("utf-8").split("\0") if name]
    issues = []
    total_size = 0
    largest = []
    for name in names:
        path = repository / name
        size = path.stat().st_size
        total_size += size
        largest.append((size, name))
        if size > 20 * 1024**2:
            issues.append({"file": name, "kind": "file_above_20MiB"})
        if path.suffix in {".FCBak", ".blend1", ".kicad_prl", ".pyc", ".log"}:
            issues.append({"file": name, "kind": "generated_junk"})
        if path.suffix.lower() in TEXT:
            content = path.read_text(encoding="utf-8-sig", errors="replace")
            for kind, pattern in PATTERNS.items():
                if pattern.search(content):
                    # Do not print matched credential content.
                    issues.append({"file": name, "kind": kind})
    report = {
        "status": "PASS" if not issues else "FAIL",
        "scope": "Tracked-file pattern scan and size/junk audit; not an exhaustive security proof",
        "tracked_files": len(names),
        "tracked_bytes": total_size,
        "issues": issues,
        "largest_files": [
            {"file": name, "bytes": size} for size, name in sorted(largest, reverse=True)[:8]
        ],
    }
    (ROOT / "results/validation/repository_audit.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    result = audit()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
