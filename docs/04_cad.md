# Parametric mechanical design and CAD evidence

ASTER-6 uses Build123d 0.13 and OpenCascade as the primary solid modeler. The design is original and generated from Python; FreeCAD is an independent STEP inspector and native assembly viewer. No duplicate OpenSCAD model is maintained.

## Units and rigid frames

`config/robot.yaml` is authoritative. The mechanism, kinematics and analyses use metres; `cad/build123d/parameters.py` multiplies geometry and gripper lengths by 1000 once at the CAD boundary. CAD BReps, STEP, STL and local triangle coordinates use millimetres.

The world base is fixed, with Z vertical. The zero arm extends along +X. Joint axes are Z, Y, Y, X, Y, X. Mesh groups `j1`…`j6` start immediately after each joint rotation; the mounting plate and fixed riser use `base`. The chain is:

`Tz(h) Rz(q1) Ry(q2) Tx(L1) Ry(q3) Tx(L2) Rx(q4) Tx(lr) Ry(q5) Tx(lp) Rx(q6) Tx(tool)`

Full CAD transforms are independently compared with `RobotArm.frames()` for all six exported configurations, including rotation matrices. Axis-angle placements avoid an ambiguous Euler rotation order. Automated tests also check a general configuration with all six joints active, and check a transformed BRep sphere center against the numerical matrix.

## Mechanical layout

The 220-mm steel mounting plate has eight Ø10.5 through holes on a 180-mm pitch circle, with Ø17 × 7-mm counterbores and a central Ø44 cable opening. A hollow fixed riser carries a conceptual slew bearing. The rotating turret includes a hollow cable neck, a shoulder fork, explicit bearing envelopes, and separately labeled gearbox and motor envelopes.

The upper arm has a nominal 80 × 100 × 4-mm aluminum section, rounded outside R9 and inside R5. Its 320-mm joint-center spacing includes a shoulder rotor, hollow Ø56/Ø34 output shaft and a long external elbow clevis. The primary extrusion terminates 110 mm before the elbow center to keep the folded articulation envelope clear. Two 12-mm-thick external cheeks at Y = ±45 connect the extrusion to the elbow rings while staying outside the forearm's ±32.5-mm width. This is a clearance-driven design choice, rather than a shifted visual joint origin.

The 280-mm forearm uses a nominal 65 × 80 × 4-mm section, elbow rotor, Ø39.6/Ø20 hollow shaft and wrist roll stator. Both links have explicitly cut side service windows, mounting holes and polymer covers. Covers close the windows visually; they are not assumed to restore the extrusion's torsional stiffness.

The wrist contains a hollow roll rotor, an external pitch fork with 2-mm nominal side clearance, a pitch rotor/neck and a final roll stator. Gearbox and motor interiors are envelope representations. This model does not claim validated bearing preload, lubrication, tooth geometry, thermal management or assembly sequence.

The interchangeable tool flange is an original Ø60 × 8-mm plate with six Ø5.5 holes on PCD46 and an Ø16 cable bore. Its adapter has a Ø30.2 pilot bore. Bolt length, thread engagement, tolerance stack and anti-rotation details need a later manufacturing design.

## Parallel gripper

The tool axis is local X and jaw translation is local ±Y. An opposite-hand screw concept moves both jaws symmetrically along two Ø7 steel guides, spaced at Z = ±14 mm. The screw is represented by an Ø8 envelope; thread helix and nut preload are intentionally not detailed. The configured 4-mm lead defines the engineering calculation, not a drawn thread pitch.

Each jaw travels 45 mm, giving 90 mm maximum contact-pad clearance. The two 60 × 10 × 18-mm fingers end at the configured TCP X = 110 mm. Replaceable 1.5-mm pads sit outside the requested contact clearance; the aluminum finger faces have a 93-mm separation when the pads have a 90-mm separation. Slim 10-mm carriages avoid overlapping when closed. Digital tests measure the actual modeled pad bounding boxes at fully open and fully closed settings, rather than relying on the center-to-center jaw distance.

