# Understanding the ASTER-6 digital robot

This guide follows one engineering question through the project: can the chosen
geometry move a tool through a useful task, support an assumed load, and be
controlled in a clearly defined digital model? Read it alongside the
[requirements](01_requirements.md), [interactive CAD twin](../simulations/aster6_twin.html)
and [engineering report](engineering_report.md). The current numerical values live
in the linked result files and [KPI table](kpis.md), so this guide concentrates on
the equations and how to interpret their evidence.

For optional inspection in a CAD or electronics application, use the [public inspection release](https://github.com/pratham-cloud-ctrl/industrial-robot-arm-digital-twin/releases/tag/inspection-2026-10-21) and [native-file opening guide](cad_downloads.md). Ordinary browser inspection remains available through the showcase. The published GitHub Pages showcase includes the browser viewers and download controls.

## 1. Start with units and assumptions

[The configuration](../config/robot.yaml) is the common source for geometry,
joint bounds, assumed masses, motion limits, gripper parameters and controller
gains. Calculations use metres, radians, kilograms, seconds and newtons. CAD
converts metres to millimetres at its export boundary. Degree-valued input fields
are converted to radians when the software loads them.

| Quantity | Symbol | Unit |
|---|---|---|
| Joint angle, speed, acceleration | q, qdot, qddot | rad, rad/s, rad/s² |
| Position, length, screw lead | p, L, lead | m |
| Force, joint torque | F, tau | N, N·m |
| Joint rotational inertia | I_joint | kg·m² |
| Beam second moment of area | I_beam | m⁴ |
| Young's modulus, stress | E, sigma | Pa = N/m² |
| Viscous rotational damping | b | N·m·s/rad |

Joint inertia and beam second moment are different physical quantities despite
often sharing the letter I. The former describes resistance to angular
acceleration; the latter describes a section's resistance to bending.

Payload, material properties, COM locations, friction, inertia and damping are
design inputs or assumptions. FK reconstruction and native CAD/PCB checks are
digital evidence. Physical payload and repeatability remain targets. These
categories are carried through the [scope audit](digital_scope_audit.md).

## 2. Turn joint angles into the tool pose

The base frame has Z upward and X along the extended arm. Positive rotations use
the right-hand rule; positive Y rotation tips an initially horizontal link
downward. A homogeneous transform maps a local point into the base frame using
column vectors. Its rotation block gives orientation and its final column gives
position.

The serial chain is:

```text
T_base_tcp = Tz(h) Rz(q1) Ry(q2) Tx(L1) Ry(q3) Tx(L2)
             Rx(q4) Tx(lr) Ry(q5) Tx(lp) Rx(q6) Tx(lt)
```

The local joint axes are Z, Y, Y, X, Y, X. Each CAD component belongs to the frame
after its joint rotation and before the next translation. This convention makes
the CAD assembly and the mathematical arm share the same joint origins.

With every angle zero, the TCP lies at `(R, 0, h)`, where
`R = L1 + L2 + lr + lp + lt`. With only q2 at −π/2, it lies at `(0, 0, h+R)`.
These are useful hand checks for signs, units and translation order. R is a
shoulder-centred radial bound; h+R is a vertical height from the base plane.
[The kinematic formulation](02_kinematics.md) explains every frame and the exact
software interface.

## 3. Solve a target pose and understand singularities

Inverse kinematics asks for joint angles that reconstruct a requested position
and orientation. The bounded numerical solver minimizes:

```text
r(q) = [(p(q) − p_target)/R,
        log_SO3(R_target R(q)^T)]
```

The SO(3) logarithm is a three-component axis-angle rotation vector. Scaling
position by R balances dimensionless position and orientation residuals. Joint
bounds constrain the search, and separate configured position/orientation
tolerances decide whether a candidate is accepted. Deterministic restarts improve
the chance of finding a branch. A failed local search inside the radial bound
does not prove that every possible branch is inaccessible.

The geometric Jacobian maps joint speed into world-frame TCP linear and angular
velocity. For joint axis a_i through origin o_i, its column is:

```text
J_i = [a_i × (p_tcp − o_i); a_i]
[v_tcp; omega_tcp] = J(q) qdot
```

A singularity removes an instantaneous motion direction. Near one, a modest tool
motion may need large joint speeds or cause an IK branch jump. The plotted
singular values use translational rows divided by R; their numerical threshold
is a diagnostic for this chosen scaling. It is not a safety limit.
[Numerical validation](../results/validation/numerical_validation.json) records
perturbed-seed reconstruction and central-difference Jacobian checks. An IK
residual measures agreement between two mathematical poses; it does not measure
physical accuracy or repeatability.

## 4. Plan smooth motion

For a joint move, every joint uses `q(t) = q_start + delta_q s(u)`, with
`u = t/T`. The three interpolation laws are:

| Law | s(u) | Peak first-derivative magnitude | Peak second-derivative magnitude |
|---|---|---|---|
| Linear interior | u | 1 | 0 inside the interval; start/stop acceleration unbounded |
| Cubic | 3u² − 2u³ | 3/2 | 6 |
| Quintic | 10u³ − 15u⁴ + 6u⁵ | 15/8 | 10/√3 |

For positive speed/acceleration limits, the minimum duration follows directly:

```text
T >= max over joints of {
     velocity_factor · |delta_q| / velocity_limit,
     sqrt(acceleration_factor · |delta_q| / acceleration_limit)
     }
```

Cubic motion has zero endpoint velocity. Quintic motion also has zero endpoint
acceleration, making it suitable for joining rest-to-rest moves and dwells. Linear
interpolation is used for a comparison of the constant-speed interior; it does
not meet finite start/stop acceleration requirements.

MOVE J applies these laws in joint space, so its TCP path generally curves. MOVE L
uses a straight position line, shortest-path orientation SLERP and a quintic time
law. It solves IK successively from the preceding joint solution, rejects large
branch jumps, estimates derivatives by finite differences, and uniformly lengthens
time to obey their sampled limits. This does not establish derivative bounds
between samples. Joint bounds and IK success also do not establish collision
clearance.

The default MOVE L regularity guard requires the smallest scaled Jacobian
singular value to exceed 0.001 at the start and solved samples, with translation
rows divided by reach. Singular continuation raises a useful error and suggests
another path or MOVE J. Cartesian quintic endpoints alone do not establish finite
joint acceleration at full extension; the inverse map can be singular. This is
a sampled numerical guard with a configurable threshold, not a safety claim.

[Trajectory evidence](../results/trajectories/trajectory_metrics.json) and the
[recorded task](../results/trajectories/pick_place_samples.json) expose the actual
samples. The object follows a scripted attachment between close/open events;
grasp contact and friction are not simulated. Separate
[CAD clearance evidence](../results/validation/cad_motion_clearance.json) screens
all component pairs at representative task configurations, with its finite
sampling scope stated explicitly.

## 5. Calculate gravity and choose a conceptual drive envelope

Each moving group has an assumed midpoint COM, and the payload acts at the TCP.
For mass m, gravity force is `[0, 0, −m g]`. Its external joint moment is:

```text
tau_gravity_i = a_i · [(p_COM − o_i) × F_gravity]
tau_holding_i = −tau_gravity_i
```

Only downstream masses contribute to a joint. The negative potential-energy
gradient supplies an independent check on the sign and magnitude. Full extension
also permits hand calculations using horizontal lever lengths. Centred lumps
give zero gravity moment around the base yaw and tool roll axes; they still need
torque for acceleration and damping.

The controller's inertia is an independent educational plant assumption. It must
not automatically become the actuator-sizing inertia: a point payload alone has
rotational inertia `m · r_perpendicular²`, which can exceed that assumption.
For each joint, the load analysis bounds the perpendicular lever to every
downstream COM point using the actual link lengths. It then calculates:

```text
I_point_bound_i = sum over downstream COM points of (m · lever_bound_i²)
I_sizing_i = max(I_control_i, I_point_bound_i)
```

Roll-axis offsets along the same axis contribute no perpendicular lever. The
point-mass bound covers every joint angle under the midpoint COM model. An
independent test differentiates COM positions at unit joint speed and checks
`2 · kinetic_energy = I_ii` against these bounds. The configured control plants
remain unchanged. Conceptual sizing adds the gravity bound to this equivalent
diagonal inertia allowance and the assumed damping allowance:

```text
tau_output = safety_factor · (gravity_bound + I_sizing·amax + b·vmax)
tau_motor = tau_output / (gear_ratio · efficiency)
```

The simultaneous maxima define an envelope for this independent-axis point-mass
model. They do not bound a coupled robot's complete dynamic torque: centroidal
body rotation tensors, off-diagonal inertia, Coriolis/centrifugal terms and
reflected drive inertia are absent. Continuous heating, brakes, gear/bearing
loads, backlash and commercial part ratings also require further engineering.
[Load results](../results/mechanical/joint_torque.json) and
[mechanical analysis](03_mechanical_analysis.md) retain the assumptions, sampled
maxima and all-angle bounds separately.

## 6. Check the opposed-screw gripper

The inner jaw faces lie at `±opening/2`. Both nuts travel one screw lead per
revolution in opposite directions, so a revolution changes the full gap by twice
the lead. For the sum N_total of both contact normal forces:

```text
gap_change = 2 · lead · screw_revolutions
input_work_per_revolution = 2π · torque
output_work_per_revolution = N_total · lead
required_torque = N_total · lead / (2π · efficiency)
friction_payload_bound = mu · N_total / (grip_safety_factor · g)
```

Summing both jaws' work avoids a factor-of-two error. The friction bound assumes
a vertical, static load, the stated coefficient and shared contacts; acceleration,
contact pressure, object damage and guide friction remain unmodelled. Screw
efficiency is an assumption and does not establish self-locking or brake holding.
The rotary-to-linear torque convention agrees with the
[Thomson engineering catalogue](https://www.thomsonlinear.com/downloads/screws/Lead_Screws_cten.pdf),
page 49. Current calculations are in the gripper section of the
[mechanical analysis](03_mechanical_analysis.md).

## 7. Estimate beam stiffness and nominal stress

The links are ideal clamped hollow rectangular beams. For width B, bending depth
H and wall t, the section model is:

```text
I_beam = [B H³ − (B−2t)(H−2t)³] / 12
M_root = F L + M_tip + w L²/2
sigma_root = M_root H / (2 I_beam)
delta_tip = [F L³/3 + M_tip L²/2 + w L⁴/8] / (E I_beam)
theta_tip = [F L²/2 + M_tip L + w L³/6] / (E I_beam)
```

F is an end force, M_tip an end couple and w a distributed load in N/m.
Superposition follows the small-deflection moment-curvature relation taught in
[MIT's cantilever lecture](https://www.ocw.mit.edu/courses/6-152j-micro-nano-processing-technology-fall-2005/4e555db93fbd2b7473f14100fbaadcc8_lecture13.pdf).
The complete extended-pose TCP estimate must carry both beam-end rotations across
their downstream rigid offsets:

```text
delta_TCP = delta_upper + delta_forearm
          + theta_upper   · (L2 + lr + lp + lt)
          + theta_forearm · (lr + lp + lt)
```

The final theory audit added the forearm-rotation term omitted from the earlier
estimate. An independent regression integrates the load moment multiplied by the
unit-TCP-load moment over both flexible sections. It agrees with the corrected
four-term expression. [Structural results](../results/mechanical/structural.json)
record each contribution, slope and the total, making the correction inspectable.

Wrist/tool sections are rigid in this calculation. Holes, the terminal clevis,
contacts, gears, bearings, shear deformation and fatigue are omitted. Yield divided
by nominal section stress describes this ideal section alone. Static deflection
describes a load-dependent pose bias. Repeatability describes the spread of
repeated returns under defined conditions; this project supplies no physical
repeatability test.

## 8. Understand the controller experiment

Each joint follows an independent assumed plant and a saturated feedback command:

```text
I_joint qddot + b qdot = tau_command
error = q_reference − q_actual
tau_unsaturated = Kp·error + Ki·integral(error) + Kd·(qdot_reference − qdot_actual)
tau_command = clip(tau_unsaturated, −torque_limit, +torque_limit)
```

Kp has units N·m/rad, Ki N·m/(rad·s), and Kd N·m·s/rad. Conditional integration
freezes the integrator when saturation would be pushed further and permits
integration that helps unwind it. Optional feedforward adds
`I_joint qddot_reference + b qdot_reference`; the retained main control experiment
uses feedback alone.

Semi-implicit Euler first updates velocity and then position, using a timestep
no greater than the configured integration interval. Positions clip at joint
bounds and clipped joints reset velocity; that simple boundary rule is not contact
or impact dynamics. Gravity, cross-axis coupling, sensor noise, backlash and drive
delay are absent. The planned CAD animation and the feedback tracking experiment
are separate outputs.

[Control results](../results/control/metrics.json) report joint-space RMSE, final
error, command peaks and step settling. The two-percent settling time is the
first sample after the last excursion outside the band, rather than the first
crossing. These metrics describe the assumed plant; they do not measure physical
bandwidth or TCP repeatability.

## 9. Read the research plots as controlled numerical experiments

| Experiment | What is varied and held fixed | What the result can establish |
|---|---|---|
| Link ratio | Change L1/L2 at fixed L1+L2; reuse joint samples and grid pitch | Sensitivity of minimum sampled radius and occupancy; outer reach remains fixed |
| Payload | Change payload at full extension; retain the link/COM model | Linear gravity-torque growth from a longer loaded lever |
| Duration | Change T for the same quintic joint displacement | Velocity scales as 1/T and acceleration as 1/T² |
| PID gains | Scale all three gains for the same joint step and plant | A tuning tradeoff among error, settling, overshoot and command torque |
| Finger length | Change L with force and section fixed | Stress grows with L and deflection with L³; ideal screw torque stays fixed |

[Experiment data](../results/research/experiments.json) records the samples and
interpretations used to generate every plot. Workspace hulls fill inaccessible
holes, and occupied voxels depend on sampling density and pitch. Neither is a
certified reachable or collision-free volume. Higher PID gain can reduce RMSE
without improving the two-percent settling time; the measured criterion matters.

## 10. Follow each claim to its evidence

Use the [KPI table](kpis.md) for current values, the
[requirements matrix](validation_matrix.md) for acceptance, the
[completion checklist](completion_checklist.md) for deliverables and publication,
and the [final theory review](../results/validation/final_theory_review.json) for
the independent cross-checks. The [electronics guide](05_electronics.md) covers
the native schematic/PCB, power calculations and enabled-rule checks. Digital
ERC/DRC verifies specified rules and connectivity; it does not establish thermal,
EMC, ESD or functional-safety performance.

From the source root, `python scripts/run_validation.py --help` describes the full
validation workflow. `python scripts/review_theory.py --help` describes the
focused theory checks. Passing evidence applies to the documented models and
samples. It should always be read together with their assumptions and limits.
