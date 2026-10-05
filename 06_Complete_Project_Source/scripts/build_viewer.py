"""Embed actual CAD meshes, centralized dimensions and simulated joint samples."""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def build_viewer():
    mesh = json.loads((ROOT / "cad/exports/meshes/assembly_meshes.json").read_text())
    trajectory = json.loads((ROOT / "results/trajectories/pick_place_samples.json").read_text())
    config = yaml.safe_load((ROOT / "config/robot.yaml").read_text())
    data = {"mesh": mesh, "trajectory": trajectory, "config": config}
    js = (ROOT / "simulations/viewer.js").read_text()
    html = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASTER-6 · Digital twin</title>
<style>*{box-sizing:border-box}body{margin:0;background:#0b151e;color:#ecf3f7;font-family:Segoe UI,Arial,sans-serif}header{padding:24px 30px;border-bottom:1px solid #274152;display:flex;justify-content:space-between;align-items:center;height:98px}h1{font-size:25px;margin:0;letter-spacing:.04em}header p{margin:8px 0 0;color:#a6bac7;font-size:14px}.tag{border:1px solid #367887;border-radius:20px;padding:8px 14px;color:#6fdfd8;font-size:12px;letter-spacing:.09em}main{display:grid;grid-template-columns:minmax(300px,1fr) 340px;height:calc(100vh - 98px);min-height:600px;grid-template-rows:minmax(0,1fr)}.scene{position:relative;min-height:0;overflow:hidden}canvas{width:100%;height:100%;display:block;touch-action:none}.hint{position:absolute;left:25px;bottom:20px;color:#97b0c3;font-size:12px}aside{min-height:0;padding:24px;background:#112330;overflow-y:auto;border-left:1px solid #274152}h2{font-size:13px;text-transform:uppercase;letter-spacing:.1em;color:#92b5c5;margin:25px 0 14px}h2:first-child{margin-top:0}button{background:#1d3b4d;color:#ecf3f7;border:1px solid #36596b;border-radius:7px;padding:9px 12px;cursor:pointer;font:inherit;font-size:13px}button:hover{background:#286178}button.primary{background:#168695;border-color:#168695}.buttons,#poses{display:flex;flex-wrap:wrap;gap:8px}label{display:grid;grid-template-columns:28px 1fr 54px;gap:8px;align-items:center;font-size:13px;margin:16px 0;color:#b9ccd6}input[type=range]{width:100%;accent-color:#45c9c5;cursor:pointer}output{text-align:right;color:#fff;font-variant-numeric:tabular-nums}#timeline{margin:18px 0 8px}#status{color:#8ddbd9;font-size:13px;min-height:32px}#time,#tcp{font-size:14px;font-variant-numeric:tabular-nums;color:#fff}small{display:block;color:#97b0c3;font-size:12px;line-height:1.7}.check{display:block}#path{accent-color:#45c9c5}@media(max-width:850px){main{grid-template-columns:1fr;height:auto}.scene{height:60vh;min-height:380px}aside{border-left:0}header{padding:20px}.tag{display:none}}</style>
<header><div><h1>ASTER-6 <span style="color:#53cdc8;font-weight:400">/ DIGITAL TWIN</span></h1><p>Original six-axis industrial arm · actual parametric CAD geometry</p></div><span class="tag">SIMULATED · DIGITAL ONLY</span></header>
<main><div class="scene"><canvas aria-label="Interactive 3D CAD robot"></canvas><div class="hint">Drag to orbit · scroll to zoom · change joints or play the recorded task</div></div><aside><h2>Pick-and-place</h2><div class="buttons"><button id="play" class="primary">Play demo</button><button id="reset">Reset</button></div><input id="timeline" type="range" min="0" step=".01" value="0" aria-label="Demo time"><div id="time"></div><p id="status">Ready / home</p><h2>Joint configuration</h2><div id="angles"></div><label><span>Jaw</span><input id="grip" type="range" min="0" step="1" aria-label="Gripper opening"><output id="gripValue"></output></label><h2>Representative poses</h2><div id="poses"></div><h2>Tool centre point · X / Y / Z</h2><div id="tcp"></div><label class="check"><input id="path" type="checkbox" checked> Show recorded TCP path</label><small>Meshes are tessellated from generated BRep parts. Playback uses the Python planner's joint samples and the same rigid transform chain. Manual configurations may collide. Grasp attachment is ideal; contact physics and physical performance are unverified.</small></aside></main><script>const DATA="""
    html += json.dumps(data, separators=(",", ":")) + ";\n" + js + "</script></html>"
    target = ROOT / "simulations/aster6_twin.html"
    target.write_text(html, encoding="utf-8")
    return target


if __name__ == "__main__":
    print(build_viewer())
