#!/usr/bin/env python3
"""
Re-render icon floorplan images WITH metric coordinate grid.

This script is a modified version of the render_one() function from
./icon_root/draw_dataset.ipynb, adding:
  - Axes ON with tick labels showing meters
  - Metric grid (1m major, 0.5m minor)
  - Proper figure layout (not edge-to-edge)
  - Fixed random seed per room for reproducibility (always "black" theme)

Usage:
    python -m src.render_icons_with_grid \
        --data_root data/generated_data \
        --icon_root ./icon_root \
        --room_types bedrooms,living_rooms,kitchens \
        --id_ranges 75-149,0-74,150-199

    # Or use the shortcut for the standard mixed dataset:
    python -m src.render_icons_with_grid --mixed
"""

import sys
import os

# We need to run from the YoloFloorplan directory to find icon assets
YOLO_ROOT = os.environ.get("YOLO_ICON_ROOT", "")  # set via env or pass icon_root explicitly

import json
import random
import math
import fire
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle, Arc, FancyBboxPatch
from matplotlib.transforms import Affine2D
from matplotlib.collections import LineCollection
from matplotlib.ticker import MultipleLocator
from shapely.geometry import Point, Polygon as ShapelyPolygon

plt.ioff()

# ── Config ────────────────────────────────────────────────────────────────────
IMG_SIZE = 1024
DPI = 128
BACKGROUND = "white"

# Theme folders & colors (same as draw_dataset.ipynb)
THEME_DIRS = {
    "black": ("stock_icons_all/stock_icons_cropped_black_png",  "#111111"),
    "blue":  ("stock_icons_all/stock_icons_cropped_blue_png",   "#1f77b4"),
    "green": ("stock_icons_all/stock_icons_cropped_green_png",  "#2ca02c"),
}


def choose_theme_for_image(icon_root: str) -> Tuple[str, Path, str]:
    """Randomly pick one theme for THIS image."""
    name = random.choice(list(THEME_DIRS.keys()))
    rel, color = THEME_DIRS[name]
    p = Path(icon_root) / rel
    tries = 0
    while (not p.exists() or not any(p.glob("*.png"))) and tries < 5:
        name = random.choice(list(THEME_DIRS.keys()))
        rel, color = THEME_DIRS[name]
        p = Path(icon_root) / rel
        tries += 1
    return name, p, color


# ── Copy all helper functions from draw_dataset.ipynb ─────────────────────────
# These are extracted verbatim from the notebook cell.

def norm_label(raw: str) -> str:
    parts = raw.lower().replace("-", " ").replace("_", " ").split()
    if len(parts) >= 2 and parts[-1].isdigit():
        parts = parts[:-1]
    return " ".join(parts).strip()


def oriented_bbox(points):
    pts = np.array(points, dtype=float)
    xs, ys = pts[:, 0], pts[:, 1]
    cx, cy = xs.mean(), ys.mean()
    centered = pts - [cx, cy]
    cov = np.cov(centered.T)
    eigvals, eigvecs = np.linalg.eigh(cov)
    angle = math.atan2(eigvecs[1, 1], eigvecs[0, 1])
    rot = np.array([[math.cos(-angle), -math.sin(-angle)],
                     [math.sin(-angle), math.cos(-angle)]])
    rotated = centered @ rot.T
    width = np.ptp(rotated[:, 0])
    height = np.ptp(rotated[:, 1])
    return cx, cy, float(width), float(height), float(angle)


_FLOOD_TOL = 60
_FLOOD_PAD = 10

