"""Create a labeled six-pose panel from actual Blender CAD renders."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from matplotlib.font_manager import findfont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "cad/renders"
POSES = [
    ("home", "HOME"),
    ("extended", "EXTENDED"),
    ("folded", "FOLDED"),
    ("vertical", "VERTICAL"),
    ("pick", "PICK"),
    ("place", "PLACE"),
]
font = ImageFont.truetype(findfont("DejaVu Sans"), 26)
small = ImageFont.truetype(findfont("DejaVu Sans"), 17)
canvas = Image.new("RGB", (2100, 1470), "#E9EFF2")
d = ImageDraw.Draw(canvas)
d.text((32, 18), "ASTER-6  |  PARAMETRIC CAD CONFIGURATIONS", font=font, fill="#243949")
d.text(
    (32, 59),
    "Actual CAD meshes • common six-axis transform model • dimensions in config/robot.yaml",
    font=small,
    fill="#486472",
)
for i, (pose, label) in enumerate(POSES):
    image = Image.open(OUT / f"pose_{pose}.png").convert("RGB")
    x = (i % 3) * 700
    y = 100 + (i // 3) * 685
    canvas.paste(image, (x, y))
    d.text((x + 24, y + 650), label, font=font, fill="#243949")
canvas.save(OUT / "poses.png", optimize=True)
