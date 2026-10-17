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

The wrist contains a hollow roll rotor, an external pitch fork with 2-mm nominal side clearance, a pitch rotor/neck and a final roll stator. The roll sleeve terminates at X=15 mm and its 4-mm backing plate at X=19 mm; the pitch barrel's nearest face is X=21 mm, leaving 2 mm axial clearance. The polymer roll cover is attached to the stationary forearm/stator, with 0.2 mm nominal radial clearance around its exterior. Gearbox and motor interiors are envelope representations. This model does not claim validated bearing preload, lubrication, tooth geometry, thermal management or assembly sequence.

The interchangeable tool flange is an original Ø60 × 8-mm plate with six Ø5.5 holes on PCD46 and an Ø16 cable bore. A real Ø30 × 4-mm locating spigot enters the Ø30.2 adapter bore with 0.1-mm radial clearance. The adapter is also Ø60 × 8 mm, leaving 4.25 mm of material outside each bolt hole; matching holes continue through the gripper rear wall. A Ø16 rear cable entrance reaches the gripper pocket; a collision-free cable bend and minimum bend radius are not modeled. Bolt length, thread engagement, tolerance stack and anti-rotation details need a later manufacturing design.

## Parallel gripper

The tool axis is local X and jaw translation is local ±Y. An opposite-hand screw concept moves both jaws symmetrically along two Ø7 steel guides, spaced at Z = ±14 mm. The screw is represented by an Ø8 envelope; thread helix and nut preload are intentionally not detailed. The configured 4-mm lead defines the engineering calculation, not a drawn thread pitch.

Each jaw travels 45 mm, giving 90 mm maximum contact-pad clearance. The two 60 × 10 × 18-mm fingers end at the configured TCP X = 110 mm. Replaceable 1.5-mm pads sit outside the requested contact clearance; the aluminum finger faces have a 93-mm separation when the pads have a 90-mm separation. Slim 10-mm carriages avoid overlapping when closed. Each carriage now includes an integrated Ø12 nut boss with an Ø8.4 smooth conceptual nut bore and a connected bridge. The 0.2-mm screw/nut radial clearance represents the location of an eventual threaded interface, not an engaged thread or force simulation. A lower mounting tab touches the finger at Z=-9 mm; two aligned Ø3.4 holes connect the finger and tab without shared material. The pocket begins at X=20.5 mm, clearing the nut bosses by 1.5 mm. A 16 × 100 × 2-mm top service hatch covers a real access window and has four aligned Ø3.4 mounting holes. It replaces the rear cover that intersected the adapter. Digital tests measure the actual modeled pad bounding boxes at fully open and fully closed settings, rather than relying on the center-to-center jaw distance.

The mesh manifest exports the maximum opening. The digital twin moves each carriage, finger and pad by `side × (requested_opening - maximum_opening)/2`; the screw and guide rods stay fixed.

## Generated deliverables

Enter `06_Complete_Project_Source` from the organized repository root, then run `python scripts/generate_cad.py`. The command builds 54 component solids and exports 54 component STEP files, 54 binary STLs, and six complete assembly STEP/STL files: home, extended, folded, vertical, pick and place. It also writes measured volume, solid count, material-density mass estimate, bounding boxes, independent STEP reimport checks and CAD/FK transform comparisons to `results/validation/cad_validation.json`.

`cad/exports/meshes/assembly_meshes.json` contains actual BRep tessellation, local frame IDs, material colors and pose transforms. Tessellation tolerance is 0.5 mm for visualization; exact BRep intersections use the CAD solids, not these triangles. Meshes are reused by the portable digital twin and Blender, so both show the same mechanism.

With Blender available, run `blender --background --python cad/build123d/render_blender.py` to regenerate the hero, gripper and six pose images. These are renderings of CAD meshes; no synthetic or AI-generated mechanism images are used. `cad/renders/aster6_home.blend` preserves the hero scene.

The native refresh wrapper below runs FreeCAD in console mode for independent import of all six assemblies. It writes `results/validation/cad_freecad_inspection.json` and a native `cad/freecad/aster6_home.FCStd` assembly with 54 descriptive part labels, group/material/role properties and visible saved view providers. The native file opens with the solid assembly visible even when generated headlessly. The script requires an installed FreeCAD runtime; it is separate from the Python virtual environment.

The three-page `docs/drawings/engineering_interfaces.pdf` and its three SVG source sheets show base/flange patterns, nominal link sections and the gripper mechanism. Dimensions are millimetres. These are interface concept drawings, with explicit manufacturing limitations; they are not fully toleranced production drawings.

## Validation scope and iteration

The first generation exposed oversized fillets on thin service covers; selecting the cover's thickness axis fixed the invalid operations. Mechanical inspection then found gaps between the arm extrusion and joint supports, leading to explicit connected cheek supports and shaft envelopes. Exact intersections found 920 mm³ of upper/forearm collision in home and 2011 mm³ in folded. The extended clevis revision eliminated these collisions for the six supplied configurations. A further gripper check found that placing pads inside the finger clearance reduced the opening by 3 mm; the finger/pad positions and closed carriage width were corrected.

