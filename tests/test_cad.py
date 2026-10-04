"""Digital CAD checks exercising solid topology, fits and independent frames."""

from pathlib import Path
import sys
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cad/build123d"))
from parameters import parameters  # noqa: E402
from geometry import build_components  # noqa: E402
from assembly import group_transforms, location  # noqa: E402
from robotarm.kinematics import RobotArm  # noqa: E402


@pytest.fixture(scope="module")
def cad():
    cfg, p = parameters()
    return cfg, p, build_components(p)


def test_cad_parts_are_valid_nonzero_breps(cad):
    _, _, parts = cad
    assert len(parts) == 54
    assert all(
        c.shape.is_valid and c.shape.volume > 0 and len(c.shape.solids()) == 1 for c in parts
    )


def test_cad_length_boundary_and_frames(cad):
    cfg, p, _ = cad
    assert p["upper_arm_length"] == 1000 * cfg["geometry"]["upper_arm_length"]
    q = np.array([15, -37, 86, 34, -51, 69.0])
    Ts = group_transforms(q, p)
    fk = RobotArm().frames(np.deg2rad(q))["link_transforms"]
    for i in range(6):
        T = Ts[f"j{i + 1}"].copy()
        T[:3, 3] /= 1000
        np.testing.assert_allclose(T, fk[i], atol=1e-13)
    from build123d import Pos, Sphere

    point = Pos(10, 20, 30) * Sphere(1)
    mapped = point.moved(location(Ts["j6"])).center()
    np.testing.assert_allclose(list(mapped), (Ts["j6"] @ [10, 20, 30, 1])[:3], atol=1e-10)


def test_gripper_actual_contact_gap_at_open_and_closed(cad):
    _, p, parts = cad
    for gap, cs in [(p["opening"], parts), (0, build_components(p, opening=0))]:
        byname = {c.name: c.shape for c in cs}
        plus = byname["gripper_contact_pad_+1"].bounding_box()
        minus = byname["gripper_contact_pad_-1"].bounding_box()
        assert plus.min.Y - minus.max.Y == pytest.approx(gap, abs=1e-7)
        assert (byname["gripper_jaw_carriage_+1"] & byname["gripper_jaw_carriage_-1"]).volume < 1e-7
    with pytest.raises(ValueError):
        build_components(p, opening=p["opening"] + 1)
