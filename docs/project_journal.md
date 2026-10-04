# Project journal

## 2026-10-05 — environment and specification

Read the complete supplied brief. Found Python 3.12.14 and Git 2.53.0, authenticated GitHub CLI, and portable/installed CAD applications outside PATH. Created an isolated project environment rather than changing the user's existing Python setups. Selected an original Z-Y-Y-X-Y-X design and central SI configuration. Parallel work is divided between numerical motion software, programmatic CAD and conceptual electronics; final integration, analysis, validation and publication remain coordinated here.

## Mechanical iteration

Initial fillets failed on thin covers; selecting the correct thickness-axis edges repaired them. Visual review found gaps between link extrusions and joint supports, so connected cheek supports were added. Exact intersections then found upper/forearm overlap in home and folded poses. The extended elbow clevis and trimmed upper extrusion removed the selected collisions. Gripper pads initially consumed 3 mm of intended opening; pad and finger locations plus carriage width were corrected, then 90 mm open / 0 mm closed gaps were tested. CAD volume comparison motivated conservative lumped mass increases; the revised load analysis uses 23.65 kg assumed total mass. First vertical renders clipped the TCP; automatic camera fitting corrected the images. Six assemblies were imported independently by FreeCAD and drawing pages rendered/inspected.

## Numerical implementation and independent review

FK, numerical IK and Jacobian passed independent known-pose and finite-difference checks. Actual seeded workspace and pick/place results were generated, including velocities and accelerations. Planner review exposed acceptance of a malformed homogeneous MOVE L target; shared pose validation and four regression cases repaired it. A fresh wheel installation reproduced the trajectory command outside the source tree with identical packaged configuration. The initial wheel build helper was missing from the shared runtime; helpers were installed only in the separate verification environment.

## Electronics iteration

First ERC reported off-grid warnings and an inherited-symbol mismatch. Grid placement and a stock symbol corrected these. Datasheet/footprint review corrected diode packages. An initial optional 680 Ω RS-485 bias pair was unsuitable with two terminators at 3.3 V; 330 Ω was selected and bias remains DNP by default. Native ERC of enabled default rules returned zero violations. The exact defaults disabled by KiCad are disclosed in electronics documentation. PCB layout and DRC are deliberately left unresolved rather than represented by an empty board.

## Integration and final audit

Browser testing caught a reserved GLSL keyword in the custom viewer shader; renaming it allowed actual WebGL rendering. Playback/gripper controls and 20 JavaScript/Python transform comparisons were executed; there were no browser page errors afterward. The first validation run caught unused report-builder variables and report links checked before the report existed. Formatting/lint removed the unused variables, and the validation workflow now writes executed evidence before auditing its links. Source/report consistency, tracked-file credential/path/junk scanning and private GitHub publication form the final handover checks. The v0.9.0 preview explicitly retains open PCB/DRC and exhaustive collision scope; v1.0.0 is deferred.
