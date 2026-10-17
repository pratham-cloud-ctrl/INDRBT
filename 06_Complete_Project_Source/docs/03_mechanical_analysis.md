# Mechanical calculations and actuator concept

## Load model and mass basis

The SI configuration assigns lumped drive and link masses to the frames used by CAD and FK. Each moving lump is placed at its segment midpoint; the payload is at the TCP. These are ASSUMED load properties. The separate CAD envelope sum is 19.908 kg; simplified gearbox/bearing interiors and overlapping seats prevent treating it as a complete physical BOM. The assumed manipulator mass is 23.65 kg, of which 15.15 kg moves, excluding the payload.

| Group | kg | Status |
|---|---|---|
| Base | 8.50 | ASSUMED |
| Turret | 4.20 | ASSUMED |
| Upper Arm | 5.50 | ASSUMED |
| Forearm | 2.70 | ASSUMED |
| Wrist Roll | 0.90 | ASSUMED |
| Wrist Pitch | 0.65 | ASSUMED |
| Flange Gripper | 1.20 | ASSUMED |
| Payload | 4.00 | ASSUMED |

For each COM, gravity force is F=[0,0,−mg]. External axis moment is τᵢ = aᵢ·[(pCOM−oᵢ)×F]; holding torque has the opposite sign. Summation includes downstream groups only. An independent potential-energy gradient test verifies the force/moment convention.

The 6001-pose sample uses seed 412; it is not proof of a worst case. Closed-form triangle-inequality lever bounds size the conceptual actuators. Full extension gives shoulder 70.165 N·m and elbow 31.880 N·m. J1 and J6 gravity moments vanish for the assumed symmetric, centred lumps; acceleration/friction allowances still require drive torque.

## Actuator sizing

Output requirement = safety factor × (gravity bound + Isizing·amax + b·vmax). Safety factor is 2.0. Motor torque = output / (ratio × efficiency). Isizing is the per-joint maximum of the educational control-plant inertia and a downstream point-COM lever-square bound: 4.49083 / 4.49083 / 1.30179 / 0.09402 / 0.09402 / 0.03000 kg·m². This prevents sizing below the same assumed load model while preserving the independent PID plants. Damping and masses are ASSUMED; simultaneous extrema define an envelope for the diagonal point-mass model. Centroidal body inertia, coupling, Coriolis/centrifugal and reflected-drive effects remain absent. These are generic digital selections, not validated commercial actuator specifications.

| Joint | Gravity bound N·m | Concept output N·m | Ratio | Efficiency | Motor N·m |
|---|---|---|---|---|---|
| J1 | 0.000 | 34.500 | 80 | 0.75 | 0.575 |
| J2 | 70.165 | 165.425 | 120 | 0.70 | 1.969 |
| J3 | 31.880 | 74.504 | 100 | 0.72 | 1.035 |
| J4 | 6.859 | 15.133 | 60 | 0.75 | 0.336 |
| J5 | 6.859 | 14.924 | 60 | 0.75 | 0.332 |
| J6 | 0.000 | 0.733 | 50 | 0.78 | 0.019 |

Configured joint speeds are 90 / 60 / 75 / 120 / 120 / 150 deg/s. Drive torque limits are modelling assumptions. Continuous/RMS heating, reflected inertia, acceleration coupling, backlash, brake capacity, bearing loads and fatigue require further engineering.

## Analytical stiffness and strength

This is an Euler–Bernoulli calculation, not FEA. Links are ideal clamped rectangular hollow sections. I = [b·h³−(b−2t)(h−2t)³]/12. Root stress = M·h/(2I). Tip displacement = FL³/(3EI) + MtipL²/(2EI) + wL⁴/(8EI). Tip slope = [FL²/2 + Mtip·L + wL³/6]/(EI). Upper-arm loading includes the downstream elbow moment as an end couple. Serial TCP displacement = δupper + δforearm + θupper·(L2+lr+lp+lt) + θforearm·(lr+lp+lt), treating the wrist and tool as rigid offsets. An independent whole-arm virtual-work integral regression checks this combined estimate.

| Member | Bending MPa | Local tip deflection mm | Yield / nominal stress |
|---|---|---|---|
| Upper Arm | 1.759 | 0.02082 | 136.45 |
| Forearm | 1.275 | 0.01354 | 188.28 |
| Finger | 20.000 | 0.06957 | 12.00 |

Combined serial TCP beam estimate is 0.10408 mm. The large ideal-section safety ratios are not real assembly factors of safety: covers, access windows, terminal side clevis, fasteners, bearings, gears and stress concentrations are omitted. Nominal section calculations cannot establish complete CAD stiffness or ±0.1 mm repeatability.

## Gripper mechanism

A transverse opposed-hand screw with a 4 mm lead drives two guided nuts/carriages. The 90 mm opening requires 45 mm travel per jaw, or 11.25 screw revolutions. Threads and nut/bearing preload remain conceptual in CAD.

The total normal-force target is 200 N, or 100 N per jaw. Energy balance gives T = Ftotal·lead/(2πη) = 0.363783 N·m at an assumed efficiency of 0.35. An assumed motor torque of 0.45 N·m gives an ideal total force of 247.400 N. With friction coefficient μ = 0.5 and safety factor 2, the target force supports an ideal friction-only payload of 5.099 kg. This is not a load rating: acceleration, contact pressure, object damage, guide friction, backlash and actual motor current limits are omitted.

At 60 mm finger length and 100 N tip force, nominal stress is 20.000 MPa and elastic deflection is 0.06957 mm. Finger length changes guide moment and stiffness; it does not change ideal screw force conversion.

Sources for the underlying formula conventions: [MIT cantilever lecture](https://www.ocw.mit.edu/courses/6-152j-micro-nano-processing-technology-fall-2005/4e555db93fbd2b7473f14100fbaadcc8_lecture13.pdf), [Thomson lead-screw engineering catalogue](https://www.thomsonlinear.com/downloads/screws/Lead_Screws_cten.pdf). Material properties are explicitly assumed in the configuration rather than certified alloy/temper values.
