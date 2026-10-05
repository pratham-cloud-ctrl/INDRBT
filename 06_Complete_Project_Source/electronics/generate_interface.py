"""Rebuild the conceptual KiCad schematic using the installed stock symbol library.

No third-party parser is required. This source also defines the reviewed connector
contract used by verify_netlist.py. Geometry is in KiCad schematic millimetres.
"""
from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import os
from pathlib import Path
import re
import uuid

ROOT = Path(__file__).resolve().parent
NAMESPACE = uuid.UUID("3f673833-f416-42a0-a7cb-89754bfca865")


class Atom(str):
    pass


def parse(source: str):
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', source)
    stack = []
    result = None
    for token in tokens:
        if token == "(":
            node = []
            if stack:
                stack[-1].append(node)
            stack.append(node)
        elif token == ")":
            result = stack.pop()
        else:
            stack[-1].append(json.loads(token) if token.startswith('"') else Atom(token))
    if stack:
        raise ValueError("Unbalanced s-expression")
    return result


def dumps(value):
    if isinstance(value, list):
        return "(" + " ".join(dumps(x) for x in value) + ")"
    if isinstance(value, Atom):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def item(node, key):
    return next((x for x in node if isinstance(x, list) and x and x[0] == key), None)


def nodes(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]


def uid(name):
    return str(uuid.uuid5(NAMESPACE, name))


def atom_node(key, *values):
    return [Atom(key), *[Atom(str(v)) if isinstance(v, (int, float)) else v for v in values]]


def effects(size=1.0, justify=None, hide=False):
    result = [Atom("effects"), [Atom("font"), atom_node("size", size, size)]]
    if justify:
        result.append([Atom("justify"), Atom(justify)])
    if hide:
        result.append([Atom("hide"), Atom("yes")])
    return result


