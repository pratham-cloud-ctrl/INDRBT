# CAD component catalog

INDRBT has 54 original modeled components and six complete pose assemblies. This catalog connects each part to its assembly role, assumed material, individual models and saved FreeCAD object. All CAD lengths are in millimetres.

## Open the robot

| What you want | Open this | How to use it |
|---|---|---|
| Move the assembled robot | [Interactive 3D viewer](../simulations/indrbt_twin.html) | Download the repository and open the HTML in a browser; use the pose selector, joint controls, gripper slider and play button. GitHub displays HTML source. |
| Inspect the solid home assembly | [FreeCAD native assembly](../cad/freecad/indrbt_home.FCStd) | Open with FreeCAD. Its 54 saved solid objects are cross-referenced below. |
| Inspect the rendering scene | [Blender native scene](../cad/renders/indrbt_home.blend) | Open with Blender. Robot object names match the component filenames. |
| See the mechanism quickly | [Home render](../cad/renders/hero.png), [gripper close-up](../cad/renders/gripper.png), [six-pose sheet](../cad/renders/poses.png) | Ordinary image previews. |
| Read interface dimensions | [Three-page drawing PDF](drawings/engineering_interfaces.pdf) | Concept dimensions for the base/flange, link sections and gripper. |
| Change the design parameters | [SI configuration](../config/robot.yaml), [parametric geometry source](../cad/build123d/geometry.py), [CAD methodology](04_cad.md) | Regenerate from the Python source after changing parameters. The saved FreeCAD assembly contains solid geometry; the Python source defines the parametric construction. |

In the organized project folder, double-click `OPEN_3D_VIEWER.cmd` or `OPEN_FREECAD_MODEL.cmd` to open the installed application. The same files are copied under `01_CAD_Models`; component STEP files are in `STEP/Individual_Parts`, and complete poses are in `STEP/Assemblies`.

STEP files preserve solid geometry for CAD inspection and exchange. STL files contain triangles for mesh viewers and printing preparation. Component exports remain in their local assembly-group frame; open a complete pose to see all parts together.

## Complete assemblies

| Pose | Joint angles in degrees, J1 to J6 | Solid CAD | Mesh | Preview |
|---|---|---|---|---|
| Home | 0, -50, 90, 0, -40, 0 | [STEP](../cad/exports/STEP/assembly_home.step) | [STL](../cad/exports/STL/assembly_home.stl) | [Image](../cad/renders/pose_home.png) |
| Extended | 0, 0, 0, 0, 0, 0 | [STEP](../cad/exports/STEP/assembly_extended.step) | [STL](../cad/exports/STL/assembly_extended.stl) | [Image](../cad/renders/pose_extended.png) |
| Folded | 0, -110, 130, 0, -20, 0 | [STEP](../cad/exports/STEP/assembly_folded.step) | [STL](../cad/exports/STL/assembly_folded.stl) | [Image](../cad/renders/pose_folded.png) |
| Vertical | 0, -90, 0, 0, 0, 0 | [STEP](../cad/exports/STEP/assembly_vertical.step) | [STL](../cad/exports/STL/assembly_vertical.stl) | [Image](../cad/renders/pose_vertical.png) |
| Pick | -25, -45, 95, 0, 40, 0 | [STEP](../cad/exports/STEP/assembly_pick.step) | [STL](../cad/exports/STL/assembly_pick.stl) | [Image](../cad/renders/pose_pick.png) |
| Place | 25, -45, 95, 0, 40, 0 | [STEP](../cad/exports/STEP/assembly_place.step) | [STL](../cad/exports/STL/assembly_place.stl) | [Image](../cad/renders/pose_place.png) |

## Find an individual component

The group labels `base`, `j1` to `j6` identify moving coordinate frames. A motor name such as `j2_motor_envelope` identifies the actuator it represents; its housing belongs to the preceding support frame. Names ending `-1` and `+1` mark the two side instances. Gripper guide rods ending `-14` and `+14` are at local Z = -14 and +14 mm.

