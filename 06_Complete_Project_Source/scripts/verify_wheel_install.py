"""Independent detached wheel verification; writes only a machine-neutral report."""

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import tomllib
import zipfile
from datetime import datetime, timezone
from tempfile import TemporaryDirectory

import numpy as np
import robotarm
from robotarm.config import load_config
from robotarm.gripper import ParallelGripper
from robotarm.planning import joint_trajectory, move_linear


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "source_root", type=Path, help="Source repository to compare with the installed wheel."
)
parser.add_argument("wheel", type=Path, help="Wheel installed in this interpreter's isolated venv.")
parser.add_argument(
    "--output",
    type=Path,
    help="Report path; defaults to source results/validation/packaging_validation.json.",
)
arguments = parser.parse_args()
repo = arguments.source_root.resolve()
wheel = arguments.wheel.resolve()
config_source = repo / "config" / "robot.yaml"
config_bundled = Path(robotarm.__file__).parent / "data" / "robot.yaml"
assert sys.prefix != sys.base_prefix
assert Path(robotarm.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
assert not Path(robotarm.__file__).resolve().is_relative_to(repo)
assert config_bundled.is_file()
assert config_bundled.read_bytes() == config_source.read_bytes()
config = load_config()
assert config["mass"]["upper_arm"] == 5.5
assert config["demo"]["approach_clearance"] == 0.070
assert config["demo"]["workspace_samples"] == 6000
source_version = tomllib.loads((repo / "pyproject.toml").read_text())["project"]["version"]
assert robotarm.__version__ == importlib.metadata.version("aster-arm") == source_version
arm = robotarm.RobotArm()
zero = arm.fk(np.zeros(6))
vertical = arm.fk(config["poses"]["vertical"])
np.testing.assert_allclose(zero[:3, 3], [0.790, 0, 0.190], atol=1e-12)
np.testing.assert_allclose(vertical[:3, 3], [0, 0, 0.980], atol=1e-12)
target = arm.fk(config["home"])
result = arm.solve_ik(target, config["home"] + np.deg2rad([3, -4, 5, 2, 4, -3]))
assert result.position_error_m < config["targets"]["ik_position_tolerance_m"]
assert result.orientation_error_rad < config["targets"]["ik_orientation_tolerance_rad"]
trajectory = joint_trajectory(arm, config["home"], config["poses"]["place"])
assert trajectory.metrics(arm)["max_velocity_limit_fraction"] <= 1
assert trajectory.metrics(arm)["max_acceleration_limit_fraction"] <= 1
gripper = ParallelGripper(config)
assert 0 < gripper.required_torque() < config["gripper"]["motor_torque"]
bad_target = target.copy()
bad_target[3, 3] = 2
try:
    move_linear(arm, config["home"], bad_target, samples=21)
except ValueError:
    pass
else:
    raise AssertionError("Wheel lacks invalid MOVE L target regression fix.")

with TemporaryDirectory(prefix="aster-wheel-cli-") as cli_directory:
    cli = subprocess.run(
        [
            sys.executable,
            "-I",
            "-m",
            "robotarm.demo",
            "--trajectory",
            "--output-dir",
            cli_directory,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    cli_summary = json.loads(cli.stdout)
    generated = Path(cli_directory) / "trajectories"
    assert (generated / "trajectory_metrics.json").is_file()
    metrics = json.loads((generated / "trajectory_metrics.json").read_text())
    assert metrics["move_l_max_xy_drift_m"] < config["targets"]["ik_position_tolerance_m"]
    images = list(generated.glob("*.png"))
    assert len(images) == 5
    for image in images:
        assert image.stat().st_size > 1000
    assert (generated / "move_j.csv").is_file() and (generated / "move_l.csv").is_file()

pip_check = subprocess.run(
    [sys.executable, "-m", "pip", "check"], check=True, capture_output=True, text=True
)
with zipfile.ZipFile(wheel) as archive:
    assert "robotarm/data/robot.yaml" in archive.namelist()
    assert archive.read("robotarm/data/robot.yaml") == config_source.read_bytes()

source_module = repo / "src" / "robotarm" / "kinematics" / "model.py"
installed_module = Path(robotarm.__file__).parent / "kinematics" / "model.py"
assert installed_module.read_bytes() == source_module.read_bytes()
source_hashes = {}
with zipfile.ZipFile(wheel) as archive:
    expected_modules = {
        path.relative_to(repo / "src").as_posix(): path
        for path in (repo / "src/robotarm").rglob("*.py")
    }
    actual_modules = {
        name for name in archive.namelist() if name.startswith("robotarm/") and name.endswith(".py")
    }
    assert actual_modules == set(expected_modules), "Wheel module inventory differs from source"
    for name, source_file in expected_modules.items():
        installed_file = Path(robotarm.__file__).parent.parent / name
        assert archive.read(name) == source_file.read_bytes() == installed_file.read_bytes(), name
        source_hashes[source_file.relative_to(repo).as_posix()] = hashlib.sha256(
            source_file.read_bytes()
        ).hexdigest()
for name in ("config/robot.yaml", "pyproject.toml", "setup.py", "MANIFEST.in"):
    source_hashes[name] = hashlib.sha256((repo / name).read_bytes()).hexdigest()
report = {
    "executed_utc": datetime.now(timezone.utc).isoformat(),
    "status": "PASS",
    "scope": "Built wheel, new isolated venv, installed runtime dependencies, detached import and actual CLI results",
    "python_version": sys.version.split()[0],
    "package_version": robotarm.__version__,
    "wheel_name": wheel.name,
    "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
    "source_sha256": source_hashes,
    "package_modules_compared": len(expected_modules),
    "authoritative_config_sha256": hashlib.sha256(config_source.read_bytes()).hexdigest(),
    "bundled_config_sha256": hashlib.sha256(config_bundled.read_bytes()).hexdigest(),
    "installed_import_relative_to_venv": Path(robotarm.__file__).relative_to(sys.prefix).as_posix(),
    "import_from_repository_source": False,
    "config_bundled_identical_to_authoritative": True,
    "current_upper_arm_mass_kg": config["mass"]["upper_arm"],
    "known_zero_tcp_m": zero[:3, 3].tolist(),
    "known_vertical_tcp_m": vertical[:3, 3].tolist(),
    "ik_from_perturbed_seed_position_error_m": result.position_error_m,
    "ik_from_perturbed_seed_orientation_error_rad": result.orientation_error_rad,
    "trajectory_velocity_limit_fraction": trajectory.metrics(arm)["max_velocity_limit_fraction"],
    "trajectory_acceleration_limit_fraction": trajectory.metrics(arm)[
        "max_acceleration_limit_fraction"
    ],
    "invalid_move_l_target_rejected": True,
    "cli_exit_code": cli.returncode,
    "cli_unique_output_directory": True,
    "cli_generated_plot_count": len(images),
    "cli_move_l_xy_drift_m": metrics["move_l_max_xy_drift_m"],
    "dependency_check": pip_check.stdout.strip(),
    "runtime_versions": {
        package: importlib.metadata.version(package)
        for package in ["numpy", "scipy", "matplotlib", "PyYAML", "pillow", "trimesh"]
    },
    "commands_normalized": [
        f"python -m venv work/{Path(sys.prefix).name}",
        f"work/{Path(sys.prefix).name}/Scripts/python -m pip install 'setuptools>=75' wheel",
        f"work/{Path(sys.prefix).name}/Scripts/python -m pip wheel --no-deps --no-build-isolation --wheel-dir OUTPUT_DIRECTORY REPOSITORY",
        f"work/{Path(sys.prefix).name}/Scripts/python -m pip install OUTPUT_DIRECTORY/{wheel.name}",
        f"cd work/{Path.cwd().name}",
        f"../{Path(sys.prefix).name}/Scripts/python -I REPOSITORY/scripts/verify_wheel_install.py REPOSITORY WHEEL",
        "python -I -m robotarm.demo --trajectory --output-dir TEMPORARY_NEW_DIRECTORY",
        "python -m pip check",
    ],
    "environment_note": "Build helpers and runtime dependencies installed in an isolated verification env; no shared or system packages modified.",
}
report_path = arguments.output or repo / "results" / "validation" / "packaging_validation.json"
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
