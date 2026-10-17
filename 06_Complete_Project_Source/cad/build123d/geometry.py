"""Original ASTER-6 prototype geometry, in millimetres.

Bearing, gearbox and motor internals are envelope representations. Hollow link
sections, interfaces, holes, clearances and gripper parts are explicit BReps.
"""

from dataclasses import dataclass
from math import cos, sin, pi
from build123d import Box, Cylinder, Pos, Rot, Axis, fillet


@dataclass
class Component:
    name: str
    group: str
    shape: object
    material: str
    color: str
    role: str


COLORS = {"aluminum": "#4C98AB", "steel": "#BAC3CB", "polymer": "#243949"}


def block(x, y, z, center=(0, 0, 0), radius=0, long_axis="X"):
    s = Box(x, y, z)
    if radius:
        s = fillet(s.edges().filter_by(getattr(Axis, long_axis)), radius)
    return Pos(*center) * s


def cyl(radius, length, center=(0, 0, 0), axis="Z"):
    s = Cylinder(radius, length)
    if axis == "X":
        s = Rot(0, 90, 0) * s
    elif axis == "Y":
        s = Rot(90, 0, 0) * s
    return Pos(*center) * s


def ring(ro, ri, length, center=(0, 0, 0), axis="Z"):
    return cyl(ro, length, center, axis) - cyl(ri, length + 2, center, axis)


def bolt_pattern(part, count, radius, hole_radius, length, center=(0, 0, 0), axis="Z"):
    for i in range(count):
        a = 2 * pi * i / count
        c = list(center)
        if axis == "Z":
            c[0] += radius * cos(a)
            c[1] += radius * sin(a)
        elif axis == "Y":
            c[0] += radius * cos(a)
            c[2] += radius * sin(a)
        else:
            c[1] += radius * cos(a)
            c[2] += radius * sin(a)
        part -= cyl(hole_radius, length, tuple(c), axis)
    return part


def hollow_link(length, width, depth, wall, start, end):
    beam = block(end - start, width, depth, ((start + end) / 2, 0, 0), radius=9)
    cavity = block(
        end - start + 2, width - 2 * wall, depth - 2 * wall, ((start + end) / 2, 0, 0), radius=5
    )
    beam -= cavity
    # Side service aperture; the two ribs on either end remain load bearing.
    aperture = block(
        max(20, end - start - 35), width + 2, depth * 0.45, ((start + end) / 2, 0, 0), radius=5
    )
    beam -= aperture
    # Four tapped cover mounting interfaces per side, outside the access cutout.
    for x in (start + 10, end - 10):
        for z in (-depth * 0.34, depth * 0.34):
            beam -= cyl(1.7, width + 4, (x, 0, z), "Y")
    return beam


