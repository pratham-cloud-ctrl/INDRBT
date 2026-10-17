# Kinematic formulation

ASTER-6 uses an explicit sequence of rigid-body transformations. All calculations
use metres, radians and seconds. A column vector represents a point; transforms
map local coordinates into the base frame. The base frame has +Z up, +X along the
zero-position arm and +Y completing a right-handed frame. This is a numerical
model of an original design, not a reverse-engineered commercial arm.

## Frames and joint definitions

Let `h`, `L1`, `L2`, `lr`, `lp` and `lt` be the shoulder height, upper-arm,
forearm, wrist-roll, wrist-pitch and tool lengths in `config/robot.yaml`.

| Joint | Axis in its parent frame before rotation | Part frame origin | Zero convention |
|---|---|---|---|
| J1 | Z | (0,0,h) | Turret aligned with base X |
| J2 | Y | Shoulder | Upper arm points along local +X |
| J3 | Y | Upper-arm end | Forearm points along local +X |
| J4 | X | Forearm end | Wrist-roll reference aligned |
| J5 | Y | Roll-section end | Wrist pitch reference aligned |
| J6 | X | Pitch-section end | Tool roll reference aligned |

Each CAD part is authored in the frame **after** its joint rotation and **before**
the following +X translation. `RobotArm.frames(q)` returns these six transforms
as `joint_transforms` and `link_transforms` (aliases), alongside joint origins,
world-frame axes, link segments, identity base frame, and the final TCP transform.
`transforms` is also an alias for those six part frames; it does not include TCP.
The world joint axis is computed before applying that joint's rotation.

The final TCP follows the configured tool length. CAD and motion software use the
same transform convention. The gripper's full jaw opening is along tool-frame Y,
with inner jaw faces at `±opening/2` and fingers extending toward +X.

## Forward kinematics

For translation `T(a)` and axis rotation `R_i(q)`, homogeneous matrices are

```text
T(a) = [ I3  a ]       R_i(q) = [ rotation_i(q)  0 ]
       [  0  1 ]                [       0        1 ]
```

The complete transformation is

```text
T_base_tcp(q) = Tz(h) Rz(q1)
               Ry(q2) Tx(L1)
               Ry(q3) Tx(L2)
               Rx(q4) Tx(lr)
               Ry(q5) Tx(lp)
               Rx(q6) Tx(lt).
```

Positive rotation follows the right-hand rule. In particular, positive rotation
about Y tips local +X downward. At all-zero angles the TCP is
`(L1+L2+lr+lp+lt, 0, h)` with identity orientation. At `q2=-π/2` and all other
angles zero it is `(0, 0, h+L1+L2+lr+lp+lt)`. Both cases are tested against exact
positions. Configured joint bounds are enforced by FK unless explicitly disabled.

## Inverse kinematics

The solver uses `scipy.optimize.least_squares` with box constraints, a supplied
seed, home seed, midrange seed and deterministic random restarts. There is no
analytical IK claim. The residual is

```text
r(q) = [ (p(q)-p_target)/reach,
         log_SO3(R_target R(q)^T) ].
```

The SO(3) logarithm is represented as an axis-angle rotation vector. Dividing
translation by the reach provides a documented dimensionless balance between
position and orientation. A returned candidate is accepted only if its separate
position and orientation errors satisfy the configured tolerances. These are
numerical solver tolerances; they are unrelated to physical repeatability.

Targets outside the shoulder-centred maximum length bound are rejected before
optimization. A failed bounded numerical search produces a useful error with the
best residual. It is **not a proof** that a target within that bound is unreachable.
Redundant branches and elbow/wrist alternatives can occur. Restarts can find an
alternative branch but do not exhaustively enumerate every solution. The planner
uses continuation from the preceding configuration to preserve local continuity.

## Geometric Jacobian

For TCP position `p`, world joint origin `o_i` and world unit rotation axis `a_i`,
the six columns are

```text
J_i = [ a_i × (p-o_i) ]
      [      a_i      ].
```

`J(q) qdot` gives world-frame linear velocity followed by angular velocity.
The translational rows have metre units; rotational rows are dimensionless.
Singularity diagnostics divide the translational rows by the configured reach
before computing singular values. This scale must be stated when comparing
condition measures. Tests compare every Jacobian column with central differences
of TCP position and world-frame SO(3) orientation across eight seeded poses.

## Singularities and workspace

All-zero extension is singular: shoulder/elbow pitch axes become parallel and
several wrist axes align. Wrist pitch near zero can align wrist-roll and tool-roll
axes. Singularities reduce one or more instantaneous motion directions and can
produce large joint speeds or unstable IK branches. The plotted diagnostic
threshold on the smallest scaled singular value is an educational indicator,
not a safety criterion or drive acceptance limit.

The workspace demonstration samples independent valid joint configurations.
It produces three projections, a 3D cloud, a separate TCP-above-floor cloud,
and singularity plots. The full cloud includes below-base positions allowed by
the joint-limit model. TCP `z>=0` filtering alone does not verify link clearance.
All workspace plots omit obstacles and self-collision filtering.

The convex-hull envelope fills inaccessible holes and cannot be called actual
reachable volume. Occupied voxels are a sampling proxy that depends on pitch,
sample count and random seed. Orientation feasibility differs from position-only
reachability. Results and their exact seeds are saved in
`results/workspace/metrics.json` and `samples.csv`.

## Motion planning and simulation limits

MOVE J uses monotonic linear, cubic or quintic scalar interpolation of all six
joints. Polynomial velocity and acceleration maxima provide an analytic minimum
duration. Linear interpolation describes a constant-velocity interior segment;
instantaneous starts and stops have unbounded acceleration. It is not used in the
stop-to-stop pick-and-place sequence. Quintic segments have zero endpoint velocity
and acceleration, permitting continuous concatenation with dwell segments.

MOVE L follows a straight TCP line, shortest-path SO(3) SLERP and a quintic time
law. Bounded IK is solved at every sample, seeded from the previous result. Large
configuration jumps are rejected. Finite-difference joint velocity and acceleration
are uniformly time-scaled to satisfy limits at returned samples. This is sampled
verification; no between-sample bound or collision-free certificate is claimed.

The start and every solved MOVE L sample must have a smallest scaled Jacobian
singular value greater than 0.001 by default; translational rows are divided by
nominal reach. This numerical regularity guard rejects singular/near-singular
continuation with an instruction to choose another path or use MOVE J. The
threshold is configurable and is not a mechanical safety limit. A Cartesian
quintic law does not guarantee bounded joint acceleration at a singular endpoint:
a radial approach to full extension can have `q ~ (1-u)^(3/2)` and divergent
joint acceleration. Endpoint derivative assignments therefore require a regular
Jacobian. Between-sample singularity and collision certification remain absent.

The FK animation evaluates the transform chain at each interpolated joint pose.
It uses stick geometry and a scripted object-attachment event. It is an ideal
kinematic simulation, without contact, rigid-body payload dynamics or collision
physics. The PID simulation separately tests assumed independent inertia/damping
joint plants with torque saturation and conditional-integration antiwindup.
