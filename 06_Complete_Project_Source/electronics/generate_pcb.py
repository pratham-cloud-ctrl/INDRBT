"""Build the routed joint interface with KiCad's installed pcbnew Python API.

Run with KiCad's bundled Python, e.g. <kicad>/bin/python electronics/generate_pcb.py.
No third-party autorouter or geometry library is required. The deterministic
two-signal-layer maze router respects pad/track/via obstacles; native KiCad DRC
is the final geometry/connectivity authority, not the router's occupancy grid.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import heapq
import json
import math
import os
from pathlib import Path
import sys
import uuid
import xml.etree.ElementTree as ET

import pcbnew as p

ROOT = Path(__file__).resolve().parent
NS = uuid.UUID("b9f6b1d3-9c26-41f5-bebc-cfd28f251534")
STEP = 0.25
BOUNDS = (20.0, 20.0, 120.0, 120.0)
CLEARANCE = 0.20
SIGNAL_WIDTH = 0.25
VIA_DIAMETER = 0.60
VIA_DRILL = 0.30

# All dimensions are millimetres. Pin-header pin 1 is the placement origin.
PLACEMENT = {
    "J1": (27, 32, 0),
    "F1": (35, 32, 0),
    "D1": (43, 32, 180),
    "C1": (50, 30, 0),
    "U1": (55, 32, 0),
    "C2": (60, 30, 180),
    "R1": (66, 30, 90),
    "D2": (66, 35, 90),
    "J2": (27, 43, 0),
    "J3": (113, 32, 0),
    "J4": (113, 61, 0),
    "J5": (113, 77, 0),
    "J6": (97, 112, 90),
    "J7": (27, 98, 0),
    "R7": (35, 98, 180),
    "R2": (92, 38, 180),
    "C3": (74, 38, 0),
    "D3": (81, 35, 180),
    "D4": (81, 41, 0),
    "R3": (92, 47, 180),
    "C4": (74, 47, 0),
    "D5": (81, 44, 180),
    "D6": (81, 50, 0),
    "R4": (92, 56, 180),
    "C5": (74, 56, 0),
    "D7": (81, 53, 180),
    "D8": (81, 59, 0),
    "R5": (92, 66, 180),
    "R6": (83, 63, 0),
    "C6": (74, 66, 0),
    "D9": (83, 69, 180),
    "D10": (83, 74, 0),
    "R9": (89, 80, 0),
    "R10": (89, 85, 0),
    "R11": (89, 90, 0),
    "R8": (100, 90, 0),
    "R12": (102, 95, 0),
    "U2": (76, 98, 0),
    "C7": (82.5, 95, 0),
    "R13": (70, 103, 0),
    "R14": (88, 94, 0),
    "R15": (90, 106, 180),
    "R16": (94, 116, 0),
    "JP1": (99, 116, 0),
}


def uid(name):
    return p.KIID(str(uuid.uuid5(NS, name)))


def vector(x, y):
    return p.VECTOR2I(p.FromMM(x), p.FromMM(y))


def xy(pos):
    return (p.ToMM(pos.x), p.ToMM(pos.y))


class Router:
    """Conservative occupancy-grid router with 45-degree tracks and vias."""

    def __init__(self, board, nets):
        self.board = board
        self.nets = nets
        self.nx = round((BOUNDS[2] - BOUNDS[0]) / STEP) + 1
        self.ny = round((BOUNDS[3] - BOUNDS[1]) / STEP) + 1
        self.size = self.nx * self.ny
        self.mask = [[0] * self.size for _ in range(2)]
        self.sequence = 0
        self.journal = []
        self.net_cells = defaultdict(set)
        # Edges and mechanical holes are obstacles for every signal net.
        for layer in range(2):
            for iy in range(self.ny):
                for ix in range(self.nx):
                    if min(ix, iy, self.nx - 1 - ix, self.ny - 1 - iy) * STEP < 1.0:
                        self.mask[layer][iy * self.nx + ix] = 1
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                if pad.GetAttribute() == p.PAD_ATTRIB_NPTH:
                    self.disk(xy(pad.GetPosition()), 2.65, 1, [0, 1])
                    continue
                net = pad.GetNetCode()
                bits = 1 << net if net else 1
                bbox = pad.GetBoundingBox()
                # Grid guard is in addition to actual requested DRC clearance.
                guard = CLEARANCE + SIGNAL_WIDTH / 2 + STEP * 0.3
                x0, y0 = xy(bbox.GetPosition())
                x1 = x0 + p.ToMM(bbox.GetWidth())
                y1 = y0 + p.ToMM(bbox.GetHeight())
                layers = [0, 1] if pad.GetAttribute() == p.PAD_ATTRIB_PTH else [0]
                self.rectangle(x0 - guard, y0 - guard, x1 + guard, y1 + guard, bits, layers)

    def cell(self, pt, layer=0):
        x, y = pt
        ix = round((x - BOUNDS[0]) / STEP)
        iy = round((y - BOUNDS[1]) / STEP)
        return layer * self.size + iy * self.nx + ix

    def point(self, cell):
        index = cell % self.size
        return (BOUNDS[0] + (index % self.nx) * STEP, BOUNDS[1] + (index // self.nx) * STEP)

    def blocked(self, cell, net):
        return self.mask[cell // self.size][cell % self.size] & ~(1 << net)

    def rectangle(self, x0, y0, x1, y1, bits, layers):
        lo_x = max(0, math.ceil((x0 - BOUNDS[0]) / STEP))
        hi_x = min(self.nx - 1, math.floor((x1 - BOUNDS[0]) / STEP))
        lo_y = max(0, math.ceil((y0 - BOUNDS[1]) / STEP))
        hi_y = min(self.ny - 1, math.floor((y1 - BOUNDS[1]) / STEP))
        for layer in layers:
            for iy in range(lo_y, hi_y + 1):
                for ix in range(lo_x, hi_x + 1):
                    self.mask[layer][iy * self.nx + ix] |= bits

    def disk(self, pt, radius, bits, layers):
        x, y = pt
        lo_x = max(0, math.ceil((x - radius - BOUNDS[0]) / STEP))
        hi_x = min(self.nx - 1, math.floor((x + radius - BOUNDS[0]) / STEP))
        lo_y = max(0, math.ceil((y - radius - BOUNDS[1]) / STEP))
        hi_y = min(self.ny - 1, math.floor((y + radius - BOUNDS[1]) / STEP))
        for iy in range(lo_y, hi_y + 1):
            for ix in range(lo_x, hi_x + 1):
                if (BOUNDS[0] + ix * STEP - x) ** 2 + (BOUNDS[1] + iy * STEP - y) ** 2 <= radius**2:
                    for layer in layers:
                        self.mask[layer][iy * self.nx + ix] |= bits

    def segment_clear(self, a, b, net, layer, radius=0.0):
        count = max(1, math.ceil(math.dist(a, b) / (STEP / 2)))
        for i in range(count + 1):
            pt = (a[0] + (b[0] - a[0]) * i / count, a[1] + (b[1] - a[1]) * i / count)
            cell = self.cell(pt, layer)
            if self.blocked(cell, net):
                return False
            if radius:
                ix = cell % self.size % self.nx
                iy = cell % self.size // self.nx
                d = math.ceil(radius / STEP)
                for dy in range(-d, d + 1):
                    for dx in range(-d, d + 1):
                        if dx * dx + dy * dy <= d * d:
                            idx = (iy + dy) * self.nx + ix + dx
                            if 0 <= idx < self.size and self.mask[layer][idx] & ~(1 << net):
                                return False
        return True

    def add_track(self, a, b, net, layer=0, width=SIGNAL_WIDTH):
        if math.dist(a, b) < 1e-6:
            return
        track = p.PCB_TRACK(self.board)
        track.SetStart(vector(*a))
        track.SetEnd(vector(*b))
        track.SetLayer(p.F_Cu if layer == 0 else p.B_Cu)
        track.SetWidth(p.FromMM(width))
        track.SetNet(self.nets[net])
        self.sequence += 1
        track.SetUuid(uid(f"track-{self.sequence}"))
        self.board.Add(track)
        count = max(1, math.ceil(math.dist(a, b) / (STEP / 2)))
        for i in range(count + 1):
            pt = (a[0] + (b[0] - a[0]) * i / count, a[1] + (b[1] - a[1]) * i / count)
            self.disk(pt, width / 2 + CLEARANCE + SIGNAL_WIDTH / 2 + STEP * 0.3, 1 << net, [layer])
            self.net_cells[net].add(self.cell(pt, layer))

    def add_via(self, pt, net):
        via = p.PCB_VIA(self.board)
        via.SetPosition(vector(*pt))
        via.SetWidth(p.FromMM(VIA_DIAMETER))
        via.SetDrill(p.FromMM(VIA_DRILL))
        via.SetViaType(p.VIATYPE_THROUGH)
        via.SetLayerPair(p.F_Cu, p.B_Cu)
        via.SetNet(self.nets[net])
        self.sequence += 1
        via.SetUuid(uid(f"via-{self.sequence}"))
        self.board.Add(via)
        self.disk(
            pt, VIA_DIAMETER / 2 + CLEARANCE + SIGNAL_WIDTH / 2 + STEP * 0.3, 1 << net, [0, 1]
        )
        self.net_cells[net].add(self.cell(pt, 0))
        self.net_cells[net].add(self.cell(pt, 1))

    def via_clear(self, cell, net):
        pt = self.point(cell)
        # Existing obstacles are inflated for a track; a via needs extra radius.
        return all(
            self.segment_clear(pt, pt, net, layer, (VIA_DIAMETER - SIGNAL_WIDTH) / 2 + STEP * 0.2)
            for layer in [0, 1]
        )

    def plane_connection(self, pad):
        if pad.GetAttribute() == p.PAD_ATTRIB_PTH:
            return
        net = pad.GetNetCode()
        a = xy(pad.GetPosition())
        # Prefer the outside of the IC body; avoid via-in-pad fabrication.
        fp = pad.GetParentFootprint()
        centre = xy(fp.GetPosition())
        outward = 1 if a[0] >= centre[0] else -1
        offsets = [(outward * d, 0) for d in [1.25, 1.5, 1.75, 2.0]]
        offsets += [(0, d) for d in [1.25, -1.25, 1.5, -1.5, 2, -2]]
        offsets += [(dx, dy) for dx in [-1.5, 1.5] for dy in [-1.5, 1.5]]
        for dx, dy in offsets:
            v = self.point(self.cell((a[0] + dx, a[1] + dy)))
            if self.via_clear(self.cell(v), net) and self.segment_clear(a, v, net, 0):
                self.add_track(a, v, net, 0, 0.3)
                self.add_via(v, net)
                self.journal.append(
                    {
                        "net": self.nets[net].GetNetname(),
                        "plane_fanout": f"{fp.GetReference()}.{pad.GetNumber()}",
                        "via_mm": v,
                    }
                )
                return
        raise RuntimeError(f"No plane fanout for {fp.GetReference()}.{pad.GetNumber()}")

    def route(self, pad_a, pad_b, width=SIGNAL_WIDTH):
        net = pad_a.GetNetCode()
        assert net == pad_b.GetNetCode()
        a, b = xy(pad_a.GetPosition()), xy(pad_b.GetPosition())
        starts = [self.cell(a, 0)]
        targets = {self.cell(b, 0)}
        if pad_a.GetAttribute() == p.PAD_ATTRIB_PTH:
            starts.append(self.cell(a, 1))
        if pad_b.GetAttribute() == p.PAD_ATTRIB_PTH:
            targets.add(self.cell(b, 1))
        for cell in starts + list(targets):
            if self.blocked(cell, net):
                raise RuntimeError(
                    f"Blocked pad grid {pad_a.GetParentFootprint().GetReference()}.{pad_a.GetNumber()} -> {pad_b.GetParentFootprint().GetReference()}.{pad_b.GetNumber()}"
                )

        def heuristic(cell):
            q = self.point(cell)
            dx, dy = abs(q[0] - b[0]) / STEP, abs(q[1] - b[1]) / STEP
            return max(dx, dy) + (math.sqrt(2) - 1) * min(dx, dy)

        frontier = []
        distance = {}
        parent = {}
        for cell in starts:
            distance[cell] = 0.0
            heapq.heappush(frontier, (heuristic(cell), 0.0, cell))
            parent[cell] = None
        goal = None
        moves = [
            (-1, 0, 1),
            (1, 0, 1),
            (0, -1, 1),
            (0, 1, 1),
            (-1, -1, 1.4143),
            (-1, 1, 1.4143),
            (1, -1, 1.4143),
            (1, 1, 1.4143),
        ]
        while frontier:
            _, cost, cell = heapq.heappop(frontier)
            if cost > distance.get(cell, math.inf) + 1e-9:
                continue
            if cell in targets:
                goal = cell
                break
            layer = cell // self.size
            index = cell % self.size
            ix, iy = index % self.nx, index // self.nx
            for dx, dy, step_cost in moves:
                nx, ny = ix + dx, iy + dy
                if not (0 <= nx < self.nx and 0 <= ny < self.ny):
                    continue
                other = layer * self.size + ny * self.nx + nx
                if self.blocked(other, net):
                    continue
                if (
                    dx
                    and dy
                    and (
                        self.blocked(layer * self.size + iy * self.nx + nx, net)
                        or self.blocked(layer * self.size + ny * self.nx + ix, net)
                    )
                ):
                    continue
                previous = parent.get(cell)
                turn = 0.0
                if previous is not None and previous // self.size == layer:
                    old_delta = cell % self.size - previous % self.size
                    if other % self.size - cell % self.size != old_delta:
                        turn = 0.12
                value = cost + step_cost + turn
                if value < distance.get(other, math.inf):
                    distance[other] = value
                    parent[other] = cell
                    heapq.heappush(frontier, (value + heuristic(other) * 1.0001, value, other))
            other = (1 - layer) * self.size + index
            if not self.blocked(other, net) and self.via_clear(cell, net):
                value = cost + 24.0
                if value < distance.get(other, math.inf):
                    distance[other] = value
                    parent[other] = cell
                    heapq.heappush(frontier, (value + heuristic(other), value, other))
        if goal is None:
            raise RuntimeError(f"Unroutable {self.nets[net].GetNetname()}")
        cells = []
        while goal is not None:
            cells.append(goal)
            goal = parent[goal]
        cells.reverse()
        layer = cells[0] // self.size
        self.add_track(a, self.point(cells[0]), net, layer, width)
        segment_start = cells[0]
        previous = cells[0]
        direction = None
        for cell in cells[1:]:
            new_layer = cell // self.size
            delta = cell % self.size - previous % self.size
            if new_layer != layer:
                self.add_track(self.point(segment_start), self.point(previous), net, layer, width)
                self.add_via(self.point(cell), net)
                segment_start = cell
                direction = None
                layer = new_layer
            elif direction is not None and delta != direction:
                self.add_track(self.point(segment_start), self.point(previous), net, layer, width)
                segment_start = previous
                direction = delta
            else:
                direction = delta
            previous = cell
        self.add_track(self.point(segment_start), self.point(cells[-1]), net, layer, width)
        self.add_track(self.point(cells[-1]), b, net, layer, width)
        self.journal.append(
            {
                "net": self.nets[net].GetNetname(),
                "from": f"{pad_a.GetParentFootprint().GetReference()}.{pad_a.GetNumber()}",
                "to": f"{pad_b.GetParentFootprint().GetReference()}.{pad_b.GetNumber()}",
                "maze_cells": len(cells),
            }
        )


def add_text(board, value, location, size=1.2, layer=p.F_SilkS):
    text = p.PCB_TEXT(board)
    text.SetText(value)
    text.SetPosition(vector(*location))
    text.SetTextSize(vector(size, size))
    text.SetTextThickness(p.FromMM(0.15))
    text.SetLayer(layer)
    board.Add(text)


def make_plane(board, net, layer):
    zone = p.ZONE(board)
    zone.SetNet(net)
    zone.SetLayer(layer)
    zone.SetLocalClearance(p.FromMM(CLEARANCE))
    zone.SetMinThickness(p.FromMM(0.25))
    zone.SetPadConnection(p.ZONE_CONNECTION_THERMAL)
    zone.SetThermalReliefGap(p.FromMM(0.25))
    zone.SetThermalReliefSpokeWidth(p.FromMM(0.30))
    poly = zone.Outline()
    poly.NewOutline()
    for x, y in [(21, 21), (119, 21), (119, 119), (21, 119)]:
        poly.Append(p.FromMM(x), p.FromMM(y))
    zone.SetUuid(uid(f"plane-{layer}"))
    board.Add(zone)


def build(footprint_directory):
    xml = ET.parse(ROOT / "joint_interface.net.xml")
    board = p.BOARD()
    board.SetCopperLayerCount(4)
    settings = board.GetDesignSettings()
    settings.m_MinClearance = p.FromMM(CLEARANCE)
    settings.m_CopperEdgeClearance = p.FromMM(0.50)
    settings.m_TrackMinWidth = p.FromMM(0.20)
    settings.m_ViasMinSize = p.FromMM(VIA_DIAMETER)
    settings.m_ViasMinAnnularWidth = p.FromMM(0.15)
    settings.m_MinThroughDrill = p.FromMM(VIA_DRILL)
    settings.m_HoleClearance = p.FromMM(0.25)
    settings.m_HoleToHoleMin = p.FromMM(0.25)
    settings.m_SilkClearance = p.FromMM(0.15)
    settings.m_MinSilkTextHeight = p.FromMM(0.8)
    settings.m_MinSilkTextThickness = p.FromMM(0.12)
    nets = {}
    net_names = {}
    for node in xml.findall("./nets/net"):
        code = int(node.get("code"))
        net = p.NETINFO_ITEM(board, node.get("name"), code)
        board.Add(net)
        nets[code] = net
        net_names[node.get("name")] = code
    sch = (ROOT / "joint_interface.kicad_sch").read_text(encoding="utf-8")
    import re

    root_uuid = re.search(r'\(uuid "?([\w-]+)"?\)', sch).group(1)
    footprints = {}
    pads = {}
    for comp in xml.findall("./components/comp"):
        ref = comp.get("ref")
        if ref.startswith("#"):
            continue
        lib, name = comp.findtext("footprint").split(":")
        fp = p.FootprintLoad(str(footprint_directory / f"{lib}.pretty"), name)
        assert fp is not None, f"Missing footprint {lib}:{name}"
        fp.SetReference(ref)
        fp.SetValue(comp.findtext("value"))
        fp.GetField("Datasheet").SetText(
            comp.findtext("datasheet") or comp.findtext("fields/field[@name='Datasheet']") or ""
        )
        # Stock solder jumpers are BOM-excluded; this schematic explicitly
        # includes its termination jumper, so preserve the schematic contract.
        fp.SetAttributes(fp.GetAttributes() & ~p.FP_EXCLUDE_FROM_BOM)
        fp.SetPath(p.KIID_PATH(f"/{root_uuid}/{comp.findtext('tstamps')}"))
        fp.SetUuid(uid(ref))
        fp.SetFPID(p.LIB_ID(lib, name))
        x, y, angle = PLACEMENT[ref]
        fp.SetPosition(vector(x, y))
        fp.SetOrientationDegrees(angle)
        fp.Reference().SetTextSize(vector(1, 1))
        fp.Reference().SetTextThickness(p.FromMM(0.15))
        fp.Reference().SetTextAngle(p.EDA_ANGLE(0, p.DEGREES_T))
        fp.Reference().SetPosition(vector(x, y - 2.4 if not ref.startswith("J") else y - 3.0))
        if ref in {f"D{i}" for i in range(3, 11)}:
            fp.Reference().SetPosition(vector(x + 4.5, y))
        for name, position in {
            "U2": (76, 93.6),
            "JP1": (104, 116),
            "J6": (106, 112),
            "R6": (87, 63),
            "R14": (88, 96.4),
        }.items():
            if ref == name:
                fp.Reference().SetPosition(vector(*position))
        fp.Value().SetVisible(False)
        if ref in ["R14", "R15"]:
            fp.SetAttributes(fp.GetAttributes() | p.FP_DNP)
        board.Add(fp)
        footprints[ref] = fp
        for pad in fp.Pads():
            pads[(ref, pad.GetNumber())] = pad
    for node in xml.findall("./nets/net"):
        net = nets[int(node.get("code"))]
        for pin in node.findall("node"):
            key = (pin.get("ref"), pin.get("pin"))
            if key in pads:
                pads[key].SetNet(net)
    for index, (x, y) in enumerate([(25, 25), (115, 25), (115, 115), (25, 115)], 1):
        fp = p.FootprintLoad(
            str(footprint_directory / "MountingHole.pretty"), "MountingHole_3.2mm_M3"
        )
        fp.SetReference(f"H{index}")
        fp.SetValue("M3 mounting")
        fp.SetAttributes(
            fp.GetAttributes()
            | p.FP_BOARD_ONLY
            | p.FP_EXCLUDE_FROM_BOM
            | p.FP_EXCLUDE_FROM_POS_FILES
        )
        fp.SetPosition(vector(x, y))
        fp.SetUuid(uid(f"H{index}"))
        fp.Reference().SetPosition(vector(x, y + 4.2))
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        board.Add(fp)
    corners = [(20, 20), (120, 20), (120, 120), (20, 120)]
    for index, (a, b) in enumerate(zip(corners, corners[1:] + corners[:1])):
        edge = p.PCB_SHAPE(board)
        edge.SetShape(p.SHAPE_T_SEGMENT)
        edge.SetStart(vector(*a))
        edge.SetEnd(vector(*b))
        edge.SetLayer(p.Edge_Cuts)
        edge.SetWidth(p.FromMM(0.05))
        edge.SetUuid(uid(f"outline-{index}"))
        board.Add(edge)
    router = Router(board, nets)
    # Local decoupling connection before general fanout/routing.
    router.route(pads["U2", "8"], pads["C7", "1"])
    plane_codes = {net_names["/+3V3"], net_names["/GND"]}
    for key, pad in sorted(pads.items()):
        if pad.GetNetCode() in plane_codes:
            router.plane_connection(pad)
    # Short paired A/B main paths: fixed reviewed front-copper corridor.
    bus_paths = {
        "RS485_A": [
            ("U2", "6"),
            (81, 98.635),
            (82, 99.635),
            (93, 99.635),
            (97, 103.635),
            (97, 112),
            ("J6", "1"),
        ],
        "RS485_B": [
            ("U2", "7"),
            (81.6, 97.365),
            (83.07, 98.835),
            (93.7, 98.835),
            (99.54, 104.675),
            (99.54, 112),
            ("J6", "2"),
        ],
    }
    paired = set()
    for name, path in bus_paths.items():
        net = net_names["/" + name]
        pts = [
            xy(pads[value].GetPosition()) if isinstance(value[0], str) else value for value in path
        ]
        for a, b in zip(pts, pts[1:]):
            if not router.segment_clear(a, b, net, 0):
                raise RuntimeError(f"Paired route obstructed: {name} {a} {b}")
            router.add_track(a, b, net)
        paired.add((path[0], path[-1]))
    # Each multi-pad signal net gets a nearest-neighbour spanning tree. Two
    # explicitly paired bus endpoints are already joined, so seed their tree.
    for node in sorted(xml.findall("./nets/net"), key=lambda n: int(n.get("code"))):
        net = int(node.get("code"))
        if net in plane_codes or node.get("name").startswith("unconnected-"):
            continue
        keys = [
            (v.get("ref"), v.get("pin"))
            for v in node.findall("node")
            if (v.get("ref"), v.get("pin")) in pads
        ]
        connected = [keys.pop(0)]
        for a, b in paired:
            if a in connected and b in keys:
                connected.append(b)
                keys.remove(b)
            elif b in connected and a in keys:
                connected.append(a)
                keys.remove(a)
        while keys:
            _, a, b = min(
                (math.dist(xy(pads[a].GetPosition()), xy(pads[b].GetPosition())), a, b)
                for a in connected
                for b in keys
            )
            print(f"Route {node.get('name')} {a} -> {b}", flush=True)
            width = 0.40 if "5V" in node.get("name") else SIGNAL_WIDTH
            router.route(pads[a], pads[b], width)
            connected.append(b)
            keys.remove(b)
    make_plane(board, nets[net_names["/GND"]], p.In1_Cu)
    make_plane(board, nets[net_names["/+3V3"]], p.In2_Cu)
    add_text(board, "ASTER-6  JOINT / SENSOR INTERFACE", (69, 24), 1.5)
    add_text(board, "5 V INPUT ONLY  |  3.3 V LOGIC", (68, 26), 0.9)
    add_text(board, "ENCODER", (105, 29), 1.0)
    add_text(board, "NC LIMIT", (105, 60), 1.0)
    add_text(board, "EXTERNAL DRIVE", (103, 73), 1.0)
    add_text(board, "MCU GPIO", (36, 63), 1.0)
    add_text(board, "E-STOP AUX MONITOR", (43, 108), 0.9)
    add_text(board, "RS-485  A B GND", (97, 109), 1.0)
    add_text(board, "DNP BIAS", (88, 92), 0.9)
    add_text(board, "TERM: CLOSE AT BUS END", (84, 119 - 0.9), 0.9)
    add_text(board, "DIGITAL PROTOTYPE  |  NOT A SAFETY CONTROLLER", (68, 113), 0.9)
    board.BuildConnectivity()
    p.SaveBoard(str(ROOT / "joint_interface.kicad_pcb"), board)
    # The SWIG API exposes the stackup descriptor as an opaque pointer. Supply
    # the native stackup syntax, then let the native CLI parse/save/check it.
    # Total nominal thickness includes 4x35 um Cu and 2x10 um solder mask.
    board_path = ROOT / "joint_interface.kicad_pcb"
    stackup = """
        (stackup
            (layer "F.SilkS" (type "Top Silk Screen"))
            (layer "F.Paste" (type "Top Solder Paste"))
            (layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
            (layer "F.Cu" (type "copper") (thickness 0.035))
            (layer "dielectric 1" (type "prepreg") (thickness 0.20) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
            (layer "In1.Cu" (type "copper") (thickness 0.035))
            (layer "dielectric 2" (type "core") (thickness 1.04) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
            (layer "In2.Cu" (type "copper") (thickness 0.035))
            (layer "dielectric 3" (type "prepreg") (thickness 0.20) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
            (layer "B.Cu" (type "copper") (thickness 0.035))
            (layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
            (layer "B.Paste" (type "Bottom Solder Paste"))
            (layer "B.SilkS" (type "Bottom Silk Screen"))
            (copper_finish "ENIG")
            (dielectric_constraints no)
        )
    """
    source = board_path.read_text(encoding="utf-8")
    source = source.replace("(setup\n", "(setup\n" + stackup, 1)
    board_path.write_text(source, encoding="utf-8")
    (ROOT / "pcb_routing_manifest.json").write_text(
        json.dumps(
            {
                "generator": "generate_pcb.py / KiCad pcbnew",
                "kicad_version": p.Version(),
                "board_size_mm": [100, 100],
                "copper_layers": 4,
                "nominal_thickness_mm": 1.6,
                "stackup_materials": "FR4 / 35 um copper / ENIG target; manufacturer stackup approval required",
                "stackup_intent": [
                    "F.Cu signals/components",
                    "In1.Cu GND plane",
                    "In2.Cu +3V3 plane",
                    "B.Cu signals",
                ],
                "signal_track_width_mm": SIGNAL_WIDTH,
                "power_5V_track_width_mm": 0.40,
                "clearance_mm": CLEARANCE,
                "via_diameter_mm": VIA_DIAMETER,
                "via_drill_mm": VIA_DRILL,
                "placements_mm": PLACEMENT,
                "router_connections": router.journal,
                "paired_bus_main_route_lengths_mm": {
                    name: sum(
                        math.dist(
                            xy(pads[a].GetPosition()) if isinstance(a[0], str) else a,
                            xy(pads[b].GetPosition()) if isinstance(b[0], str) else b,
                        )
                        for a, b in zip(path, path[1:])
                    )
                    for name, path in bus_paths.items()
                },
                "authority": "Native KiCad DRC and schematic parity, not this generation manifest",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return board


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--footprints", type=Path, default=os.environ.get("KICAD10_FOOTPRINT_DIR"))
    args = parser.parse_args()
    directory = (
        args.footprints
        or Path(sys.executable).resolve().parent.parent / "share" / "kicad" / "footprints"
    )
    if not directory.is_dir():
        parser.error("Stock footprint directory unavailable; provide --footprints.")
    build(directory)
    print("Board created; run native DRC and inspect before claiming completion.")
