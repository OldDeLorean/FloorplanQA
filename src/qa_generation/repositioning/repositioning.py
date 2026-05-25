# src/qa_pairs_generation/move_axis_aligned.py
from __future__ import annotations
import os, math
from typing import Dict, List, Tuple, Optional
from functools import partial
import numpy as np
import json
from shapely.geometry import Polygon, MultiPolygon
from shapely.geometry import Polygon as ShpPolygon, Point
from shapely.affinity import translate
from shapely.ops import unary_union
from shapely.validation import make_valid
import hashlib

###Swap labels ablation
import copy
import hashlib
import random
from typing import Union, Optional


def _stable_seed_from_layout(layout_id: Union[int, str]) -> int:
    """Stable 32-bit seed from layout_id (consistent across runs)."""
    return int(hashlib.md5(str(layout_id).encode()).hexdigest(), 16) % (2**32)


def swap_object_labels(
    room: dict,
    strategy: str = "rotate",  # "rotate" | "reverse" | "shuffle"
    seed: Optional[int] = None,  # used only when strategy="shuffle"
) -> dict:
    """
    Return a copy of room with all object labels swapped.
    - rotate: cyclic shift by 1 (derangement if len>1 and labels unique)
    - reverse: reverse order
    - shuffle: deterministic if you pass a seed
    """
    out = copy.deepcopy(room)
    objs = out.get("objects")
    if not isinstance(objs, list) or len(objs) < 2:
        return out  # nothing to do

    labels = [obj.get("label", "") for obj in objs]
    new_labels = labels[:]

    if strategy == "rotate":
        new_labels = labels[1:] + labels[:1]
    elif strategy == "reverse":
        new_labels = list(reversed(labels))
    elif strategy == "shuffle":
        rng = random.Random(seed if seed is not None else 0)
        rng.shuffle(new_labels)
        # ensure we actually swapped at least one position; if not, rotate
        if new_labels == labels and len(labels) > 1:
            new_labels = labels[1:] + labels[:1]
    else:
        raise ValueError("strategy must be 'rotate', 'reverse', or 'shuffle'")

    for obj, new_label in zip(objs, new_labels):
        obj["label"] = new_label
    return out


obj_for_movement = {
    "kitchen": ["stove", "fridge", "sink", "dishwasher"],
    "living_room": ["sofa", "loveseat", "armchair", "coffee_table", "side_table", "tv_stand", "bookshelf", "plant"],
    "bedroom": ["bed", "dresser", "wardrobe", "desk", "chair", "bookshelf", "ottoman", "closet_alcove", "floor_lamp", "plant"],
}

GEOMETRY_TOLERANCE = 1e-4

from src.qa_pairs_generation.utils import (
    build_room_polygon,
    get_polygon_centroid,
    is_rug_label,
    is_light_label,
    _label,
    generate_qa_pairs_with_subsampling,
    merge_objects_and_openings,
    save_and_info,
)


def _poly(points: List[Dict[str, float]]) -> Optional[ShpPolygon]:
    if not points or len(points) < 3:
        return None
    coords = [(float(p["x"]), float(p["y"])) for p in points]
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    poly = ShpPolygon(coords)
    poly = make_valid(poly)
    if poly.is_empty or not poly.is_valid or poly.area <= 0:
        return None
    return poly


def _dir_vec(direction: str) -> Tuple[float, float]:
    d = direction.lower()
    if d in ("up", "top"):
        return (0.0, 1.0)
    if d in ("down", "bottom"):
        return (0.0, -1.0)
    if d == "left":
        return (-1.0, 0.0)
    if d == "right":
        return (1.0, 0.0)
    raise ValueError(f"Invalid direction '{direction}'. Use top/bottom/left/right.")


