# ASTER-6 · Industrial robot arm and parallel gripper

**Version 1.0.0 · DIGITAL SCOPE COMPLETE · Digital engineering design**

An original six-axis robot with parametric CAD, kinematics, workspace analysis, motion planning, simulated PID control, a parallel-jaw gripper and a conceptual KiCad joint/sensor interface.

![Actual ASTER-6 CAD assembly](01_CAD_Models/Preview_Images/hero.png)

## Start here

Download the complete release bundle or clone this repository. Double-click **OPEN_PROJECT_HOME.cmd** for the project guide or **OPEN_3D_VIEWER.cmd** to view and move the robot. Use **OPEN_FREECAD_MODEL.cmd** for CAD editing and **OPEN_PCB_LAYOUT.cmd** for the KiCad board. These Windows launchers locate installed Chrome/Edge, FreeCAD and KiCad; they avoid incorrect file associations. On other systems, open [START_HERE.html](START_HERE.html) or [the interactive viewer](02_Simulation_and_Animation/Interactive_3D_Viewer.html) in a browser.

GitHub displays HTML source. Download the project to run its offline viewer.

![Forward-kinematics line-model pick-and-place animation](02_Simulation_and_Animation/Trajectories/pick_place_fk.gif)

## Organized project folders

| Folder | Contents |
|---|---|
| [01_CAD_Models](01_CAD_Models) | FreeCAD and Blender models, STEP/STL assemblies and individual parts, drawings and renders |
| [02_Simulation_and_Animation](02_Simulation_and_Animation) | Offline interactive 3D viewer, pick/place data, workspace and PID results |
| [03_Reports_and_Results](03_Reports_and_Results) | Browser-readable engineering reports, mechanical/research data and validation evidence |
| [04_Electronics](04_Electronics) | Native KiCad schematic/PCB, BOM, board views, Gerbers/drill and verification reports |
| [05_Reference_and_Project_Notes](05_Reference_and_Project_Notes) | Index to original source documents and browser-readable reports |
| [06_Complete_Project_Source](06_Complete_Project_Source) | Reproducible CAD, analysis, software, tests, electronics generators and authoritative configuration |

Presentation folders contain verified copies. The complete source folder is authoritative; regenerate outputs there and run `python scripts/sync_presentation.py` to refresh the organized copies. The copy hashes are in [ORGANIZATION_MANIFEST.json](ORGANIZATION_MANIFEST.json).

## Engineering and verification

Read the [engineering report](06_Complete_Project_Source/docs/engineering_report.md), [scope audit](06_Complete_Project_Source/docs/digital_scope_audit.md), [requirements matrix](06_Complete_Project_Source/docs/validation_matrix.md), [executed validation](06_Complete_Project_Source/results/validation/validation_report.md) and [detailed source README](06_Complete_Project_Source/README.md).

The robot has six revolute joints, 790 mm nominal shoulder-centred reach and a 90 mm parallel-jaw opening. Payload 4 kg and repeatability ±0.1 mm are design targets. No physical robot or electronics were built. Analytical stiffness, independent-axis PID, sampled clearance and conceptual PCB checks establish their stated digital scope; they do not establish certified hardware performance, EMC, production suitability or functional safety.

## Reproduce

From the cloned repository:

```bash
cd 06_Complete_Project_Source
python -m venv .venv
```

Activate the environment, then:

```bash
python -m pip install -e ".[cad,dev]"
python -m robotarm.demo --all
python scripts/run_validation.py --full
python scripts/sync_presentation.py
```

KiCad 10 is required for native electronics checks. Build123d and the numerical libraries are installed by the CAD/development extras. FreeCAD and Blender support independent CAD inspection and rendering. Detailed tool commands and engineering assumptions are in the source documentation.

MIT-licensed original source. Third-party software and libraries retain their licenses.