def build_components(p, opening=None):
    """Return components in local frames base, j1, ..., j6.

    The parallel jaw setting is an explicit inner-face separation. All fingers
    translate symmetrically; maximum opening is from config, not a render scale.
    """
    opening = p["opening"] if opening is None else opening
    if not 0 <= opening <= p["opening"]:
        raise ValueError("Gripper opening outside travel")
    c = []

    def add(name, group, shape, material="aluminum", role="structure", color=None):
        c.append(Component(name, group, shape, material, color or COLORS[material], role))

    h = p["shoulder_height"]
    L = p["upper_arm_length"]
    F = p["forearm_length"]
    w = p["wall_thickness"]
    B = p["base_diameter"] / 2
    # Steel base, fixed hollow riser and slew-bearing seat.
    plate = ring(B, 22, 20, (0, 0, 10))
    plate = bolt_pattern(plate, 8, B - 20, 5.25, 24, (0, 0, 10))
    plate = bolt_pattern(plate, 8, B - 20, 8.5, 7, (0, 0, 16.5))
    add("base_mounting_plate", "base", plate, "steel")
    riser = ring(76, 57, h - 94, (0, 0, (20 + h - 74) / 2))
    riser = bolt_pattern(riser, 6, 66, 3.2, h - 90, (0, 0, (20 + h - 74) / 2))
    add("fixed_base_riser", "base", riser)
    add(
        "j1_slew_bearing_envelope",
        "base",
        ring(68, 55, 14, (0, 0, h - 74)),
        "steel",
        "bearing envelope",
    )
    add(
        "base_electronics_cover",
        "base",
        ring(79, 76.7, h - 103, (0, 0, (24 + h - 79) / 2)),
        "polymer",
        "removable cover",
    )
    # Rotating turret: axis at shoulder. Central cable shaft remains open.
    # Keep the fixed shoulder support below the rotating barrel and extrusion.
    # The original tall neck crossed the shoulder's articulation volume.
    add("turret_neck", "j1", ring(55, 25, 30, (0, 0, -65)))
    add("turret_bridge", "j1", block(110, 118, 12, (0, 0, -57), radius=4))
    for side in (-1, 1):
        cheek = ring(60, 37, 18, (0, side * 60, 0), "Y")
        cheek = bolt_pattern(cheek, 8, 48, 2.7, 24, (0, side * 60, 0), "Y")
        add(f"shoulder_fork_{side:+}", "j1", cheek)
        add(
            f"shoulder_bearing_{side:+}",
            "j1",
            ring(37, 28, 12, (0, side * 54, 0), "Y"),
            "steel",
            "bearing envelope",
        )
    add("j2_gearbox_envelope", "j1", cyl(46, 18, (0, -80, 0), "Y"), "steel", "gearbox envelope")
    add(
        "j2_motor_envelope",
        "j1",
        block(63, 60, 63, (0, -119, 0), radius=7, long_axis="Y"),
        "polymer",
        "motor envelope",
    )
    add("j2_motor_endcap", "j1", cyl(29, 5, (0, -151.5, 0), "Y"), "steel", "motor end cap")
    # Upper arm joint rotor and hollow extrusion with access covers.
    add("shoulder_rotor", "j2", ring(46, 28.1, 96, (0, 0, 0), "Y"))
    add(
        "shoulder_output_shaft",
        "j2",
        ring(28, 17, 128, (0, 0, 0), "Y"),
        "steel",
        "hollow output shaft",
    )
    add(
        "upper_arm_hollow_link",
        "j2",
        hollow_link(L, p["upper_arm_width"], p["upper_arm_depth"], w, 32, L - 110),
    )
    for sign in (-1, 1):
        # Long external cheek supports leave the central articulation envelope
        # clear for the 135-degree folded elbow. They overlap the extrusion wall
        # and joint rings in their own rigid group, not the rotating forearm.
        add(
            f"elbow_fork_bridge_{sign:+}",
            "j2",
            block(104, 12, 80, (L - 77, sign * 45, 0), radius=6, long_axis="Y"),
        )
    for side in (-1, 1):
        cover = block(
            L - 166,
            2.5,
            p["upper_arm_depth"] * 0.56,
            ((L - 78) / 2, side * (p["upper_arm_width"] / 2 + 1.25), 0),
            radius=4,
            long_axis="Y",
        )
        add(f"upper_service_cover_{side:+}", "j2", cover, "polymer", "service cover")
        fork = ring(52, 29, 12, (L, side * 47, 0), "Y")
        fork = bolt_pattern(fork, 8, 42, 2.2, 18, (L, side * 47, 0), "Y")
        add(f"elbow_fork_{side:+}", "j2", fork)
        add(
            f"elbow_bearing_{side:+}",
            "j2",
            ring(29, 20, 10, (L, side * 39, 0), "Y"),
            "steel",
            "bearing envelope",
        )
    add("j3_gearbox_envelope", "j2", cyl(38, 16, (L, -61, 0), "Y"), "steel", "gearbox envelope")
    add(
        "j3_motor_envelope",
        "j2",
        block(51, 53, 51, (L, -95.5, 0), radius=6, long_axis="Y"),
        "polymer",
        "motor envelope",
    )
    # Forearm and hollow wrist-roll stator with actual central cable bore.
    add("elbow_rotor", "j3", ring(38, 20, 64, (0, 0, 0), "Y"))
    add(
        "elbow_output_shaft",
        "j3",
        ring(19.8, 10, 92, (0, 0, 0), "Y"),
        "steel",
        "hollow output shaft",
    )
    add(
        "forearm_hollow_link",
        "j3",
        hollow_link(F, p["forearm_width"], p["forearm_depth"], w, 26, F - 24),
    )
    for side in (-1, 1):
        add(
            f"forearm_service_cover_{side:+}",
            "j3",
            block(
                F - 74,
                2.5,
                p["forearm_depth"] * 0.54,
                ((F + 2) / 2, side * (p["forearm_width"] / 2 + 1.25), 0),
                radius=4,
                long_axis="Y",
            ),
            "polymer",
            "service cover",
        )
    housing = ring(38, 27, 42, (F - 7, 0, 0), "X")
    housing = bolt_pattern(housing, 6, 32, 2.2, 48, (F - 7, 0, 0), "X")
    add("wrist_roll_stator", "j3", housing)
    add(
        "j4_bearing_envelope",
        "j3",
        ring(27, 24, 12, (F + 6, 0, 0), "X"),
        "steel",
        "bearing envelope",
    )
    # Roll rotor and pitch fork. The pitch housing clearance is 2 mm per side.
    lr = p["wrist_roll_length"]
    lp = p["wrist_pitch_length"]
    # Short roll sleeve and output backing plate leave a 2-mm axial gap to the
    # pitch barrel. The plate ties into the pitch cheeks outside their aperture.
    sleeve_length = lr - 30
    roll_rotor = ring(23.5, 11, sleeve_length, (sleeve_length / 2, 0, 0), "X")
    roll_rotor += ring(35, 11, 4, (sleeve_length + 2, 0, 0), "X")
    add("wrist_roll_rotor", "j4", roll_rotor)
    # This removable cover belongs to the stationary forearm/stator, not to
    # the rotating roll sleeve. Its inner diameter clears the stator exterior.
    add("wrist_roll_cover", "j3", ring(40, 38.2, 42, (F - 7, 0, 0), "X"), "polymer", "cover")
    for side in (-1, 1):
        cheek = ring(30, 17, 8, (lr, side * 30, 0), "Y")
        cheek = bolt_pattern(cheek, 6, 24, 1.8, 12, (lr, side * 30, 0), "Y")
        add(f"wrist_pitch_fork_{side:+}", "j4", cheek)
    add("wrist_pitch_rotor", "j5", ring(24, 12, 48, (0, 0, 0), "Y"))
    add("wrist_pitch_neck", "j5", ring(19, 10, lp - 12, ((lp + 12) / 2, 0, 0), "X"))
    add(
        "j6_stator_envelope",
        "j5",
        ring(24, 15, 12, (lp - 6, 0, 0), "X"),
        "steel",
        "gearbox envelope",
    )
    # Original interface: six M5 holes on 46-mm pitch circle, 30-mm pilot.
    flange = ring(p["tool_flange_diameter"] / 2, 8, 8, (4, 0, 0), "X")
    flange = bolt_pattern(flange, 6, 23, 2.75, 12, (4, 0, 0), "X")
    # The pilot is a real locating spigot, with 0.1-mm radial adapter clearance.
    flange += ring(15, 8, 4, (10, 0, 0), "X")
    add("tool_flange_6xM5_PCD46", "j6", flange, "steel")
    # OD60 leaves 4.25 mm of material outside each PCD46 clearance hole.
    adapter = ring(30, 15.1, 8, (12, 0, 0), "X")
    adapter = bolt_pattern(adapter, 6, 23, 2.75, 12, (12, 0, 0), "X")
    add("interchangeable_gripper_adapter", "j6", adapter)
    # Opposite-hand 4-mm lead screw + two transverse guides; body pocket exposes
    # motion on the front face, while screw/guide internals remain envelopes.
    body_width = p["opening"] + 56
    body = block(25, body_width, 48, (28.5, 0, 0), radius=6, long_axis="Y")
    # Carriages are 36 mm tall; the 38-mm pocket gives 1-mm top/bottom clearance.
    # Extend the cutting tool beyond the front face: an internal fillet at the
    # cutter's front would otherwise leave a small lip in the carriage path.
    body -= block(34, body_width - 20, 38, (37.5, 0, 0), radius=4, long_axis="Y")
    body = bolt_pattern(body, 6, 23, 2.75, 30, (28, 0, 0), "X")
    # Rear entrance reaches the pocket; the internal cable bend is conceptual.
    body -= cyl(8, 30, (28, 0, 0), "X")
    body -= cyl(4.3, body_width + 2, (28, 0, 0), "Y")
    for z in (-14, 14):
        body -= cyl(3.7, body_width + 2, (43, 0, z), "Y")
    for y in (-body_width / 2 + 10, body_width / 2 - 10):
        for z in (-18, 18):
            body -= cyl(2.25, 30, (28, y, z), "X")
    # A removable top hatch replaces the rear plate that crossed the adapter.
    body -= block(12, 80, 9, (29, 0, 22), radius=2, long_axis="Z")
    cover = block(16, 100, 2, (29, 0, 25), radius=2, long_axis="Z")
    for x in (24, 34):
        for y in (-44, 44):
            body -= cyl(1.7, 10, (x, y, 22), "Z")
            cover -= cyl(1.7, 4, (x, y, 25), "Z")
    add("gripper_pocketed_body", "j6", body)
    add(
        "gripper_top_service_cover",
        "j6",
        cover,
        "polymer",
        "service cover",
    )
    for z in (-14, 14):
        add(
            f"gripper_guide_rod_{z:+}",
            "j6",
            cyl(3.5, body_width - 10, (43, 0, z), "Y"),
            "steel",
            "linear guide",
        )
    add(
        "opposite_hand_screw_envelope",
        "j6",
        cyl(4, body_width + 8, (28, 0, 0), "Y"),
        "steel",
        "opposite hand screw envelope",
    )
    add(
        "gripper_actuator_envelope",
        "j6",
        block(30, 28, 30, (28, body_width / 2 + 19, 0), radius=4, long_axis="Y"),
        "polymer",
        "motor envelope",
    )
    for side in (-1, 1):
        yc = side * (opening / 2 + p["finger_thickness"] / 2 + 1.5)
        jaw = block(13, 10, 36, (43.5, yc, 0), radius=2, long_axis="Y")
        # An integrated nut boss and bridge connect the transverse screw to
        # each guided carriage. The smooth bore represents the threaded nut;
        # screw teeth, preload and contact forces remain conceptual.
        jaw += cyl(6, 10, (28, yc, 0), "Y")
        jaw += block(16, 10, 12, (36, yc, 0), radius=1, long_axis="Y")
        jaw -= cyl(4.2, 12, (28, yc, 0), "Y")
        # A lower mounting tab supports the finger without overlapping it.
        start = p["tool_length"] - p["finger_length"]
        jaw += block(20, 10, 7, (start + 9, yc, -12.5), radius=1, long_axis="Y")
        for z in (-14, 14):
            jaw -= cyl(3.6, 20, (43, yc, z), "Y")
        for x in (start + 6, start + 14):
            jaw -= cyl(1.7, 10, (x, yc, -12.5), "Z")
        add(f"gripper_jaw_carriage_{side:+}", "j6", jaw)
        finger = block(
            p["finger_length"],
            p["finger_thickness"],
            p["finger_width"],
            (start + p["finger_length"] / 2, yc, 0),
            radius=1.5,
        )
        for x in (start + 6, start + 14):
            finger -= cyl(1.7, p["finger_width"] + 2, (x, yc, 0), "Z")
        add(f"gripper_finger_{side:+}", "j6", finger)
        add(
            f"gripper_contact_pad_{side:+}",
            "j6",
            block(
                22,
                1.5,
                p["finger_width"] - 3,
                (p["tool_length"] - 11, side * (opening / 2 + 0.75), 0),
                radius=0.6,
            ),
            "polymer",
            "replaceable contact pad",
            "#EDA34E",
        )
    return c
