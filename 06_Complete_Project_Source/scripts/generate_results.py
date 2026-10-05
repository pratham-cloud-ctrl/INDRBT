"""Regenerate numerical demonstrations and transparent engineering experiments."""

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    commands = [
        ["-m", "robotarm.demo", "--all"],
        ["-m", "analysis.joint_torque_analysis"],
        ["-m", "analysis.structural_analysis"],
        ["-m", "analysis.research_experiments"],
        ["scripts/build_viewer.py"],
    ]
    for args in commands:
        result = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True)
        if result.returncode:
            print(result.stdout, result.stderr)
            raise SystemExit(result.returncode)
        print(f"{' '.join(args)}: generated", flush=True)
