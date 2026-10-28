# Independent engineering review — current revision

The final review checks the project against its digital engineering brief and
asks whether another student can inspect the models, understand the theory and
reproduce the evidence. The result is supported by executed checks, rather than
an assurance that every possible use has been proved. The 17–18 October 2026 review
revisited the original goals and deliberately probed beyond the earlier passing
file/hash tests. [Project purpose and goals](project_alignment.md) explains the
intended connected demonstration; the [journal](project_journal.md) preserves
the findings in context.

## Additional corrections in version 1.2.0

| Area | Demonstrated issue and resulting behavior |
|---|---|
| Native CAD access | The saved assembly opened with all 54 parts hidden. Visible named parts, camera state and a native GUI check now make the model inspectable immediately. Material colours are shown in the browser and Blender renders. |
| Mechanical interfaces | Adapter holes broke the outer edge; the rear cover overlapped the adapter; screw/carriage and removable-finger attachments lacked coherent support. The revised 54-part geometry includes a wider adapter, locating pilot, matching rear fasteners, nut bridges, supported finger holes and a top service hatch. Counterbore depth now matches the drawing. |
| Motion and model inputs | NaN/nonphysical configurations, small invalid transform/segment errors and malformed trajectories could pass. Domain/finite checks and explicit absolute tolerances reject them. Sampled singular MOVE L continuation now raises a useful error instead of reporting misleading endpoint accelerations. |
| Loads and control | Actuator sizing reused control inertia below the same assumed mass model. Separate mass-derived point-inertia bounds now inform sizing; default PID plants are unchanged. Zero-load/signed beam and invalid controller/payload cases have explicit behavior and regressions. |
| Electronics and proof freshness | Regulator heat omitted a small quiescent allowance. A scratch disconnected board could reuse old clean DRC evidence. The heat balance and source binding are corrected; fresh native checks of the design remain clean. |
| Browser demonstration | The attached object translated with the TCP but did not rotate. Its ideal attachment now follows the complete tool pose, checked in the actual browser. |
| Acceptance and reproduction | Residual limits, nonfinite saved values, native CAD source/artifact freshness, complete wheel module comparison, fresh CLI output directories and source/input revision binding now prevent the reproduced false passes. |

The current [executed report](../results/validation/validation_report.md),
[native CAD review](../results/validation/final_cad_review.json),
[theory audit](../results/validation/final_theory_review.json) and
[electronics audit](../results/validation/final_electronics_review.json)
record the actual results and exact revision. Earlier beam and fuse corrections
remain part of the engineering history and are summarized below.

The [software boundary review](../results/validation/software_boundary_review.json)
retains reproduced failure cases, focused regression evidence and an unchanged
nominal-task comparison. The [circuit review](../results/validation/electronics_circuit_review.json)
records native/library inspection and explains generic power-audit notices
without concealing them or treating heuristics as native rule violations.

| Area | Finding and correction | Retained evidence |
|---|---|---|
| CAD and mechanical components | All 54 components and six assemblies agree across STEP/STL/native data. Five jaw openings, drawing dimensions and hole patterns were checked. A role/material/native-object catalog makes every part traceable. | [CAD review](../results/validation/final_cad_review.json), [component catalog](component_catalog.md) |
| Structural theory | The earlier serial TCP estimate omitted forearm slope acting over the rigid wrist/tool offset. Both link displacements and both downstream rotation terms are now included. A separate whole-arm unit-load/virtual-work integration checks the result. | [Theory review](../results/validation/final_theory_review.json), [mechanical model](03_mechanical_analysis.md), [structural data](../results/mechanical/structural.json) |
| Electronics and PCB | The generic fuse footprint differed from the manufacturer drawing. The exact Bourns MF-NSMF025X-2 selection now has project-local 1.0 × 1.6 mm pads with a 2.0 mm gap. Native schematic/board checks and fabrication exports were rerun; footprint assignments, BOM, physical pads and export hashes are audited. | [Electronics review](../results/validation/final_electronics_review.json), [PCB evidence](../electronics/pcb_verification.json), [component guide](electronics_components.md) |
| Viewing and navigation | All 54 components can be isolated and automatically framed in the offline viewer. Browser documents link to readable HTML counterparts. Native CAD/PCB data has explicit application launchers, and folder README indexes separate viewing from editing. | [Executed browser checks](../results/validation/viewer_validation.json), project guide and organization manifest at the repository root |
| Software and reproducibility | Central parameters, numerical/analytical regressions, native checks, saved artifact consistency and a detached wheel installation establish their recorded scope. GitHub automation covers the software and saved-artifact subset; full CAD/native KiCad checks use local engineering tools. | [Executed validation](../results/validation/validation_report.md), [wheel evidence](../results/validation/packaging_validation.json), [GitHub workflow](https://github.com/pratham-cloud-ctrl/INDRBT/actions/workflows/validation.yml) |

The readable [theory guide](theory_guide.md) explains the equations, units and
assumptions. The [engineering report](engineering_report.md), [requirements
matrix](validation_matrix.md) and [journal](project_journal.md) expose design
choices, actual corrections and limitations. Physical payload/repeatability,
production qualification and continuous swept collision certification remain
outside this digital brief. Assumed values are not certified component ratings.
