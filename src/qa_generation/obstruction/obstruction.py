# ---- new-format version (polygons + openings) ----
import os
import json
import numpy as np
from typing import Dict, List
from functools import partial
from src.qa_pairs_generation.utils import (
    merge_objects_and_openings,
    render_layout_pair,
    get_polygon_centroid,
    euclidean_distance,
    generate_qa_pairs_with_subsampling,
    save_and_info,
    _label,
)
from pathlib import Path
from typing import Dict, List, Tuple
from shapely.geometry import Polygon as ShpPolygon, LineString, Point
from shapely.ops import unary_union
from src.qa_pairs_generation.utils import get_polygon_centroid
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


def _points_to_polygon(points: List[Dict[str, float]]) -> ShpPolygon | None:
    if not points or len(points) < 3:
        return None
    coords = [(float(p["x"]), float(p["y"])) for p in points]
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    poly = ShpPolygon(coords)
    if not poly.is_valid or poly.is_empty or poly.area <= 0:
        return None
    return poly


def _collect_entities_with_openings(data: Dict) -> List[Dict]:
    """Return objects + openings as object-like dicts: {'label', 'points'}."""
    out: List[Dict] = []
    out.extend(data.get("objects") or [])
    openings = data.get("openings") or {}
    for key in ("windows", "doors"):
        for ent in openings.get(key) or []:
            out.append({"label": ent.get("label") or key, "points": ent.get("points") or []})
    return out


def find_objects_intersecting_line_poly(
    data: Dict,
    start_label: str,
    goal_label: str,
    *,
    include_openings: bool = True,
    ignore_labels: List[str] | None = None,
) -> Tuple[List[Dict], Tuple[float, float]]:
    """
    New-format: use polygon centroids + polygon/segment intersection.
    Returns (objects_on_the_way, (dx, dy)) where objects_on_the_way are dicts from entities list.
    """
    entities = _collect_entities_with_openings(data) if include_openings else (data.get("objects") or [])
    label_lc_map = {_label(o).lower(): o for o in entities if _label(o)}

    s_ent = label_lc_map.get(start_label.strip().lower())
    g_ent = label_lc_map.get(goal_label.strip().lower())
    if not s_ent or not g_ent:
        return [], (0.0, 0.0)

    s_cent = get_polygon_centroid(s_ent["points"])
    g_cent = get_polygon_centroid(g_ent["points"])
    seg = LineString([s_cent, g_cent])
    dx, dy = g_cent[0] - s_cent[0], g_cent[1] - s_cent[1]

    ignore = set([_label(s_ent).lower(), _label(g_ent).lower()])
    if ignore_labels:
        ignore |= {l.strip().lower() for l in ignore_labels}

    on_the_way: List[Dict] = []
    for obj in entities:
        lab = _label(obj)
        if not lab or lab.strip().lower() in ignore:
            continue
        poly = _points_to_polygon(obj.get("points") or [])
        if poly is None:
            continue

        inter = seg.intersection(poly)
        if inter.is_empty:
            continue

        # Count as "on the way" if the intersection isn’t just a single endpoint exactly at s_cent or g_cent.
        # i.e., any non-empty intersection that isn’t {start_point, goal_point} only.
        allowed_endpoints = {Point(s_cent), Point(g_cent)}
        if inter.geom_type == "Point" and any(inter.equals(pt) for pt in allowed_endpoints):
            continue
        if inter.geom_type == "MultiPoint" and all(any(g.equals(pt) for pt in allowed_endpoints) for g in inter.geoms):
            continue

        on_the_way.append(obj)

    return on_the_way, (dx, dy)


import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from pathlib import Path


