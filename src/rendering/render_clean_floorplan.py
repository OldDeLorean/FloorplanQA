#!/usr/bin/env python3
"""
Render floorplan JSON files as clean black-on-white images with a metric grid.

Style:
  - White background, black lines only (no colors)
  - Walls: thick solid black lines
  - Room boundary: thin dashed black
  - Objects: thin solid black rectangles with centered labels
  - Doors: thin gray rectangles with "D" label
  - Windows: double-line pattern on wall (architectural style)
  - Metric grid with 0.5m spacing, light gray
  - Axis labels in meters
  - No legend clutter

Usage:
    python -m src.render_clean_floorplan \
        --json_dir data/generated_data/bedrooms \
        --out_dir data/generated_data/bedrooms_clean \
        --ids 0-199

    # Or render all three room types for mixed dataset:
    python -m src.render_clean_floorplan --mixed
"""

import json
import math
import fire
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.ticker import MultipleLocator
from pathlib import Path


# ── Style constants ──────────────────────────────────────────────────────────
BG_COLOR = "white"
WALL_COLOR = "black"
WALL_LW = 3.0
ROOM_BOUNDARY_COLOR = "black"
ROOM_BOUNDARY_LW = 1.0
OBJ_COLOR = "black"
OBJ_LW = 1.2
OBJ_FILL = "#f0f0f0"        # very light gray fill for objects
DOOR_COLOR = "#555555"
DOOR_LW = 1.0
WINDOW_COLOR = "black"
WINDOW_LW = 1.5
GRID_COLOR = "#d0d0d0"
GRID_LW_MAJOR = 0.5
GRID_LW_MINOR = 0.25
LABEL_FONT = 7
FIG_SIZE = (8, 8)
DPI = 150
GRID_SPACING_MAJOR = 1.0  # meters
GRID_SPACING_MINOR = 0.5  # meters


def _poly_segments(points, close=True):
    """Convert list of {x,y} dicts to line segments."""
    coords = [(p["x"], p["y"]) for p in points]
    segs = []
    for i in range(len(coords) - 1):
        segs.append([coords[i], coords[i + 1]])
    if close and len(coords) > 2:
        segs.append([coords[-1], coords[0]])
    return segs


def _centroid(points):
    xs = [p["x"] for p in points]
    ys = [p["y"] for p in points]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def _bbox(points):
    xs = [p["x"] for p in points]
    ys = [p["y"] for p in points]
    return min(xs), max(xs), min(ys), max(ys)


