"""Independent STEP inspection and a visible, named native FreeCAD assembly.

Run with FreeCADCmd cad/freecad/inspect_step.py. GUI documents already open
are preserved when main() is invoked through FreeCAD's Python console.
"""

import hashlib
import json
import math
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile

import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def visible_gui_state(path, names, center):
    """Add standard view providers so a headless FCStd opens visibly.

    Solid properties and GUI properties occupy separate archive entries.
    Visibility, display mode and a fitted camera require no GUI runtime.
    """
    root = ET.Element("Document", SchemaVersion="1", HasExpansion="1")
    ET.SubElement(root, "Expand")
    providers = ET.SubElement(root, "ViewProviderData", Count=str(len(names)))
    for name in names:
        view = ET.SubElement(providers, "ViewProvider", name=name, expanded="0", treeRank="-1")
        props = ET.SubElement(view, "Properties", Count="2", TransientCount="0")
        visibility = ET.SubElement(
            props, "Property", name="Visibility", type="App::PropertyBool", status="1"
        )
        ET.SubElement(visibility, "Bool", value="true")
        display = ET.SubElement(
            props, "Property", name="DisplayMode", type="App::PropertyEnumeration", status="1"
        )
        ET.SubElement(display, "Integer", value="0")
    direction = App.Vector(1, -1, 1)
    direction.normalize()
    rotation = App.Rotation(App.Vector(0, 0, 1), direction)
    position = center + direction * 1500
    axis = rotation.Axis
    camera = (
        "OrthographicCamera {\n viewportMapping ADJUST_CAMERA\n"
        f" position {position.x} {position.y} {position.z}\n"
        f" orientation {axis.x} {axis.y} {axis.z} {rotation.Angle}\n"
        " nearDistance 1\n farDistance 4000\n aspectRatio 1.5\n"
        " focalDistance 1500\n height 900\n}\n"
    )
    ET.SubElement(root, "Camera", settings=camera)
    with zipfile.ZipFile(path) as archive:
        entries = {n: archive.read(n) for n in archive.namelist() if n != "GuiDocument.xml"}
    temp = path.with_suffix(".FCStd.tmp")
    with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
        archive.writestr(
            "GuiDocument.xml", ET.tostring(root, encoding="utf-8", xml_declaration=True)
        )
    temp.replace(path)


def inspect_existing_native(cad):
    """Validate a saved native file without rewriting its BRep or view data."""
    path = ROOT / "cad/freecad/indrbt_home.FCStd"
    before = digest(path)
    opened_before = set(App.listDocuments())
    doc = App.openDocument(str(path))
    mapping = []
    try:
        doc.recompute()
        for i, component in enumerate(cad["components"], 1):
            obj = doc.getObject(f"Component{i:02}")
            if obj is None or not obj.Shape.isValid() or len(obj.Shape.Solids) != 1:
                raise ValueError(f"Invalid saved native component: {component['name']}")
            if obj.ComponentName != component["name"] or obj.Label != component["name"]:
                raise ValueError(f"Saved native semantic label mismatch: {component['name']}")
            if obj.getGroupOfProperty("ComponentName") != "INDRBT":
                raise ValueError("Saved native property group does not match project identity")
            error = abs(obj.Shape.Volume - component["volume_mm3"]) / component["volume_mm3"]
            if error > 1e-6:
                raise ValueError(f"Saved native volume mismatch: {component['name']}")
            mapping.append(
                {"object": obj.Name, "component": component["name"], "volume_relative_error": error}
            )
        if doc.Label != "indrbt_home":
            raise ValueError("Saved native document label does not match filename")
        with zipfile.ZipFile(path) as archive:
            gui = ET.fromstring(archive.read("GuiDocument.xml"))
            visible = sum(
                item.get("value") == "true"
                for item in gui.findall(".//Property[@name='Visibility']/Bool")
            )
        if visible != len(cad["components"]):
            raise ValueError("Saved native assembly has hidden components")
    finally:
        if doc.Name not in opened_before:
            App.closeDocument(doc.Name)
    if digest(path) != before:
        raise ValueError("Read-only native inspection changed saved bytes")
    return mapping


