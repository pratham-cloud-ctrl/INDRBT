"""Refresh the organized presentation from the authoritative source project.

Requires the development extra (Markdown). Preserves Git metadata and archives.
"""

from pathlib import Path
import hashlib
import html
import json
import os
import re
import shutil
import tomllib
from urllib.parse import quote, unquote
import markdown

SOURCE = Path(__file__).resolve().parents[1]
ROOT = SOURCE
DEST = SOURCE.parent
PROJECT = SOURCE
version = tomllib.loads((SOURCE / "pyproject.toml").read_text(encoding="utf-8"))["project"][
    "version"
]
validation_path = SOURCE / "results/validation/validation_report.json"
status = (
    json.loads(validation_path.read_text())["project_status"]
    if validation_path.exists()
    else "VALIDATION PENDING"
)
copies = []
derived = []
previous_manifest = (
    json.loads((DEST / "ORGANIZATION_MANIFEST.json").read_text())
    if (DEST / "ORGANIZATION_MANIFEST.json").exists()
    else {}
)


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


TRANSIENT_SUFFIXES = {".log", ".lck", ".bak", ".pyc", ".pyo", ".kicad_prl", ".FCBak", ".blend1"}


def copy(rel, target):
    src = SOURCE / rel
    dst = DEST / target
    if src.suffix in TRANSIENT_SUFFIXES or src.name in {"Thumbs.db", ".DS_Store"}:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    if digest(src) != digest(dst):
        raise RuntimeError(f"Copy hash mismatch: {dst.name}")
    copies.append(
        {
            "source": str(rel).replace("\\", "/"),
            "file": str(target).replace("\\", "/"),
            "sha256": digest(dst),
        }
    )


for kind in ("STEP", "STL"):
    for p in (SOURCE / f"cad/exports/{kind}").glob("*"):
        group = "Assemblies" if p.name.startswith("assembly_") else "Individual_Parts"
        copy(p.relative_to(SOURCE), f"01_CAD_Models/{kind}/{group}/{p.name}")
copy("cad/freecad/aster6_home.FCStd", "01_CAD_Models/FreeCAD/aster6_home.FCStd")
copy("cad/renders/aster6_home.blend", "01_CAD_Models/Blender/aster6_home.blend")
for p in (SOURCE / "docs/drawings").glob("*"):
    if p.is_file():
        copy(p.relative_to(SOURCE), f"01_CAD_Models/Drawings/{p.name}")
for p in (SOURCE / "cad/renders").glob("*.png"):
    copy(p.relative_to(SOURCE), f"01_CAD_Models/Preview_Images/{p.name}")
copy("simulations/aster6_twin.html", "02_Simulation_and_Animation/Interactive_3D_Viewer.html")
copy("simulations/viewer_preview.png", "02_Simulation_and_Animation/viewer_preview.png")
for category in ("trajectories", "control", "workspace"):
    for p in (SOURCE / f"results/{category}").glob("*"):
        if p.is_file():
            copy(p.relative_to(SOURCE), f"02_Simulation_and_Animation/{category.title()}/{p.name}")
for category in ("mechanical", "research", "validation"):
    for p in (SOURCE / f"results/{category}").glob("*"):
        if p.is_file():
            copy(p.relative_to(SOURCE), f"03_Reports_and_Results/{category.title()}/{p.name}")
for p in (SOURCE / "electronics").rglob("*"):
    if (
        p.is_file()
        and p.suffix not in (".py", ".md", ".kicad_prl")
        and "__pycache__" not in p.parts
    ):
        copy(p.relative_to(SOURCE), Path("04_Electronics") / p.relative_to(SOURCE / "electronics"))
