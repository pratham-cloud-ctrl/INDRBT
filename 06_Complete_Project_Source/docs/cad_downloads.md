# Open the engineering files

[Inspect the robot online](https://aster-six-engineering-showcase.warmkiwi64.chatgpt.site/#robot) · [Inspect the PCB online](https://aster-six-engineering-showcase.warmkiwi64.chatgpt.site/#pcb) · [Documentation index](README.md)

The public browser showcase is the quickest viewing route. For optional inspection in a CAD or electronics application, use the actual engineering files below. Repository links require access to the private GitHub repository; a local project copy opens directly from disk.

**Download status — 21 October 2026:** the consolidated public download page and focused inspection packs are prepared, but that page has not been published because the Sites connection cannot currently access the project. No public ZIP download is claimed here. The existing browser showcase remains available.

## Choose a model format

| What you want | Actual file or folder | Open it with |
|---|---|---|
| Complete solid assembly | [Home STEP](../cad/exports/STEP/assembly_home.step) | FreeCAD or another CAD application supporting STEP |
| Another complete configuration | [Six STEP assemblies](../cad/exports/STEP) — files named `assembly_home`, `assembly_extended`, `assembly_folded`, `assembly_vertical`, `assembly_pick` and `assembly_place` | CAD application, **File → Open** or **File → Import** |
| One component | [Individual STEP files](../../01_CAD_Models/STEP/Individual_Parts) | CAD application, **File → Open** or **File → Import** |
| Native FreeCAD inspection assembly | [aster6_home.FCStd](../cad/freecad/aster6_home.FCStd) | FreeCAD, **File → Open** |
| Triangle meshes | [STL exports](../cad/exports/STL) | Mesh viewer or a CAD application supporting STL |
| Dimensioned interfaces | [Engineering drawings PDF](drawings/engineering_interfaces.pdf) | Any PDF viewer |

**STEP is standard solid-geometry exchange without construction history.** Its geometry can be inspected or modified using the receiving application's tools; it does not include the original parametric feature sequence. The native FreeCAD file contains 54 named, saved solids and inspection metadata, rather than a sketch-based construction tree.

The reproducible parametric design lives in [Build123d geometry](../cad/build123d/geometry.py), [assembly transforms](../cad/build123d/assembly.py) and the [shared SI configuration](../config/robot.yaml). Read [CAD reproduction](04_cad.md#refresh-native-cad-evidence) before changing the design or regenerating its exports.

### Open or import safely

1. Save or extract the chosen file to a normal folder. On GitHub, use the file page's **Download raw file** control when available; do not copy its displayed text into another application.
2. Start FreeCAD or your CAD application, then choose **File → Open** for a new document, or **File → Import** when deliberately adding geometry to an existing document. Select the `.step` or `.FCStd` file using the file-type filter.
3. Use **Fit all** if the model is outside the current view. Open an `assembly_*.step` file to see positioned parts together.
4. Save intentional edits as a **new filename**. Generated files are refreshed by the project scripts; an older open document should not overwrite a newer generated file.

CAD exports use **millimetres**; numerical calculations use **metres**. Individual parts retain local group frames, so opening all part files at a common origin does not assemble the robot. Use a complete assembly or the native FreeCAD home model for that purpose.

## Open the KiCad project

| Native item | Actual file or folder |
|---|---|
| Project entry point | [joint_interface.kicad_pro](../electronics/joint_interface.kicad_pro) |
| Schematic | [joint_interface.kicad_sch](../electronics/joint_interface.kicad_sch) |
| Routed PCB | [joint_interface.kicad_pcb](../electronics/joint_interface.kicad_pcb) |
| Project-local footprint resolution | [fp-lib-table](../electronics/fp-lib-table) and [ASTER_Interface.pretty](../electronics/ASTER_Interface.pretty) |
| Symbol resolution and rules | [sym-lib-table](../electronics/sym-lib-table) and [joint_interface.kicad_dru](../electronics/joint_interface.kicad_dru) |
| Readable circuit and layers | [Schematic PDF](../electronics/exports/joint_interface.pdf) and [PCB layer PDF](../electronics/exports/pcb_layers.pdf) |

With **KiCad 10** and its standard libraries installed, keep the project, schematic, PCB, rule files, library tables and local footprint folder together. Open the `.kicad_pro` file in KiCad, then open the schematic or PCB editor. Open the `.kicad_sch` or `.kicad_pcb` directly only when their surrounding project context is retained. The custom F1 footprint resolves through `${KIPRJMOD}`; downloading the board alone omits that editable library context.

For component roles, supply assumptions and verification scope, read the [circuit tour](electronics_tour.md), [component guide](electronics_components.md) and [electronics chapter](05_electronics.md). Native files and rule checks remain digital design evidence, without physical qualification.

## Focused inspection ZIPs on this computer

These archives exist in the local `07_Releases` folder. They are ignored by Git and are **not downloads hosted in the GitHub file tree**. Open that local folder to use them; when reading on GitHub, use the tracked engineering files above instead.

| Local archive | Intended use |
|---|---|
| `ASTER-6_STEP_STL_CAD.zip` | Extract the CAD exchange files, then open a complete STEP assembly |
| `ASTER-6_FreeCAD_Model.zip` | Extract and open the native saved-solid FreeCAD model |
| `ASTER-6_KiCad_Project.zip` | Extract the project with its local library context, then open the `.kicad_pro` file |
| `ASTER-6_PCB_STEP.zip` | Import the native board STEP into mechanical CAD; 100 × 100 × 11.54 mm, with fitted component and copper geometry |
| `ASTER-6_Browser_Inspection.zip` | Extract the self-contained browser inspection pack for offline viewing |
| `ASTER-6_Inspection_With_CAD.zip` | Extract the browser viewers together with the selected CAD and KiCad downloads for combined offline inspection |

Downloading or opening these files is optional. The online viewers remain the immediate inspection route, and the [source project guide](../README.md) covers local reproduction.
