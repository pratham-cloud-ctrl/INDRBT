"""Cross-check the saved electrical design and fabrication package without KiCad.

This audits existing native evidence. It does not execute a new native ERC/DRC.
Run the native run_checks.py workflow first whenever the design changes.
"""

from __future__ import annotations

from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

from generate_interface import item, nodes, parse
from interface_analysis import calculate
from verify_netlist import verify as verify_netlist
from verify_pcb import prop, verify as verify_pcb

ROOT = Path(__file__).resolve().parent
REPOSITORY_SOURCE = ROOT.parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def review():
    net = verify_netlist()
    pcb = verify_pcb()
    saved = json.loads((ROOT / "pcb_verification.json").read_text(encoding="utf-8"))
    assert saved["status"] == pcb["status"] == net["status"] == "PASS"
    assert saved["native_drc_exit_code"] == 0
    erc = json.loads((ROOT / "erc_report.json").read_text(encoding="utf-8"))
    erc_count = sum(len(sheet["violations"]) for sheet in erc["sheets"])
    assert erc_count == 0, "Saved native ERC has findings"
    commands = json.loads((ROOT / "pcb_command_log.json").read_text(encoding="utf-8"))
    assert all(command["exit_code"] == 0 for command in commands)
    drc_command = commands[0]["command"]
    for flag in [
        "--all-track-errors",
        "--schematic-parity",
        "--severity-all",
        "--exit-code-violations",
        "--refill-zones",
        "--save-board",
    ]:
        assert flag in drc_command
    hash_sets = {
        "source": saved["source_sha256"],
        "fabrication": saved["fabrication_exports"]["file_sha256"],
        "review_exports": saved["review_export_sha256"],
    }
    hash_counts = {}
    for group, values in hash_sets.items():
        for name, expected in values.items():
            assert digest(ROOT / name) == expected, f"Stale {group} hash: {name}"
        hash_counts[group] = len(values)
    assert saved["export_source_board_sha256"] == digest(ROOT / "joint_interface.kicad_pcb")
    assert saved["review_render_refreshed"], "Rendered review views were not refreshed"
    board = parse((ROOT / "joint_interface.kicad_pcb").read_text(encoding="utf-8"))
    footprints = {prop(fp, "Reference"): fp for fp in nodes(board, "footprint")}
    with (ROOT / "bom.csv").open(encoding="utf-8", newline="") as handle:
        bom_rows = list(csv.DictReader(handle))
    bom = {row["Reference"]: row for row in bom_rows}
    assert len(bom) == len(bom_rows) == pcb["schematic_footprint_count"]
    xml = ET.parse(ROOT / "joint_interface.net.xml")
    for component in xml.findall("./components/comp"):
        reference = component.get("ref")
        if reference.startswith("#"):
            continue
        row = bom[reference]
        assert row["Value"] == component.findtext("value") == prop(footprints[reference], "Value")
        assert row["Footprint"] == component.findtext("footprint") == footprints[reference][1]
    with (ROOT / "fabrication/assembly_positions.csv").open(encoding="utf-8", newline="") as handle:
        positions = list(csv.DictReader(handle))
    expected_positions = {
        reference
        for reference, fp in footprints.items()
        if not {"board_only", "exclude_from_pos_files", "dnp"}.intersection(item(fp, "attr")[1:])
    }
    assert Counter(row["Ref"] for row in positions) == Counter(
        {reference: 1 for reference in expected_positions}
    )
    for row in positions:
        fp = footprints[row["Ref"]]
        at = item(fp, "at")
        assert row["Val"] == prop(fp, "Value")
        assert row["Package"] == fp[1].split(":")[1]
        assert abs(float(row["PosX"]) - float(at[1])) < 1e-6
        assert abs(float(row["PosY"]) + float(at[2])) < 1e-6
    fabrication = ROOT / "fabrication"
    job = json.loads((fabrication / "joint_interface-job.gbrjob").read_text(encoding="utf-8"))
    expected_functions = {
        "Copper,L1,Top",
        "Copper,L2,Inr",
        "Copper,L3,Inr",
        "Copper,L4,Bot",
        "SolderPaste,Top",
        "Legend,Top",
        "Legend,Bot",
        "SolderMask,Top",
        "SolderMask,Bot",
        "Profile",
    }
    assert {entry["FileFunction"] for entry in job["FilesAttributes"]} == expected_functions
    assert len(job["FilesAttributes"]) == 10
    assert job["GeneralSpecs"]["LayerNumber"] == pcb["copper_layers"]
    for entry in job["FilesAttributes"]:
        assert (fabrication / entry["Path"]).is_file()
    drill_counts = {}
    for name, plated in [("joint_interface-PTH.drl", True), ("joint_interface-NPTH.drl", False)]:
        source = (fabrication / name).read_text(encoding="utf-8")
        assert ("TF.FileFunction,Plated" if plated else "TF.FileFunction,NonPlated") in source
        actual = len(re.findall(r"^X[-+0-9.]+Y[-+0-9.]+$", source, re.MULTILINE))
        expected = sum(
            pad[2] == ("thru_hole" if plated else "np_thru_hole")
            for fp in footprints.values()
            for pad in nodes(fp, "pad")
        )
        if plated:
            expected += pcb["via_count"]
        assert actual == expected, f"{name} drill count differs from native board"
        drill_counts[name] = actual
    contents = {
        path.name: path
        for path in fabrication.iterdir()
        if path.is_file() and path.suffix != ".zip"
    }
    contents["bom.csv"] = ROOT / "bom.csv"
    with zipfile.ZipFile(fabrication / "joint_interface_fabrication.zip") as archive:
        assert Counter(archive.namelist()) == Counter({name: 1 for name in contents})
        assert archive.testzip() is None
        for name, path in contents.items():
            assert archive.read(name) == path.read_bytes(), f"ZIP contains stale {name}"
    ipc = (fabrication / "joint_interface.d356").read_text(encoding="utf-8").splitlines()
    ipc_rows = [line for line in ipc if line.startswith(("317", "327"))]
    expected_ipc_rows = pcb["physical_pad_nets_checked_including_nc"] + pcb["via_count"]
    assert len(ipc_rows) == expected_ipc_rows
    assert ipc[-1] == "999", "IPC-D-356 end marker missing"
    for pin in ["1", "2"]:
        line = next(line for line in ipc_rows if re.search(rf"\bF1\s+-{pin}\b", line))
        assert "X0394Y0630" in line, (
            "F1 IPC-D-356 pad size does not reflect the corrected 1.0 x 1.6 mm lands"
        )
    calculations = calculate()
    assert calculations == json.loads(
        (ROOT / "interface_calculations.json").read_text(encoding="utf-8")
    ), "Saved electrical calculations are stale"
    return {
        "status": "PASS",
        "scope": "Saved native KiCad evidence plus an independent file/content audit for the low-voltage external-drive interface. This script does not run fresh native checks or certify a physical product.",
        "native_kicad_version": pcb["kicad_version"],
        "native_erc_violations": erc_count,
        "native_drc_errors": pcb["native_drc_errors"],
        "native_drc_warnings": pcb["native_drc_warnings"],
        "native_unconnected_items": pcb["unconnected_items"],
        "native_schematic_parity_issues": pcb["schematic_parity_issues"],
        "native_pcb_commands_reviewed": len(commands),
        "native_pcb_command_exit_codes": [command["exit_code"] for command in commands],
        "component_count": len(bom),
        "connected_nets": pcb["net_count"],
        "physical_pad_nets_checked_including_nc": pcb["physical_pad_nets_checked_including_nc"],
        "stock_footprints": sum(
            not row["Footprint"].startswith("INDRBT_Interface:") for row in bom_rows
        ),
        "local_manufacturer_footprints": sum(
            row["Footprint"].startswith("INDRBT_Interface:") for row in bom_rows
        ),
        "fuse_correction": pcb["fuse_manufacturer_land_pattern_review"],
        "footprint_wildcard_matches": pcb["independent_footprint_filter_review"][
            "wildcard_matches"
        ],
        "bom_values_and_footprints_match_native_design": True,
        "assembly_position_count": len(positions),
        "assembly_exclusions": {
            "R14": "DNP optional bias",
            "R15": "DNP optional bias",
            "JP1": "bare copper solder jumper, no body",
            "H1-H4": "board-only mechanical holes",
        },
        "gerber_layer_functions": sorted(expected_functions),
        "drill_counts": drill_counts,
        "ipc_d356_testpoint_count": len(ipc_rows),
        "fabrication_zip_entries_checked": len(contents),
        "file_hashes_recomputed": hash_counts,
        "file_hash_mismatches": 0,
        "board_sha256": digest(ROOT / "joint_interface.kicad_pcb"),
        "pcb_verification_sha256": digest(ROOT / "pcb_verification.json"),
        "component_guide": "docs/electronics_components.md",
        "component_guide_sha256": digest(REPOSITORY_SOURCE / "docs/electronics_components.md"),
        "power_calculations": calculations,
        "factory_disabled_erc_checks": [entry["key"] for entry in erc["ignored_checks"]],
        "factory_disabled_drc_checks": [
            entry["key"] for entry in pcb["native_drc_factory_ignored_checks"]
        ],
        "custom_rule_severity_overrides": pcb["rule_severity_overrides"],
        "drc_exclusions": pcb["drc_exclusions"],
        "remaining_physical_review": [
            "Generic stock land patterns are package-compatible design selections, not a complete manufacturer soldering-process approval",
            "Passive/LED/connector purchasing codes and effective capacitance under DC bias",
            "Controller and encoder currents within the shared 150 mA budget, including terminated-bus loading",
            "Fuse trip/inrush and cold/hot voltage-drop behaviour",
            "Measured thermal, EMC, ESD, timing, cable grounding/isolation and safety qualification",
        ],
        "references": {
            "fuse": "https://www.bourns.com/docs/product-datasheets/mf-nsmf.pdf",
            "regulator": "https://www.diodes.com/assets/Datasheets/AP2112.pdf",
            "reverse_polarity_diode": "https://www.vishay.com/docs/88746/ss12.pdf",
            "input_clamps": "https://assets.nexperia.com/documents/data-sheet/BAT54H.pdf",
            "rs485_transceiver": "https://www.analog.com/media/en/technical-documentation/data-sheets/285012fe.pdf",
        },
    }


if __name__ == "__main__":
    report = review()
    path = REPOSITORY_SOURCE / "results/validation/final_electronics_review.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        f"PASS: {report['component_count']} components, corrected F1 lands, {sum(report['file_hashes_recomputed'].values())} hashes, {report['assembly_position_count']} placements and complete fabrication package"
    )