An **envelope** is a simplified spatial placeholder for a motor, gearbox, bearing or screw. Its interior is not a detailed purchased component. Materials are assumed; the geometric mass estimate is separate from the conservative dynamic mass inputs.

FreeCAD objects retain `Component01` to `Component54` internal names and display the descriptive component label. The mapping below was checked against the individual part volumes and home-assembly positions. Blender and individual exports retain the descriptive part names.

### Fixed base (base; 4 parts)

Mounting plate, hollow riser and fixed covers.

| Component / filename | Assembly role | Assumed material | FreeCAD object | Individual model |
|---|---|---|---|---|
| `base_mounting_plate` | Structure | Steel | `Component01` | [STEP](../cad/exports/STEP/base_mounting_plate.step) / [STL](../cad/exports/STL/base_mounting_plate.stl) |
| `fixed_base_riser` | Structure | Aluminum | `Component02` | [STEP](../cad/exports/STEP/fixed_base_riser.step) / [STL](../cad/exports/STL/fixed_base_riser.stl) |
| `j1_slew_bearing_envelope` | Bearing envelope | Steel | `Component03` | [STEP](../cad/exports/STEP/j1_slew_bearing_envelope.step) / [STL](../cad/exports/STL/j1_slew_bearing_envelope.stl) |
| `base_electronics_cover` | Removable cover | Polymer | `Component04` | [STEP](../cad/exports/STEP/base_electronics_cover.step) / [STL](../cad/exports/STL/base_electronics_cover.stl) |

### Turret and shoulder support (j1; 9 parts)

Rotates around J1; supports the shoulder bearing and J2 actuator housing.

| Component / filename | Assembly role | Assumed material | FreeCAD object | Individual model |
|---|---|---|---|---|
| `turret_neck` | Structure | Aluminum | `Component05` | [STEP](../cad/exports/STEP/turret_neck.step) / [STL](../cad/exports/STL/turret_neck.stl) |
| `turret_bridge` | Structure | Aluminum | `Component06` | [STEP](../cad/exports/STEP/turret_bridge.step) / [STL](../cad/exports/STL/turret_bridge.stl) |
| `shoulder_fork_-1` | Structure | Aluminum | `Component07` | [STEP](../cad/exports/STEP/shoulder_fork_-1.step) / [STL](../cad/exports/STL/shoulder_fork_-1.stl) |
| `shoulder_bearing_-1` | Bearing envelope | Steel | `Component08` | [STEP](../cad/exports/STEP/shoulder_bearing_-1.step) / [STL](../cad/exports/STL/shoulder_bearing_-1.stl) |
| `shoulder_fork_+1` | Structure | Aluminum | `Component09` | [STEP](../cad/exports/STEP/shoulder_fork_+1.step) / [STL](../cad/exports/STL/shoulder_fork_+1.stl) |
| `shoulder_bearing_+1` | Bearing envelope | Steel | `Component10` | [STEP](../cad/exports/STEP/shoulder_bearing_+1.step) / [STL](../cad/exports/STL/shoulder_bearing_+1.stl) |
| `j2_gearbox_envelope` | Gearbox envelope | Steel | `Component11` | [STEP](../cad/exports/STEP/j2_gearbox_envelope.step) / [STL](../cad/exports/STL/j2_gearbox_envelope.stl) |
| `j2_motor_envelope` | Motor envelope | Polymer | `Component12` | [STEP](../cad/exports/STEP/j2_motor_envelope.step) / [STL](../cad/exports/STL/j2_motor_envelope.stl) |
| `j2_motor_endcap` | Motor end cap | Steel | `Component13` | [STEP](../cad/exports/STEP/j2_motor_endcap.step) / [STL](../cad/exports/STL/j2_motor_endcap.stl) |

### Upper arm and elbow support (j2; 13 parts)

