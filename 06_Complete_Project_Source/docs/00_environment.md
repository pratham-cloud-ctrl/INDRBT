# Environment audit — 2026-10-05

Audit performed before geometry implementation. No system CAD application was installed or replaced.

| Tool | Observed availability | Project use |
|---|---|---|
| Python | 3.12.14, working isolated virtual environment | Numerical software, analyses and Build123d |
| Git | 2.53.0.windows.3 | Coherent development milestones |
| GitHub CLI | Authenticated account; repository scope available | Initial private publication; repository made public by explicit owner instruction on 21 October 2026 |
| Build123d | Initially absent from discovered Python environments; 0.13.0 installed in project environment | Reproducible BRep, STEP and STL |
| OpenSCAD | 2021.01 command line verified | Available; unnecessary duplicate geometry avoided |
| FreeCAD | 1.1.4 installation found, command-line executable available | Independent STEP inspection |
| KiCad | CLI 10.0.6 verified | Native conceptual schematic/PCB, netlist, ERC/DRC and fabrication exports |
| Blender | Existing executable found | Available for CAD visualization |
| NumPy/SciPy | 2.5.3 / 1.18.1 | Transforms, bounded least-squares IK and analysis |
| Matplotlib | 3.11.2 | Reproducible scientific plots |
| pytest / Ruff | 9.1.1 / 0.16.10 | Numerical tests and code checks |

`pip check` returned **No broken requirements found** after dependency installation. The final dependency snapshot is `requirements-lock.txt`. The bundled Python was selected instead of the Windows Store alias. Existing application paths were discovered from installation records; scripts expose command-line overrides instead of requiring another machine to reproduce those paths.

The selected toolchain is Python + Build123d/OpenCascade + SciPy + Matplotlib + KiCad CLI. Analytical beam calculations are used in place of unsupported FEA. Tests and reports distinguish available software from actions actually performed.