def calculate_max_slide_distance(
    object_to_move: Polygon, room_boundary: Polygon, obstacles: List[Polygon], direction: Tuple[float, float], step_distance: float = 0.01  # Move by 1cm at a time
) -> float:
    """
    Calculates max slide distance by moving iteratively in small steps.
    This avoids the "tunneling" problem of binary search.
    """
    if not object_to_move or object_to_move.is_empty:
        return 0.0

    obstacle_union = unary_union(obstacles)

    # --- 1. Initial Position Sanity Check ---
    if not room_boundary.covers(object_to_move):
        return 0.0
    if isinstance(obstacle_union, (Polygon, MultiPolygon)) and object_to_move.overlaps(obstacle_union):
        return 0.0

    vx, vy = direction

    # --- 2. Iterative Stepping Loop ---
    current_dist = 0.0
    # Set a reasonable limit to prevent infinite loops (e.g., room diagonal)
    min_x, min_y, max_x, max_y = room_boundary.bounds
    max_possible_dist = np.sqrt((max_x - min_x) ** 2 + (max_y - min_y) ** 2)

    num_steps = int(max_possible_dist / step_distance)

    for i in range(1, num_steps + 1):
        next_dist = i * step_distance
        moved_object = translate(object_to_move, xoff=vx * next_dist, yoff=vy * next_dist)

        # --- Check for collision at the new step ---
        # A) Is it outside the room?
        if not room_boundary.buffer(-GEOMETRY_TOLERANCE).covers(moved_object):
            break  # We've hit a wall, stop here.

        # B) Does it overlap an obstacle? (Allowing touch)
        intersection = moved_object.intersection(obstacle_union)
        if not intersection.is_empty and intersection.area > GEOMETRY_TOLERANCE:
            break  # We've hit an obstacle, stop here.

        # If we reach here, the step was valid. Update our distance.
        current_dist = next_dist

    return current_dist


def move_object_and_get_distance(
    data: Dict,
    object_to_move: Dict,
    direction: str,
) -> Tuple[Optional[List[Dict[str, float]]], float]:
    """
    Prepares data and uses the robust calculation engine to find the max
    move distance and new object position.
    """
    # print()
    # print()
    # print("\n" + "=" * 50)
    # print(f"--- Attempting to move object '{_label(object_to_move)}' in direction '{direction}' ---")

    # --- 1. Prepare Data ---
    room_poly = build_room_polygon(data)
    poly_to_move = _poly(object_to_move.get("points") or [])

    if room_poly is None or poly_to_move is None:
        # print("[DEBUG] Failed: Could not create a valid polygon for the room or the object to move.")
        return object_to_move.get("points"), 0.0

    obstacle_polys = []
    for o in data.get("objects", []):
        if o is object_to_move:
            continue
        lab = _label(o)
        if is_rug_label(lab) or is_light_label(lab):
            continue
        p = _poly(o.get("points") or [])
        if p:
            obstacle_polys.append(p)

    # print(f"[DEBUG] Found {len(obstacle_polys)} blocking obstacles.")
    dir_vector = _dir_vec(direction)

    # --- 2. Call the Geometry Engine ---
    # print("[DEBUG] Calling the core geometry engine 'calculate_max_slide_distance'...")
    distance = calculate_max_slide_distance(object_to_move=poly_to_move, room_boundary=room_poly, obstacles=obstacle_polys, direction=dir_vector)
    # print(f"[DEBUG] Engine returned a final distance of: {distance:.4f}")

    # --- 3. Calculate Final Position and Return ---
    vx, vy = dir_vector
    P_new = translate(poly_to_move, xoff=vx * distance, yoff=vy * distance)

    coords = list(P_new.exterior.coords)[:-1]
    after_pts = [{"x": float(x), "y": float(y)} for x, y in coords]

    # print("=" * 50 + "\n")
    return after_pts, float(distance)


# src/qa_pairs_generation/move_axis_aligned.py (append below)
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import numpy as np
from pathlib import Path


def _segments_from_points(points: List[Dict[str, float]], close=True):
    if not points or len(points) < 2:
        return []
    segs = []
    n = len(points)
    for i in range(n - 1):
        a, b = points[i], points[i + 1]
        segs.append([(a["x"], a["y"]), (b["x"], b["y"])])
    if close and n >= 3:
        a, b = points[-1], points[0]
        segs.append([(a["x"], a["y"]), (b["x"], b["y"])])
    return segs