Rotates around J2; carries the upper link, elbow clevis, bearings and J3 actuator housing.

| Component / filename | Assembly role | Assumed material | FreeCAD object | Individual model |
|---|---|---|---|---|
| `shoulder_rotor` | Structure | Aluminum | `Component14` | [STEP](../cad/exports/STEP/shoulder_rotor.step) / [STL](../cad/exports/STL/shoulder_rotor.stl) |
| `shoulder_output_shaft` | Hollow output shaft | Steel | `Component15` | [STEP](../cad/exports/STEP/shoulder_output_shaft.step) / [STL](../cad/exports/STL/shoulder_output_shaft.stl) |
| `upper_arm_hollow_link` | Structure | Aluminum | `Component16` | [STEP](../cad/exports/STEP/upper_arm_hollow_link.step) / [STL](../cad/exports/STL/upper_arm_hollow_link.stl) |
| `elbow_fork_bridge_-1` | Structure | Aluminum | `Component17` | [STEP](../cad/exports/STEP/elbow_fork_bridge_-1.step) / [STL](../cad/exports/STL/elbow_fork_bridge_-1.stl) |
| `elbow_fork_bridge_+1` | Structure | Aluminum | `Component18` | [STEP](../cad/exports/STEP/elbow_fork_bridge_+1.step) / [STL](../cad/exports/STL/elbow_fork_bridge_+1.stl) |
| `upper_service_cover_-1` | Service cover | Polymer | `Component19` | [STEP](../cad/exports/STEP/upper_service_cover_-1.step) / [STL](../cad/exports/STL/upper_service_cover_-1.stl) |
| `elbow_fork_-1` | Structure | Aluminum | `Component20` | [STEP](../cad/exports/STEP/elbow_fork_-1.step) / [STL](../cad/exports/STL/elbow_fork_-1.stl) |
| `elbow_bearing_-1` | Bearing envelope | Steel | `Component21` | [STEP](../cad/exports/STEP/elbow_bearing_-1.step) / [STL](../cad/exports/STL/elbow_bearing_-1.stl) |
| `upper_service_cover_+1` | Service cover | Polymer | `Component22` | [STEP](../cad/exports/STEP/upper_service_cover_+1.step) / [STL](../cad/exports/STL/upper_service_cover_+1.stl) |
| `elbow_fork_+1` | Structure | Aluminum | `Component23` | [STEP](../cad/exports/STEP/elbow_fork_+1.step) / [STL](../cad/exports/STL/elbow_fork_+1.stl) |
| `elbow_bearing_+1` | Bearing envelope | Steel | `Component24` | [STEP](../cad/exports/STEP/elbow_bearing_+1.step) / [STL](../cad/exports/STL/elbow_bearing_+1.stl) |
| `j3_gearbox_envelope` | Gearbox envelope | Steel | `Component25` | [STEP](../cad/exports/STEP/j3_gearbox_envelope.step) / [STL](../cad/exports/STL/j3_gearbox_envelope.stl) |
| `j3_motor_envelope` | Motor envelope | Polymer | `Component26` | [STEP](../cad/exports/STEP/j3_motor_envelope.step) / [STL](../cad/exports/STL/j3_motor_envelope.stl) |

### Forearm and wrist roll support (j3; 8 parts)

Rotates around J3; carries the forearm and stationary wrist roll housing/cover.

