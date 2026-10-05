"""Configuration-derived, dimensioned interface concept drawings in SVG/PDF."""

from math import sin, cos, pi
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch
from matplotlib.backends.backend_pdf import PdfPages
from parameters import ROOT

INK = "#243949"
BLUE = "#367E96"


def sheet(title, subtitle, xlim, ylim):
    fig, ax = plt.subplots(figsize=(11.7, 8.3))
    ax.set_aspect("equal")
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.axis("off")
    fig.suptitle(
        "ASTER-6  |  " + title, x=0.08, y=0.94, ha="left", fontweight="bold", fontsize=19, color=INK
    )
    fig.text(0.08, 0.89, subtitle, fontsize=10, color=INK)
    fig.text(
        0.08,
        0.045,
        "DIMENSIONS: mm  |  Concept interface drawing  |  Parameter source: config/robot.yaml\n"
        "No manufacturing tolerances assigned. Fit, fastener length, thread engagement and assembly require detailed design.",
        fontsize=9,
        color=INK,
    )
    return fig, ax


def dim(ax, p1, p2, text, offset=15):
    x1, y1 = p1
    x2, y2 = p2
    if abs(y2 - y1) < 1e-8:
        y = y1 + offset
        ax.plot([x1, x1], [y1, y + 3], color=INK, lw=0.7)
        ax.plot([x2, x2], [y2, y + 3], color=INK, lw=0.7)
        ax.annotate("", (x1, y), (x2, y), arrowprops=dict(arrowstyle="<->", color=INK, lw=0.8))
        ax.text((x1 + x2) / 2, y + 3, text, ha="center", va="bottom", fontsize=9, color=INK)
    else:
        x = x1 + offset
        ax.plot([x1, x + 3], [y1, y1], color=INK, lw=0.7)
        ax.plot([x2, x + 3], [y2, y2], color=INK, lw=0.7)
        ax.annotate("", (x, y1), (x, y2), arrowprops=dict(arrowstyle="<->", color=INK, lw=0.8))
        ax.text(
            x + 4, (y1 + y2) / 2, text, ha="left", va="center", rotation=90, fontsize=9, color=INK
        )


def circle(ax, x, y, r, style="-", fill=False):
    ax.add_patch(
        Circle(
            (x, y),
            r,
            facecolor="#E5EEF2" if fill else "none",
            edgecolor=INK,
            lw=1.2,
            linestyle=style,
        )
    )


