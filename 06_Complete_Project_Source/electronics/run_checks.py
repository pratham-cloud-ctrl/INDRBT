"""Run native KiCad ERC/export and the interface connectivity review.

Usage: python electronics/run_checks.py --kicad-cli /path/to/kicad-cli
Alternatively set KICAD_CLI or put kicad-cli on PATH. KiCad 10 is required.
"""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

from verify_netlist import ROOT, verify
from interface_analysis import calculate
import json


def find_kicad(explicit: str | None = None) -> str:
    configured = explicit or os.environ.get("KICAD_CLI") or shutil.which("kicad-cli")
    if configured:
        return configured
    if os.name == "nt":
        import winreg

        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            key_name = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
            try:
                with winreg.OpenKey(hive, key_name) as parent:
                    for index in range(winreg.QueryInfoKey(parent)[0]):
                        with winreg.OpenKey(parent, winreg.EnumKey(parent, index)) as entry:
                            try:
                                name = winreg.QueryValueEx(entry, "DisplayName")[0]
                                location = winreg.QueryValueEx(entry, "InstallLocation")[0]
                            except OSError:
                                continue
                            candidate = Path(location) / "bin" / "kicad-cli.exe"
                            if name.startswith("KiCad") and candidate.is_file():
                                return str(candidate)
            except OSError:
                pass
    raise RuntimeError("KiCad CLI not found. Provide --kicad-cli or set KICAD_CLI.")


def normalize_netlist(path: Path) -> None:
    """Keep generated source/library paths portable without altering connectivity."""
    tree = ET.parse(path)
    source = tree.find("./design/source")
    if source is not None:
        source.text = "joint_interface.kicad_sch"
    for library in tree.findall("./libraries/library"):
        uri = library.find("uri")
        if uri is not None and uri.text:
            uri.text = "${KICAD10_SYMBOL_DIR}/" + Path(uri.text).name
    tree.write(path, encoding="utf-8", xml_declaration=True)


def run(cli: str, arguments: list[str]) -> None:
    result = subprocess.run([cli, *arguments], cwd=ROOT, text=True, capture_output=True)
    message = result.stdout + result.stderr
    # Reports store machine-neutral command/output labels; do not retain personal paths.
    message = message.replace(str(ROOT), "<electronics>").replace(cli, "<kicad-cli>")
    print(message.strip())
    if result.returncode:
        raise RuntimeError(f"KiCad {' '.join(arguments[:3])}: exit {result.returncode}")


def footprint_check(directory: Path) -> int:
    checked = 0
    with (ROOT / "bom.csv").open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            library, footprint = row["Footprint"].split(":")
            assert (directory / f"{library}.pretty" / f"{footprint}.kicad_mod").is_file(), (
                f"Footprint not found: {row['Footprint']}"
            )
            checked += 1
    return checked


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli")
    parser.add_argument("--footprints", type=Path, default=os.environ.get("KICAD10_FOOTPRINT_DIR"))
    parser.add_argument(
        "--skip-pcb-render",
        action="store_true",
        help="Validate/export the PCB without refreshing 3D review images",
    )
    args = parser.parse_args()
    cli = find_kicad(args.kicad_cli)
    version = subprocess.run(
        [cli, "version"], text=True, capture_output=True, check=True
    ).stdout.strip()
    if not version.startswith("10."):
        raise RuntimeError(f"This revision requires KiCad 10, found {version}")
    run(
        cli,
        [
            "sch",
            "erc",
            "joint_interface.kicad_sch",
            "--severity-all",
            "--exit-code-violations",
            "--format",
            "json",
            "-o",
            "erc_report.json",
        ],
    )
    run(
        cli,
        [
            "sch",
            "export",
            "netlist",
            "joint_interface.kicad_sch",
            "--format",
            "kicadxml",
            "-o",
            "joint_interface.net.xml",
        ],
    )
    normalize_netlist(ROOT / "joint_interface.net.xml")
    report = verify()
    footprints = (
        args.footprints or Path(cli).resolve().parent.parent / "share" / "kicad" / "footprints"
    )
    if not footprints.is_dir():
        raise RuntimeError(
            "Footprint library not found. Set --footprints or KICAD10_FOOTPRINT_DIR."
        )
    report["stock_footprints_found"] = footprint_check(footprints)
    (ROOT / "net_verification.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    calculations = calculate()
    (ROOT / "interface_calculations.json").write_text(
        json.dumps(calculations, indent=2) + "\n", encoding="utf-8"
    )
    run(
        cli,
        [
            "sch",
            "export",
            "svg",
            "joint_interface.kicad_sch",
            "--exclude-drawing-sheet",
            "-o",
            "exports/",
        ],
    )
    run(
        cli,
        [
            "sch",
            "export",
            "pdf",
            "joint_interface.kicad_sch",
            "--exclude-drawing-sheet",
            "--exclude-pdf-property-popups",
            "-o",
            "exports/joint_interface.pdf",
        ],
    )
    print(
        f"PASS: {report['component_count']} components, {report['connected_net_count']} nets, {report['pin_assignments_checked']} pin assignments, {report['independent_topology_checks']} topology checks, 0 ERC violations"
    )
    from run_pcb_checks import check_board

    check_board(cli, render=not args.skip_pcb_render)