def render_move_subplot(
    data: Dict,
    moved_label: str,
    points_before: List[Dict[str, float]],
    points_after: List[Dict[str, float]],
    distance_moved: float,
    direction: str,
    out_path: str,
    *,
    dpi: int = 150,
):
    from pathlib import Path
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    import numpy as np

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    COL_ROOM = "#444444"
    COL_WALL = "#000000"
    COL_OBJ = "#A0A0A0"
    COL_OBJ_EDGE = "#666666"
    COL_RUG = "#b2df8a"
    COL_LIGHT = "#ffd166"
    COL_MOVED_BEFORE = "#1f77b4"
    COL_MOVED_AFTER = "#e74c3c"
    COL_ARROW = "#e67e22"

    def _bounds():
        xs, ys = [], []
        rb = data.get("room_boundary") or []
        for p in rb:
            xs.append(p["x"])
            ys.append(p["y"])
        for w in data.get("walls") or (data.get("room", {}) or {}).get("walls") or []:
            s, e = w.get("start"), w.get("end")
            if s and e:
                xs += [s["x"], e["x"]]
                ys += [s["y"], e["y"]]
        for o in data.get("objects") or []:
            for p in o.get("points") or []:
                xs.append(p["x"])
                ys.append(p["y"])
        if not xs:
            return (-1, -1, 1, 1)
        return (min(xs), min(ys), max(xs), max(ys))

    def _draw(ax, use_after=False):
        rb = data.get("room_boundary") or []
        if rb:
            arr = np.array([[p["x"], p["y"]] for p in rb], dtype=float)
            ax.plot(arr[:, 0], arr[:, 1], "--", color=COL_ROOM, linewidth=1.6, alpha=0.9)

        # walls
        wall_segs = []
        for w in data.get("walls") or (data.get("room", {}) or {}).get("walls") or []:
            s, e = w.get("start"), w.get("end")
            if s and e:
                wall_segs.append([(float(s["x"]), float(s["y"])), (float(e["x"]), float(e["y"]))])
        if wall_segs:
            ax.add_collection(LineCollection(wall_segs, linewidths=2.5, colors=[COL_WALL]))

        # objects
        for o in data.get("objects") or []:
            lab = (o.get("label") or o.get("name") or "").lower()
            pts = o.get("points") or []
            if not pts:
                continue
            arr = np.array([[p["x"], p["y"]] for p in pts], dtype=float)

            if lab == moved_label.lower():
                draw_pts = points_after if use_after else points_before
                arr2 = np.array([[p["x"], p["y"]] for p in draw_pts], dtype=float)
                ax.fill(arr2[:, 0], arr2[:, 1], facecolor=(COL_MOVED_AFTER if use_after else COL_MOVED_BEFORE), edgecolor="#222222", alpha=0.45, linewidth=1.5)
            else:
                if is_rug_label(lab):
                    ax.fill(arr[:, 0], arr[:, 1], facecolor=COL_RUG, edgecolor=COL_OBJ_EDGE, alpha=0.25)
                elif is_light_label(lab):
                    ax.fill(arr[:, 0], arr[:, 1], facecolor=COL_LIGHT, edgecolor=COL_OBJ_EDGE, alpha=0.25)
                else:
                    ax.fill(arr[:, 0], arr[:, 1], facecolor=COL_OBJ, edgecolor=COL_OBJ_EDGE, alpha=0.30)

        # arrow
        if points_before and points_after:
            c0 = get_polygon_centroid(points_before)
            c1 = get_polygon_centroid(points_after)
            ax.annotate("", xy=c1, xytext=c0, arrowprops=dict(arrowstyle="->", lw=2.0, color=COL_ARROW))
            ax.plot([c0[0]], [c0[1]], "o", color="#2ecc71", ms=6, zorder=5)
            ax.plot([c1[0]], [c1[1]], "*", color="#d62728", ms=9, zorder=5)

        ax.set_aspect("equal", adjustable="box")
        minx, miny, maxx, maxy = _bounds()
        pad = 0.05 * max(maxx - minx, maxy - miny, 1e-6)
        ax.set_xlim(minx - pad, maxx + pad)
        ax.set_ylim(miny - pad, maxy + pad)
        ax.grid(True, which="both", linewidth=0.6, alpha=0.7)

    # subplot with before and after
    fig, axes = plt.subplots(1, 2, figsize=(12, 6), dpi=dpi)
    _draw(axes[0], use_after=False)
    axes[0].set_title("Before movement")
    _draw(axes[1], use_after=True)
    axes[1].set_title("After movement")

    fig.suptitle(f"Object '{moved_label}' moved by {distance_moved:.2f} meters {direction}", fontsize=14)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(out_path, dpi=dpi, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


# Example usage in your generator
def process_single_file(file_path: str, file: str, room_type: str, out_dir: str) -> Optional[Dict]:
    with open(file_path, "r") as f:
        data = json.load(f)
    # ---- layout_id ----
    layout_id = data.get("layout_id")
    if layout_id is None:
        layout_id = file.replace(".json", "").replace("real_", "").replace("room_", "")
    # # 2) deterministic shuffle per layout_id:
    # seed = _stable_seed_from_layout(layout_id)
    # data = swap_object_labels(data, strategy="shuffle", seed=seed)

    with open(f"data/hssd_data/json_simplified/swapped_labels/room_{layout_id}.json", "r") as f:
        swapped_labels_data = json.load(f)

    # ---- room_type ----
    if room_type == "unknown":
        room_type = data.get("room_type") or (data.get("room", {}) or {}).get("room_type") or "unknown"

    # Always filter objects based on the determined room_type.
    # This ensures we only consider objects relevant to the target room.
    if room_type in obj_for_movement and room_type in file_path:
        # print("YES")
        def check_any_label(obj):
            lab = _label(obj).lower()
            for target in obj_for_movement[room_type]:
                if target in lab:
                    return True
            return False

        objects = [obj for obj in data["objects"] if check_any_label(obj)]
    else:
        # print("NO", room_type)
        # Fallback for unknown or unsupported room types: use all objects.
        objects = data["objects"]

    # pick eligible movable objects (no openings, no rugs/lights)
    movable = [o for o in objects if (not is_rug_label(_label(o))) and (not is_light_label(_label(o)))]
    if not movable:
        print("NONE movable objects found in", objects, room_type, file_path)
        return None

    seed = int(hashlib.md5(str(layout_id).encode()).hexdigest(), 16) % (2**32)
    rng = np.random.default_rng(seed=seed)
    rng = np.random.default_rng(seed=abs(hash(layout_id)))
    mv = rng.choice(movable)
    mv_label = _label(mv)

    before_pts = mv["points"]

    tried_dirs = set()
    directions = ["top", "bottom", "left", "right"]
    direction = rng.choice(directions)

    swapped_labels_objects = swapped_labels_data["objects"]
    mv = next((obj for obj in swapped_labels_objects if _label(obj) == mv_label), mv)

    # after_pts, dist = move_object_and_get_distance(data, mv, direction)
    after_pts, dist = move_object_and_get_distance(swapped_labels_data, mv, direction)
    tried_dirs.add(direction)

    # print("After trying direction", direction, "got distance", dist, "pts", after_pts)

    # Try up to 4 times with different directions if dist == 0
    attempts = 1
    while dist < 1e-2 and attempts < 4:
        remaining_dirs = [d for d in directions if d not in tried_dirs]
        if not remaining_dirs:
            break
        direction = rng.choice(remaining_dirs)
        after_pts, dist = move_object_and_get_distance(data, mv, direction)
        tried_dirs.add(direction)
        attempts += 1

        # print("After trying direction", direction, "got distance", dist, "pts", after_pts)

    if after_pts is None:
        after_pts = before_pts
        dist = 0.0
    # render (no try/except)
    out_png = Path(out_dir) / f"{layout_id}.png"
    out_png.parent.mkdir(parents=True, exist_ok=True)

    render_move_subplot(data, mv_label, before_pts, after_pts, dist, direction, out_png)

    return {
        "layout_id": layout_id,
        "room_type": room_type,
        "object_to_move": mv_label,
        "direction": direction,
        "answer": round(float(dist), 3),
        "N_objects": len(objects),
    }


def main_repositioning(
    input_dir: str = "data/hssd_data/new_format",
    output_csv: str = "benchmark/{parent_folder_name}/{parent_folder_name}_qa_hssd_data.csv",
    output_img: str = "benchmark/{parent_folder_name}/{parent_folder_name}_qa_hssd_images/",
    enable_subsampling: bool = False,
    bedrooms_count: int = 80,
    living_rooms_count: int = 80,
    kitchens_count: int = 40,
):
    parent_folder_name = os.path.basename(os.path.dirname(os.path.realpath(__file__)))
    output_csv = output_csv.format(parent_folder_name=parent_folder_name)
    output_img = output_img.format(parent_folder_name=parent_folder_name)

    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)

    # Configure subsampling
    subsample_config = None
    if enable_subsampling:
        subsample_config = {"bedrooms": bedrooms_count, "living_rooms": living_rooms_count, "kitchens": kitchens_count}
        print(f"Subsampling enabled: {subsample_config}")
    else:
        print("Processing all available files")

    qa_pairs = generate_qa_pairs_with_subsampling(input_dir=input_dir, process_single_file=partial(process_single_file, out_dir=output_img), subsample_config=subsample_config)

    save_and_info(qa_pairs, output_csv=output_csv)