The mesh manifest exports the maximum opening. The digital twin moves each carriage, finger and pad by `side × (requested_opening - maximum_opening)/2`; the screw and guide rods stay fixed.

## Generated deliverables

Run `python scripts/generate_cad.py` from the repository root. The command builds 54 component solids and exports 54 component STEP files, 54 binary STLs, and six complete assembly STEP/STL files: home, extended, folded, vertical, pick and place. It also writes measured volume, solid count, material-density mass estimate, bounding boxes, independent STEP reimport checks and CAD/FK transform comparisons to `results/validation/cad_validation.json`.

`cad/exports/meshes/assembly_meshes.json` contains actual BRep tessellation, local frame IDs, material colors and pose transforms. Tessellation tolerance is 0.5 mm for visualization; exact BRep intersections use the CAD solids, not these triangles. Meshes are reused by the portable digital twin and Blender, so both show the same mechanism.

With Blender available, run `blender --background --python cad/build123d/render_blender.py` to regenerate the hero, gripper and six pose images. These are renderings of CAD meshes; no synthetic or AI-generated mechanism images are used. `cad/renders/aster6_home.blend` preserves the hero scene.

Run `FreeCADCmd cad/freecad/inspect_step.py` for independent import of all six assemblies. It writes `results/validation/cad_freecad_inspection.json` and a native `cad/freecad/aster6_home.FCStd` assembly. The script requires an installed FreeCAD runtime; it is separate from the Python virtual environment.

The three-page `docs/drawings/engineering_interfaces.pdf` and its three SVG source sheets show base/flange patterns, nominal link sections and the gripper mechanism. Dimensions are millimetres. These are interface concept drawings, with explicit manufacturing limitations; they are not fully toleranced production drawings.

## Validation scope and iteration

The first generation exposed oversized fillets on thin service covers; selecting the cover's thickness axis fixed the invalid operations. Mechanical inspection then found gaps between the arm extrusion and joint supports, leading to explicit connected cheek supports and shaft envelopes. Exact intersections found 920 mm³ of upper/forearm collision in home and 2011 mm³ in folded. The extended clevis revision eliminated these collisions for the six supplied configurations. A further gripper check found that placing pads inside the finger clearance reduced the opening by 3 mm; the finger/pad positions and closed carriage width were corrected.

All 54 final components are valid, single, nonzero-volume BReps. Six assembly STEP files are reimported through Build123d and independently through FreeCAD. There are 36 exact intersection checks for selected nonadjacent primary structures across six poses. Bearing/shaft fits and intentional overlap within each rigid assembly are excluded from collision claims.

`python cad/build123d/check_motion.py` samples the actual pick/place joint trajectory at 65 configurations, performs 390 exact BRep pair intersections, and checks all moving mesh vertices against the ground plane. Its output includes the trajectory content hash and measured minimum clearance. This is discrete screening of selected pairs; it is not an exhaustive continuous collision proof, a validated environment planner, or a guarantee that every combination inside the joint limits is mechanically safe.

## Materials and mass interpretation

Assumed densities are aluminum 2700, steel 7850 and polymer 1200 kg/m³. CAD volume × density is a **CALCULATED geometric estimate**. The manifest reports both the sum of all component envelopes and a structure-only subtotal excluding motor/gearbox/bearing envelopes and covers. The sum includes any deliberate material overlaps within a rigid assembly, so it is not a certified BOM mass. Conceptual gearbox and bearing internals are not physically manufactured components.

Dynamic lumped masses in `config/robot.yaml` are deliberately separate, conservatively assumed inputs that also allow for omitted actuators and fasteners. They must not be labeled measured or experimentally verified. Structural analytical calculations simplify the service apertures, joints and long clevis. Their nominal beam deflection is not a full CAD stiffness result; torsional rigidity, bearing compliance, fatigue, bolt preload and tolerance effects remain unverified.