| Component / filename | Assembly role | Assumed material | FreeCAD object | Individual model |
|---|---|---|---|---|
| `elbow_rotor` | Structure | Aluminum | `Component27` | [STEP](../cad/exports/STEP/elbow_rotor.step) / [STL](../cad/exports/STL/elbow_rotor.stl) |
| `elbow_output_shaft` | Hollow output shaft | Steel | `Component28` | [STEP](../cad/exports/STEP/elbow_output_shaft.step) / [STL](../cad/exports/STL/elbow_output_shaft.stl) |
| `forearm_hollow_link` | Structure | Aluminum | `Component29` | [STEP](../cad/exports/STEP/forearm_hollow_link.step) / [STL](../cad/exports/STL/forearm_hollow_link.stl) |
| `forearm_service_cover_-1` | Service cover | Polymer | `Component30` | [STEP](../cad/exports/STEP/forearm_service_cover_-1.step) / [STL](../cad/exports/STL/forearm_service_cover_-1.stl) |
| `forearm_service_cover_+1` | Service cover | Polymer | `Component31` | [STEP](../cad/exports/STEP/forearm_service_cover_+1.step) / [STL](../cad/exports/STL/forearm_service_cover_+1.stl) |
| `wrist_roll_stator` | Structure | Aluminum | `Component32` | [STEP](../cad/exports/STEP/wrist_roll_stator.step) / [STL](../cad/exports/STL/wrist_roll_stator.stl) |
| `j4_bearing_envelope` | Bearing envelope | Steel | `Component33` | [STEP](../cad/exports/STEP/j4_bearing_envelope.step) / [STL](../cad/exports/STL/j4_bearing_envelope.stl) |
| `wrist_roll_cover` | Cover | Polymer | `Component35` | [STEP](../cad/exports/STEP/wrist_roll_cover.step) / [STL](../cad/exports/STL/wrist_roll_cover.stl) |

### Wrist roll rotor and pitch supports (j4; 3 parts)

Rotates around J4; the roll output carries the pitch fork.

| Component / filename | Assembly role | Assumed material | FreeCAD object | Individual model |
|---|---|---|---|---|
| `wrist_roll_rotor` | Structure | Aluminum | `Component34` | [STEP](../cad/exports/STEP/wrist_roll_rotor.step) / [STL](../cad/exports/STL/wrist_roll_rotor.stl) |
| `wrist_pitch_fork_-1` | Structure | Aluminum | `Component36` | [STEP](../cad/exports/STEP/wrist_pitch_fork_-1.step) / [STL](../cad/exports/STL/wrist_pitch_fork_-1.stl) |
| `wrist_pitch_fork_+1` | Structure | Aluminum | `Component37` | [STEP](../cad/exports/STEP/wrist_pitch_fork_+1.step) / [STL](../cad/exports/STL/wrist_pitch_fork_+1.stl) |

### Wrist pitch link (j5; 3 parts)

Rotates around J5; carries the pitch neck and final roll stator.

| Component / filename | Assembly role | Assumed material | FreeCAD object | Individual model |
|---|---|---|---|---|
| `wrist_pitch_rotor` | Structure | Aluminum | `Component38` | [STEP](../cad/exports/STEP/wrist_pitch_rotor.step) / [STL](../cad/exports/STL/wrist_pitch_rotor.stl) |
| `wrist_pitch_neck` | Structure | Aluminum | `Component39` | [STEP](../cad/exports/STEP/wrist_pitch_neck.step) / [STL](../cad/exports/STL/wrist_pitch_neck.stl) |
| `j6_stator_envelope` | Gearbox envelope | Steel | `Component40` | [STEP](../cad/exports/STEP/j6_stator_envelope.step) / [STL](../cad/exports/STL/j6_stator_envelope.stl) |

### Tool flange and parallel gripper (j6; 14 parts)

Rotates around J6; the two gripper jaw families additionally translate along local Y.