STYLE = """body{margin:0;background:#101923;color:#e2eaf2;font:17px/1.65 Segoe UI,Arial,sans-serif}main{max-width:1150px;margin:auto;padding:36px}h1,h2,h3{line-height:1.2;color:#fff}h1{font-size:42px}a{color:#7dd9f8}img{max-width:100%;border-radius:14px}header{display:grid;grid-template-columns:1fr 1fr;gap:28px;align-items:center}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:18px}.card{padding:22px;background:#1d2b3a;border:1px solid #34465a;border-radius:14px}.button{display:inline-block;padding:12px 20px;background:#38b8d4;color:#071c25;font-weight:700;border-radius:9px;text-decoration:none;margin:4px 8px 4px 0}.tag{font-size:13px;color:#a3bbce;letter-spacing:1px}table{border-collapse:collapse;display:block;overflow:auto}td,th{border:1px solid #47596b;padding:8px}pre{overflow:auto;background:#192839;padding:18px}code{font-size:14px}li{margin:5px 0}@media(max-width:750px){header{grid-template-columns:1fr}main{padding:20px}h1{font-size:30px}}"""


def page(title, body):
    return f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(title)}</title><style>{STYLE}</style><main>{body}</main></html>'


# Markdown documents link to their readable HTML counterparts. Data and native
# engineering files retain their source-relative targets.
reports = []
report_sources = [SOURCE / "README.md", *(SOURCE / "docs").glob("*.md")]
report_targets = {
    p.resolve(): (
        DEST
        / "03_Reports_and_Results/Readable_Reports"
        / ("Project_Readme.html" if p.name == "README.md" else p.with_suffix(".html").name)
    )
    for p in report_sources
}
for p in report_sources:
    target = report_targets[p.resolve()]
    target.parent.mkdir(parents=True, exist_ok=True)
    rendered = markdown.markdown(
        p.read_text(encoding="utf-8"), extensions=["tables", "fenced_code", "toc"]
    )

    def rewrite(m):
        url = html.unescape(m.group(2))
        if re.match(r"^(?:[a-zA-Z]+:|#|//)", url):
            return m.group(0)
        filepart, sep, fragment = url.partition("#")
        resolved = (p.parent / unquote(filepart)).resolve()
        try:
            rel = resolved.relative_to(SOURCE)
        except ValueError:
            return m.group(0)
        mapped = report_targets.get(resolved, PROJECT / rel)
        link = quote(os.path.relpath(mapped, target.parent).replace("\\", "/"), safe="/") + (
            sep + fragment if sep else ""
        )
        return f'{m.group(1)}="{html.escape(link, quote=True)}"'

    rendered = re.sub(r'(href|src)="([^"]*)"', rewrite, rendered)
    target.write_text(
        page(p.stem, '<a href="../../START_HERE.html">← Project home</a>' + rendered),
        encoding="utf-8",
    )
    reports.append((p.stem, str(target.relative_to(DEST)).replace("\\", "/")))
    derived.append(
        {
            "source": p.relative_to(SOURCE).as_posix(),
            "source_sha256": digest(p),
            "file": target.relative_to(DEST).as_posix(),
            "sha256": digest(target),
        }
    )
