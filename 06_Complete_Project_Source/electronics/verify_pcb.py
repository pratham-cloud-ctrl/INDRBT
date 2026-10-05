"""Independently audit native PCB/netlist evidence without pcbnew dependencies."""

from __future__ import annotations

from collections import Counter, defaultdict
import fnmatch
import hashlib
import heapq
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from generate_interface import item, nodes, parse

ROOT = Path(__file__).resolve().parent

# KiCad 10 constructor defaults from pcbnew/board_design_settings.cpp:
# every rule starts at ERROR, then the following WARNING/IGNORE sets apply.
# Comparing the serialized project with these defaults detects real overrides
# while allowing KiCad --save-board to serialize its normal default map.
DEFAULT_WARNINGS = set(
    """holes_co_located hole_to_hole track_dangling via_dangling
copper_sliver isolated_copper padstack missing_footprint duplicate_footprints
extra_footprint net_conflict footprint_symbol_mismatch footprint_symbol_field_mismatch
silk_overlap silk_over_copper silk_edge_clearance text_height text_thickness
lib_footprint_issues lib_footprint_mismatch connection_width mirrored_text_on_front_layer
nonmirrored_text_on_back_layer missing_tuning_profile""".split()
)
DEFAULT_IGNORES = set(
    """missing_courtyard footprint_filters_mismatch footprint_type_mismatch
tuning_profile_track_geometries track_not_centered_on_via""".split()
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def net_name(node):
    net = item(node, "net")
    return str(net[-1]) if net else ""


def prop(footprint, name):
    return next(v[2] for v in nodes(footprint, "property") if v[1] == name)


def position(footprint, pad):
    origin = item(footprint, "at")
    local = item(pad, "at")
    angle = math.radians(float(origin[3]) if len(origin) > 3 else 0)
    x, y = float(local[1]), float(local[2])
    return (
        round(float(origin[1]) + math.cos(angle) * x + math.sin(angle) * y, 6),
        round(float(origin[2]) - math.sin(angle) * x + math.cos(angle) * y, 6),
    )


def local_track_distance(board, net, start, end):
    """Shortest explicit front-copper track path, excluding plane shortcuts."""
    graph = defaultdict(list)
    for track in nodes(board, "segment"):
        if net_name(track) != net or item(track, "layer")[1] != "F.Cu":
            continue
        a = tuple(float(v) for v in item(track, "start")[1:])
        b = tuple(float(v) for v in item(track, "end")[1:])
        distance = math.dist(a, b)
        graph[a].append((b, distance))
        graph[b].append((a, distance))
    frontier = [(0.0, start)]
    best = {start: 0.0}
    while frontier:
        value, current = heapq.heappop(frontier)
        if current == end:
            return value
        if value > best[current]:
            continue
        for other, distance in graph[current]:
            candidate = value + distance
            if candidate < best.get(other, math.inf):
                best[other] = candidate
                heapq.heappush(frontier, (candidate, other))
    raise AssertionError(f"No explicit front-copper {net} path between reviewed pads")


def verify():
    board_path = ROOT / "joint_interface.kicad_pcb"
    board = parse(board_path.read_text(encoding="utf-8"))
    xml = ET.parse(ROOT / "joint_interface.net.xml")
    contract = json.loads((ROOT / "pin_contract.json").read_text())
    footprints = {prop(fp, "Reference"): fp for fp in nodes(board, "footprint")}
    expected = {
        comp.get("ref"): comp
        for comp in xml.findall("./components/comp")
        if not comp.get("ref").startswith("#")
    }
    assert set(footprints) == set(expected) | {"H1", "H2", "H3", "H4"}, (
        "Unexpected/missing footprints"
    )
    pad_map = {}
    physical_pad_positions = {}
    courtyard_count = 0
    for ref, fp in footprints.items():
        courtyard_count += any(
            item(v, "layer") and item(v, "layer")[1] in ["F.CrtYd", "B.CrtYd"]
            for key in ["fp_line", "fp_arc", "fp_poly", "fp_rect", "fp_circle"]
            for v in nodes(fp, key)
        )
        if ref.startswith("H"):
            assert "board_only" in item(fp, "attr"), "Mechanical footprints must be board-only"
            assert all(pad[2] == "np_thru_hole" for pad in nodes(fp, "pad")), (
                "Mounting holes must be nonplated"
            )
            continue
        assert fp[1] == expected[ref].findtext("footprint"), f"{ref} footprint differs"
        assert prop(fp, "Value") == expected[ref].findtext("value"), f"{ref} value differs"
        symbol_id = expected[ref].findtext("tstamps")
        assert str(item(fp, "path")[1]).endswith("/" + symbol_id), (
            f"{ref} schematic UUID link differs"
        )
        for pad in nodes(fp, "pad"):
            key = (ref, str(pad[1]))
            pad_map[key] = net_name(pad)
            physical_pad_positions[key] = position(fp, pad)
    native_pins = {}
    net_count = 0
    for net in xml.findall("./nets/net"):
        pins = [
            (pin.get("ref"), pin.get("pin"))
            for pin in net.findall("node")
            if pin.get("ref") in expected
        ]
        if len(pins) > 1:
            net_count += 1
        for key in pins:
            native_pins[key] = net.get("name")
    assert native_pins == pad_map, "Native XML and physical board pad nets differ"
    assigned = 0
    for ref, pins in contract.items():
        if ref.startswith("#"):
            continue
        for pin, name in pins.items():
            assert pad_map[ref, pin].lstrip("/") == name, f"Pin contract mismatch: {ref}.{pin}"
            assigned += 1
    assert pad_map["U1", "4"].startswith("unconnected-"), "Regulator NC pad must remain isolated"
    tracks, vias = nodes(board, "segment"), nodes(board, "via")
    assert tracks and vias, "Board must contain real routing"
    layers = [str(layer[1]) for layer in item(board, "layers")[1:] if str(layer[1]).endswith(".Cu")]
    assert layers == ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]
    zones = nodes(board, "zone")
    assert {(net_name(zone), item(zone, "layer")[1]) for zone in zones} == {
        ("/GND", "In1.Cu"),
        ("/+3V3", "In2.Cu"),
    }
    assert all(nodes(zone, "filled_polygon") for zone in zones), "Plane fills are missing"
    outline = [line for line in nodes(board, "gr_line") if item(line, "layer")[1] == "Edge.Cuts"]
    assert len(outline) == 4, "Expected closed rectangular board outline"
    endpoints = Counter(
        tuple(float(v) for v in item(line, endpoint)[1:])
        for line in outline
        for endpoint in ["start", "end"]
    )
    assert len(endpoints) == 4 and set(endpoints.values()) == {2}, "Outline is not closed"
    xs, ys = zip(*endpoints)
    dimensions = [max(xs) - min(xs), max(ys) - min(ys)]
    assert dimensions == [100.0, 100.0]
    project = json.loads((ROOT / "joint_interface.kicad_pro").read_text())
    assert not project.get("board", {}).get("design_settings", {}).get("drc_exclusions", []), (
        "DRC exclusions are not allowed"
    )
    severities = project.get("board", {}).get("design_settings", {}).get("rule_severities", {})
    overrides = {
        name: severity
        for name, severity in severities.items()
        if severity
        != (
            "ignore"
            if name in DEFAULT_IGNORES
            else "warning"
            if name in DEFAULT_WARNINGS
            else "error"
        )
    }
    assert not overrides, f"Non-default DRC severity overrides: {overrides}"
    # Audit a factory-disabled wildcard rule honestly. The generic Polyfuse
    # filter uses PTC/polyfuse names, while KiCad names its generic 1206 Fuse.
    wildcard_mismatches = []
    for ref, comp in expected.items():
        filters = next(
            (
                prop.get("value", "")
                for prop in comp.findall("property")
                if prop.get("name") == "ki_fp_filters"
            ),
            "",
        ).split()
        footprint = comp.findtext("footprint")
        if filters and not any(
            fnmatch.fnmatchcase(footprint, pattern)
            or fnmatch.fnmatchcase(footprint.split(":", 1)[1], pattern)
            for pattern in filters
        ):
            wildcard_mismatches.append(
                {"reference": ref, "footprint": footprint, "symbol_filters": filters}
            )
    assert {entry["reference"] for entry in wildcard_mismatches} <= {"F1"}, (
        "Unreviewed footprint wildcard mismatch"
    )
    drc_path = ROOT / "pcb_drc_report.json"
    drc = json.loads(drc_path.read_text())
    assert {entry["key"] for entry in drc["ignored_checks"]} == DEFAULT_IGNORES, (
        "DRC ignored checks differ from factory defaults"
    )
    all_findings = drc["violations"] + drc["unconnected_items"] + drc["schematic_parity"]
    errors = sum(entry["severity"] == "error" for entry in all_findings)
    warnings = sum(entry["severity"] == "warning" for entry in all_findings)
    local_paths = {
        "U2_supply_to_C7_mm": local_track_distance(
            board, "/+3V3", physical_pad_positions["U2", "8"], physical_pad_positions["C7", "1"]
        ),
        "RS485_A_main_mm": local_track_distance(
            board, "/RS485_A", physical_pad_positions["U2", "6"], physical_pad_positions["J6", "1"]
        ),
        "RS485_B_main_mm": local_track_distance(
            board, "/RS485_B", physical_pad_positions["U2", "7"], physical_pad_positions["J6", "2"]
        ),
    }
    local_paths["RS485_main_length_difference_mm"] = abs(
        local_paths["RS485_A_main_mm"] - local_paths["RS485_B_main_mm"]
    )
    assert local_paths["U2_supply_to_C7_mm"] < 5.0, "Transceiver decoupling path is too long"
    assert local_paths["RS485_main_length_difference_mm"] < 5.0, (
        "Reviewed low-rate paired bus corridor changed"
    )
    bound_files = [
        "joint_interface.kicad_pcb",
        "joint_interface.kicad_sch",
        "joint_interface.kicad_pro",
        "joint_interface.kicad_dru",
        "joint_interface.net.xml",
        "pin_contract.json",
        "pcb_routing_manifest.json",
        "pcb_drc_report.json",
        "fp-lib-table",
        "bom.csv",
    ]
    return {
        "status": "PASS" if not all_findings else "FAIL",
        "kicad_version": drc["kicad_version"],
        "footprint_count": len(footprints),
        "schematic_footprint_count": len(expected),
        "mechanical_footprint_count": 4,
        "net_count": net_count,
        "total_net_count_including_nc": len(xml.findall("./nets/net")),
        "pin_assignments_checked": assigned,
        "physical_pad_nets_checked_including_nc": len(pad_map),
        "track_count": len(tracks),
        "via_count": len(vias),
        "board_dimensions_mm": dimensions,
        "copper_layers": len(layers),
        "copper_layer_names": layers,
        "filled_plane_count": len(zones),
        "footprints_with_courtyard": courtyard_count,
        "native_drc_errors": errors,
        "native_drc_warnings": warnings,
        "native_drc_violations": len(drc["violations"]),
        "unconnected_items": len(drc["unconnected_items"]),
        "schematic_parity": "PASS" if not drc["schematic_parity"] else "FAIL",
        "schematic_parity_issues": len(drc["schematic_parity"]),
        "native_drc_included_severities": drc["included_severities"],
        "native_drc_factory_ignored_checks": drc["ignored_checks"],
        "drc_exclusions": [],
        "rule_severity_overrides": overrides,
        "fabrication_rules_mm": project["board"]["design_settings"]["rules"],
        "independent_footprint_filter_review": {
            "wildcard_matches": len(expected) - len(wildcard_mismatches),
            "lexical_mismatches": wildcard_mismatches,
            "review": "F1 uses the generic 1206 fuse land pattern; the generic Polyfuse symbol suggests PTC/polyfuse names. Manufacturer 1206 package-family review is documented; exact purchasing/land-pattern approval remains required before fabrication.",
        },
        "local_front_copper_paths": local_paths,
        "source_sha256": {name: digest(ROOT / name) for name in bound_files},
        "scope": "Native PCB geometry, enabled default DRC plus explicit fabrication constraints, schematic parity and independent pad/net audit. No fabricated board, measured EMC/thermal/timing/ESD performance or functional-safety qualification.",
    }


if __name__ == "__main__":
    report = verify()
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["status"] == "PASS" else 1)