def load_png_as_image(png_path: str):
    """Load icon PNG and make its outer (background) white region transparent.

    The source icon PNGs have opaque white backgrounds. We flood-fill from the
    four corners through "near-white" pixels (darkness within FLOOD_TOL of the
    seed) and set their alpha to 0; interior whites enclosed by the icon's own
    strokes stay opaque. A white padding ring is added before the flood so the
    BFS can wrap around any stroke that touches the original image border.
    """
    from PIL import Image, ImageDraw
    arr = plt.imread(png_path)
    if arr.dtype.kind == "f":
        arr = (arr * 255.0).clip(0, 255).astype(np.uint8)
    if arr.ndim == 2:
        arr = np.stack([arr, arr, arr], axis=-1)
    rgb = arr[..., :3] if arr.shape[2] == 4 else arr
    h, w = rgb.shape[:2]
    rgb_pad = np.pad(rgb, ((_FLOOD_PAD, _FLOOD_PAD), (_FLOOD_PAD, _FLOOD_PAD), (0, 0)),
                     constant_values=255)
    darkness = np.ascontiguousarray((255 - rgb_pad.min(axis=2)).astype(np.uint8))
    # .copy() forces PIL to allocate a writable buffer; without it floodfill is a no-op
    mask_img = Image.fromarray(darkness, mode="L").copy()
    SENT = 200
    H, W = darkness.shape
    for cx, cy in [(0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1)]:
        ImageDraw.floodfill(mask_img, (cx, cy), value=SENT, thresh=_FLOOD_TOL)
    outer = (np.array(mask_img) == SENT)[_FLOOD_PAD:_FLOOD_PAD + h,
                                          _FLOOD_PAD:_FLOOD_PAD + w]
    alpha = np.where(outer, 0, 255).astype(np.uint8)
    return np.concatenate([rgb, alpha[..., None]], axis=-1)


def choose_wall_style():
    base_thickness_min = 0.05
    base_thickness_max = 0.30
    thickness = random.uniform(base_thickness_min, base_thickness_max)
    fill_options = [
        ("#2c2c2c", None),
        ("#3a3a3a", "///"),
        ("#4a4a4a", "\\\\\\"),
        ("#1a1a1a", None),
        ("#555555", "xx"),
    ]
    fill_color, hatch = random.choice(fill_options)
    edge_options = ["#000000", "#1a1a1a", "#333333"]
    edge_color = random.choice(edge_options)
    edge_lw = random.uniform(0.5, 2.0)
    thickness_range = (base_thickness_min, base_thickness_max)
    return thickness, fill_color, edge_color, hatch, edge_lw, thickness_range