cards = [
    (
        "01 · CAD models",
        "Individual parts and six complete poses. Editable FreeCAD, STEP/STL, Blender, drawings and preview images.",
        "#open-cad",
        "FreeCAD opening instructions",
    ),
    (
        "02 · Simulation and animation",
        "Rotate the actual 3D robot, select poses, adjust six joints, move the gripper and play the pick-and-place demonstration.",
        "02_Simulation_and_Animation/Interactive_3D_Viewer.html",
        "Open 3D viewer",
    ),
    (
        "03 · Reports and results",
        "Engineering report, mechanical calculations, research experiments and executed validation results.",
        "03_Reports_and_Results/Readable_Reports/engineering_report.html",
        "Read engineering report",
    ),
    (
        "04 · Electronics",
        "Native KiCad schematic and routed PCB, readable PDFs, manufacturing exports, component list, connection data and checks.",
        "04_Electronics/exports/joint_interface.pdf",
        "View schematic PDF",
    ),
    (
        "05 · Reference and notes",
        "Requirements, design decisions, project journal and links to the authoritative documents.",
        "03_Reports_and_Results/Readable_Reports/project_journal.html",
        "Read project journal",
    ),
    (
        "06 · Complete source project",
        "Complete reproducible source. The parent repository retains the Git history; scripts keep their source-relative layout.",
        "03_Reports_and_Results/Readable_Reports/Project_Readme.html",
        "Project source guide",
    ),
]
body = """<header><div><div class="tag">ASTER-6 · DIGITAL ENGINEERING PROJECT</div><h1>Your robot project,<br>all in one place.</h1><p>Start with the interactive 3D viewer. It opens in a browser and displays the actual CAD meshes without needing a CAD application.</p><a class="button" href="02_Simulation_and_Animation/Interactive_3D_Viewer.html">View the robot in 3D</a><a href="03_Reports_and_Results/Readable_Reports/engineering_report.html">Engineering report</a><p class="tag">VERSION_PLACEHOLDER · Digital only · STATUS_PLACEHOLDER</p></div><img src="01_CAD_Models/Preview_Images/hero.png" alt="ASTER-6 actual CAD assembly"></header><h2 id="open-cad">Open the CAD models</h2><ol><li><b>For viewing:</b> double-click <b>OPEN_3D_VIEWER.cmd</b> in this folder. It explicitly opens an installed browser, avoiding Windows file-association problems. Drag to orbit; use the wheel to zoom.</li><li><b>For CAD editing:</b> double-click <b>OPEN_FREECAD_MODEL.cmd</b>. It explicitly opens the assembled robot in the installed FreeCAD application. STEP and STL files are CAD/mesh data, rather than ordinary documents.</li><li><b>For individual parts:</b> use FreeCAD’s File → Open and select a file from <b>01_CAD_Models/STEP/Individual_Parts</b>. Complete poses are under <b>STEP/Assemblies</b>.</li></ol><h2>Project folders</h2><section class="cards">"""
for title, desc, url, label in cards:
    body += f'<div class="card"><h3>{title}</h3><p>{desc}</p><a href="{url}">{label} →</a></div>'
body = body.replace(
    '<h2 id="open-cad">',
    '<nav aria-label="Engineering guides"><p><a class="button" href="03_Reports_and_Results/Readable_Reports/component_catalog.html">CAD component catalog</a>'
    '<a class="button" href="03_Reports_and_Results/Readable_Reports/theory_guide.html">Theory guide</a>'
    '<a class="button" href="03_Reports_and_Results/Readable_Reports/electronics_components.html">Electronics components</a></p></nav><h2 id="open-cad">',
)
body += '</section><h2>CAD drawings and previews</h2><p><a href="01_CAD_Models/Drawings/engineering_interfaces.pdf">Dimensioned interface drawings (PDF)</a> · <a href="01_CAD_Models/Preview_Images/gripper.png">Gripper close-up</a> · <a href="01_CAD_Models/Preview_Images/poses.png">All six poses</a></p><h2>Readable documentation</h2><ul>'
for name, url in reports:
    body += f'<li><a href="{url}">{html.escape(name.replace("_", " "))}</a></li>'
body += "</ul><h2>Engineering scope</h2><p>This is a digital engineering project with a conceptual PCB. Physical payload/repeatability, EMC, production suitability and full continuous collision verification are outside the verified scope. The browser viewer does not prevent collisions when manually changing joint angles.</p><p>Presentation folders contain verified copies of source artifacts. Regenerate outputs from 06_Complete_Project_Source, then refresh the organized copies. SHA-256 checks are recorded in ORGANIZATION_MANIFEST.json.</p>"
body += '<h2>Completed PCB layout</h2><p>Open <b>OPEN_PCB_LAYOUT.cmd</b> for editing in KiCad. <a href="04_Electronics/exports/pcb_top.png">Top view</a> · <a href="04_Electronics/exports/pcb_layers.pdf">Layer drawings</a> · <a href="04_Electronics/pcb_verification.json">Executed board checks</a></p><img src="04_Electronics/exports/pcb_3d.png" alt="Native KiCad render of the routed joint interface PCB">'
body = body.replace("VERSION_PLACEHOLDER", version).replace(
    "STATUS_PLACEHOLDER", html.escape(status)
)
(DEST / "START_HERE.html").write_text(page("ASTER-6 | Start here", body), encoding="utf-8")
for filename, view in (
    ("OPEN_3D_VIEWER.cmd", "Viewer"),
    ("OPEN_FREECAD_MODEL.cmd", "FreeCAD"),
    ("OPEN_PCB_LAYOUT.cmd", "PCB"),
    ("OPEN_PROJECT_HOME.cmd", "Home"),
):
    script = (
        '@echo off\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp006_Complete_Project_Source\\scripts\\open_project.ps1" -View '
        + view
        + "\r\n"
    )
    (DEST / filename).write_bytes(script.encode("utf-8"))
