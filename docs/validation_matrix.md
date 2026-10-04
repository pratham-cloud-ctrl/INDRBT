# Requirement traceability

Results refer to executed digital evidence, not physical performance. The exact command report is [validation report](../results/validation/validation_report.md); [numerical trials](../results/validation/numerical_validation.json) and [CAD manifest](../results/validation/cad_validation.json) retain details.

| Requirement | Result | Evidence and scope |
|---|---|---|
| MECH-001 | PASS | 54 valid BRep components; 6 assemblies, STEP reimport and actual mesh renders |
| MECH-002 | PASS | 790 mm nominal reach; independent FK and CAD match |
| MECH-003 | PASS for calculation / TARGET for payload | Static gravity and conceptual actuator envelope; no load rating |
| MECH-004 | PASS for digital range / TARGET for force | 90 mm maximum jaw opening; closure tests and gripper energy calculation |
| MECH-005 | PASS for concept | Volumes, material assumptions, covers and cable bores; no production tolerances |
| KIN-001 | PASS | SE(3), known poses, independent planar discrepancy 2.544e-16 m |
| KIN-002 | PASS for tested cases | 60 perturbed-seed FK–IK–FK trials, max position 2.700e-11 m; unreachable and malformed targets tested |
| KIN-003 | PASS | Finite-difference max discrepancy 2.517e-10 |
| KIN-004 | PASS | Configuration/planning tests and every task joint sample |
| CTRL-001 | PASS with interpolation caveat | Analytic cubic/quintic limits; linear interior only, unbounded instantaneous start/stop acceleration |
| CTRL-002 | PASS at samples | MOVE J and MOVE L reconstruction, branch continuity and sampled derivatives |
| CTRL-003 | PASS for model | PID response/tracking saturation and antiwindup; independent inertia/damping plant only |
| ELEC-001 | PASS for schematic concept | 44 components, 28 connected nets, 118 pin assignments and 22 topology checks |
| ELEC-002 | PARTIAL | Native ERC: 0 violations under enabled default rules; PCB not created, DRC not applicable |
| SIM-001 | PASS for geometric sampling | 6000 seeded FK samples; hull/voxel limitations explicit |
| SIM-002 | PASS for ideal task | 9.24398 s, close/open events, home return; no contact dynamics |
| SIM-003 | PARTIAL | 36 pose pair checks plus 65 task samples / 390 selected BRep pair checks; no exhaustive continuous swept collision proof |
| VAL-001 | PASS | 31 tests; 0 failures; 0 errors; details in pytest.xml |
| VAL-002 | PASS | Single executed validation workflow and artifact consistency audit |
| DOC-001 | PASS | Setup, decisions, architecture, report, figures and portable commands |
| DOC-002 | PASS | Claims vocabulary and limitations audited throughout |
| RESEARCH-001 | PASS | Five actual numerical sweeps with data/plots |
| PERF-001 | NOT VERIFIED | ±0.1 mm repeatability remains TARGET |

The v0.9.0 engineering preview is **PARTIALLY COMPLETE**. PCB layout/DRC and exhaustive collision analysis remain open; v1.0.0 is deferred. The digital-only brief does not permit substituting numerical IK residuals for physical repeatability.