def generate_drawings(p, qa_dir=None):
    folder = ROOT / "docs/drawings"
    folder.mkdir(parents=True, exist_ok=True)
    sheets = []
    fig, ax = sheet(
        "BASE & TOOL INTERFACES",
        "Orthographic end views; original flange pattern; all holes explicitly modeled.",
        (-135, 310),
        (-145, 145),
    )
    circle(ax, 0, 0, p["base_diameter"] / 2, fill=True)
    circle(ax, 0, 0, 22)
    circle(ax, 0, 0, p["base_diameter"] / 2 - 20, ":")
    for i in range(8):
        a = i * 2 * pi / 8
        x = (p["base_diameter"] / 2 - 20) * cos(a)
        y = (p["base_diameter"] / 2 - 20) * sin(a)
        circle(ax, x, y, 5.25)
        circle(ax, x, y, 8.5)
    ax.plot([-118, 118], [0, 0], ls="-.", color=BLUE, lw=0.7)
    ax.plot([0, 0], [-118, 118], ls="-.", color=BLUE, lw=0.7)
    dim(
        ax,
        (-p["base_diameter"] / 2, 0),
        (p["base_diameter"] / 2, 0),
        f"Ø{p['base_diameter']:g}",
        -128,
    )
    ax.text(
        -118,
        127,
        "BASE: 8 × Ø10.5 THRU\nØ17 counterbore, 7 deep\nPCD 180 / pilot cable bore Ø44\nPlate thickness 20",
        fontsize=10,
        color=INK,
    )
    x = 235
    circle(ax, x, 0, p["tool_flange_diameter"] / 2, fill=True)
    circle(ax, x, 0, 8)
    circle(ax, x, 0, 23, ":")
    for i in range(6):
        a = i * 2 * pi / 6
        circle(ax, x + 23 * cos(a), 23 * sin(a), 2.75)
    dim(ax, (x - 30, 0), (x + 30, 0), "Ø60", -50)
    ax.text(
        172,
        78,
        "TOOL: 6 × Ø5.5 THRU\nPCD 46 / cable bore Ø16\nFlange thickness 8\nAdapter pilot bore Ø30.2",
        fontsize=10,
        color=INK,
    )
    sheets.append(("01_base_tool_interfaces", fig))
    fig, ax = sheet(
        "LINK SECTIONS & JOINT CENTERS",
        "Side outline and nominal extrusion section. Access windows require a separate structural refinement.",
        (-65, 535),
        (-130, 145),
    )
    L = p["upper_arm_length"]
    D = p["upper_arm_depth"]
    W = p["upper_arm_width"]
    t = p["wall_thickness"]
    circle(ax, 0, 0, 46)
    circle(ax, L, 0, 52)
    ax.add_patch(
        FancyBboxPatch(
            (32, -D / 2),
            L - 142,
            D,
            boxstyle="round,pad=0,rounding_size=9",
            fc="#DCEAF0",
            ec=INK,
            lw=1.2,
        )
    )
    ax.add_patch(
        FancyBboxPatch(
            (49.5, -D * 0.225),
            L - 177,
            D * 0.45,
            boxstyle="round,pad=0,rounding_size=5",
            fc="white",
            ec=INK,
            lw=0.8,
        )
    )
    ax.add_patch(
        FancyBboxPatch(
            (L - 129, -40),
            104,
            80,
            boxstyle="round,pad=0,rounding_size=6",
            fc="none",
            ec=INK,
            lw=1.2,
            linestyle="--",
        )
    )
    ax.plot([-55, L + 58], [0, 0], ls="-.", color=BLUE, lw=0.7)
    dim(ax, (0, 0), (L, 0), f"{L:g} joint-center spacing", 80)
    sx = 460
    dim(ax, (sx + W / 2, -D / 2), (sx + W / 2, D / 2), f"{D:g}", 12)
    ax.add_patch(
        FancyBboxPatch(
            (sx - W / 2, -D / 2),
            W,
            D,
            boxstyle="round,pad=0,rounding_size=9",
            fc="#DCEAF0",
            ec=INK,
            lw=1.2,
        )
    )
    ax.add_patch(
        FancyBboxPatch(
            (sx - W / 2 + t, -D / 2 + t),
            W - 2 * t,
            D - 2 * t,
            boxstyle="round,pad=0,rounding_size=5",
            fc="white",
            ec=INK,
            lw=1,
        )
    )
    dim(ax, (sx - W / 2, 0), (sx + W / 2, 0), f"{W:g}", -72)
    ax.text(415, 77, f"UPPER NOMINAL\n{W:g} × {D:g} × {t:g} wall", fontsize=10, color=INK)
    ax.text(
        -10,
        -112,
        f"FOREARM: {p['forearm_length']:g} center spacing; {p['forearm_width']:g} × {p['forearm_depth']:g} × {t:g} wall.\n"
        "Longitudinal fillets R9 outside / R5 inside; service cover mounting Ø3.4.\n"
        "Joint barrels, fork bridges and material overlap are structural assembly interfaces.",
        fontsize=10,
        color=INK,
    )
    sheets.append(("02_link_sections", fig))
    fig, ax = sheet(
        "SYMMETRIC PARALLEL GRIPPER",
        "Top view: transverse opposite-hand screw and two guides; fingers translate along ±Y.",
        (-5, 140),
        (-130, 130),
    )
    width = p["opening"] + 56
    gap = p["opening"]
    th = p["finger_thickness"]
    start = p["tool_length"] - p["finger_length"]
    ax.add_patch(
        FancyBboxPatch(
            (16, -width / 2),
            25,
            width,
            boxstyle="round,pad=0,rounding_size=6",
            fc="#DCEAF0",
            ec=INK,
            lw=1.2,
        )
    )
    ax.add_patch(Rectangle((24, -width / 2 + 10), 17, width - 20, fc="white", ec=INK, lw=0.8))
    ax.plot([28, 28], [-width / 2 - 4, width / 2 + 4], color=INK, lw=2.5)
    ax.plot([43, 43], [-width / 2 + 5, width / 2 - 5], color="#81909B", lw=3)
    for side in (-1, 1):
        y = side * (gap / 2 + th / 2 + 1.5)
        ax.add_patch(Rectangle((37, y - 5), 16, 10, fc="#CBDDE4", ec=INK, lw=1))
        ax.add_patch(
            FancyBboxPatch(
                (start, y - th / 2),
                p["finger_length"],
                th,
                boxstyle="round,pad=0,rounding_size=1.5",
                fc="#DCEAF0",
                ec=INK,
                lw=1,
            )
        )
        ax.add_patch(
            Rectangle(
                (p["tool_length"] - 22, side * gap / 2 if side > 0 else -gap / 2 - 1.5),
                22,
                1.5,
                fc="#EDA34E",
                ec=INK,
                lw=0.6,
            )
        )
    dim(
        ax,
        (p["tool_length"], -gap / 2),
        (p["tool_length"], gap / 2),
        f"{gap:g} max clear opening",
        15,
    )
    dim(
        ax,
        (start, -gap / 2 - th),
        (p["tool_length"], -gap / 2 - th),
        f"{p['finger_length']:g} finger",
        -37,
    )
    dim(ax, (16, width / 2), (41, width / 2), "25 body depth", 26)
    ax.text(
        60,
        92,
        "Each jaw: 45 mm travel\n2 guides: Ø7, Z = ±14\nScrew envelope: Ø8\n4 mm/rev opposed lead",
        fontsize=10,
        color=INK,
    )
    ax.text(
        0,
        -117,
        "Finger section 10 × 18; replaceable 1.5-thick pads. TCP at X=110, jaw mid-plane.\n"
        "Selected positions are visualized at maximum opening; no screw thread/gear tooth detail.",
        fontsize=9,
        color=INK,
    )
    sheets.append(("03_gripper_layout", fig))
    with PdfPages(folder / "engineering_interfaces.pdf") as pdf:
        for name, fig in sheets:
            fig.savefig(folder / (name + ".svg"), bbox_inches="tight")
            pdf.savefig(fig, bbox_inches="tight")
            if qa_dir is not None:
                fig.savefig(qa_dir / (name + ".png"), dpi=130, bbox_inches="tight")
            plt.close(fig)