(DEST / "START_HERE.txt").write_text(
    "ASTER-6 PROJECT\n\nDouble-click OPEN_PROJECT_HOME.cmd for the visual project guide.\nDouble-click OPEN_3D_VIEWER.cmd to see the robot in a browser.\nDouble-click OPEN_FREECAD_MODEL.cmd to edit the assembly in FreeCAD.\nDouble-click OPEN_PCB_LAYOUT.cmd to edit the routed board in KiCad.\n\nCAD files are not Word/text documents. The launchers explicitly select the correct installed applications.\nIf you move the folder to another computer, open START_HERE.html in a web browser and open the FCStd file through FreeCAD File > Open.\n\n01_CAD_Models: assemblies, individual parts, drawings, renders and native models\n02_Simulation_and_Animation: interactive 3D viewer, trajectories, workspace and control results\n03_Reports_and_Results: readable reports, numerical data and validation\n04_Electronics: native schematic/PCB, views, fabrication exports and actual checks\n05_Reference_and_Project_Notes: index to authoritative documents and readable reports\n06_Complete_Project_Source: complete reproducible source; Git history belongs to the parent repository\n07_Releases: downloadable release ZIP; original preview retained in 07_Original_Release_Archive\n\nPresentation files are copies. Use 06_Complete_Project_Source for regeneration.\n",
    encoding="utf-8",
)
for name in ("LICENSE", "NOTICE.md", "CITATION.cff", "CONTRIBUTING.md", "CHANGELOG.md"):
    copy(name, name)
