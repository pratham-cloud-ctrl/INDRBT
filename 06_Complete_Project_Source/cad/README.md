# CAD source and models

[Project home](../../README.md) · [Illustrated mechanical tour](../docs/cad_tour.md) · [54-part catalog](../docs/component_catalog.md) · [CAD method and validation](../docs/04_cad.md)

This folder contains ASTER-6's reproducible mechanical design and generated models: **54 components and six complete pose assemblies**.

[Inspect the robot online](https://aster-six-engineering-showcase.warmkiwi64.chatgpt.site/#robot) to orbit, move joints, adjust the gripper, isolate parts and play the task without downloading files. Native files and reproduction steps below are optional for offline inspection or editing.

**[Native-file and local-pack guide](../docs/cad_downloads.md)** — open the actual STEP assembly, individual parts or FreeCAD model, understand their units/history and find the local inspection ZIPs. Consolidated public ZIP hosting is still pending; the guide states its status.

![The ASTER-6 solid model in its home configuration](renders/hero.png)

## Open the right file

| Purpose | File or folder | What it contains |
|---|---|---|
| Inspect the complete solid assembly | [freecad/aster6_home.FCStd](freecad/aster6_home.FCStd) | FreeCAD home pose; 54 visible solids with descriptive labels, rigid groups and assumed materials |
| Exchange exact solid geometry | [Home STEP](exports/STEP/assembly_home.step) · [all STEP files](exports/STEP) | Six positioned assemblies and 54 individual parts |
| Use triangle meshes | [All STL files](exports/STL) | Six assembly meshes and 54 individual part meshes; assembly meshes retain separate contacting bodies |
| Read the mechanism on GitHub | [Mechanical tour](../docs/cad_tour.md) · [drawings](../docs/drawings/engineering_interfaces.pdf) | Rendered assembly, gripper, six poses and dimensioned interface drawings |
| Inspect the render scene | [renders/aster6_home.blend](renders/aster6_home.blend) | Blender scene using the exported CAD meshes |
| Move the robot and isolate a part | [Public interactive viewer](https://aster-six-engineering-showcase.warmkiwi64.chatgpt.site/#robot) · [optional offline copy](../simulations/aster6_twin.html) | Online joint controls and playback; download only for offline use |

STEP, STL and FCStd links provide optional downloads for native inspection or editing. Use FreeCAD for the native model or STEP solids. After downloading on Windows, [OPEN_FREECAD_MODEL.cmd](../../OPEN_FREECAD_MODEL.cmd) opens the native assembly and [OPEN_3D_VIEWER.cmd](../../OPEN_3D_VIEWER.cmd) opens the offline browser viewer. PNG/SVG previews also display directly on GitHub.

## Edit and regenerate

| Authoritative source | Role |
|---|---|
| [config/robot.yaml](../config/robot.yaml) | Shared SI configuration for dimensions, joint poses and engineering assumptions |
| [build123d/parameters.py](build123d/parameters.py) | Converts configured lengths from metres to CAD millimetres |
| [build123d/geometry.py](build123d/geometry.py) | Constructs the component solids and their interfaces |
| [build123d/assembly.py](build123d/assembly.py) | Applies the six joint-frame transforms |
| [build123d/export_all.py](build123d/export_all.py) | Exports STEP/STL, local meshes and CAD measurements |
| [freecad/inspect_step.py](freecad/inspect_step.py) | Independently imports assembly STEP files and generates the native FreeCAD inspection assembly |

The Python geometry is parametric. The saved FreeCAD model is a solid export with inspection metadata, not the construction feature tree. For reproducible changes, edit the shared configuration or geometry source and regenerate. Save intentional manual FreeCAD edits under a separate filename; close older views without saving before replacing their generated file.

From `06_Complete_Project_Source`, with the project's CAD dependencies, FreeCAD and Blender installed:

```bash
python scripts/generate_cad.py
python -m robotarm.demo --all
python scripts/refresh_cad.py
```

The final command refreshes native inspection, renders and CAD evidence. To audit saved outputs without regenerating them, run `python scripts/review_cad.py`. See [the full workflow](../docs/04_cad.md#refresh-native-cad-evidence) for tool discovery and overrides.

## Coordinates and evidence

CAD lengths are **millimetres**; numerical kinematics use **metres**. Individual part files are authored in local groups `base`, `j1` through `j6`. Open a complete assembly for positioned parts; [assembly_meshes.json](exports/meshes/assembly_meshes.json) records local meshes and pose transforms. Motor, gearbox and bearing **envelopes** are simplified spatial representations with assumed materials.

[CAD inspection](../results/validation/final_cad_review.json), [named-pose clearance](../results/validation/cad_assembly_clearance.json) and [sampled-task clearance](../results/validation/cad_motion_clearance.json) state what was checked. Drawings are concept interfaces rather than production drawings; geometric validity and sampled clearance do not establish hardware performance.

The numbered [01_CAD_Models](../../01_CAD_Models) folder contains organized copies for browsing. Regenerate here, then use the source project's presentation sync to refresh those copies.
