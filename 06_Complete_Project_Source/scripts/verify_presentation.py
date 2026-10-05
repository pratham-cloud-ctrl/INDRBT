"""Check presentation copies, local links, version/status and source consistency."""

from pathlib import Path
import hashlib
import html
import json
import re
import tomllib
from urllib.parse import unquote

SOURCE = Path(__file__).resolve().parents[1]
DEST = SOURCE.parent


def verify():
    manifest = json.loads((DEST / "ORGANIZATION_MANIFEST.json").read_text())
    version = tomllib.loads((SOURCE / "pyproject.toml").read_text())["project"]["version"]
    validation = json.loads((SOURCE / "results/validation/validation_report.json").read_text())
    issues = []
    if manifest["version"] != version:
        issues.append({"issue": "stale presentation version"})
    if validation.get("project_version") != version:
        issues.append({"issue": "validation does not belong to this project version"})
    if (
        manifest["project_status"] != validation["project_status"]
        or validation["project_status"] != "DIGITAL SCOPE COMPLETE"
    ):
        issues.append({"issue": "digital scope is not fully accepted"})
    for artifact in manifest["artifact_copies"]:
        original, copy = SOURCE / artifact["source"], DEST / artifact["file"]
        for path in (original, copy):
            if not path.is_file():
                issues.append({"file": artifact["file"], "issue": "missing copy/source"})
            elif hashlib.sha256(path.read_bytes()).hexdigest() != artifact["sha256"]:
                issues.append({"file": artifact["file"], "issue": "stale source/copy hash"})
    for document in manifest.get("derived_documents", []):
        for path, expected in (
            (SOURCE / document["source"], document["source_sha256"]),
            (DEST / document["file"], document["sha256"]),
        ):
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                issues.append(
                    {"file": document["file"], "issue": "stale derived document or source"}
                )
    for entry in manifest.get("generated_files", []):
        path = DEST / entry["file"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            issues.append({"file": entry["file"], "issue": "stale generated presentation"})
    for entry in manifest.get("generation_inputs", []):
        path = SOURCE / entry["source"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            issues.append({"file": entry["source"], "issue": "stale presentation generation input"})
    links = 0
    for path in DEST.rglob("*.html"):
        if any(part in (".git", "build", ".venv") for part in path.parts):
            continue
        for link in re.findall(r'(?:href|src)="([^"]+)"', path.read_text(encoding="utf-8")):
            if re.match(r"(?:[a-z]+:|#|//)", link, re.I):
                continue
            links += 1
            link = unquote(html.unescape(link.split("#")[0]))
            if link and not (path.parent / link).exists():
                issues.append(
                    {
                        "file": str(path.relative_to(DEST)),
                        "issue": "broken local link",
                        "link": link,
                    }
                )
    for file in (DEST / "README.md", DEST / "START_HERE.html"):
        text = file.read_text(encoding="utf-8")
        if version not in text or "DIGITAL SCOPE COMPLETE" not in text:
            issues.append({"file": file.name, "issue": "stale version/status text"})
    for path in [DEST / "README.md", *DEST.glob("0*/README.md")]:
        for link in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if (
                not re.match(r"(?:[a-z]+:|#|//)", link, re.I)
                and not (path.parent / unquote(link.split("#")[0])).exists()
            ):
                issues.append(
                    {
                        "file": str(path.relative_to(DEST)),
                        "issue": "broken Markdown link",
                        "link": link,
                    }
                )
    report = {
        "status": "PASS" if not issues else "FAIL",
        "version": version,
        "project_status": validation["project_status"],
        "artifact_copies_verified": len(manifest["artifact_copies"]),
        "local_html_links_checked": links,
        "issues": issues,
        "scope": "Exact copy hashes, file links, current version/status; browser interaction is checked separately",
    }
    (DEST / "ORGANIZATION_CHECK.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    result = verify()
    print(json.dumps(result))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
