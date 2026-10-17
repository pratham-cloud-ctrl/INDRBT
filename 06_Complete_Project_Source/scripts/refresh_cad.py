"""Refresh native CAD inspection, renders, trajectory clearance and current proof.

Run after scripts/generate_cad.py and numerical trajectory generation. External
applications are located from PATH, Windows installation records, or explicit
--freecad-cmd / --blender paths. No user document is opened in the GUI.
"""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def executable(override, kind):
    if override:
        path = Path(override).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"{kind} executable missing: {path}")
        return str(path)
    name = "FreeCADCmd" if kind == "FreeCAD" else "blender"
    found = shutil.which(name) or shutil.which(name.lower())
    if found:
        return found
    if os.name == "nt":
        import winreg

        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for branch in (
                r"Software\Microsoft\Windows\CurrentVersion\Uninstall",
                r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
            ):
                try:
                    key = winreg.OpenKey(hive, branch)
                except OSError:
                    continue
                with key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            with winreg.OpenKey(key, winreg.EnumKey(key, i)) as entry:
                                display = str(winreg.QueryValueEx(entry, "DisplayName")[0])
                                if kind.lower() not in display.lower():
                                    continue
                                try:
                                    location = str(winreg.QueryValueEx(entry, "InstallLocation")[0])
                                except OSError:
                                    location = ""
                                try:
                                    icon = str(winreg.QueryValueEx(entry, "DisplayIcon")[0])
                                except OSError:
                                    icon = ""
                            root = Path(location)
                            candidates = (
                                [root / "bin/freecadcmd.exe", root / "freecadcmd.exe"]
                                if kind == "FreeCAD"
                                else [root / "blender.exe"]
                            )
                            if icon:
                                icon_path = Path(re.sub(r",\d+$", "", icon).strip('"'))
                                candidates.insert(
                                    0,
                                    icon_path.parent
                                    / ("freecadcmd.exe" if kind == "FreeCAD" else "blender.exe"),
                                )
                            for candidate in candidates:
                                if candidate.is_file():
                                    return str(candidate)
                        except OSError:
                            continue
    raise FileNotFoundError(
        f"{kind} not found. Put it on PATH or pass --{'freecad-cmd' if kind == 'FreeCAD' else 'blender'}."
    )


def run(command, input_text=None):
    print("CAD refresh:", Path(command[0]).name, " ".join(str(x) for x in command[1:]), flush=True)
    subprocess.run(command, cwd=ROOT, input=input_text, text=True, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freecad-cmd")
    parser.add_argument("--blender")
    parser.add_argument(
        "--review-only",
        action="store_true",
        help="Audit existing refreshed outputs; do not regenerate them",
    )
    args = parser.parse_args()
    if not args.review_only:
        freecad = executable(args.freecad_cmd, "FreeCAD")
        blender = executable(args.blender, "Blender")
        # FreeCADCmd console stdin is reliable on Windows even when positional
        # .py arguments are silently treated as documents rather than executed.
        script = ROOT / "cad/freecad/inspect_step.py"
        run(
            [freecad, "-c"], f"import runpy; runpy.run_path({str(script)!r}, run_name='__main__')\n"
        )
        run([blender, "--background", "--python", "cad/build123d/render_blender.py"])
        run([sys.executable, "cad/build123d/compose_poses.py"])
        run([blender, "--background", "--python", "cad/build123d/inspect_blender.py"])
        run([sys.executable, "cad/build123d/check_motion.py"])
    run([sys.executable, "scripts/review_cad.py"])
    proof = json.loads((ROOT / "results/validation/cad_release_consistency.json").read_text())
    if proof.get("status") != "PASS":
        raise RuntimeError("CAD release proof failed")
    print("CAD refresh and native consistency: PASS", flush=True)


if __name__ == "__main__":
    main()