def perpendicular_offset(p1, p2, distance):
    """Get points offset perpendicular to line p1->p2."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.sqrt(dx*dx + dy*dy)
    if length < 1e-9:
        return p1, p2
    px = -dy / length
    py = dx / length
    return (px * distance, py * distance)


def draw_thick_walls(ax, walls, room_boundary, thickness, wall_fill_color,
                     wall_edge_color, hatch_pattern, edge_linewidth, thickness_range):
    """Draw walls as thick rectangles, extending OUTWARD from room only."""
    boundary_pts = np.array(room_boundary, dtype=float)
    room_polygon = ShapelyPolygon(boundary_pts)

    wall_patches = []
    wall_thicknesses = []

    for wall in walls:
        s, e = wall["start"], wall["end"]
        p1 = np.array([s["x"], s["y"]])
        p2 = np.array([e["x"], e["y"]])

        wall_mid = (p1 + p2) / 2

        if thickness is None:
            wall_thickness = random.uniform(thickness_range[0], thickness_range[1])
        else:
            wall_thickness = thickness

        wall_thicknesses.append(wall_thickness)

        perp = perpendicular_offset(p1, p2, wall_thickness)

        test_point1 = wall_mid + np.array(perp)
        test_point2 = wall_mid - np.array(perp)

        pt1_shapely = Point(test_point1[0], test_point1[1])
        pt2_shapely = Point(test_point2[0], test_point2[1])

        pt1_inside = room_polygon.contains(pt1_shapely)
        pt2_inside = room_polygon.contains(pt2_shapely)

        if not pt1_inside and pt2_inside:
            outward_perp = np.array(perp)
        elif pt1_inside and not pt2_inside:
            outward_perp = -np.array(perp)
        else:
            room_cx, room_cy = boundary_pts.mean(axis=0)
            dist1 = np.linalg.norm(test_point1 - np.array([room_cx, room_cy]))
            dist2 = np.linalg.norm(test_point2 - np.array([room_cx, room_cy]))
            if dist1 > dist2:
                outward_perp = np.array(perp)
            else:
                outward_perp = -np.array(perp)

        corners = [
            p1,
            p2,
            p2 + outward_perp,
            p1 + outward_perp,
        ]

        poly = Polygon(corners,
                       facecolor=wall_fill_color,
                       edgecolor=wall_edge_color,
                       linewidth=edge_linewidth,
                       zorder=10,
                       hatch=hatch_pattern)
        ax.add_patch(poly)
        wall_patches.append((corners, poly))

    return wall_patches, wall_thicknesses


def find_closest_wall_segment(point, walls):
    """Find which wall segment is closest to given point and return wall info."""
    min_dist = float('inf')
    closest_wall = None
    closest_wall_idx = None

    for idx, wall in enumerate(walls):
        s = np.array([wall["start"]["x"], wall["start"]["y"]])
        e = np.array([wall["end"]["x"], wall["end"]["y"]])
        p = np.array(point)

        line_vec = e - s
        line_len = np.linalg.norm(line_vec)
        if line_len < 1e-9:
            continue

        line_unitvec = line_vec / line_len
        point_vec = p - s
        proj_length = np.dot(point_vec, line_unitvec)
        proj_length = max(0, min(line_len, proj_length))
        closest_point = s + line_unitvec * proj_length

        dist = np.linalg.norm(p - closest_point)
        if dist < min_dist:
            min_dist = dist
            closest_wall = (s, e, closest_point)
            closest_wall_idx = idx

    return closest_wall, closest_wall_idx


def iter_objects_with_openings(data):
    for obj in data.get("objects", []):
        yield obj.get("label", "object"), [(p["x"], p["y"]) for p in obj["points"]]
    for w in data.get("openings", {}).get("windows", []):
        yield "window", [(p["x"], p["y"]) for p in w["points"]]
    for d in data.get("openings", {}).get("doors", []):
        yield "door", [(p["x"], p["y"]) for p in d["points"]]


def draw_door_in_wall(ax, door_pts, walls, room_boundary, wall_thicknesses, wall_edge_color):
    """Draw door, using actual wall thickness."""
    pts = np.array(door_pts, dtype=float)
    cx, cy = pts.mean(axis=0)

    wall_info, wall_idx = find_closest_wall_segment((cx, cy), walls)
    if wall_info is None or wall_idx is None:
        return

    thickness = wall_thicknesses[wall_idx]

    boundary_pts = np.array(room_boundary, dtype=float)
    room_cx, room_cy = boundary_pts.mean(axis=0)

    wall_start, wall_end, closest_pt = wall_info

    door_width = np.linalg.norm(pts.max(axis=0) - pts.min(axis=0))

    wall_vec = wall_end - wall_start
    wall_len = np.linalg.norm(wall_vec)
    if wall_len < 1e-9:
        return
    wall_dir = wall_vec / wall_len
    perp_dir = np.array([-wall_dir[1], wall_dir[0]])

    test_point1 = closest_pt + perp_dir
    test_point2 = closest_pt - perp_dir
    dist1 = np.linalg.norm(test_point1 - np.array([room_cx, room_cy]))
    dist2 = np.linalg.norm(test_point2 - np.array([room_cx, room_cy]))

    if dist1 > dist2:
        outward_perp = perp_dir
    else:
        outward_perp = -perp_dir

    half_width = door_width / 2
    door_rect_pts = [
        closest_pt - wall_dir * half_width,
        closest_pt + wall_dir * half_width,
        closest_pt + wall_dir * half_width + outward_perp * thickness,
        closest_pt - wall_dir * half_width + outward_perp * thickness,
    ]

    door_rect = Polygon(door_rect_pts, facecolor='white', edgecolor=wall_edge_color,
                        linewidth=2, zorder=11)
    ax.add_patch(door_rect)

    hinge = closest_pt - wall_dir * half_width
    arc_radius = door_width

    wall_angle = math.degrees(math.atan2(wall_dir[1], wall_dir[0]))
    inward_angle = math.degrees(math.atan2(-outward_perp[1], -outward_perp[0]))

    theta1 = wall_angle
    theta2 = inward_angle

    if abs(theta2 - theta1) > 180:
        if theta2 > theta1:
            theta1 += 360
        else:
            theta2 += 360

    arc = Arc(xy=hinge, width=2*arc_radius, height=2*arc_radius,
              angle=0, theta1=min(theta1, theta2), theta2=max(theta1, theta2),
              edgecolor=wall_edge_color, linewidth=2, zorder=12)
    ax.add_patch(arc)

    # Draw radius lines to close the quarter circle
    arc_end_wall = hinge + wall_dir * arc_radius
    arc_end_inward = hinge + (-outward_perp) * arc_radius
    ax.plot([hinge[0], arc_end_wall[0]], [hinge[1], arc_end_wall[1]],
            color=wall_edge_color, linewidth=2, zorder=12)
    ax.plot([hinge[0], arc_end_inward[0]], [hinge[1], arc_end_inward[1]],
            color=wall_edge_color, linewidth=2, zorder=12)

    return door_pts


def draw_window_in_wall(ax, window_pts, walls, room_boundary, wall_thicknesses, icon_path):
    """Draw window, using actual wall thickness."""
    pts = np.array(window_pts, dtype=float)
    cx, cy = pts.mean(axis=0)

    wall_info, wall_idx = find_closest_wall_segment((cx, cy), walls)
    if wall_info is None or wall_idx is None:
        return

    thickness = wall_thicknesses[wall_idx]

    boundary_pts = np.array(room_boundary, dtype=float)
    room_cx, room_cy = boundary_pts.mean(axis=0)

    wall_start, wall_end, closest_pt = wall_info

    window_width = np.linalg.norm(pts.max(axis=0) - pts.min(axis=0))

    wall_vec = wall_end - wall_start
    wall_len = np.linalg.norm(wall_vec)
    if wall_len < 1e-9:
        return
    wall_dir = wall_vec / wall_len
    perp_dir = np.array([-wall_dir[1], wall_dir[0]])

    test_point1 = closest_pt + perp_dir
    test_point2 = closest_pt - perp_dir
    dist1 = np.linalg.norm(test_point1 - np.array([room_cx, room_cy]))
    dist2 = np.linalg.norm(test_point2 - np.array([room_cx, room_cy]))

    if dist1 > dist2:
        outward_perp = perp_dir
    else:
        outward_perp = -perp_dir

    half_width = window_width / 2
    window_rect_pts = [
        closest_pt - wall_dir * half_width,
        closest_pt + wall_dir * half_width,
        closest_pt + wall_dir * half_width + outward_perp * thickness,
        closest_pt - wall_dir * half_width + outward_perp * thickness,
    ]

    window_clear = Polygon(window_rect_pts, facecolor='white', edgecolor='none',
                           linewidth=0, zorder=11)
    ax.add_patch(window_clear)

    if icon_path and icon_path.exists():
        icon_img = get_icon_image(icon_path)
        if icon_img is not None:
            wall_angle = math.atan2(wall_dir[1], wall_dir[0])
            window_center = closest_pt + outward_perp * thickness / 2
            place_icon(ax, icon_img, window_center[0], window_center[1],
                       window_width, thickness, wall_angle, mode="stretch", zorder=12)
    else:
        ax.plot([window_rect_pts[0][0], window_rect_pts[1][0]],
                [window_rect_pts[0][1], window_rect_pts[1][1]],
                color='black', linewidth=2, zorder=12)
        ax.plot([window_rect_pts[2][0], window_rect_pts[3][0]],
                [window_rect_pts[2][1], window_rect_pts[3][1]],
                color='black', linewidth=2, zorder=12)

    return window_rect_pts


# ── Icon cache + placement ────────────────────────────────────────────────────
IMAGE_CACHE: Dict[Path, np.ndarray] = {}

def get_icon_image(path: Path):
    if path is None:
        return None
    if path in IMAGE_CACHE:
        return IMAGE_CACHE[path]
    img = load_png_as_image(str(path))
    IMAGE_CACHE[path] = img
    return img


PLACE_MODE = "stretch"

def place_icon(ax, img_rgba, cx, cy, width, height, angle_rad, mode="stretch", zorder=15):
    if img_rgba is None:
        return None
    ih, iw = img_rgba.shape[:2]
    img_aspect = iw / ih
    box_aspect = width / height if height > 0 else np.inf
    w, h = width, height
    if mode == "contain":
        if img_aspect >= box_aspect:
            w = width; h = w / img_aspect
        else:
            h = height; w = h * img_aspect
    elif mode == "cover":
        if img_aspect >= box_aspect:
            h = height; w = h * img_aspect
        else:
            w = width; h = w / img_aspect
    extent = [-w/2, w/2, -h/2, h/2]
    trans = Affine2D().rotate(angle_rad).translate(cx, cy) + ax.transData
    return ax.imshow(img_rgba, extent=extent, interpolation="bilinear", zorder=zorder, transform=trans)


# ── Icon label mapping ────────────────────────────────────────────────────────
# Exact copies from draw_dataset.ipynb
RANDOM_CHOICES = {
    "bed": ["1place_bed_stock_cropped_FINAL.png", "2place_bed_stock_cropped_FINAL.png", "3place_bed_stock_cropped_FINAL.png"],
    "sofa": ["sofa_2_stock_cropped_FINAL.png", "sofa_3_stock_cropped_FINAL.png", "sofa_ikea_stock_cropped_FINAL.png", "sofa_leather_stock_cropped_FINAL.png"],
    "armchair": ["armchair_1_stock_cropped_FINAL.png", "armchair_2_stock_cropped_FINAL.png", "office_armchair_stock_cropped_FINAL.png", "gamer_armchair_stock_cropped_FINAL.png"],
    "chair": ["chair_1_stock_cropped_FINAL.png", "chair_2_stock_cropped_FINAL.png", "chair_3_stock_cropped_FINAL.png"],
    "coffee table": ["coffee_table_1_stock_cropped_FINAL.png", "coffee_table_2_stock_cropped_FINAL.png", "coffee_table_3_stock_cropped_FINAL.png"],
    "table": ["table_1_stock_cropped_FINAL.png", "table_2_stock_cropped_FINAL.png", "table_3_stock_cropped_FINAL.png", "table_4_stock_cropped_FINAL.png"],
    "sink": ["sink_1_stock_cropped_FINAL.png", "sink_2_stock_cropped_FINAL.png", "sink_3_stock_cropped_FINAL.png"],
    "stove": ["stove_1_stock_cropped_FINAL.png", "stove_2_stock_cropped_FINAL.png"],
    "tv": ["tv_1_stock_cropped_FINAL.png", "tv_2_stock_cropped_FINAL.png"],
    "tv stand": ["tv_stand_1_stock_cropped_FINAL.png", "tv_stand_2_stock_cropped_FINAL.png"],
    "fireplace": ["fireplace_1_stock_cropped_FINAL.png", "fireplace_2_stock_cropped_FINAL.png"],
    "cabinet": ["cabinet_1_stock_cropped_FINAL.png", "cabinet_2_stock_cropped_FINAL.png", "cabinet_3_stock_cropped_FINAL.png"],
    "mirror": ["mirror_1_stock_cropped_FINAL.png", "mirror_2_stock_cropped_FINAL.png"],
    "plant": ["plant_1_stock_cropped_FINAL.png", "plant_2_stock_cropped_FINAL.png"],
    "pouf": ["pouf_1_stock_cropped_FINAL.png", "pouf_2_stock_cropped_FINAL.png", "pouf_3_stock_cropped_FINAL.png"],
    "fridge": ["fridge_1_stock_cropped_FINAL.png", "fridge_2_stock_cropped_FINAL.png"],
    "window": ["window_cropped_FINAL.png"],
}

LABEL_TO_ICON = {
    "dishwasher": "dishwasher_stock_cropped_FINAL.png",
    "dresser": "dresser_stock_cropped_FINAL.png",
    "fireplace": "fireplace",
    "floor lamp": "lamp_stock_cropped_FINAL.png",
    "foot stool": "pouf",
    "fridge": "fridge",
    "island": "island_stock_cropped_FINAL.png",
    "island cabinet": "island_stock_cropped_FINAL.png",
    "island counter": "island_stock_cropped_FINAL.png",
    "loveseat": "loveseat_stock_cropped_FINAL.png",
    "luggage rack": "rack_stock_cropped_FINAL.png",
    "mirror": "mirror",
    "nightstand": "nightstand_1_stock_cropped_FINAL.png",
    "ottoman": "pouf",
    "plant": "plant",
    "pouf": "pouf",
    "recamiere": "recamiere_cropped_FINAL.png",
    "rug": None,
    "side table": "table",
    "sink": "sink",
    "sofa": "sofa",
    "stove": "stove",
    "table": "table",
    "table lamp": "lamp_stock_cropped_FINAL.png",
    "television": "tv",
    "tv stand": "tv stand",
    "wardrobe": "wardrobe_1_stock_cropped_FINAL.png",
    "armchair": "armchair",
    "armchair main": "armchair",
    "armchair nook": "armchair",
    "base cabinet": "cabinet",
    "bed": "bed",
    "bench": "bench_stock_cropped_FINAL.png",
    "bookshelf": "bookshelf_stock_cropped_FINAL.png",
    "cabinet": "cabinet",
    "chair": "chair",
    "closet alcove": "closet_stock_cropped_FINAL.png",
    "coffee table": "coffee table",
    "console table": "table",
    "corner cabinet": "cabinet",
    "desk": "table",
    "window": "window",
    "door": None,
}


def pick_icon_file(label: str, icon_dir: Path) -> Optional[Path]:
    l = norm_label(label)
    key = LABEL_TO_ICON.get(l)
    if key is None:
        return None
    if key in RANDOM_CHOICES:
        candidates = RANDOM_CHOICES[key][:]
        random.shuffle(candidates)
        for fname in candidates:
            p = icon_dir / fname
            if p.exists():
                return p
        return None
    p = icon_dir / key
    return p if p.exists() else None


# ── Main render function (WITH GRID) ──────────────────────────────────────────

def render_one_with_grid(scene_path: Path, out_png: Path, icon_root: str):
    """Render a single room with icons + metric coordinate grid."""
    with open(scene_path) as f:
        data = json.load(f)

    layout_id = data.get("layout_id", "")

    # Use deterministic seed per room for reproducible wall style + theme
    random.seed(hash(str(scene_path)) & 0xFFFFFFFF)

    fig, ax = plt.subplots(figsize=(8, 8), dpi=150)
    ax.set_facecolor(BACKGROUND)
    fig.patch.set_facecolor(BACKGROUND)
    ax.set_aspect("equal")

    # Wall style
    wall_thickness, wall_fill_color, wall_edge_color, hatch_pattern, edge_linewidth, thickness_range = choose_wall_style()

    # Choose theme for furniture (blue, green, or black — same as notebook)
    theme_name, icon_dir, outline_color = choose_theme_for_image(icon_root)

    # Draw room floor
    boundary_points = [(p["x"], p["y"]) for p in data["room_boundary"]]
    ax.add_patch(Polygon(boundary_points, facecolor="whitesmoke",
                         edgecolor="none", linewidth=0, alpha=0.3, zorder=1))

    # Room boundary dotted line
    if data.get("room_boundary"):
        open_boundary = [(p["x"], p["y"]) for p in data["room_boundary"]]
        bxs, bys = zip(*open_boundary)
        bxs = bxs + (bxs[0],)
        bys = bys + (bys[0],)
        ax.plot(bxs, bys, color='gray', linewidth=1.5, linestyle=':', zorder=9)

    # Draw walls
    walls = data.get("walls", [])
    wall_patches, wall_thicknesses = draw_thick_walls(
        ax, walls, boundary_points, wall_thickness,
        wall_fill_color, wall_edge_color, hatch_pattern,
        edge_linewidth, thickness_range
    )

    # Bounds
    all_x = [p["x"] for p in data["room_boundary"]]
    all_y = [p["y"] for p in data["room_boundary"]]
    margin = 0.5
    ax.set_xlim(min(all_x) - margin, max(all_x) + margin)
    ax.set_ylim(min(all_y) - margin, max(all_y) + margin)

    # Draw objects, doors, windows
    for raw_label, pts in iter_objects_with_openings(data):
        l = norm_label(raw_label)
        if l == "door":
            draw_door_in_wall(ax, pts, walls, boundary_points, wall_thicknesses, wall_edge_color)
        elif l == "window":
            icon_path = pick_icon_file(l, icon_dir)
            draw_window_in_wall(ax, pts, walls, boundary_points, wall_thicknesses, icon_path)
        else:
            cx_o, cy_o, w_o, h_o, ang = oriented_bbox(pts)
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
                    import matplotlib.colors as mcolors
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

    # ── ADD GRID (the key difference from original) ──
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


# ── CLI ───────────────────────────────────────────────────────────────────────

def render_rooms(
    data_root: str = "data/generated_data",
    icon_root: str = YOLO_ROOT,
    room_types: str = "bedrooms",
    id_ranges: str = "75-149",
    out_suffix: str = "_icons_grid",
):
    """Render icon images with grid for specified room types and ID ranges."""
    # Verify at least one theme dir exists
    found_theme = False
    for _, (rel, _) in THEME_DIRS.items():
        if (Path(icon_root) / rel).exists():
            found_theme = True
            break
    if not found_theme:
        print(f"[ERROR] No icon theme directories found in: {icon_root}")
        return

    rt_list = [r.strip() for r in str(room_types).split(",")]
    id_list = [r.strip() for r in str(id_ranges).split(",")]

    for rt, ids_str in zip(rt_list, id_list):
        json_dir = Path(data_root) / rt
        out_dir = Path(data_root) / f"{rt}{out_suffix}"
        out_dir.mkdir(parents=True, exist_ok=True)

        # Parse ID range
        id_set = set()
        for part in ids_str.split(","):
            part = part.strip()
            if "-" in part:
                lo, hi = part.split("-")
                id_set.update(range(int(lo), int(hi) + 1))
            else:
                id_set.add(int(part))

        rendered = 0
        for rid in sorted(id_set):
            scene_path = json_dir / f"room_{rid}.json"
            if not scene_path.exists():
                continue
            out_path = out_dir / f"room_{rid}.png"
            render_one_with_grid(scene_path, out_path, icon_root)
            rendered += 1

        print(f"Rendered {rendered} icon+grid images to {out_dir}")


def mixed(
    data_root: str = "data/generated_data",
    icon_root: str = YOLO_ROOT,
):
    """Render all three mixed room types with icons + grid."""
    render_rooms(
        data_root=data_root,
        icon_root=icon_root,
        room_types="bedrooms,living_rooms,kitchens",
        id_ranges="75-149,0-74,150-199",
    )


if __name__ == "__main__":
    fire.Fire({
        "render": render_rooms,
        "mixed": mixed,
    })
