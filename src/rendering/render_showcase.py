"""Re-render a floorplan with the icon pipeline, plus optional per-object
angle overrides for showcase figures."""
import os, json, random, math
import numpy as np
from pathlib import Path

from src.rendering.render_icons_with_grid import (
    render_one_with_grid, oriented_bbox, place_icon,
    get_icon_image, pick_icon_file, choose_wall_style,
    choose_theme_for_image, draw_thick_walls, draw_door_in_wall,
    draw_window_in_wall, iter_objects_with_openings, norm_label,
    BACKGROUND, PLACE_MODE, YOLO_ROOT,
)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle
from matplotlib.ticker import MultipleLocator
from shapely.geometry import Polygon as ShapelyPolygon
import matplotlib.colors as mcolors

# Angle overrides: (room_id, label) -> angle in radians
# Convention: 0° = icon as-is (facing up), π = facing down,
#             π/2 = rotated 90° CCW, -π/2 = rotated 90° CW
ANGLE_OVERRIDES = {
    # Room 0: sofa faces down, armchair_1 faces right, armchair_2 faces left, armchair_3 faces right
    (0, "sofa"): math.pi,            # flip down (was facing up toward fireplace)
    (0, "armchair_1"): -math.pi/2,   # face right (toward center)
    (0, "armchair_2"): math.pi/2,    # face left (toward center)
    (0, "armchair_3"): -math.pi/2,   # face right
    # Room 31: television faces down toward sofa
    (31, "television"): math.pi,     # flip down
}


def render_showcase(scene_path: Path, out_png: Path, icon_root: str, room_id: int):
    """Render with custom angle overrides for showcase."""
    with open(scene_path) as f:
        data = json.load(f)

    layout_id = data.get("layout_id", "")
    random.seed(hash(str(scene_path)) & 0xFFFFFFFF)

    fig, ax = plt.subplots(figsize=(8, 8), dpi=150)
    ax.set_facecolor(BACKGROUND)
    fig.patch.set_facecolor(BACKGROUND)
    ax.set_aspect("equal")

    wall_thickness, wall_fill_color, wall_edge_color, hatch_pattern, edge_linewidth, thickness_range = choose_wall_style()
    theme_name, icon_dir, outline_color = choose_theme_for_image(icon_root)

    boundary_points = [(p["x"], p["y"]) for p in data["room_boundary"]]
    ax.add_patch(Polygon(boundary_points, facecolor="whitesmoke",
                         edgecolor="none", linewidth=0, alpha=0.3, zorder=1))

    if data.get("room_boundary"):
        open_boundary = [(p["x"], p["y"]) for p in data["room_boundary"]]
        bxs, bys = zip(*open_boundary)
        bxs = bxs + (bxs[0],)
        bys = bys + (bys[0],)
        ax.plot(bxs, bys, color='gray', linewidth=1.5, linestyle=':', zorder=9)

    walls = data.get("walls", [])
    wall_patches, wall_thicknesses = draw_thick_walls(
        ax, walls, boundary_points, wall_thickness,
        wall_fill_color, wall_edge_color, hatch_pattern,
        edge_linewidth, thickness_range
    )

    all_x = [p["x"] for p in data["room_boundary"]]
    all_y = [p["y"] for p in data["room_boundary"]]
    margin = 0.5
    ax.set_xlim(min(all_x) - margin, max(all_x) + margin)
    ax.set_ylim(min(all_y) - margin, max(all_y) + margin)

    for raw_label, pts in iter_objects_with_openings(data):
        l = norm_label(raw_label)
        if l == "door":
            draw_door_in_wall(ax, pts, walls, boundary_points, wall_thicknesses, wall_edge_color)
        elif l == "window":
            icon_path = pick_icon_file(l, icon_dir)
            draw_window_in_wall(ax, pts, walls, boundary_points, wall_thicknesses, icon_path)
        else:
            cx_o, cy_o, w_o, h_o, ang = oriented_bbox(pts)

            # Apply angle override if exists
            override_key = (room_id, raw_label)
            if override_key in ANGLE_OVERRIDES:
                ang = ANGLE_OVERRIDES[override_key]

            icon_path = pick_icon_file(l, icon_dir)
            if icon_path is not None:
                icon_img = get_icon_image(icon_path)
                place_icon(ax, icon_img, cx_o, cy_o, w_o, h_o, ang,
                           mode=PLACE_MODE, zorder=15)
            else:
                x0 = min(x for x, _ in pts)
                x1 = max(x for x, _ in pts)
                y0 = min(y for _, y in pts)
                y1 = max(y for _, y in pts)
                if 'rug' in l:
                    rgb = np.array(mcolors.to_rgb(outline_color))
                    light_rgb = np.clip(rgb + (1.0 - rgb) * 0.8, 0.0, 1.0)
                    fill = mcolors.to_hex(light_rgb)
                    zorder = 9
                else:
                    fill = None
                    zorder = 12
                ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0,
                                       facecolor=fill if fill else 'none',
                                       edgecolor=outline_color,
                                       linewidth=2.0, fill=(fill is not None), zorder=zorder))

    ax.xaxis.set_major_locator(MultipleLocator(1.0))
    ax.xaxis.set_minor_locator(MultipleLocator(0.5))
    ax.yaxis.set_major_locator(MultipleLocator(1.0))
    ax.yaxis.set_minor_locator(MultipleLocator(0.5))
    ax.grid(True, which="major", color="#999999", linewidth=0.5, alpha=0.5, zorder=0)
    ax.grid(True, which="minor", color="#cccccc", linewidth=0.25, alpha=0.3, zorder=0)
    ax.set_xlabel("X (meters)", fontsize=9)
    ax.set_ylabel("Y (meters)", fontsize=9)
    ax.tick_params(axis="both", labelsize=7)
    ax.set_title(f"Room {layout_id}", fontsize=11, fontweight="bold")

    plt.tight_layout(pad=0.2)
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=150, facecolor=BACKGROUND, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    print(f"[OK] {out_png}")


if __name__ == "__main__":
    data_root = Path("data/generated_data")
    out_dir = data_root / "showcase"
    out_dir.mkdir(parents=True, exist_ok=True)

    for room_id in [0, 31]:
        scene_path = data_root / "living_rooms" / f"room_{room_id}.json"
        out_path = out_dir / f"room_{room_id}_icons.png"
        render_showcase(scene_path, out_path, YOLO_ROOT, room_id)