class Schematic:
    def __init__(self, library_dir: Path):
        self.library_dir = library_dir
        self.libraries = {}
        self.cache = {}
        self.content = []
        self.components = []
        self.pin_contract = {}
        self.count = 0
        self.root_id = uid("root")

    def symbol(self, lib_id):
        library, name = lib_id.split(":")
        if library not in self.libraries:
            data = parse((self.library_dir / f"{library}.kicad_sym").read_text(encoding="utf-8"))
            self.libraries[library] = {s[1]: s for s in nodes(data, "symbol")}

        def resolve(n):
            child = copy.deepcopy(self.libraries[library][n])
            inherit = item(child, "extends")
            if not inherit:
                return child
            parent = resolve(inherit[1])
            base = parent[1]
            parent[1] = n
            properties = {p[1]: p for p in nodes(child, "property")}
            parent = [x for x in parent if not (isinstance(x, list) and x and x[0] == "property" and x[1] in properties)]
            parent.extend(properties.values())
            for sub in nodes(parent, "symbol"):
                sub[1] = n + sub[1][len(base):]
            return parent

        if lib_id not in self.cache:
            result = resolve(name)
            result[1] = lib_id
            self.cache[lib_id] = result
        return self.cache[lib_id]

    def add(self, ref, lib_id, value, x, y, pin_nets, angle=0, footprint="", description="", nc=(), dnp=False, datasheet=""):
        x, y = round(round(x / 1.27) * 1.27, 4), round(round(y / 1.27) * 1.27, 4)
        lib = self.symbol(lib_id)
        pins = [pin for sub in nodes(lib, "symbol") for pin in nodes(sub, "pin")]
        properties = {p[1]: p[2] for p in nodes(lib, "property")}
        fp = footprint or properties.get("Footprint", "")
        sym = [Atom("symbol"), [Atom("lib_id"), lib_id], atom_node("at", x, y, angle),
               atom_node("unit", 1), [Atom("in_bom"), Atom("yes")], [Atom("on_board"), Atom("yes")],
               [Atom("dnp"), Atom("yes" if dnp else "no")], [Atom("uuid"), uid(ref)]]
        # Put component IDs/values consistently beside passives and above ICs.
        passive = lib_id.startswith("Device:")
        label_x, label_y = (x + 5, y - 1.2) if passive and angle in (0, 180) else (x, y - 6.0)
        if lib_id.startswith("Interface_"):
            label_y = y - 17
        if lib_id.startswith("Regulator_"):
            label_y = y - 10
        if lib_id.startswith("Connector_"):
            label_x, label_y = x + 4, y - 7
        for name, text, px, py, hidden in [
            ("Reference", ref, label_x, label_y, False),
            ("Value", value, label_x, label_y + 2.2, False),
            ("Footprint", fp, x, y, True),
            ("Datasheet", datasheet or properties.get("Datasheet", ""), x, y, True),
        ]:
            field_angle = angle if angle in (90, 270) else 0
            sym.append([Atom("property"), name, text, atom_node("at", px, py, field_angle), effects(0.95, hide=hidden)])
        self.pin_contract[ref] = {str(k): v for k, v in pin_nets.items()}
        for pin in pins:
            number = str(item(pin, "number")[1])
            sym.append([Atom("pin"), number, [Atom("uuid"), uid(f"{ref}-{number}")]])
        sym.append([Atom("instances"), [Atom("project"), "joint_interface", [Atom("path"), "/" + self.root_id,
                         [Atom("reference"), ref], atom_node("unit", 1)]]])
        self.content.append(sym)
        c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        for pin in pins:
            number = str(item(pin, "number")[1])
            at = item(pin, "at")
            dx, dy = float(at[1]), float(at[2])
            px, py = round(x + c * dx - s * dy, 4), round(y - s * dx - c * dy, 4)
            if number in nc or item(pin, "type") == "no_connect" or pin[1] == "no_connect":
                self.content.append([Atom("no_connect"), atom_node("at", px, py), [Atom("uuid"), uid(f"NC-{ref}-{number}")]])
                continue
            if number not in self.pin_contract[ref]:
                raise ValueError(f"Undefined net for {ref}.{number}")
            net = self.pin_contract[ref][number]
            # Outward 5.08-mm wire from each real library pin, with a local net label.
            # Connectivity therefore comes from native KiCad pins and wires, not text.
            theta = math.radians(float(at[3]) + angle)
            ex, ey = round(px - 5.08 * math.cos(theta), 4), round(py + 5.08 * math.sin(theta), 4)
            self.wire((px, py), (ex, ey), f"{ref}-{number}")
            justify = "right" if ex < px - 0.1 else "left"
            self.content.append([Atom("label"), net, atom_node("at", ex, ey, 0), effects(0.9, justify),
                                 [Atom("uuid"), uid(f"label-{ref}-{number}")]])
        if not lib_id.startswith("power:"):
            self.components.append({"Reference": ref, "Value": value, "Footprint": fp,
                                    "Population": "DNP by default" if dnp else "Fit",
                                    "Description": description or properties.get("Description", ""),
                                    "Datasheet": datasheet or properties.get("Datasheet", "")})

    def wire(self, p1, p2, name):
        self.content.append([Atom("wire"), [Atom("pts"), atom_node("xy", *p1), atom_node("xy", *p2)],
                             [Atom("stroke"), atom_node("width", 0), [Atom("type"), Atom("default")]],
                             [Atom("uuid"), uid("wire-" + name)]])

    def text(self, message, x, y, size=1.4):
        self.count += 1
        self.content.append([Atom("text"), message, atom_node("at", x, y, 0), effects(size, "left"),
                             [Atom("uuid"), uid(f"text-{self.count}")]])

    def write(self):
        project_config = (ROOT.parent / "config" / "robot.yaml").read_text(encoding="utf-8")
        project_name = re.search(r"^name:\s*(.+)$", project_config, re.MULTILINE).group(1).strip()
        document = [Atom("kicad_sch"), atom_node("version", 20250114), [Atom("generator"), "eeschema"],
                    [Atom("generator_version"), "10.0"], [Atom("uuid"), self.root_id], [Atom("paper"), "User", Atom("440"), Atom("330")],
                    [Atom("title_block"), [Atom("title"), project_name + " | Joint / Sensor Interface"],
                     [Atom("date"), "2026-10-05"], [Atom("rev"), "0.1 conceptual"],
                     [Atom("company"), "Digital engineering project"],
                     [Atom("comment"), Atom("1"), "3.3 V logic | 5 V input | External motor drive | No physical validation"]],
                    [Atom("lib_symbols"), *self.cache.values()], *self.content,
                    [Atom("embedded_fonts"), Atom("no")]]
        (ROOT / "joint_interface.kicad_sch").write_text(dumps(document) + "\n", encoding="utf-8")
        # Preserve reviewed PCB fabrication constraints when refreshing the
        # schematic. A new schematic still starts with factory ERC defaults.
        project_path = ROOT / "joint_interface.kicad_pro"
        if not project_path.exists():
            project_path.write_text("{}\n", encoding="utf-8")
        (ROOT / "pin_contract.json").write_text(json.dumps(self.pin_contract, indent=2) + "\n", encoding="utf-8")
        with (ROOT / "bom.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(self.components[0]))
            writer.writeheader()
            writer.writerows(self.components)
        tables = [f'(lib (name "{name}")(type "KiCad")(uri "${{KICAD10_SYMBOL_DIR}}/{name}.kicad_sym")(options "")(descr "Stock KiCad library"))' for name in self.libraries]
        (ROOT / "sym-lib-table").write_text("(sym_lib_table (version 7)\n" + "\n".join(tables) + "\n)\n", encoding="utf-8")
        print(f"Generated {len(self.components)} components, {len(self.pin_contract)} symbols")


def build(libraries):
    s = Schematic(libraries)
    R = "Resistor_SMD:R_0805_2012Metric"
    C = "Capacitor_SMD:C_0805_2012Metric"
    D = "Diode_SMD:D_SOD-123F"
    HEADER = "Connector_PinHeader_2.54mm:PinHeader_1x{n:02d}_P2.54mm_Vertical"

    def connector(ref, n, value, x, y, nets):
        s.add(ref, f"Connector_Generic:Conn_01x{n:02d}", value, x, y, dict(enumerate(nets, 1)), footprint=HEADER.format(n=n))

    def resistor(ref, value, x, y, a, b, angle=90, dnp=False):
        s.add(ref, "Device:R", value, x, y, {1: a, 2: b}, angle, R, dnp=dnp)

    def capacitor(ref, value, x, y, a, b):
        s.add(ref, "Device:C", value, x, y, {1: a, 2: b}, 0, C)

    def diode(ref, value, x, y, cathode, anode, angle=0):
        footprint = "Diode_SMD:D_SMA" if value == "SS14" else D
        datasheet = "https://www.vishay.com/docs/88746/ss12.pdf" if value == "SS14" else "https://assets.nexperia.com/documents/data-sheet/BAT54H.pdf"
        s.add(ref, "Device:D_Schottky", value, x, y, {1: cathode, 2: anode}, angle, footprint, datasheet=datasheet)

    s.text("1 | PROTECTED LOGIC SUPPLY", 16, 17, 2)
    connector("J1", 2, "5V INPUT", 30, 43, ["+5V_IN", "GND"])
    s.add("F1", "Device:Polyfuse", "0.25A hold", 61, 40, {1: "+5V_IN", 2: "+5V_FUSED"}, 90,
          "Fuse:Fuse_1206_3216Metric", "Resettable fuse, conceptual 250 mA hold; select trip curve before fabrication")
    diode("D1", "SS14", 96, 40, "+5V_PROTECTED", "+5V_FUSED", 180)
    capacitor("C1", "10uF / 10V", 123, 51, "+5V_PROTECTED", "GND")
    s.add("U1", "Regulator_Linear:AP2112K-3.3", "AP2112K-3.3", 161, 42,
          {1: "+5V_PROTECTED", 2: "GND", 3: "+5V_PROTECTED", 5: "+3V3"}, nc=("4",))
    capacitor("C2", "4.7uF / 10V", 196, 51, "+3V3", "GND")
    resistor("R1", "1k", 215, 39, "+3V3", "LED_A")
    s.add("D2", "Device:LED", "GREEN", 246, 39, {1: "GND", 2: "LED_A"}, 0,
          "LED_SMD:LED_0805_2012Metric", "3.3 V rail status indicator")
    for i, net in enumerate(("+5V_IN", "+5V_PROTECTED", "GND"), 1):
        s.add(f"#FLG0{i}", "power:PWR_FLAG", "PWR_FLAG", 25 + i * 45, 76, {1: net})
    s.text("5.0 V +/-5% regulated source. 3.3 V total load budget <=150 mA.\nPWR_FLAG: external source / diode-passive source declaration.\nC1/C2 X7R; effective output capacitance >=1 uF after DC bias.", 17, 91, 1.2)

    s.text("2 | EXTERNAL MCU / LOGIC CONTRACT", 278, 17, 2)
    connector("J2", 16, "MCU 3V3 I/O", 306, 46,
              ["+3V3", "GND", "ENC_A", "ENC_B", "ENC_Z", "LIMIT_N", "STEP_CMD", "DIR_CMD", "ENABLE_CMD",
               "DRIVE_FAULT_N", "UART_TX", "UART_RX", "RS485_DIR", "ESTOP_MON_N", "GND", "GND"])
    s.text("MCU is external; signal directions in electronics documentation.\nGPIO must have Schmitt inputs on ENC_* and LIMIT_N.\n3.3 V supply is an output: do not back-power this interface.", 332, 41, 1.1)
    s.text("3 | QUADRATURE ENCODER INPUTS", 16, 113, 2)
    connector("J3", 5, "ENCODER 3V3", 30, 134, ["+3V3", "GND", "ENC_A_RAW", "ENC_B_RAW", "ENC_Z_RAW"])
    for i, name in enumerate(("A", "B", "Z")):
        y = 132 + i * 35
        raw, filtered = f"ENC_{name}_RAW", f"ENC_{name}"
        resistor(f"R{2+i}", "1k", 82, y, raw, filtered)
        capacitor(f"C{3+i}", "100pF / 50V", 122, y + 8, filtered, "GND")
        diode(f"D{3+2*i}", "BAT54H", 162, y - 4, "+3V3", filtered, 270)
        diode(f"D{4+2*i}", "BAT54H", 189, y + 8, filtered, "GND", 270)
    s.text("3.3 V push-pull / open collector encoder only; add source pull-ups\nfor open collector. RC nominal 100 ns; selected as an educational\nshort-cable interface. Clamp diodes provide limited surge protection.\nCable ESD / EMC, hysteresis and edge timing need physical verification.", 16, 227, 1.15)

    s.text("4 | LIMIT + E-STOP MONITOR", 235, 113, 2)
    connector("J4", 2, "NC LIMIT", 256, 137, ["LIMIT_RAW", "GND"])
    resistor("R5", "1k", 299, 135, "LIMIT_RAW", "LIMIT_N")
    resistor("R6", "10k", 326, 135, "+3V3", "LIMIT_N", 0)
    capacitor("C6", "100nF / 50V", 357, 142, "LIMIT_N", "GND")
    diode("D9", "BAT54H", 385, 134, "+3V3", "LIMIT_N", 270)
    diode("D10", "BAT54H", 385, 155, "LIMIT_N", "GND", 270)
    connector("J7", 2, "E-STOP AUX NC", 256, 181, ["ESTOP_MON_N", "GND"])
    resistor("R7", "10k", 302, 180, "+3V3", "ESTOP_MON_N", 0)
    resistor("R8", "10k", 348, 180, "ENABLE_DRV", "GND", 0)
    s.text("NC switch closed: LIMIT_N ~0.30 V; open/broken wire: high.\nNominal release RC 1 ms; closure RC 91 us. Debounce in MCU.\nE-STOP AUX is monitoring only. An independent safety relay\nmust interrupt drive STO / actuator energy outside this board.", 235, 206, 1.15)

    s.text("5 | EXTERNAL DRIVE COMMAND", 16, 253, 2)
    connector("J5", 6, "3V3 DRIVE I/O", 46, 272,
              ["STEP_DRV", "DIR_DRV", "ENABLE_DRV", "DRIVE_FAULT_N", "GND", "GND"])
    resistor("R9", "330", 96, 263, "STEP_CMD", "STEP_DRV")
    resistor("R10", "330", 96, 275, "DIR_CMD", "DIR_DRV")
    resistor("R11", "330", 96, 287, "ENABLE_CMD", "ENABLE_DRV")
    resistor("R12", "10k", 146, 274, "+3V3", "DRIVE_FAULT_N", 0)
    s.text("Drive must accept 3.3 V STEP/DIR and active-high ENABLE.\nFAULT is 3.3 V open drain. No motor voltage/current on board.\nENABLE default low. A firmware fault must lower ENABLE.", 171, 271, 1.05)

    s.text("6 | HALF-DUPLEX RS-485", 235, 237, 2)
    s.add("U2", "Interface_UART:LTC2850xS8", "LTC2850IS8", 276, 269,
          {1: "UART_RX", 2: "RS485_DIR", 3: "RS485_DIR", 4: "UART_TX", 5: "GND", 6: "RS485_A", 7: "RS485_B", 8: "+3V3"},
          footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm")
    capacitor("C7", "100nF / 50V", 320, 259, "+3V3", "GND")
    resistor("R13", "10k", 319, 282, "RS485_DIR", "GND", 0)
    connector("J6", 3, "RS485 BUS", 389, 267, ["RS485_A", "RS485_B", "GND"])
    resistor("R14", "330", 349, 252, "+3V3", "RS485_A", 0, dnp=True)
    resistor("R15", "330", 349, 273, "RS485_B", "GND", 0, dnp=True)
    resistor("R16", "120", 370, 283, "RS485_A", "TERM_LINK", 0)
    s.add("JP1", "Jumper:Jumper_2_Open", "END TERM", 390, 291,
          {1: "TERM_LINK", 2: "RS485_B"}, 0, "Jumper:SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm")
    s.text("R14/R15 DNP by default: LTC2850 has internal receiver failsafe.\nOptional bias at one node only. JP1 closed only at two bus ends.\n250 kbit/s target; non-isolated short bench bus; common ground.\nSix joint nodes + gripper node; bus firmware remains conceptual.", 236, 311, 1.1)
    s.write()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", type=Path, default=os.environ.get("KICAD10_SYMBOL_DIR"))
    args = parser.parse_args()
    if not args.symbols:
        parser.error("Provide --symbols PATH or KICAD10_SYMBOL_DIR")
    build(args.symbols)