readme = f"""# ASTER-6 · Six-axis robot arm and parallel gripper

**Version {version} · {status} · Digital engineering design**

An educational mechatronics project connecting original parametric CAD, robot kinematics, motion planning, PID control, analytical mechanics and a routed KiCad joint/sensor interface. The models, results and engineering decisions are reproducible from versioned source.

![Actual ASTER-6 CAD assembly](01_CAD_Models/Preview_Images/hero.png)

## Start here

[Download the complete v{version} release](https://github.com/pratham-cloud-ctrl/industrial-robot-arm-digital-twin/releases/tag/v{version}) or clone this repository. Double-click **OPEN_PROJECT_HOME.cmd** for the project guide or **OPEN_3D_VIEWER.cmd** to view and move the robot. The viewer can isolate any of the 54 components and automatically fit it on screen. Use **OPEN_FREECAD_MODEL.cmd** for CAD editing and **OPEN_PCB_LAYOUT.cmd** for the KiCad board. These Windows launchers locate installed Chrome/Edge, FreeCAD and KiCad; they avoid incorrect file associations. On other systems, open [START_HERE.html](START_HERE.html) or [the interactive viewer](02_Simulation_and_Animation/Interactive_3D_Viewer.html) in a browser.

GitHub displays HTML source. Download the project to run its offline viewer.

## Review the project in five minutes

| Inspect | Start with | Continue with |
|---|---|---|
| Mechanical design | [Dimensioned drawings](01_CAD_Models/Drawings/engineering_interfaces.pdf) and [six poses](01_CAD_Models/Preview_Images/poses.png) | [54-part component catalog](06_Complete_Project_Source/docs/component_catalog.md) and [CAD methodology](06_Complete_Project_Source/docs/04_cad.md) |
| Robot theory | [Theory guide](06_Complete_Project_Source/docs/theory_guide.md) | [Kinematics](06_Complete_Project_Source/docs/02_kinematics.md), [mechanics](06_Complete_Project_Source/docs/03_mechanical_analysis.md) and [engineering report](06_Complete_Project_Source/docs/engineering_report.md) |
| Motion and control | [Workspace](02_Simulation_and_Animation/Workspace/workspace_3d.png), animation below and [PID tracking](02_Simulation_and_Animation/Control/pid_tracking.png) | [Recorded trajectories](02_Simulation_and_Animation/Trajectories) and [numerical software](06_Complete_Project_Source/src/robotarm) |
| Electronics | [Schematic PDF](04_Electronics/exports/joint_interface.pdf), [board layers](04_Electronics/exports/pcb_layers.pdf) and [component guide](06_Complete_Project_Source/docs/electronics_components.md) | [Electronics design](06_Complete_Project_Source/docs/05_electronics.md), [BOM](04_Electronics/bom.csv) and [fabrication files](04_Electronics/fabrication) |
| Verification | [Executed validation](06_Complete_Project_Source/results/validation/validation_report.md) and [requirements matrix](06_Complete_Project_Source/docs/validation_matrix.md) | [Independent review evidence](03_Reports_and_Results/Validation) and [software checks on GitHub](https://github.com/pratham-cloud-ctrl/industrial-robot-arm-digital-twin/actions/workflows/validation.yml) |

Native STEP/STL/FCStd and KiCad files are editable engineering data. Use the supplied app launchers or open them inside the appropriate application; PDF/PNG previews provide immediate viewing.

![Forward-kinematics line-model pick-and-place animation](02_Simulation_and_Animation/Trajectories/pick_place_fk.gif)

## Organized project folders

| Folder | Contents |
|---|---|
| [01_CAD_Models](01_CAD_Models) | FreeCAD and Blender models, STEP/STL assemblies and individual parts, drawings and renders |
| [02_Simulation_and_Animation](02_Simulation_and_Animation) | Offline interactive 3D viewer, pick/place data, workspace and PID results |
| [03_Reports_and_Results](03_Reports_and_Results) | Browser-readable engineering reports, mechanical/research data and validation evidence |
| [04_Electronics](04_Electronics) | Native KiCad schematic/PCB, BOM, board views, Gerbers/drill and verification reports |
| [05_Reference_and_Project_Notes](05_Reference_and_Project_Notes) | Index to original source documents and browser-readable reports |
| [06_Complete_Project_Source](06_Complete_Project_Source) | Reproducible CAD, analysis, software, tests, electronics generators and authoritative configuration |
| [07_Releases](07_Releases) | Versioned complete download and Python wheel information |

Presentation folders contain verified copies. The complete source folder is authoritative; regenerate outputs there and run `python scripts/sync_presentation.py` to refresh the organized copies. The copy hashes are in [ORGANIZATION_MANIFEST.json](ORGANIZATION_MANIFEST.json).

## Engineering and verification

Read the [engineering report](06_Complete_Project_Source/docs/engineering_report.md), [scope audit](06_Complete_Project_Source/docs/digital_scope_audit.md), [requirements matrix](06_Complete_Project_Source/docs/validation_matrix.md), [executed validation](06_Complete_Project_Source/results/validation/validation_report.md) and [detailed source README](06_Complete_Project_Source/README.md).

The robot has six revolute joints, 790 mm nominal shoulder-centred reach and a 90 mm parallel-jaw opening. Payload 4 kg and repeatability ±0.1 mm are design targets. No physical robot or electronics were built. Analytical stiffness, independent-axis PID, sampled clearance and conceptual PCB checks establish their stated digital scope; they do not establish certified hardware performance, EMC, production suitability or functional safety.

![Native KiCad view of the joint and sensor PCB](04_Electronics/exports/pcb_3d.png)

## Engineering process

Start from [requirements](06_Complete_Project_Source/docs/01_requirements.md), follow [architecture](06_Complete_Project_Source/docs/architecture.md) and [design decisions](06_Complete_Project_Source/docs/design_decisions.md), then compare calculations with the generated evidence. The [project journal](06_Complete_Project_Source/docs/project_journal.md) records actual faults, corrections and tool checks. CAD clearance is checked at named poses and sampled task configurations; the scope and limitations are recorded alongside the results.

The GitHub workflow checks numerical software, analytical regressions, lint, documentation, copied artifacts and saved electronics connectivity. Native KiCad ERC/DRC and full CAD checks are executed locally with the required engineering applications. [Reproduce the full validation](06_Complete_Project_Source/README.md#run) for those checks.

## Reproduce

From the cloned repository:

```bash
cd 06_Complete_Project_Source
python -m venv .venv
```

Activate the environment, then:

```bash
python -m pip install -e ".[cad,dev]"
python -m robotarm.demo --all
python scripts/run_validation.py --full
python scripts/sync_presentation.py
```

KiCad 10 is required for native electronics checks. Build123d and the numerical libraries are installed by the CAD/development extras. FreeCAD and Blender support independent CAD inspection and rendering. Detailed tool commands and engineering assumptions are in the source documentation.

MIT-licensed original source. Third-party software and libraries retain their licenses.
"""
(DEST / "README.md").write_text(readme, encoding="utf-8")
notes = DEST / "05_Reference_and_Project_Notes/README.md"
notes.parent.mkdir(parents=True, exist_ok=True)
notes.write_text(
    "# Reference and project notes\n\nRead [the source documentation](../06_Complete_Project_Source/docs) or [the browser-readable reports](../03_Reports_and_Results/Readable_Reports).\n\n- [Requirements](../03_Reports_and_Results/Readable_Reports/01_requirements.html)\n- [Design decisions](../03_Reports_and_Results/Readable_Reports/design_decisions.html)\n- [Project journal](../03_Reports_and_Results/Readable_Reports/project_journal.html)\n- [Release notes](../03_Reports_and_Results/Readable_Reports/release_notes.html)\n\nCanonical Markdown stays in its source-relative layout so its links remain valid.\n",
    encoding="utf-8",
)
folder_indexes = {
    "01_CAD_Models/README.md": """# CAD models and mechanical components

Start with **OPEN_3D_VIEWER.cmd** in the parent folder. Choose **CAD component** in the viewer to inspect any of the 54 parts, or select a complete named pose. Use **OPEN_FREECAD_MODEL.cmd** for the editable assembly.

- [Part roles, materials and STEP/STL links](../06_Complete_Project_Source/docs/component_catalog.md)
- [Native FreeCAD assembly](FreeCAD/aster6_home.FCStd) — open inside FreeCAD
- [Blender scene](Blender/aster6_home.blend) — open inside Blender
- [STEP assemblies](STEP/Assemblies) and [individual STEP parts](STEP/Individual_Parts)
- [STL assemblies](STL/Assemblies) and [individual STL parts](STL/Individual_Parts)
- [Dimensioned drawing PDF](Drawings/engineering_interfaces.pdf)
- [Assembly render](Preview_Images/hero.png), [gripper](Preview_Images/gripper.png) and [six poses](Preview_Images/poses.png)
- [CAD methodology and clearance scope](../06_Complete_Project_Source/docs/04_cad.md)

STEP/STL links are engineering data. Open them through FreeCAD's File > Open rather than an ordinary text/document application.
""",
    "02_Simulation_and_Animation/README.md": """# Simulation and animation

- [Interactive CAD viewer](Interactive_3D_Viewer.html) — download the project and open locally in a browser
- [Recorded FK animation](Trajectories/pick_place_fk.gif)
- [Joint/TCP trajectory data](Trajectories) and [pick/place metrics](Trajectories/pick_place_metrics.json)
- [Workspace cloud](Workspace/workspace_3d.png), [projections](Workspace/workspace_projections.png) and [singularities](Workspace/singularity_analysis.png)
- [PID tracking](Control/pid_tracking.png), [step response](Control/pid_step_response.png) and [metrics](Control/metrics.json)
- [Theory guide](../06_Complete_Project_Source/docs/theory_guide.md)

The viewer isolates individual CAD parts and animates the planner's recorded joints. Object attachment is ideal, controller plants are independent assumed inertias/damping, and manual joint settings can collide. These are documented digital models.
""",
    "03_Reports_and_Results/README.md": """# Reports, theory and verification

For browser reading, open the [project guide](../START_HERE.html) and [readable reports](Readable_Reports). Document links within readable reports stay in readable HTML.

- [Engineering report](../06_Complete_Project_Source/docs/engineering_report.md)
- [Theory guide](../06_Complete_Project_Source/docs/theory_guide.md)
- [Mechanical calculations](Mechanical) and [research experiments](Research)
- [Executed validation](Validation/validation_report.md), [numerical checks](Validation/numerical_validation.json) and [requirements matrix](../06_Complete_Project_Source/docs/validation_matrix.md)
- [CAD review](Validation/final_cad_review.json), [electronics review](Validation/final_electronics_review.json) and [theory review](Validation/final_theory_review.json)

Results distinguish assumptions, design targets, calculations and digitally verified behavior. Source documents and generation scripts remain authoritative in 06_Complete_Project_Source.
""",
    "04_Electronics/README.md": """# Electronics, components and PCB

Double-click **OPEN_PCB_LAYOUT.cmd** in the parent folder to edit the board in KiCad. For immediate viewing, use the PDF and PNG links below.

- [Schematic PDF](exports/joint_interface.pdf)
- [PCB 3D view](exports/pcb_3d.png), [top view](exports/pcb_top.png) and [six-page layer PDF](exports/pcb_layers.pdf)
- [Component functions and selection guide](../06_Complete_Project_Source/docs/electronics_components.md), [BOM](bom.csv) and [electrical calculations](interface_calculations.json)
- [Native schematic](joint_interface.kicad_sch), [native PCB](joint_interface.kicad_pcb) and [KiCad project](joint_interface.kicad_pro) — open inside KiCad
- [Portable project libraries](fp-lib-table) and [local fuse footprint](ASTER_Interface.pretty)
- [Native ERC evidence](erc_report.json), [native DRC evidence](pcb_drc_report.json) and [independent PCB verification](pcb_verification.json)
- [Fabrication ZIP](fabrication/joint_interface_fabrication.zip), [Gerbers/drills/positions](fabrication) and [fabrication review](../06_Complete_Project_Source/docs/05_electronics.md)

This is a conceptual low-voltage joint/sensor interface, not a motor power stage or safety controller. Native layout/connectivity checks and manufacturer footprint dimensions are documented; physical qualification and manufacturer CAM approval have not been performed.
""",
}
for name, contents in folder_indexes.items():
    (DEST / name).write_text(contents, encoding="utf-8")