The later all-component audit exposed adjacent-joint collisions outside the original selected-pair scope: the turret neck and bridge crossed the shoulder rotor/shaft, the rotating roll cover crossed its stator/bearing, and the roll sleeve crossed the pitch barrel. The turret support was lowered beneath the shoulder barrel; the roll cover was relocated to the stationary stator; and the shortened sleeve/backing plate established axial clearance. Gripper carriages also intersected the fixed body's pocket by about 77 mm³ each. Increasing pocket height to 38 mm and extending its cutting tool beyond the body's front face removed the top/bottom lips while retaining 1 mm nominal carriage clearance. Shoulder and elbow rotor bores now clear their shaft envelopes. The pre-repair findings are preserved separately as historical validation evidence; they are not current acceptance results.

All 54 final components are valid, single, nonzero-volume BReps. Six assembly STEP files are reimported through Build123d and independently through FreeCAD. The current acceptance screen classifies all 1,431 component pairs at each of six poses: 8,586 pair classifications. Conservative axis-aligned bounding boxes reject pairs that cannot intersect; every remaining distinct-motion pair receives an exact BRep common-volume test. The named-pose and closed/45/90-mm gripper checks require 312 exact BRep tests in total and pass with no prohibited overlap above the 0.001-mm³ threshold. Only parts within the same rigid-motion family are excluded as assembled interfaces. Adjacent robot joints are included, and each moving gripper jaw is distinct from the fixed gripper body. The original 36 selected checks are retained as regression evidence, and the CAD generator additionally gates acceptance on the full-pair audit. Results are recorded in `results/validation/cad_assembly_clearance.json` and embedded in `cad_validation.json`.

`python cad/build123d/check_motion.py` checks the actual pick/place trajectory at 75 configurations: 65 uniform samples plus all phase boundaries and gripper events. The current run classifies 107,325 component pairs and performs 6,126 exact BRep intersections. It uses the task's actual 90/28-mm gripper opening states and transformed BRep bounding boxes for ground screening. The minimum moving geometry height is 22.3097 mm, with no prohibited overlaps. The output includes both trajectory and geometry/configuration content hashes, so stale results can be detected. This is representative digital interference validation; it is not an exhaustive continuous swept proof, a validated environment planner, or a guarantee that every combination inside the joint limits is mechanically safe.

The seven CAD regression tests check valid nonzero single solids, SI/mm boundaries and independent transforms, actual contact-pad gaps, all-component clearance at the six named poses, and moving-jaw clearance at closed/mid/open settings. Added interface regressions check actual 7-mm base counterbore depth, retained adapter bolt-hole ligaments, real pilot geometry, matching flange/adapter/body bolt passages, connected screw nut bridges, supported finger seats and the nonintersecting service hatch.

## Materials and mass interpretation

Assumed densities are aluminum 2700, steel 7850 and polymer 1200 kg/m³. CAD volume × density is a **CALCULATED geometric estimate**; the revised component-envelope sum is 19.908 kg. The manifest reports both the sum of all component envelopes and a structure-only subtotal excluding motor/gearbox/bearing envelopes and covers. The sum includes any deliberate material overlaps within a rigid assembly, so it is not a certified BOM mass. Conceptual gearbox and bearing internals are not physically manufactured components.

Dynamic lumped masses in `config/robot.yaml` are deliberately separate, conservatively assumed inputs that also allow for omitted actuators and fasteners. They must not be labeled measured or experimentally verified. Structural analytical calculations simplify the service apertures, joints and long clevis. Their nominal beam deflection is not a full CAD stiffness result; torsional rigidity, bearing compliance, fatigue, bolt preload and tolerance effects remain unverified.

## Refresh native CAD evidence

From the source folder, run the CAD generator and generate the task trajectory before the native refresh:

```bash
python scripts/generate_cad.py
python -m robotarm.demo --all
python scripts/refresh_cad.py
```

`refresh_cad.py` locates FreeCADCmd and Blender from PATH or Windows installation records. Override discovery with `--freecad-cmd PATH_TO_FREECADCMD --blender PATH_TO_BLENDER`. It executes FreeCAD STEP/native inspection, Blender renders, pose composition, independent saved Blender inspection, trajectory clearance and `review_cad.py`, in that order. On Windows the FreeCAD script is sent to console mode through standard input; a positional `.py` argument alone can silently fail to execute in some installations.

`python scripts/review_cad.py` checks current outputs without regenerating them. It reimports all component and assembly STEP files, inspects binary STL bounds and saved FreeCAD BReps/visibility, checks the actual fastening and gripper interfaces, verifies the five contact gaps, decodes images and checks drawing readability. It requires fresh hash-bound FreeCAD/Blender inspection records and current geometry/trajectory clearance. It writes `cad_release_consistency.json` and `final_cad_review.json` with PASS or explicit FAIL. Stale native/render records cannot be refreshed by hashing them alone. STEP exporters can include timestamps, so regenerate native evidence after regenerating STEP files.

The 17 October review corrected six real issues: hidden native FreeCAD solids, adapter holes breaking the outer edge, a disconnected screw-to-carriage load path, an adapter/rear-cover overlap, unsupported finger fastener locations and a 5.5-mm modeled counterbore labeled 7 mm. The revision retains the original six joint frames, configured lengths, 90-mm opening, 4-mm conceptual screw lead and 54-component count. The changed cover filename is `gripper_top_service_cover`.