def main(rebuild_native=True):
    cad = json.loads((ROOT / "results/validation/cad_validation.json").read_text())
    mesh_path = ROOT / "cad/exports/meshes/assembly_meshes.json"
    mesh = json.loads(mesh_path.read_text())
    prior = App.ActiveDocument.Name if App.ActiveDocument else None
    out = {
        "application": "FreeCAD",
        "version": ".".join(App.Version()[:3]),
        "assemblies": {},
        "step_sha256": {},
    }
    native_path = ROOT / "cad/freecad/indrbt_home.FCStd"
    for name in cad["poses"]:
        path = ROOT / f"cad/exports/STEP/assembly_{name}.step"
        shape = Part.Shape()
        shape.read(str(path))
        b = shape.BoundBox
        out["assemblies"][name] = {
            "valid": shape.isValid(),
            "solids": len(shape.Solids),
            "volume_mm3": shape.Volume,
            "bbox_mm": [b.XLength, b.YLength, b.ZLength],
        }
        out["step_sha256"][name] = digest(path)
        if not shape.isValid() or len(shape.Solids) != cad["component_count"]:
            raise ValueError(f"Invalid imported assembly: {name}")
        if name != "home":
            continue
        if not rebuild_native:
            out["native_components"] = inspect_existing_native(cad)
            continue
        doc = App.newDocument("INDRBTHomeInspection")
        candidates = list(shape.Solids)
        mapping = []
        for i, c in enumerate(cad["components"]):
            T = mesh["pose_transforms"]["home"][c["group"]]
            expected = [
                sum(T[j][k] * c["center_of_geometry_mm"][k] for k in range(3)) + T[j][3]
                for j in range(3)
            ]

            def score(solid):
                center = solid.CenterOfMass
                distance = math.sqrt(
                    sum((a - v) ** 2 for a, v in zip(expected, (center.x, center.y, center.z)))
                )
                return distance + abs(solid.Volume - c["volume_mm3"]) / c["volume_mm3"] * 1000

            solid = min(candidates, key=score)
            candidates.remove(solid)
            if score(solid) > 1e-3:
                raise ValueError(f"Cannot match imported native solid: {c['name']}")
            obj = doc.addObject("Part::Feature", f"Component{i + 1:02}")
            obj.Shape = solid
            obj.Label = c["name"]
            for prop, value in [
                ("ComponentName", c["name"]),
                ("RigidGroup", c["group"]),
                ("AssumedMaterial", c["material"]),
                ("RepresentationRole", c["role"]),
            ]:
                obj.addProperty("App::PropertyString", prop, "INDRBT")
                setattr(obj, prop, value)
            mapping.append(
                {"object": obj.Name, "component": c["name"], "matching_score_mm": score(solid)}
            )
        doc.recompute()
        names = [obj.Name for obj in doc.Objects]
        doc.saveAs(str(native_path))
        App.closeDocument(doc.Name)
        visible_gui_state(native_path, names, b.Center)
        out["native_components"] = mapping
    if prior and prior in App.listDocuments():
        App.setActiveDocument(prior)
    out["native_sha256"] = digest(native_path)
    out["mesh_sha256"] = digest(mesh_path)
    out["saved_visibility_count"] = cad["component_count"]
    out["inspection_mode"] = "rebuild_native" if rebuild_native else "verify_existing_no_save"
    out["source_sha256"] = {
        "geometry.py": digest(ROOT / "cad/build123d/geometry.py"),
        "robot.yaml": digest(ROOT / "config/robot.yaml"),
    }
    (ROOT / "results/validation/cad_freecad_inspection.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8"
    )
    print(json.dumps(out), flush=True)
    return out


if __name__ == "__main__":
    main(rebuild_native="--verify-existing" not in sys.argv)
    if not getattr(App, "GuiUp", False):
        os._exit(0)
