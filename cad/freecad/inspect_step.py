"""Independent FreeCAD/OpenCascade STEP inspection and native home assembly.

Run with FreeCADCmd cad/freecad/inspect_step.py. No GUI window is necessary.
"""

import json
import os
from pathlib import Path
import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parents[2]
out = {"application": "FreeCAD", "version": ".".join(App.Version()[:3]), "assemblies": {}}
for name in ("home", "extended", "folded", "vertical", "pick", "place"):
    shape = Part.Shape()
    shape.read(str(ROOT / f"cad/exports/STEP/assembly_{name}.step"))
    b = shape.BoundBox
    out["assemblies"][name] = {
        "valid": shape.isValid(),
        "solids": len(shape.Solids),
        "volume_mm3": shape.Volume,
        "bbox_mm": [b.XLength, b.YLength, b.ZLength],
    }
    if name == "home":
        doc = App.newDocument("ASTER6Home")
        for i, solid in enumerate(shape.Solids):
            obj = doc.addObject("Part::Feature", f"Component{i + 1:02}")
            obj.Shape = solid
        doc.recompute()
        doc.saveAs(str(ROOT / "cad/freecad/aster6_home.FCStd"))
(ROOT / "results/validation/cad_freecad_inspection.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out), flush=True)
os._exit(0)
