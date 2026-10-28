# INDRBT requirements

INDRBT is an original, digital-only six-revolute-axis manipulator for an educational pick-and-place cell. Dimensions, joint conventions, masses, motion limits and control gains are authoritative in `config/robot.yaml`. Algorithms use metres, radians, kilograms and seconds. CAD converts metres to millimetres at the export boundary.

The 320/280 mm upper-arm/forearm pair balances a 790 mm geometric radial reach against distal mass. A Z-Y-Y-X-Y-X joint sequence gives shoulder/elbow positioning and three-axis wrist orientation. The 190 mm shoulder height makes low bench tasks possible. A 90 mm opening gripper uses opposed lead-screw nuts for symmetric jaw travel. The tool flange is an original 60 mm interface; compatibility with an industry flange standard is not claimed.

| ID | Requirement | Acceptance evidence |
|---|---|---|
| MECH-001 | Six moving joints, realistic housings, hollow links, mount and original tool interface | CAD manifest, STEP assembly and renders |
| MECH-002 | 600–800 mm nominal radial reach | Geometry sum and FK at extension |
| MECH-003 | 4 kg payload design target, conservative torque sizing | Static load analysis; no physical rating |
| MECH-004 | 90 mm gripper opening, opposed moving fingers, 200 N total normal-force target | CAD and gripper calculations/tests |
| MECH-005 | Materials, mass assumptions, access and cable-routing concepts documented | CAD/mass report and mechanical analysis |
| KIN-001 | Correct six-axis FK and coordinate frames | Known poses, SO(3)/SE(3) tests |
| KIN-002 | Numerical IK with limits, pose residual checks and unreachable errors | FK–IK–FK trials and pytest |
| KIN-003 | Geometric Jacobian verified against finite differences | Numerical Jacobian tests |
| KIN-004 | Joint ranges obey configured limits | Configuration and planner tests |
| CTRL-001 | Linear, cubic and quintic joint interpolation obey speed/acceleration limits | Planner tests and plotted derivatives |
| CTRL-002 | MOVE J and continuous approximate MOVE L | TCP straightness and reconstruction metrics |
| CTRL-003 | PID feedback drives inertia/damping model; tracking error is measured | Step/tracking results; no physical bandwidth claim |
| ELEC-001 | Conceptual joint/sensor interface with power, encoders, limit input and drive commands | Native KiCad schematic, BOM and net checks |
| ELEC-002 | Record ERC and available DRC, including unresolved exceptions | Actual KiCad reports |
| SIM-001 | Workspace samples derive from FK; projections and 3D plot include limitations | Seeded sampling results |
| SIM-002 | Pick, grip, lift, transport, release and return are demonstrated | Recorded trajectory and animation from FK |
| SIM-003 | Representative poses and collision/interference screening | CAD checks; report scope of sampled evidence |
| VAL-001 | Automated FK/IK/limits/trajectory/gripper/configuration tests | Executed pytest report |
| VAL-002 | One reproducible validation entry point, evidence-linked traceability | Validation report and matrix |
| DOC-001 | Setup, architecture, decisions, engineering report and reproducible results | Documentation audit |
| DOC-002 | All claims distinguished as ASSUMED, TARGET, CALCULATED, SIMULATED or VERIFIED DIGITALLY | Final claims audit |
| RESEARCH-001 | Numerical experiments vary link ratio, payload, duration, PID gains and fingers | Generated experiment data and plots |
| PERF-001 | ±0.1 mm repeatability TARGET | Explicitly unverified; kinematic reconstruction is not repeatability |

## Operating assumptions and limitations

Configured ranges in degrees are J1 ±170, J2 −120…75, J3 ±135, J4 ±180, J5 ±110 and J6 ±180. Speeds are 90/60/75/120/120/150 deg/s; accelerations are 180/120/150/240/240/300 deg/s². These are design assumptions. Only collision-screened task poses are suitable for the supplied demo; joint limits alone do not imply collision-free motion. Workspace sampling is geometric and must not be interpreted as a certified safe operating envelope.

Safety concepts include hardware emergency-stop power removal, limit inputs, current/torque limiting and encoder feedback. This project does not implement or certify functional safety, protective separation, physical collaborative operation, structural fatigue, EMC, thermal limits or actual drive firmware. No hardware will be built. The software model separates planning, kinematics, virtual drive/control and visualization; a symmetric gripper state is sequenced alongside the arm.