def render_direct_line(
    data: Dict,
    start_label: str,
    goal_label: str,
    on_the_way: List[Dict],
    out_path: str,
    *,
    show_grid: bool = True,
    show_axes: bool = True,
    dpi: int = 150,
) -> str:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    COL_ROOM = "#444444"
    COL_WALL = "#000000"
    COL_WINDOW = "#1f77b4"
    COL_DOOR = "#22aa55"
    COL_OBJ = "#999999"
    COL_OBJ_EDGE = "#666666"
    COL_HIT = "#f39c12"  # highlight objects on the way
    COL_LINE = "#e74c3c"  # line between centroids
    COL_START = "#2ecc71"
    COL_GOAL = "#1f77b4"

    fig, ax = plt.subplots(figsize=(8, 8), dpi=dpi)

    # room boundary (optional)
    rb = data.get("room_boundary") or []
    if rb:
        arr = np.array([[p["x"], p["y"]] for p in rb], dtype=float)
        ax.plot(arr[:, 0], arr[:, 1], "--", color=COL_ROOM, linewidth=1.6, alpha=0.9, label="Room boundary")

    # walls
    wall_segs = []
    for w in data.get("walls") or (data.get("room", {}) or {}).get("walls") or []:
        s, e = w.get("start"), w.get("end")
        if s and e:
            wall_segs.append([(float(s["x"]), float(s["y"])), (float(e["x"]), float(e["y"]))])
    if wall_segs:
        ax.add_collection(LineCollection(wall_segs, linewidths=2.5, colors=[COL_WALL], label="Walls"))

    # openings (for context)
    openings = data.get("openings") or {}
    for ent in openings.get("windows") or []:
        pts = ent.get("points") or []
        if len(pts) >= 2:
            arr = np.array([[p["x"], p["y"]] for p in pts], dtype=float)
            ax.plot(arr[:, 0], arr[:, 1], "-", color=COL_WINDOW, linewidth=2.0, alpha=0.9, label="Window")
    for ent in openings.get("doors") or []:
        pts = ent.get("points") or []
        if len(pts) >= 2:
            arr = np.array([[p["x"], p["y"]] for p in pts], dtype=float)
            ax.plot(arr[:, 0], arr[:, 1], "-", color=COL_DOOR, linewidth=2.0, alpha=0.9, label="Door")

    # objects (fill), but highlight on-the-way
    objs = data.get("objects") or []
    hit_set = {(_label(o).strip().lower()) for o in on_the_way}

    def _fill_poly(o, face, edge, alpha=0.35, lw=1.0, z=1):
        pts = o.get("points") or []
        if len(pts) < 3:
            return
        arr = np.array([[p["x"], p["y"]] for p in pts], dtype=float)
        ax.fill(arr[:, 0], arr[:, 1], facecolor=face, edgecolor=edge, alpha=alpha, linewidth=lw, zorder=z)

    for o in objs:
        lab_l = _label(o).strip().lower()
        if lab_l in hit_set:
            _fill_poly(o, COL_HIT, COL_HIT, alpha=0.40, lw=1.4, z=3)
        else:
            _fill_poly(o, COL_OBJ, COL_OBJ_EDGE, alpha=0.28, lw=1.0, z=1)

    # determine start/goal centroids
    ent_map = {_label(o).strip().lower(): o for o in _collect_entities_with_openings(data)}
    s = ent_map.get(start_label.strip().lower())
    g = ent_map.get(goal_label.strip().lower())
    if s and g:
        from src.qa_pairs_generation.utils import get_polygon_centroid

        s_cent = get_polygon_centroid(s["points"])
        g_cent = get_polygon_centroid(g["points"])
        ax.plot([s_cent[0], g_cent[0]], [s_cent[1], g_cent[1]], "-", color=COL_LINE, linewidth=2.6, zorder=4, label="Direct line")
        ax.plot(s_cent[0], s_cent[1], "o", color=COL_START, markersize=7, zorder=5, label="Start")
        ax.plot(g_cent[0], g_cent[1], "*", color=COL_GOAL, markersize=11, zorder=5, label="Target")

    # bounds
    xs, ys = [], []
    for src in [rb] if rb else []:
        xs += [p["x"] for p in src]
        ys += [p["y"] for p in src]
    for (x1, y1), (x2, y2) in wall_segs:
        xs += [x1, x2]
        ys += [y1, y2]
    for o in _collect_entities_with_openings(data):
        for p in o.get("points") or []:
            xs.append(p["x"])
            ys.append(p["y"])
    if xs:
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        pad = 0.05 * max(maxx - minx, maxy - miny, 1e-6)
        ax.set_xlim(minx - pad, maxx + pad)
        ax.set_ylim(miny - pad, maxy + pad)
    ax.set_aspect("equal", adjustable="box")

    if show_axes:
        ax.set_xlabel("X (m)")
        ax.set_ylabel("Y (m)")
    if show_grid:
        ax.grid(True, which="both", linewidth=0.6, alpha=0.7)

    # dedup legend
    hds, lbls = ax.get_legend_handles_labels()
    seen = set()
    H = []
    L = []
    for h, l in zip(hds, lbls):
        if l in seen:
            continue
        seen.add(l)
        H.append(h)
        L.append(l)
    if len(L) >= 2:
        ax.legend(H, L, loc="upper right", fontsize=8)

    plt.tight_layout(pad=0.2)
    plt.savefig(out_path, dpi=dpi, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    return out_path


def process_single_file(file_path: str, file: str, room_type_arg: str, out_dir: str) -> Dict:
    """
    Process a single JSON file and return QA pair data
    """
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
    room_type = room_type_arg
    if room_type == "unknown":
        room_type = data.get("room_type") or (data.get("room", {}) or {}).get("room_type") or "unknown"

    # ---- objects (include windows/doors as objects) ----
    objects = merge_objects_and_openings(data)
    if len(objects) < 2:
        raise ValueError(f"Need at least 2 objects (incl. windows/doors) in {file_path}")

    # ---- Create a DETERMINISTIC random number generator based on the layout_id ----
    # We use hash() to convert the string ID to an integer for the seed.
    # This ensures the same file ALWAYS gets the same random sequence.
    # seed = int(hashlib.md5(str(layout_id).encode()).hexdigest(), 16) % (2**32)
    # rng = np.random.default_rng(seed=seed)
    rng = np.random.default_rng(seed=abs(hash(layout_id)))
    obj1, obj2 = rng.choice(objects, 2, replace=False)

    # pick labels however you like (override map, pool, etc.)
    on_the_way, (dx, dy) = find_objects_intersecting_line_poly(
        swapped_labels_data,
        start_label=_label(obj1),
        goal_label=_label(obj2),
        include_openings=True,
    )

    # ---- centroids ----
    center1 = get_polygon_centroid(obj1["points"])
    center2 = get_polygon_centroid(obj2["points"])

    # render (no try/except)
    out_png = Path(out_dir) / f"{layout_id}.png"
    out_png.parent.mkdir(parents=True, exist_ok=True)

    render_direct_line(data, _label(obj1), _label(obj2), on_the_way, out_png)

    return {
        "answer": [_label(obj) for obj in on_the_way],
        "layout_id": layout_id,
        "room_type": room_type,
        "object_1": _label(obj1),
        "object_2": _label(obj2),
        "N_points_obj_1": len(obj1["points"]),
        "N_points_obj_2": len(obj2["points"]),
        "center_1": center1,
        "center_2": center2,
        "N_objects": len(objects),
    }


def main_obstruction(
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
