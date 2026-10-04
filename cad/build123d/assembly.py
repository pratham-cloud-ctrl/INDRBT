"""Explicit rigid transforms match the robotics model; CAD uses mm at boundary."""

import numpy as np
from build123d import Location, Compound


def rotation(axis, angle):
    c, s = np.cos(angle), np.sin(angle)
    R = {
        "X": [[1, 0, 0], [0, c, -s], [0, s, c]],
        "Y": [[c, 0, s], [0, 1, 0], [-s, 0, c]],
        "Z": [[c, -s, 0], [s, c, 0], [0, 0, 1]],
    }[axis]
    T = np.eye(4)
    T[:3, :3] = R
    return T


def translation(x=0, y=0, z=0):
    T = np.eye(4)
    T[:3, 3] = [x, y, z]
    return T


def group_transforms(q_deg, p):
    q = np.deg2rad(q_deg)
    out = {"base": np.eye(4)}
    T = translation(z=p["shoulder_height"])
    offsets = [
        0,
        0,
        p["upper_arm_length"],
        p["forearm_length"],
        p["wrist_roll_length"],
        p["wrist_pitch_length"],
    ]
    for i, (axis, d) in enumerate(zip("ZYYXYX", offsets)):
        T = T @ translation(x=d) @ rotation(axis, q[i])
        out[f"j{i + 1}"] = T.copy()
    return out


def location(T):
    # Axis-angle avoids ambiguities in Euler convention and gimbal lock.
    from scipy.spatial.transform import Rotation

    rv = Rotation.from_matrix(T[:3, :3]).as_rotvec()
    angle = np.linalg.norm(rv)
    if angle < 1e-12:
        return Location(tuple(T[:3, 3]))
    return Location(tuple(T[:3, 3]), tuple(rv / angle), float(np.rad2deg(angle)))


def assemble(components, q_deg, p):
    Ts = group_transforms(q_deg, p)
    shapes = []
    for c in components:
        s = c.shape.moved(location(Ts[c.group]))
        s.label = c.name
        shapes.append(s)
    return Compound(children=shapes), Ts