def render_clean(room_data: dict, out_path: str | Path, dpi: int = DPI):
    """Render a single room JSON as a clean black-on-white floorplan."""
    room_boundary = room_data.get("room_boundary", [])
    walls = room_data.get("walls", [])
    objects = room_data.get("objects", [])
    doors = room_data.get("openings", {}).get("doors", [])
    windows = room_data.get("openings", {}).get("windows", [])
    layout_id = room_data.get("layout_id", "")

    # ── Compute bounds ───────────────────────────────────────────────────
    all_points = list(room_boundary)
    for obj in objects + doors + windows:
        all_points.extend(obj.get("points", []))
    if not all_points:
        return

    x_min, x_max, y_min, y_max = _bbox(all_points)
    margin = 0.3
    x_min -= margin
    x_max += margin
    y_min -= margin
    y_max += margin

    # ── Figure ───────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=FIG_SIZE, dpi=dpi)
    ax.set_facecolor(BG_COLOR)
    fig.patch.set_facecolor(BG_COLOR)

    # Grid
    ax.xaxis.set_major_locator(MultipleLocator(GRID_SPACING_MAJOR))
    ax.xaxis.set_minor_locator(MultipleLocator(GRID_SPACING_MINOR))
    ax.yaxis.set_major_locator(MultipleLocator(GRID_SPACING_MAJOR))
    ax.yaxis.set_minor_locator(MultipleLocator(GRID_SPACING_MINOR))
    ax.grid(True, which="major", color=GRID_COLOR, linewidth=GRID_LW_MAJOR)
    ax.grid(True, which="minor", color=GRID_COLOR, linewidth=GRID_LW_MINOR, alpha=0.5)

    # Room boundary (dashed)
    if room_boundary:
        rb = np.array([[p["x"], p["y"]] for p in room_boundary])
        ax.plot(rb[:, 0], rb[:, 1], color=ROOM_BOUNDARY_COLOR,
                linewidth=ROOM_BOUNDARY_LW, linestyle="--", alpha=0.5)

    # Walls (thick solid black)
    wall_segs = []
    for w in walls:
        s, e = w.get("start"), w.get("end")
        if s and e:
            wall_segs.append([(s["x"], s["y"]), (e["x"], e["y"])])
    if wall_segs:
        ax.add_collection(LineCollection(
            wall_segs, linewidths=WALL_LW, colors=[WALL_COLOR], zorder=3))

    # Objects (thin black outline + light fill + label)
    for obj in objects:
        pts = obj.get("points", [])
        if not pts:
            continue
        label = obj.get("label", "")

        # Draw filled rectangle
        segs = _poly_segments(pts, close=True)
        xs = [p["x"] for p in pts]
        ys = [p["y"] for p in pts]
        # Fill
        ax.fill(xs + [xs[0]], ys + [ys[0]], color=OBJ_FILL, zorder=1)
        # Outline
        ax.add_collection(LineCollection(
            segs, linewidths=OBJ_LW, colors=[OBJ_COLOR], zorder=2))

        # Label
        cx, cy = _centroid(pts)
        ax.text(cx, cy, label, ha="center", va="center",
                fontsize=LABEL_FONT, color="black", fontweight="normal",
                zorder=4)

    # Doors (gray outline, "D" label)
    for door in doors:
        pts = door.get("points", [])
        if not pts:
            continue
        label = door.get("label", "door")
        segs = _poly_segments(pts, close=True)
        ax.add_collection(LineCollection(
            segs, linewidths=DOOR_LW, colors=[DOOR_COLOR], zorder=2,
            linestyle="dashed"))
        cx, cy = _centroid(pts)
        ax.text(cx, cy, label, ha="center", va="center",
                fontsize=LABEL_FONT - 1, color=DOOR_COLOR, zorder=4)

    # Windows (double line to look architectural)
    for win in windows:
        pts = win.get("points", [])
        if not pts:
            continue
        label = win.get("label", "window")
        segs = _poly_segments(pts, close=True)
        # Thicker outline for windows
        ax.add_collection(LineCollection(
            segs, linewidths=WINDOW_LW, colors=[WINDOW_COLOR], zorder=2))
        # Cross-hatch pattern inside
        x1, x2, y1, y2 = _bbox(pts)
        ax.plot([x1, x2], [y1, y2], color=WINDOW_COLOR, lw=0.5, zorder=2)
        ax.plot([x1, x2], [y2, y1], color=WINDOW_COLOR, lw=0.5, zorder=2)

        cx, cy = _centroid(pts)
        ax.text(cx, cy, label, ha="center", va="center",
                fontsize=LABEL_FONT - 1, color="black", zorder=4,
                bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.8))

    # Axis settings
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("X (meters)", fontsize=9)
    ax.set_ylabel("Y (meters)", fontsize=9)
    ax.set_title(f"Room {layout_id}", fontsize=11, fontweight="bold")

    # Tick labels show metric values
    ax.tick_params(axis="both", labelsize=7)

    plt.tight_layout(pad=0.2)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=dpi, bbox_inches="tight", pad_inches=0.05,
                facecolor=BG_COLOR)
    plt.close(fig)
    return str(out_path)


def render_directory(
    json_dir: str = "data/generated_data/bedrooms",
    out_dir: str | None = None,
    ids: str | None = None,
    dpi: int = DPI,
):
    """Render all JSON rooms in a directory.

    Args:
        json_dir: Path to directory containing room_*.json files
        out_dir: Output directory. Defaults to {json_dir}_clean
        ids: Range string like "0-199" or "75,80,100". None = all.
        dpi: Image DPI
    """
    json_dir = Path(json_dir)
    if out_dir is None:
        out_dir = json_dir.parent / f"{json_dir.name}_clean"
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Parse ID filter
    id_set = None
    if ids is not None:
        ids = str(ids)
        id_set = set()
        for part in ids.split(","):
            part = part.strip()
            if "-" in part:
                lo, hi = part.split("-")
                id_set.update(range(int(lo), int(hi) + 1))
            else:
                id_set.add(int(part))

    json_files = sorted(json_dir.glob("room_*.json"))
    rendered = 0
    for jf in json_files:
        # Extract ID from filename
        try:
            rid = int(jf.stem.replace("room_", ""))
        except ValueError:
            continue
        if id_set is not None and rid not in id_set:
            continue

        with open(jf) as f:
            room_data = json.load(f)

        out_path = out_dir / f"room_{rid}.png"
        render_clean(room_data, out_path, dpi=dpi)
        rendered += 1

    print(f"Rendered {rendered} clean floorplans to {out_dir}")


def render_mixed(
    base_dir: str = "data/generated_data",
    dpi: int = DPI,
):
    """Render all three room types for the mixed dataset."""
    base = Path(base_dir)
    for room_type, start, end in [
        ("bedrooms", 75, 149),
        ("living_rooms", 0, 74),
        ("kitchens", 150, 199),
    ]:
        json_dir = base / room_type
        out_dir = base / f"{room_type}_clean"
        render_directory(
            json_dir=str(json_dir),
            out_dir=str(out_dir),
            ids=f"{start}-{end}",
            dpi=dpi,
        )


if __name__ == "__main__":
    fire.Fire({
        "render": render_directory,
        "mixed": render_mixed,
        "single": render_clean,
    })
