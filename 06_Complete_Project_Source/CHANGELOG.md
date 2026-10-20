# Changelog

## Unreleased — 2026-10-20 — repository presentation and reading guides

- Added illustrated mechanical, circuit/PCB and engineering walkthroughs with direct previews, native-file access and clear reading routes.
- Rebuilt the repository landing page and CAD, electronics, theory and simulation folder guides around GitHub viewing. Added source-folder maps and a documentation index.
- Kept the local browser guide in sync with the GitHub guides, including distinct index pages and working chapter links. Presentation templates are versioned and verified during synchronization.
- The v1.2.0 engineering models, board, configuration and packaged release retain their existing design revision.

## 1.2.0 — 2026-10-18 — mechanical interfaces and rigorous review gates

- Repaired the gripper adapter edge ligaments, mating fastening pattern, locating pilot, carriage/nut bridges, finger attachment and service-cover interference. Corrected base counterbore depth; refreshed actual solids, drawings, native models and renders.
- Fixed native FreeCAD saved visibility so the complete assembly opens visibly, with semantic component labels. Added reproducible native/render refresh and independent CAD review scripts.
- Rejected nonfinite/nonphysical configurations, malformed poses/trajectories, segment discontinuities and singular MOVE L continuation. Corrected PID input/state checks and zero-load/signed beam and payload edge cases.
- Separated educational control inertia from actuator sizing: conceptual sizing now uses the greater of the control inertia and mass-derived point-COM inertia bounds. Added independent kinetic-energy regressions and clarified the model limits.
- Fixed rigid grasp orientation in the browser, regulator quiescent heat accounting, stale PCB/wheel/native proof acceptance, numerical residual acceptance and nonfinite saved-evidence handling.
- Bound current validation to source and authoritative inputs; compare every packaged module and use a new output directory for each detached CLI check. Added a project-purpose guide linking the deliverables to the original brief.

The nominal SI specification and pick/place trajectory remain unchanged. This release records a new executed review; earlier releases and their evidence remain historical.

## 1.1.0 — 2026-10-05 — independent engineering review and accessibility

- Corrected analytical TCP deflection to include forearm rotation across the rigid wrist/tool offset; added an independent whole-arm virtual-work regression.
- Selected Bourns MF-NSMF025X-2 explicitly and replaced the generic fuse pads with a project-local manufacturer land pattern; removed the disclosed footprint-filter exception.
- Added a linked 54-part CAD catalog, a theory guide and an electronics component/BOM guide.
- Added automatic framing and individual component inspection to the offline viewer.
- Kept browser documentation links in readable HTML, added folder indexes and improved GitHub navigation and PCB previews.
- Added a GitHub workflow for numerical/analytical software, lint, documentation, organized artifacts and saved electronics connectivity. Native CAD and KiCad checks remain explicitly scoped to the local engineering workflow.

## 1.0.0 — 2026-10-05 — complete digital engineering release

- Complete organized folder structure is the actual repository layout; original Git history is retained.
- Browser-readable project guide/reports and portable Chrome/Edge, FreeCAD and PCB-editor launchers.
- Reproducible presentation synchronization with exact artifact-copy SHA-256 checks.
- Corrected shoulder, wrist and gripper interfaces found by broader all-pair CAD review.
- Routed native KiCad joint/sensor PCB with fabrication exports and actual DRC/connectivity review.
- Refreshed digital-scope traceability and independent clean-wheel verification.

The full validation workflow passed all 33 tests and native KiCad ERC/PCB DRC/connectivity checks. Digital scope is complete; physical performance and manufacturing qualification remain outside the validated scope.

## 0.9.0 — 2026-10-05 — engineering preview

- Original ASTER-6 six-axis architecture and centralized SI configuration.
- Build123d components, six STEP/STL assemblies, engineering interface drawings and actual CAD renders.
- Parallel gripper with moving guides/jaws, original 6×M5 flange and interchangeable adapter.
- FK, bounded numerical IK, geometric Jacobian and independent mathematical verification.
- Workspace/singularity sampling, MOVE J/MOVE L and timed pick-and-place demonstrations.
- Interactive offline CAD twin plus FK animation and reproducible plots/data.
- Gravity torque, conceptual actuator sizing, analytical beam/finger estimates and five numerical parameter studies.
- Saturated PID joint simulation and conceptual native KiCad interface schematic with ERC/net checks.
- Validation runner, packaging verification and evidence-linked engineering documentation.

At the 0.9.0 handover, PCB layout and DRC were unfinished. Version 1.0.0 completes that digital work. Continuous swept collision certification, full coupled dynamics and physical performance remain documented extensions or outside scope; neither release establishes a hardware-ready product.