| Component / filename | Assembly role | Assumed material | FreeCAD object | Individual model |
|---|---|---|---|---|
| `tool_flange_6xM5_PCD46` | Structure | Steel | `Component41` | [STEP](../cad/exports/STEP/tool_flange_6xM5_PCD46.step) / [STL](../cad/exports/STL/tool_flange_6xM5_PCD46.stl) |
| `interchangeable_gripper_adapter` | Structure | Aluminum | `Component42` | [STEP](../cad/exports/STEP/interchangeable_gripper_adapter.step) / [STL](../cad/exports/STL/interchangeable_gripper_adapter.stl) |
| `gripper_pocketed_body` | Structure | Aluminum | `Component43` | [STEP](../cad/exports/STEP/gripper_pocketed_body.step) / [STL](../cad/exports/STL/gripper_pocketed_body.stl) |
| `gripper_top_service_cover` | Service cover | Polymer | `Component44` | [STEP](../cad/exports/STEP/gripper_top_service_cover.step) / [STL](../cad/exports/STL/gripper_top_service_cover.stl) |
| `gripper_guide_rod_-14` | Linear guide | Steel | `Component45` | [STEP](../cad/exports/STEP/gripper_guide_rod_-14.step) / [STL](../cad/exports/STL/gripper_guide_rod_-14.stl) |
| `gripper_guide_rod_+14` | Linear guide | Steel | `Component46` | [STEP](../cad/exports/STEP/gripper_guide_rod_+14.step) / [STL](../cad/exports/STL/gripper_guide_rod_+14.stl) |
| `opposite_hand_screw_envelope` | Opposite hand screw envelope | Steel | `Component47` | [STEP](../cad/exports/STEP/opposite_hand_screw_envelope.step) / [STL](../cad/exports/STL/opposite_hand_screw_envelope.stl) |
| `gripper_actuator_envelope` | Motor envelope | Polymer | `Component48` | [STEP](../cad/exports/STEP/gripper_actuator_envelope.step) / [STL](../cad/exports/STL/gripper_actuator_envelope.stl) |
| `gripper_jaw_carriage_-1` | Structure | Aluminum | `Component49` | [STEP](../cad/exports/STEP/gripper_jaw_carriage_-1.step) / [STL](../cad/exports/STL/gripper_jaw_carriage_-1.stl) |
| `gripper_finger_-1` | Structure | Aluminum | `Component50` | [STEP](../cad/exports/STEP/gripper_finger_-1.step) / [STL](../cad/exports/STL/gripper_finger_-1.stl) |
| `gripper_contact_pad_-1` | Replaceable contact pad | Polymer | `Component51` | [STEP](../cad/exports/STEP/gripper_contact_pad_-1.step) / [STL](../cad/exports/STL/gripper_contact_pad_-1.stl) |
| `gripper_jaw_carriage_+1` | Structure | Aluminum | `Component52` | [STEP](../cad/exports/STEP/gripper_jaw_carriage_+1.step) / [STL](../cad/exports/STL/gripper_jaw_carriage_+1.stl) |
| `gripper_finger_+1` | Structure | Aluminum | `Component53` | [STEP](../cad/exports/STEP/gripper_finger_+1.step) / [STL](../cad/exports/STL/gripper_finger_+1.stl) |
| `gripper_contact_pad_+1` | Replaceable contact pad | Polymer | `Component54` | [STEP](../cad/exports/STEP/gripper_contact_pad_+1.step) / [STL](../cad/exports/STL/gripper_contact_pad_+1.stl) |

## Gripper motion and checked scope

The two contact pads have 90 mm clear separation at maximum opening and touch at zero opening. Each jaw moves 45 mm; its carriage, finger and contact pad move together along local Y. The guide rods, body, screw envelope and actuator remain fixed in the tool frame. The saved component files show maximum opening; the interactive viewer applies the symmetric jaw translation.

The final review checked the pad gaps and jaw/body intersections at 0, 22.5, 45, 67.5 and 90 mm openings. The retained assembly screen checks every component pair at six poses and the closed/mid/open gripper. The trajectory screen checks 75 representative configurations. These finite digital checks do not certify every joint-angle combination or continuous physical motion.

See [final component review](../results/validation/final_cad_review.json), [native release consistency](../results/validation/cad_release_consistency.json), [CAD properties](../results/validation/cad_validation.json), [assembly clearance](../results/validation/cad_assembly_clearance.json) and [trajectory clearance](../results/validation/cad_motion_clearance.json) for the executed evidence. Drawings are concept interfaces without production tolerances.
