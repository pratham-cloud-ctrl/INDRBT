"""Validate a freshly exported KiCad netlist against reviewed electrical intent.

Run `kicad-cli sch export netlist --format kicadxml` before this script after edits.
The saved contract checks all implemented pin assignments; independent invariants
below check the safety-relevant structure rather than trusting generated text.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent


def verify(netlist: Path = ROOT / "joint_interface.net.xml") -> dict:
    tree = ET.parse(netlist).getroot()
    actual: dict[tuple[str, str], str] = {}
    by_net: dict[str, set[tuple[str, str]]] = {}
    for net in tree.findall("./nets/net"):
        name = net.attrib["name"].removeprefix("/")
        endpoints = {(n.attrib["ref"], n.attrib["pin"]) for n in net.findall("node")}
        by_net[name] = endpoints
        for endpoint in endpoints:
            if endpoint in actual:
                raise AssertionError(f"Pin assigned twice: {endpoint}")
            actual[endpoint] = name
    contract = json.loads((ROOT / "pin_contract.json").read_text(encoding="utf-8"))
    checked = 0
    for ref, pins in contract.items():
        if ref.startswith("#"):
            continue  # KiCad flags describe external supply; they are not board parts.
        for pin, net in pins.items():
            found = actual.get((ref, pin))
            assert found == net, f"{ref}.{pin}: expected {net}, exported {found}"
            checked += 1
    components = {c.attrib["ref"]: c for c in tree.findall("./components/comp")}
    assert len(components) == 44, f"Expected 44 board components, found {len(components)}"
    assert set(components) == {r for r in contract if not r.startswith("#")}
    for ref, component in components.items():
        assert component.findtext("footprint"), f"Footprint missing: {ref}"
    # These reviewed statements do not derive from the generator's pin contract.
    invariants = {
        "fuse_before_reverse_diode": actual[("F1", "2")] == actual[("D1", "2")] == "+5V_FUSED",
        "reverse_diode_cathode_to_ldo": actual[("D1", "1")] == actual[("U1", "1")] == "+5V_PROTECTED",
        "ldo_output_separate_from_input": actual[("U1", "5")] == "+3V3" != actual[("U1", "1")],
        "ldo_always_enabled_from_protected_input": actual[("U1", "3")] == "+5V_PROTECTED",
        "ldo_ground": actual[("U1", "2")] == "GND",
        "rs485_driver_receiver_enable_paired": actual[("U2", "2")] == actual[("U2", "3")] == "RS485_DIR",
        "rs485_default_receive_pulldown": actual[("R13", "1")] == "RS485_DIR" and actual[("R13", "2")] == "GND",
        "termination_is_switchable_series_path": actual[("R16", "1")] == "RS485_A" and actual[("R16", "2")] == actual[("JP1", "1")] == "TERM_LINK" and actual[("JP1", "2")] == "RS485_B",
        "drive_enable_default_off": actual[("R8", "1")] == "ENABLE_DRV" and actual[("R8", "2")] == "GND",
        "limit_closed_to_ground_through_series_resistor": actual[("J4", "1")] == actual[("R5", "1")] == "LIMIT_RAW" and actual[("J4", "2")] == "GND",
        "limit_pullup_and_cap": actual[("R6", "1")] == "+3V3" and actual[("R6", "2")] == actual[("C6", "1")] == "LIMIT_N" and actual[("C6", "2")] == "GND",
        "no_motor_power_connector": all(not net.startswith(("MOTOR", "VBUS", "+24V", "+48V")) for net in by_net),
        "no_multi_pin_net_floating": all(len(pins) >= 2 for name, pins in by_net.items() if not name.startswith("unconnected-")),
    }
    for i, letter in enumerate("ABZ"):
        invariants[f"encoder_{letter}_series_filter"] = actual[(f"R{2+i}", "1")] == f"ENC_{letter}_RAW" and actual[(f"R{2+i}", "2")] == actual[(f"C{3+i}", "1")] == f"ENC_{letter}"
        invariants[f"encoder_{letter}_positive_clamp_polarity"] = actual[(f"D{3+2*i}", "1")] == "+3V3" and actual[(f"D{3+2*i}", "2")] == f"ENC_{letter}"
        invariants[f"encoder_{letter}_negative_clamp_polarity"] = actual[(f"D{4+2*i}", "1")] == f"ENC_{letter}" and actual[(f"D{4+2*i}", "2")] == "GND"
    assert all(invariants.values()), [name for name, ok in invariants.items() if not ok]
    assert actual.get(("U1", "4"), "unconnected-").startswith("unconnected-"), "LDO NC pin must remain unconnected"
    erc = json.loads((ROOT / "erc_report.json").read_text(encoding="utf-8"))
    violations = [v for sheet in erc["sheets"] for v in sheet["violations"]]
    assert not violations, f"ERC contains {len(violations)} violations"
    return {
        "status": "PASS", "kicad_version": erc["kicad_version"],
        "component_count": len(components), "connected_net_count": sum(not n.startswith("unconnected-") for n in by_net),
        "pin_assignments_checked": checked, "independent_topology_checks": len(invariants),
        "erc_violations": len(violations), "topology_checks": invariants,
        "schematic_sha256": hashlib.sha256((ROOT / "joint_interface.kicad_sch").read_bytes()).hexdigest(),
        "netlist_sha256": hashlib.sha256(netlist.read_bytes()).hexdigest(),
        "claim_boundary": "Native schematic/ERC and exported connectivity only; no physical measurements, PCB routing or hardware safety validation",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--netlist", type=Path, default=ROOT / "joint_interface.net.xml")
    args = parser.parse_args()
    report = verify(args.netlist)
    (ROOT / "net_verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("topology_checks", "schematic_sha256", "netlist_sha256")}, indent=2))
