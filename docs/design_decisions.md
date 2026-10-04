# Design decisions

| Decision | Reason | Alternative / tradeoff |
|---|---|---|
| Python and Build123d primary CAD | Same language as analysis; explicit parametric BRep export | Manual CAD harder to regenerate; OpenSCAD duplicates geometry |
| Original Z-Y-Y-X-Y-X chain | Two positioning links and three wrist rotations; all transforms inspectable | Offset wrist gives orientation-dependent reach and numerical IK complexity |
| 320/280 mm link lengths | Near-balanced position workspace with reduced distal span | Longer forearm increases elbow torque and inertia |
| Hollow aluminum links and service covers | Lower structural mass with accessible cabling and actuator interfaces | Simplified exterior does not specify complete manufacturing tolerances |
| Numerical bounded IK with SO(3) residual | Handles this non-spherical offset wrist and joint limits | Local convergence; multiple starts improve robustness without completeness proof |
| Quintic default joint motion | Rest-to-rest velocity and acceleration endpoints | Linear interpolation has endpoint velocity discontinuity; educational comparison only |
| Opposed lead-screw nuts for gripper | Symmetric positive jaw travel, simple force/lead calculation | Backlash, efficiency, wear and actual threads remain conceptual |
| Explicit lumped drive masses | Exterior CAD does not model copper, magnet, bearing and gear internals | CAD material volume is reported separately, not silently substituted |
| Analytical beam model | Transparent calculations reproducible without pretending FEA | Does not resolve contact, holes, bearings, fasteners or fatigue |
| Diagonal inertia/damping PID model | Clear feedback and saturation experiment | No claim of full manipulator dynamics or physically tuned gains |
| Low-voltage joint/sensor interface | Useful meaningful electronics scope without fictional power inverter | External controller and certified drive still required |
| Private GitHub publication | Publication authorized; public visibility not specified | User may later choose public visibility |

The journal records actual iterations and failures. The validation matrix marks partial evidence explicitly.
