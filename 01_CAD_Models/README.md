# CAD models · Arm, joints and parallel gripper

[← Project home](../README.md) · [Electronics](../04_Electronics/README.md) · [Theory](../03_Reports_and_Results/README.md)

**[Open the interactive 3D robot](https://pratham-cloud-ctrl.github.io/industrial-robot-arm-digital-twin/#robot)** — orbit, move joints, adjust the gripper and inspect all 54 parts directly in your browser. No download or CAD software is required.

**Start with the [illustrated mechanical tour](../06_Complete_Project_Source/docs/cad_tour.md).** It explains the structure, joint groups, flange and gripper using the actual models and dimensioned drawings.

![Six actual CAD poses of ASTER-6](Preview_Images/poses.png)

## Inspect the design here

| What you want to see | GitHub preview |
|---|---|
| Rotate, move joints and isolate parts in 3D | [Public interactive robot viewer](https://pratham-cloud-ctrl.github.io/industrial-robot-arm-digital-twin/#robot) |
| Complete arm and six configurations | [Assembly image](Preview_Images/hero.png) · [Pose sheet](Preview_Images/poses.png) |
| Jaw mechanism, guide rods and tool interface | [Gripper close-up](Preview_Images/gripper.png) · [Mechanical tour](../06_Complete_Project_Source/docs/cad_tour.md) |
| Base, flange, link and gripper dimensions | [Three-page drawing PDF](Drawings/engineering_interfaces.pdf) |
| Every part's function, material and filename | [54-part component catalog](../06_Complete_Project_Source/docs/component_catalog.md) |
| Model construction and clearance evidence | [CAD methodology](../06_Complete_Project_Source/docs/04_cad.md) · [Independent CAD review](../03_Reports_and_Results/Validation/final_cad_review.json) |

[The online viewer](https://pratham-cloud-ctrl.github.io/industrial-robot-arm-digital-twin/#robot) is the main inspection route. GitHub may decline the STL preview; [the STL assembly](STL/Assemblies/assembly_home.stl) remains available as engineering data for download.

## Download and edit

**[Public CAD download release](https://github.com/pratham-cloud-ctrl/industrial-robot-arm-digital-twin/releases/tag/inspection-2026-10-21)** — STEP/STL exchange geometry, the native FreeCAD saved-solid model and a combined offline inspection pack. The [opening guide](../06_Complete_Project_Source/docs/cad_downloads.md) explains millimetre units and format/history differences. The published GitHub Pages showcase includes the browser viewers and download controls.

For optional native inspection or editing, download and extract the repository. **OPEN_FREECAD_MODEL.cmd** in the parent folder opens the solid assembly on Windows. On other systems use FreeCAD **File → Open**.

| Format | Direct file / folder | Intended use |
|---|---|---|
| **FreeCAD `.FCStd`** | [Home assembly](FreeCAD/aster6_home.FCStd) | Inspect 54 named solid objects in FreeCAD |
| **STEP** | [Home assembly](STEP/Assemblies/assembly_home.step) · [Six assemblies](STEP/Assemblies) · [54 individual parts](STEP/Individual_Parts) | Solid geometry for CAD inspection and exchange |
| **STL** | [Home assembly](STL/Assemblies/assembly_home.stl) · [Six assemblies](STL/Assemblies) · [54 individual parts](STL/Individual_Parts) | Triangular mesh viewing; assembly files contain multiple contacting parts |
| **Blender `.blend`** | [Saved scene](Blender/aster6_home.blend) | Inspect the named scene and render setup |
| **Parametric source** | [Geometry construction](../06_Complete_Project_Source/cad/build123d/geometry.py) · [SI configuration](../06_Complete_Project_Source/config/robot.yaml) | Change the design and regenerate the exports |

For immediate browser inspection, [open the public robot viewer](https://pratham-cloud-ctrl.github.io/industrial-robot-arm-digital-twin/#robot) to orbit, move joints and isolate every component; the image/PDF previews above are also available. GitHub's native-file pages provide a **Download raw file** control for optional CAD inspection or editing. After downloading the complete project, **OPEN_3D_VIEWER.cmd** opens the optional offline viewer.

The saved FreeCAD model contains exported solids. Its reproducible parametric construction lives in Python/Build123d. Exported lengths are **millimetres**; individual components retain their local assembly-group frame. Complete pose assemblies already place the parts together. See the [CAD source map](../06_Complete_Project_Source/cad/README.md) for reproduction.