generated_names = [
    "START_HERE.html",
    "START_HERE.txt",
    "README.md",
    "OPEN_PROJECT_HOME.cmd",
    "OPEN_3D_VIEWER.cmd",
    "OPEN_FREECAD_MODEL.cmd",
    "OPEN_PCB_LAYOUT.cmd",
    "05_Reference_and_Project_Notes/README.md",
    *folder_indexes,
]
generated = [{"file": name, "sha256": digest(DEST / name)} for name in generated_names]
managed = {entry["file"] for entry in copies + derived + generated}
for previous in previous_manifest.get("artifact_copies", []):
    name = previous["file"]
    if name not in managed and name.startswith(
        (
            "01_CAD_Models/",
            "02_Simulation_and_Animation/",
            "03_Reports_and_Results/",
            "04_Electronics/",
            "05_Reference_and_Project_Notes/",
        )
    ):
        old = DEST / name
        if (
            old.is_file()
            and old.resolve().is_relative_to(DEST.resolve())
            and digest(old) == previous["sha256"]
        ):
            old.unlink()
manifest = {
    "status": "VERIFIED COPIES",
    "version": version,
    "project_status": status,
    "copied_artifacts": len(copies),
    "artifact_copies": copies,
    "derived_documents": derived,
    "generated_files": generated,
    "generation_inputs": [
        {"source": name, "sha256": digest(SOURCE / name)}
        for name in [
            "scripts/sync_presentation.py",
            "pyproject.toml",
            "results/validation/validation_report.json",
        ]
    ],
    "source_repository": "06_Complete_Project_Source",
    "format": "SHA-256 exact bytes for copies, generated pages and their source inputs",
}
(DEST / "ORGANIZATION_MANIFEST.json").write_text(
    json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
)
print(
    json.dumps(
        {"destination": str(DEST), "version": version, "verified_artifact_copies": len(copies)}
    )
)
