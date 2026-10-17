"""Run violation-sensitive native PCB DRC/parity, audit and fabrication exports."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import zipfile

from verify_pcb import ROOT, verify


def command(cli, arguments, log, require_success=True):
    result = subprocess.run([cli, *arguments], cwd=ROOT, text=True, capture_output=True)
    output = (
        (result.stdout + result.stderr)
        .replace(str(ROOT), "<electronics>")
        .replace(cli, "<kicad-cli>")
    )
    print(output.strip(), flush=True)
    log.append(
        {
            "command": ["<kicad-cli>", *arguments],
            "exit_code": result.returncode,
            "output": output.strip(),
        }
    )
    if require_success and result.returncode:
        raise RuntimeError(
            f"Native PCB command failed: {' '.join(arguments[:3])}; exit {result.returncode}"
        )
    return result.returncode


def check_board(cli, render=True):
    log = []
    (ROOT / "exports").mkdir(exist_ok=True)
    fabrication = ROOT / "fabrication"
    fabrication.mkdir(exist_ok=True)
    drc_exit = command(
        cli,
        [
            "pcb",
            "drc",
            "joint_interface.kicad_pcb",
            "--format",
            "json",
            "--all-track-errors",
            "--schematic-parity",
            "--severity-all",
            "--exit-code-violations",
            "--refill-zones",
            "--save-board",
            "-o",
            "pcb_drc_report.json",
        ],
        log,
        False,
    )
    # Preserve the native findings while keeping report paths machine-neutral.
    path = ROOT / "pcb_drc_report.json"
    drc = json.loads(path.read_text(encoding="utf-8"))
    drc["source"] = "joint_interface.kicad_pcb"
    path.write_text(json.dumps(drc, indent=2) + "\n", encoding="utf-8")
    # The previous saved manifest is deliberately stale after this fresh DRC
    # run. Audit the newly written native report, then bind it below; offline
    # verify() callers retain strict saved-source binding by default.
    report = verify(fresh_native_report=True)
    report["native_drc_exit_code"] = drc_exit
    report["drc_command"] = log[0]["command"]
    if drc_exit or report["status"] != "PASS":
        report["status"] = "FAIL"
        (ROOT / "pcb_verification.json").write_text(json.dumps(report, indent=2) + "\n")
        raise RuntimeError("PCB DRC, schematic parity or independent board audit failed")
    # Actual, separate layers: no flattened copper image is substituted for
    # fabrication data. Drill includes plated vias/headers and nonplated M3 holes.
    command(
        cli,
        [
            "pcb",
            "export",
            "gerbers",
            "joint_interface.kicad_pcb",
            "--layers",
            "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,F.Paste,Edge.Cuts",
            "--check-zones",
            "-o",
            "fabrication/",
        ],
        log,
    )
    command(
        cli,
        [
            "pcb",
            "export",
            "drill",
            "joint_interface.kicad_pcb",
            "--format",
            "excellon",
            "--excellon-units",
            "mm",
            "--excellon-separate-th",
            "--generate-map",
            "--map-format",
            "pdf",
            "--generate-report",
            "--report-path",
            "fabrication/drill_report.txt",
            "-o",
            "fabrication/",
        ],
        log,
    )
    command(
        cli,
        [
            "pcb",
            "export",
            "pos",
            "joint_interface.kicad_pcb",
            "--format",
            "csv",
            "--units",
            "mm",
            "--side",
            "both",
            "--exclude-dnp",
            "-o",
            "fabrication/assembly_positions.csv",
        ],
        log,
    )
    command(
        cli,
        [
            "pcb",
            "export",
            "ipcd356",
            "joint_interface.kicad_pcb",
            "-o",
            "fabrication/joint_interface.d356",
        ],
        log,
    )
    for name, layers in [
        ("top", "F.Cu,F.Silkscreen,Edge.Cuts"),
        ("bottom", "B.Cu,B.Silkscreen,Edge.Cuts"),
        ("ground_plane", "In1.Cu,Edge.Cuts"),
        ("power_plane", "In2.Cu,Edge.Cuts"),
        ("assembly", "F.Fab,F.Silkscreen,Edge.Cuts"),
    ]:
        command(
            cli,
            [
                "pcb",
                "export",
                "svg",
                "joint_interface.kicad_pcb",
                "--layers",
                layers,
                "--mode-single",
                "--fit-page-to-board",
                "--exclude-drawing-sheet",
                "-o",
                f"exports/pcb_{name}.svg",
            ],
            log,
        )
    command(
        cli,
        [
            "pcb",
            "export",
            "pdf",
            "joint_interface.kicad_pcb",
            "--layers",
            "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Fab,F.Silkscreen",
            "--common-layers",
            "Edge.Cuts",
            "--mode-multipage",
            "--exclude-value",
            "--no-property-popups",
            "--black-and-white",
            "-o",
            "exports/pcb_layers.pdf",
        ],
        log,
    )
    if render:
        command(
            cli,
            [
                "pcb",
                "render",
                "joint_interface.kicad_pcb",
                "--width",
                "1800",
                "--height",
                "1500",
                "--quality",
                "high",
                "--background",
                "opaque",
                "--rotate",
                "30,0,15",
                "--side",
                "top",
                "--zoom",
                "0.72",
                "-o",
                "exports/pcb_3d.png",
            ],
            log,
        )
        command(
            cli,
            [
                "pcb",
                "render",
                "joint_interface.kicad_pcb",
                "--width",
                "1800",
                "--height",
                "1800",
                "--quality",
                "basic",
                "--background",
                "opaque",
                "--side",
                "top",
                "--zoom",
                "0.80",
                "-o",
                "exports/pcb_top.png",
            ],
            log,
        )
    files = sorted(
        path for path in fabrication.iterdir() if path.is_file() and path.suffix != ".zip"
    )
    gerbers = [
        path
        for path in files
        if path.suffix
        in [".gbr", ".gtl", ".gbl", ".gts", ".gbs", ".gto", ".gbo", ".gtp", ".gm1", ".g1", ".g2"]
    ]
    drills = [path for path in files if path.suffix == ".drl"]
    assert len(gerbers) >= 10, "Incomplete Gerber layer set"
    assert len(drills) == 2, "Expected separate PTH and NPTH Excellon files"
    assert all(path.stat().st_size > 100 for path in gerbers + drills), "Empty fabrication output"
    archive = fabrication / "joint_interface_fabrication.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in files:
            bundle.write(path, path.name)
        bundle.write(ROOT / "bom.csv", "bom.csv")
    file_hashes = {
        str(path.relative_to(ROOT)).replace(os.sep, "/"): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in files + [archive]
    }
    report["fabrication_exports"] = {
        "status": "PASS",
        "gerber_layer_file_count": len(gerbers),
        "excellon_file_count": len(drills),
        "file_sha256": file_hashes,
        "scope": "Native export success and nonempty layer/drill checks; manufacturer CAM approval and assembly qualification are not performed.",
    }
    report["review_exports"] = [
        str(path.relative_to(ROOT)).replace(os.sep, "/")
        for path in sorted((ROOT / "exports").glob("pcb_*"))
    ]
    report["review_export_sha256"] = {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in report["review_exports"]
    }
    report["review_render_refreshed"] = render
    report["export_source_board_sha256"] = report["source_sha256"]["joint_interface.kicad_pcb"]
    (ROOT / "pcb_command_log.json").write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    (ROOT / "pcb_verification.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"PASS: {report['schematic_footprint_count']} schematic footprints + 4 mechanical, "
        f"{report['net_count']} connected nets, {report['track_count']} tracks, {report['via_count']} vias; "
        "0 DRC violations, 0 unconnected items, 0 schematic parity issues",
        flush=True,
    )
    return report


if __name__ == "__main__":
    from run_checks import find_kicad

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli")
    parser.add_argument(
        "--skip-render",
        action="store_true",
        help="Run all electrical/fabrication checks without refreshing 3D review images",
    )
    args = parser.parse_args()
    check_board(find_kicad(args.kicad_cli), not args.skip_render)
