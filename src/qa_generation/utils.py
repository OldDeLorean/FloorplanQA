import math
import os
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Callable
from multiprocessing import Pool, cpu_count
from shapely.geometry import Polygon, LineString, Point
import json
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import numpy as np


def get_polygon_centroid(points: List[Dict[str, float]]) -> Tuple[float, float]:
    n = len(points)
    if n < 2:
        raise ValueError("A line or polygon must have at least 2 points.")

    coords = [(p["x"], p["y"]) for p in points]

    if n == 2:
        # Line segment: midpointc
        (x1, y1), (x2, y2) = coords
        return (round((x1 + x2) / 2.0, 2), round((y1 + y2) / 2.0, 2))

    poly = Polygon(coords)
    if not poly.is_valid or poly.area == 0:
        # Degenerate polygon: average of vertices
        cx = sum(x for x, _ in coords) / n
        cy = sum(y for _, y in coords) / n
        return (round(cx, 3), round(cy, 3))

    c = poly.centroid  # shapely Point
    return (round(c.x, 3), round(c.y, 3))


def get_polygon_centroid_mannualy(points: List[Dict[str, float]]) -> Tuple[float, float]:
    """
    Computes the true geometric centroid (center of mass) of a polygon
    defined by a list of vertices.

    Args:
        points: A list of dictionaries, where each dictionary represents a vertex
                and has 'x' and 'y' keys.

    Returns:
        A tuple containing the x and y coordinates of the centroid, rounded to 3 decimal places.
    """
    n = len(points)
    if n < 2:
        raise ValueError("A line or polygon must have at least 2 points.")

    # Special case for a line segment (n=2). The centroid is the midpoint.
    if n == 2:
        x_coords = [p["x"] for p in points]
        y_coords = [p["y"] for p in points]
        cx = sum(x_coords) / n
        cy = sum(y_coords) / n
        return (round(cx, 2), round(cy, 2))

    # To simplify the loop, we create a new list where the first point is
    # also the last point, closing the polygon.
    vertices = points + [points[0]]

    signed_area = 0.0
    sum_cx = 0.0
    sum_cy = 0.0

    # Iterate through the vertices to calculate the signed area and weighted sums
    for i in range(n):
        x_i, y_i = vertices[i]["x"], vertices[i]["y"]
        x_next, y_next = vertices[i + 1]["x"], vertices[i + 1]["y"]

        # This cross product term is a key component for both area and centroid calculation.
        cross_product_term = (x_i * y_next) - (x_next * y_i)

        # Accumulate the signed area.
        signed_area += cross_product_term

        # Accumulate the weighted sums for the centroid's x and y coordinates.
        sum_cx += (x_i + x_next) * cross_product_term
        sum_cy += (y_next + y_i) * cross_product_term  # Switched order, but math is the same

    # The actual area is half of the signed area sum.
    final_signed_area = signed_area / 2.0

    # Handle the case of a degenerate polygon (e.g., all points on a line).
    # In this case, the centroid is just the average of the vertices.
    if math.isclose(final_signed_area, 0.0):
        print("Warning: Polygon has a very small or zero area. Using simple average of vertices.")
        x_coords = [p["x"] for p in points]
        y_coords = [p["y"] for p in points]
        cx = sum(x_coords) / n
        cy = sum(y_coords) / n
    else:
        # Calculate the final centroid coordinates using the full formula.
        cx = sum_cx / (6.0 * final_signed_area)
        cy = sum_cy / (6.0 * final_signed_area)

    # Return the rounded result.
    return (round(cx, 3), round(cy, 3))


def euclidean_distance(p1: tuple, p2: tuple) -> float:
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


from multiprocessing import Pool, cpu_count
from typing import Callable  # Make sure to import Callable


def generate_qa_pairs_with_subsampling(input_dir: str, process_single_file: Callable, SEED: int = 42, subsample_config: Dict[str, int] = None) -> List[Dict]:
    """
    Generate QA pairs with optional subsampling by room type.
    """
    qa_pairs: List[Dict] = []

    # Use a single RNG for the subsampling logic itself
    rng = np.random.default_rng(SEED)

    if subsample_config:
        # --- Subsampling branch (now properly randomized and reproducible) ---
        for room_type, max_count in subsample_config.items():
            room_dir = os.path.join(input_dir, room_type)
            if not os.path.exists(room_dir):
                print(f"Warning: Directory {room_dir} does not exist, skipping {room_type}")
                continue

            all_files = sorted([f for f in os.listdir(room_dir) if f.endswith(".json")])

            # Shuffle the files reproducibly before selecting
            rng.shuffle(all_files)

            selected_files = all_files[:max_count]
            print(f"Processing {len(selected_files)} randomly selected files from {room_type} (out of {len(all_files)} available)")

            for file in selected_files:
                file_path = os.path.join(room_dir, file)
                qa_pair = process_single_file(file_path=file_path, file=file, room_type_arg=room_type)
                if qa_pair:
                    qa_pairs.append(qa_pair)

        return qa_pairs

    # --- No-subsampling branch: PARALLEL ---
    # (No changes needed here, the fix is in process_single_file)
    tasks: List[tuple] = []
    for item in sorted(os.listdir(input_dir)):
        item_path = os.path.join(input_dir, item)
        if os.path.isdir(item_path):
            room_type = item
            for file in sorted(os.listdir(item_path)):
                if file.endswith(".json"):
                    file_path = os.path.join(item_path, file)
                    tasks.append((file_path, file, room_type))
        elif item.endswith(".json"):
            tasks.append((item_path, item, "unknown"))

    if not tasks:
        return qa_pairs

    for idx, task in enumerate(tasks):
        print(f"Processing {idx}...")
        res = process_single_file(*task)
        if res:
            qa_pairs.append(res)

    # procs = min(20, cpu_count() or 1)
    # chunksize = max(1, len(tasks) // (procs * 4))
    # print(f"Parallel processing {len(tasks)} files with {procs} processes (chunksize={chunksize})")

    # The function passed to starmap now needs keyword arguments.
    # We can use partial to fix the `out_dir` argument and let starmap handle the rest.
    # Let's assume process_single_file takes `out_dir` from the main function's partial.

    # with Pool(processes=procs) as pool:
    #     # starmap unpacks the tuples in `tasks` as positional arguments
    #     # e.g., process_single_file(file_path, file, room_type_arg)
    #     results = pool.starmap(process_single_file, tasks, chunksize=chunksize)
    #     # Filter out any None results from skipped files
    #     qa_pairs = [res for res in results if res is not None]

    return qa_pairs


def save_and_info(qa_pairs, output_csv="output.csv"):
    df = pd.DataFrame(qa_pairs)
    df["layout_id"] = df["layout_id"].astype(int)
    df.sort_values(by="layout_id", inplace=True)
    df.reset_index(drop=True, inplace=True)
    df.to_csv(output_csv, index=False)
    print(f"Saved {len(df)} QA pairs to {output_csv}")

    # Print summary by room type
    if len(df) > 0:
        summary = df["room_type"].value_counts()
        print(f"\nSummary by room type:")
        for room_type, count in summary.items():
            print(f"  {room_type}: {count}")


def merge_objects_and_openings(data: dict) -> list:
    """
    Return a unified list of objects, where windows and doors
    (if present in 'openings') are treated as objects.
    """
    objects = data.get("objects", []) or []

    openings = data.get("openings", {}) or {}
    windows = openings.get("windows", []) or []
    doors = openings.get("doors", []) or []

    return objects + windows + doors


def _poly_to_segments(points, close=True):
    if not points or len(points) < 2:
        return []
    segs = []
    n = len(points)
    for i in range(n - 1):
        p0, p1 = points[i], points[i + 1]
        segs.append([(float(p0["x"]), float(p0["y"])), (float(p1["x"]), float(p1["y"]))])
    if close and n >= 3:
        p0, p1 = points[-1], points[0]
        segs.append([(float(p0["x"]), float(p0["y"])), (float(p1["x"]), float(p1["y"]))])
    return segs


def _polygon_centroid_numpy(points):
    # area-weighted centroid with fallback to vertex-mean
    if not points:
        return (0.0, 0.0)
    x = np.asarray([p["x"] for p in points], dtype=float)
    y = np.asarray([p["y"] for p in points], dtype=float)
    if len(points) >= 3:
        x2 = np.r_[x, x[0]]
        y2 = np.r_[y, y[0]]
        cross = x2[:-1] * y2[1:] - x2[1:] * y2[:-1]
        area = cross.sum() / 2.0
        if abs(area) > 1e-9:
            cx = ((x2[:-1] + x2[1:]) * cross).sum() / (6.0 * area)
            cy = ((y2[:-1] + y2[1:]) * cross).sum() / (6.0 * area)
            return (float(cx), float(cy))
    return (float(x.mean()), float(y.mean()))


def render_layout_pair(
    data: dict,
    obj1: dict,
    obj2: dict,
    center1: tuple,
    center2: tuple,
    distance: float,
    out_dir: str,
    layout_id,
    dpi: int = 150,
):
    """
    Renders the full layout (room boundary, walls, ALL objects + windows + doors with labels),
    highlights the two sampled items with their centers and a connecting line,
    and saves to {out_dir}/{layout_id}.png
    """
    # ---------- styling ----------
    FIG_SIZE = (8, 8)
    COLOR_ROOM_OUTLINE = "#444444"
    COLOR_WALL_SEGMENTS = "#000000"
    COLOR_OBJECTS = "#8888ff"
    COLOR_DOORS = "#22aa55"
    COLOR_WINDOWS = "#1f77b4"
    COLOR_LABEL = "#222222"
    COLOR_CENTER_A = "#d62728"
    COLOR_CENTER_B = "#9467bd"
    COLOR_PAIR_LINE = "#111111"

    LW_ROOM_OUTLINE = 1.8
    LW_WALL_SEGMENTS = 3.0
    LW_OBJECTS = 1.8
    LW_DOORS = 2.2
    LW_WINDOWS = 2.2
    LW_PAIR_LINE = 2.2

    MARKER_SIZE = 30
    LABEL_FONT = 8
    LABEL_BBOX = dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.8)

    # ---------- prepare output path ----------
    out_path = Path(out_dir) / f"{layout_id}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # ---------- unpack data ----------
    room_boundary = data.get("room_boundary", []) or []
    walls = data.get("walls", []) or []
    openings = data.get("openings", {}) or {}
    windows = openings.get("windows", []) or []
    doors = openings.get("doors", []) or []
    objects = data.get("objects", []) or []
    units = data.get("units") or (data.get("room", {}) or {}).get("units") or ""

    # ---------- gather drawables ----------
    # room outline
    room_np = np.asarray([[p["x"], p["y"]] for p in room_boundary], dtype=float) if room_boundary else None

    # walls segments
    wall_segs = []
    for w in walls:
        s, e = w.get("start"), w.get("end")
        if not s or not e:
            continue
        wall_segs.append([(float(s["x"]), float(s["y"])), (float(e["x"]), float(e["y"]))])

    # polygons + label positions for each group
    def _collect(polys, default_label):
        segs, labels = [], []
        for obj in polys:
            pts = obj.get("points", []) or []
            lbl = obj.get("label", default_label)
            segs.extend(_poly_to_segments(pts, close=True))
            cx, cy = _polygon_centroid_numpy(pts)
            labels.append((lbl, cx, cy))
        return segs, labels

    segs_objects, lbl_objects = _collect(objects, "object")
    segs_doors, lbl_doors = _collect(doors, "door")
    segs_windows, lbl_windows = _collect(windows, "window")

    # ---------- figure ----------
    fig, ax = plt.subplots(figsize=FIG_SIZE, dpi=dpi)

    if room_np is not None and len(room_np):
        ax.plot(room_np[:, 0], room_np[:, 1], color=COLOR_ROOM_OUTLINE, linewidth=LW_ROOM_OUTLINE, linestyle="--", alpha=0.8, label="Room boundary")

    if wall_segs:
        ax.add_collection(LineCollection(wall_segs, linewidths=LW_WALL_SEGMENTS, colors=[COLOR_WALL_SEGMENTS], label="Walls"))

    if segs_objects:
        ax.add_collection(LineCollection(segs_objects, linewidths=LW_OBJECTS, colors=[COLOR_OBJECTS], label="Objects"))

    if segs_doors:
        ax.add_collection(LineCollection(segs_doors, linewidths=LW_DOORS, colors=[COLOR_DOORS], label="Doors"))

    if segs_windows:
        ax.add_collection(LineCollection(segs_windows, linewidths=LW_WINDOWS, colors=[COLOR_WINDOWS], label="Windows"))

    # labels
    for txt, x, y in lbl_doors:
        ax.text(x, y, txt, ha="center", va="center", fontsize=LABEL_FONT, color=COLOR_DOORS, bbox=LABEL_BBOX)
    for txt, x, y in lbl_windows:
        ax.text(x, y, txt, ha="center", va="center", fontsize=LABEL_FONT, color=COLOR_WINDOWS, bbox=LABEL_BBOX)
    for txt, x, y in lbl_objects:
        ax.text(x, y, txt, ha="center", va="center", fontsize=LABEL_FONT, color=COLOR_LABEL, bbox=LABEL_BBOX)

    # ---------- highlight the chosen pair ----------
    ax.scatter([center1[0]], [center1[1]], s=MARKER_SIZE, color=COLOR_CENTER_A, zorder=5)
    ax.scatter([center2[0]], [center2[1]], s=MARKER_SIZE, color=COLOR_CENTER_B, zorder=5)
    ax.plot([center1[0], center2[0]], [center1[1], center2[1]], color=COLOR_PAIR_LINE, linewidth=LW_PAIR_LINE, zorder=4)

    # distance text at midpoint
    mx, my = (center1[0] + center2[0]) / 2.0, (center1[1] + center2[1]) / 2.0
    suffix = f" {units}" if units else ""
    ax.text(mx, my, f"{distance:.2f}{suffix}", ha="center", va="bottom", fontsize=LABEL_FONT, color=COLOR_PAIR_LINE, bbox=LABEL_BBOX)

    # niceties
    ax.set_aspect("equal", adjustable="box")
    handles, labels = ax.get_legend_handles_labels()
    if labels:
        ax.legend(loc="upper right", fontsize=8)

    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")

    ax.grid(True, which="major", linewidth=0.6, alpha=0.7)
    ax.grid(True, which="minor", linewidth=0.3, alpha=0.4)
    from matplotlib.ticker import AutoMinorLocator

    ax.xaxis.set_minor_locator(AutoMinorLocator())
    ax.yaxis.set_minor_locator(AutoMinorLocator())

    plt.tight_layout(pad=0.1)
    plt.savefig(out_path, dpi=dpi, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)

    return str(out_path)


# --- utils.py additions ---
import re
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from shapely.geometry import Polygon, LineString, MultiPolygon
from shapely.ops import unary_union, linemerge, polygonize
from shapely.validation import make_valid


def collect_opening_polygons(data: dict):
    """
    Collect polygons for openings (doors + windows) if they have area.
    Works with the new format under data['openings'].
    """
    openings = data.get("openings", {}) or {}
    windows = openings.get("windows", []) or []
    doors = openings.get("doors", []) or []

    polys = []
    for o in windows + doors:
        pts = o.get("points", []) or []
        if len(pts) < 3:
            continue
        poly = Polygon([(p["x"], p["y"]) for p in pts])
        if poly.is_valid and poly.area > 0:
            polys.append(poly)
    return polys


# Reuse your robust wall→room builder
def build_room_polygon_from_walls(walls):
    segs = []
    for w in walls or []:
        s, e = w.get("start"), w.get("end")
        if not s or not e:
            continue
        p1 = (s["x"], s["y"])
        p2 = (e["x"], e["y"])
        if p1 != p2:
            segs.append(LineString([p1, p2]))

    if not segs:
        return None

    merged = unary_union(segs)
    merged = linemerge(merged)
    faces = list(polygonize(merged))
    if not faces:
        return None

    room_poly = max(faces, key=lambda p: p.area)
    return make_valid(room_poly)


def build_room_polygon(data: dict):
    """
    Prefer 'room_boundary' polygon if present & valid; otherwise polygonize from 'walls'.
    Works with both new format (top-level) and old format (under data['room']).
    """
    # New format
    rb = data.get("room_boundary")
    if rb and len(rb) >= 3:
        pts = [(p["x"], p["y"]) for p in rb]
        poly = Polygon(pts)
        if poly.is_valid and poly.area > 0:
            return make_valid(poly)

    # Old format fallback
    walls = data.get("walls") or (data.get("room", {}) or {}).get("walls") or []
    return build_room_polygon_from_walls(walls)


def collect_occupied_polygons(data: dict, exclude_labels_regex=r"(light|chandelier|fan|pendant)"):
    """
    Returns polygons for *objects* that count as occupied floor area.
    Skips labels that match exclude_labels_regex (ceiling fixtures).
    Does NOT include openings (doors/windows) — those are handled separately.
    """
    ...
    patt = re.compile(exclude_labels_regex, flags=re.IGNORECASE)
    occupied = []
    for obj in data.get("objects", []) or []:
        label = str(obj.get("label", ""))
        if patt.search(label or ""):
            # Skip area counting for ceiling fixtures
            continue
        pts = obj.get("points", []) or []
        if len(pts) < 3:
            continue
        coords = [(p["x"], p["y"]) for p in pts]
        poly = Polygon(coords)
        if poly.is_valid and poly.area > 0:
            occupied.append(make_valid(poly))
    return occupied


def _draw_room_walls(ax, data: dict):
    # room boundary
    rb = data.get("room_boundary") or []
    if rb:
        rb_xy = np.array([[p["x"], p["y"]] for p in rb], dtype=float)
        ax.plot(rb_xy[:, 0], rb_xy[:, 1], "--", color="#444444", linewidth=1.6, alpha=0.8, label="Room boundary")

    # walls
    walls = data.get("walls") or (data.get("room", {}) or {}).get("walls") or []
    wall_segs = []
    for w in walls:
        s, e = w.get("start"), w.get("end")
        if not s or not e:
            continue
        wall_segs.append([(float(s["x"]), float(s["y"])), (float(e["x"]), float(e["y"]))])
    if wall_segs:
        ax.add_collection(LineCollection(wall_segs, linewidths=2.2, colors=["#000000"], label="Walls"))


def _fill_multipolygon(ax, geom, facecolor="#69d26f", edgecolor="none", alpha=0.35, lw=0.0):
    """
    Fill a Polygon/MultiPolygon on a matplotlib Axes.
    """

    def _fill_poly(poly):
        x, y = poly.exterior.xy
        ax.fill(x, y, facecolor=facecolor, edgecolor=edgecolor, alpha=alpha, linewidth=lw)
        # holes as cutouts (optional: draw with white fill)
        for ring in poly.interiors:
            hx, hy = ring.xy
            ax.fill(hx, hy, facecolor="white", edgecolor="none", alpha=1.0)

    if geom.is_empty:
        return
    if isinstance(geom, (MultiPolygon,)):
        for p in geom.geoms:
            _fill_poly(p)
    else:
        _fill_poly(geom)


def render_free_space_green(data: dict, free_geom, out_dir: str, layout_id, dpi: int = 150):
    """
    Render the room (boundary + walls) and fill the 'free space' geometry in green.
    Saves to {out_dir}/{layout_id}.png
    """
    out_path = Path(out_dir) / f"{layout_id}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7.5, 7.5), dpi=dpi)
    _draw_room_walls(ax, data)
    _fill_multipolygon(ax, free_geom, facecolor="#7CFC00", alpha=0.45)  # lawn green-ish

    ax.set_aspect("equal", adjustable="box")

    # Axes + grid
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")

    # major + minor grid; minor helps with fine layout inspection
    ax.grid(True, which="major", linewidth=0.6, alpha=0.7)
    ax.grid(True, which="minor", linewidth=0.3, alpha=0.4)
    from matplotlib.ticker import AutoMinorLocator

    ax.xaxis.set_minor_locator(AutoMinorLocator())
    ax.yaxis.set_minor_locator(AutoMinorLocator())

    plt.tight_layout(pad=0.1)
    plt.savefig(out_path, dpi=dpi, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)

    return str(out_path)


# --- utils.py (additions) ---
import math
from typing import List, Tuple, Optional, Dict
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from shapely.geometry import Polygon as ShpPolygon, MultiPolygon, LineString
from shapely.ops import unary_union, linemerge, polygonize
from shapely.validation import make_valid

# You already have:
# - build_room_polygon(data)
# - collect_occupied_polygons(data, exclude_labels_regex)
# - collect_opening_polygons(data)
# - render_free_space_green(...)
# Optionally also keep _fill_multipolygon, _draw_room_walls from earlier.


# ----------------------------
# Obstacle collection (new-format aware)
# ----------------------------
def is_rug_label(label: str) -> bool:
    keywords = ["rug", "carpet", "mat", "doormat", "runner"]
    label_lc = (label or "").lower()
    return any(k in label_lc for k in keywords)


def is_light_label(label: str) -> bool:
    keywords = ["light", "chandelier", "fan", "pendant"]
    label_lc = (label or "").lower()
    return any(k in label_lc for k in keywords)


def _label(o: Dict) -> str:
    return (o.get("label") or o.get("name") or "").strip().lower()


def collect_obstacle_polygons_for_maxbox(data: dict, exclude_ceiling_regex: str = r"(light|chandelier|fan|pendant)") -> List[ShpPolygon]:
    """Objects (excluding rugs and ceiling fixtures) + openings (doors/windows)."""
    from shapely.geometry import Polygon
    import re

    patt = re.compile(exclude_ceiling_regex, flags=re.IGNORECASE)

    polys: List[ShpPolygon] = []

    # objects
    for obj in data.get("objects", []) or []:
        lbl = obj.get("label", "") or ""
        if is_rug_label(lbl) or patt.search(lbl):
            continue
        pts = obj.get("points", []) or []
        if len(pts) < 3:
            continue
        P = Polygon([(p["x"], p["y"]) for p in pts])
        if P.is_valid and P.area > 0:
            polys.append(make_valid(P))

    # openings
    openings = data.get("openings", {}) or {}
    for o in (openings.get("doors", []) or []) + (openings.get("windows", []) or []):
        pts = o.get("points", []) or []
        if len(pts) < 3:
            continue
        P = Polygon([(p["x"], p["y"]) for p in pts])
        if P.is_valid and P.area > 0:
            polys.append(make_valid(P))

    return polys


# ----------------------------
# Rotation helpers
# ----------------------------
def _rot2d(xy: np.ndarray, theta: float) -> np.ndarray:
    """Rotate Nx2 array by angle theta (radians) around origin."""
    c, s = math.cos(theta), math.sin(theta)
    R = np.array([[c, -s], [s, c]], dtype=float)
    return xy @ R.T


def _polygon_to_np(poly: ShpPolygon) -> np.ndarray:
    return np.asarray(poly.exterior.coords, dtype=float)[:, :2]


# def _rect_to_polygon(rect: Tuple[float, float, float, float]) -> ShpPolygon:
#     x1, y1, x2, y2 = rect
#     return ShpPolygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2)])

# utils.py
from shapely.geometry import box
from shapely.prepared import prep


def _rect_to_polygon(rect: Tuple[float, float, float, float]) -> ShpPolygon:
    x1, y1, x2, y2 = rect
    # box() is a C-optimized fast path
    return box(x1, y1, x2, y2)


def _poly_from_np(xy: np.ndarray) -> ShpPolygon:
    return ShpPolygon(xy)


def _rotate_polygon(poly: ShpPolygon, theta: float) -> ShpPolygon:
    xy = _polygon_to_np(poly)
    rxy = _rot2d(xy, theta)
    return _poly_from_np(rxy)


def _rotate_rect(rect: Tuple[float, float, float, float], theta: float) -> ShpPolygon:
    """Return oriented polygon by rotating an axis-aligned rect around origin by theta."""
    return _rotate_polygon(_rect_to_polygon(rect), theta)


# ----------------------------
# Candidate angles
# ----------------------------
def _angles_from_edges(polys: List[ShpPolygon]) -> List[float]:
    """Collect unique edge directions (0..pi) from polygons."""
    angs = set()
    for P in polys:
        coords = np.asarray(P.exterior.coords, dtype=float)[:, :2]
        for i in range(len(coords) - 1):
            v = coords[i + 1] - coords[i]
            if np.allclose(v, 0):
                continue
            a = math.atan2(v[1], v[0])
            # normalize to [0, pi)
            a = a % math.pi
            # snap to a small grid to dedup numerically
            angs.add(round(a, 10))
    return sorted(angs)


# ----------------------------
# Axis-aligned solver (same idea as yours), now as util
# ----------------------------
class _Rect:
    __slots__ = ("x1", "y1", "x2", "y2")

    def __init__(self, x1, y1, x2, y2):
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2

    @property
    def area(self):
        return max(0.0, self.x2 - self.x1) * max(0.0, self.y2 - self.y1)


# utils.py
def _largest_empty_rectangle_axis_aligned(
    room_polygon: ShpPolygon,
    obstacle_polys: List[ShpPolygon],
    min_size: float = 0.01,
    snap: float = 1e-3,  # snap coords to reduce duplicates
    max_grid: int = 2500,  # cap |xs|*|ys| to avoid O(n^4) blowups
    thin_stride: int = 2,  # when capping, sample every k-th coordinate
    *,
    verbose: bool = True,
    report_every: int = 20000,  # print every N rectangles scanned
    progress_prefix: str = "",
) -> Tuple[_Rect, float]:
    """
    Faster axis-aligned search with:
      - snapped coordinate buckets
      - prepared geometries
      - optional grid thinning when grid too dense
      - progress printing (angle-aware)
    """
    from shapely.geometry import box
    from shapely.prepared import prep
    import time

    t0 = time.perf_counter()

    def _sn(v):
        return float(np.round(v / snap) * snap)

    minx, miny, maxx, maxy = room_polygon.bounds

    xs = {_sn(minx), _sn(maxx)}
    ys = {_sn(miny), _sn(maxy)}

    rx, ry = zip(*list(room_polygon.exterior.coords))
    xs.update(_sn(x) for x in rx)
    ys.update(_sn(y) for y in ry)

    for poly in obstacle_polys:
        bx1, by1, bx2, by2 = poly.bounds
        xs.update((_sn(bx1), _sn(bx2)))
        ys.update((_sn(by1), _sn(by2)))

    xs = sorted(xs)
    ys = sorted(ys)
    combos = len(xs) * len(ys)
    if verbose:
        print(f"{progress_prefix}grid pre-thin: |xs|={len(xs)}, |ys|={len(ys)}, combos≈{combos}")

    # If the grid is still huge, thin it deterministically
    if combos > max_grid:
        xs = xs[::thin_stride] + ([xs[-1]] if xs[-1] != xs[::thin_stride][-1] else [])
        ys = ys[::thin_stride] + ([ys[-1]] if ys[-1] != ys[::thin_stride][-1] else [])
        if verbose:
            print(f"{progress_prefix}grid post-thin: |xs|={len(xs)}, |ys|={len(ys)}, combos≈{len(xs)*len(ys)} (stride={thin_stride})")

    best = _Rect(0, 0, 0, 0)
    best_area = 0.0

    room_prep = prep(room_polygon)
    merged_obs = unary_union(obstacle_polys) if obstacle_polys else None
    merged_prep = prep(merged_obs) if merged_obs else None

    checked = 0
    last_print = t0

    for i, x1 in enumerate(xs):
        for x2 in xs[i + 1 :]:
            if (x2 - x1) <= min_size:
                continue
            for j, y1 in enumerate(ys):
                for y2 in ys[j + 1 :]:
                    if (y2 - y1) <= min_size:
                        continue

                    area = (x2 - x1) * (y2 - y1)
                    if area <= best_area:
                        continue

                    Rpoly = box(x1, y1, x2, y2)

                    # Inside room (allow boundary touch)
                    if not room_prep.contains(Rpoly) and not room_polygon.covers(Rpoly):
                        continue

                    # Avoid obstacles
                    if merged_prep and not Rpoly.disjoint(merged_obs):
                        continue

                    best = _Rect(x1, y1, x2, y2)
                    best_area = area

                    # progress logging throttled on improvements too
                    checked += 1
                    if verbose and (checked % report_every == 0 or (time.perf_counter() - last_print) > 2.0):
                        print(f"{progress_prefix}…checked={checked:,} best_area={best_area:.3f}")
                        last_print = time.perf_counter()

                # also count the inner loop iterations for progress ticks
                checked += max(0, len(ys) - (j + 1))

    if verbose:
        dt = time.perf_counter() - t0
        print(f"{progress_prefix}done in {dt:.2f}s, total checks≈{checked:,}, best_area={best_area:.3f}")

    return best, best_area


# ----------------------------
# Any-angle (rotated) solver
# ----------------------------
def largest_empty_rectangle_any_angle(
    room_polygon: ShpPolygon, obstacle_polys: List[ShpPolygon], extra_angles_deg: Optional[List[float]] = None, min_size: float = 0.01
) -> Tuple[ShpPolygon, float, float]:
    """
    Try best axis-aligned rectangle across multiple rotations (edge-driven + optional).
    Returns (oriented_rectangle_polygon, area, angle_radians).
    Angle is the rotation applied to the scene (i.e., rectangle’s orientation).
    """
    # candidate angles from geometry
    angs = set(_angles_from_edges([room_polygon] + obstacle_polys))
    # add their perpendiculars
    for a in list(angs):
        angs.add(round((a + math.pi / 2) % math.pi, 10))
    # optional extras
    if extra_angles_deg:
        for d in extra_angles_deg:
            a = math.radians(d) % math.pi
            angs.add(round(a, 10))

    best_poly = None
    best_area = 0.0
    best_angle = 0.0

    # rotate scene by -theta, solve axis-aligned, rotate result back by +theta
    for a in sorted(angs):
        theta = -a  # rotate scene so candidate edges align to axis

        Rroom = _rotate_polygon(room_polygon, theta)
        Robs = [_rotate_polygon(p, theta) for p in obstacle_polys]

        rect_axis, area = _largest_empty_rectangle_axis_aligned(Rroom, Robs, min_size=min_size)
        if area <= best_area:
            continue

        # rotate back the found axis-aligned rect
        rect_poly = _rotate_rect((rect_axis.x1, rect_axis.y1, rect_axis.x2, rect_axis.y2), -theta)
        best_poly, best_area, best_angle = rect_poly, area, (a % math.pi)

    return best_poly, best_area, best_angle


# ----------------------------
# Rendering
# ----------------------------
def render_max_box(
    data: dict,
    room_polygon: ShpPolygon,
    obstacles: List[ShpPolygon],
    obox: ShpPolygon,  # oriented rectangle polygon
    out_path: str,
    dpi: int = 150,
) -> str:
    """Draw room, walls, all objects/openings outlines, and the max box (bold)."""
    from pathlib import Path

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    # colors / styles
    COL_ROOM = "#444444"
    COL_WALL = "#000000"
    COL_OBJ = "#8888ff"
    COL_DOOR = "#22aa55"
    COL_WIN = "#1f77b4"
    COL_BOX = "#e74c3c"

    fig, ax = plt.subplots(figsize=(8, 8), dpi=dpi)

    # room boundary (prefer provided; else derived walls)
    rb = data.get("room_boundary") or []
    if rb:
        rb_xy = np.array([[p["x"], p["y"]] for p in rb], dtype=float)
        ax.plot(rb_xy[:, 0], rb_xy[:, 1], "--", color=COL_ROOM, linewidth=1.6, alpha=0.8, label="Room boundary")

    # walls
    walls = data.get("walls") or (data.get("room", {}) or {}).get("walls") or []
    wall_segs = []
    for w in walls:
        s, e = w.get("start"), w.get("end")
        if s and e:
            wall_segs.append([(float(s["x"]), float(s["y"])), (float(e["x"]), float(e["y"]))])
    if wall_segs:
        ax.add_collection(LineCollection(wall_segs, linewidths=2.2, colors=[COL_WALL], label="Walls"))

    # outlines: objects
    for obj in data.get("objects", []) or []:
        pts = obj.get("points", []) or []
        if len(pts) >= 2:
            xs = [p["x"] for p in pts]
            ys = [p["y"] for p in pts]
            if len(pts) >= 3:
                xs += [pts[0]["x"]]
                ys += [pts[0]["y"]]
            ax.plot(xs, ys, color=COL_OBJ, linewidth=1.4, alpha=0.9)

    # outlines: openings
    openings = data.get("openings", {}) or {}
    for group, col in (("doors", COL_DOOR), ("windows", COL_WIN)):
        for o in openings.get(group, []) or []:
            pts = o.get("points", []) or []
            if len(pts) >= 2:
                xs = [p["x"] for p in pts]
                ys = [p["y"] for p in pts]
                if len(pts) >= 3:
                    xs += [pts[0]["x"]]
                    ys += [pts[0]["y"]]
                ax.plot(xs, ys, color=col, linewidth=1.6, alpha=1.0)

    # oriented rectangle
    if obox and not obox.is_empty:
        x, y = obox.exterior.xy
        ax.plot(x, y, color=COL_BOX, linewidth=3.0, alpha=0.95, label="Max box")

    ax.set_aspect("equal", adjustable="box")
    h, l = ax.get_legend_handles_labels()
    if l:
        ax.legend(loc="upper right", fontsize=8)

    # Axes + grid
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")

    ax.grid(True, which="major", linewidth=0.6, alpha=0.7)
    ax.grid(True, which="minor", linewidth=0.3, alpha=0.4)
    from matplotlib.ticker import AutoMinorLocator

    ax.xaxis.set_minor_locator(AutoMinorLocator())
    ax.yaxis.set_minor_locator(AutoMinorLocator())

    plt.tight_layout(pad=0.1)
    layout_id = data["layout_id"]
    out_path = Path(out_path) / f"{layout_id}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=dpi, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)

    return out_path


# --- utils.py: fast approximate max box ---
import math, random, time
from typing import List, Tuple, Optional
import numpy as np
from shapely.geometry import Polygon as ShpPolygon, Point, box
from shapely.ops import unary_union
from shapely.prepared import prep


def _rot_mat(theta: float):
    c, s = math.cos(theta), math.sin(theta)
    return np.array([[c, -s], [s, c]], dtype=float)


def _rect_poly(center: Tuple[float, float], w: float, h: float, theta: float) -> ShpPolygon:
    """Rectangle polygon centered at center, width w, height h, rotated by theta."""
    cx, cy = center
    hw, hh = 0.5 * w, 0.5 * h
    local = np.array([[-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh]], dtype=float)
    R = _rot_mat(theta)
    pts = (local @ R.T) + np.array([cx, cy])
    return ShpPolygon(pts)


def _grow_axis(
    prep_space,
    free_space,  # shapely geometry for covers()
    fs_bounds,  # free_space.bounds
    center,
    theta,
    w0,
    h0,
    w_max,
    h_max,
    *,
    tol: float = 1e-3,  # 1 mm tightness
    allow_touch: bool = True,
    clearance: float = 0.0,  # >0 leaves a deliberate gap
    max_passes: int = 50,  # coordinate-ascent passes (w/h alternation)
    time_budget_s: float | None = None,
    t_start: float | None = None,
) -> tuple[float, float]:
    """
    Coordinate-ascent grow with robust binary searches to the global caps.
    This version eliminates large "gaps" by not capping binary search at 2×.
    """
    import time

    if t_start is None:
        t_start = time.perf_counter()

    fs_minx, fs_miny, fs_maxx, fs_maxy = fs_bounds

    # Effective free-space if a clearance is requested
    eff_space = free_space.buffer(-clearance) if clearance > 0 else free_space
    eff_prep = prep_space if clearance == 0 else shapely.prepared.prep(eff_space)

    def ok(W: float, H: float) -> bool:
        if W <= 0.0 or H <= 0.0:
            return False
        poly = _rect_poly(center, W, H, theta)

        # cheap bbox gate (allow equality for touching)
        minx, miny, maxx, maxy = poly.bounds
        if minx < fs_minx or miny < fs_miny or maxx > fs_maxx or maxy > fs_maxy:
            return False

        # inside free space (prepared fast path)
        if eff_prep.contains(poly):
            return True
        # allow touching boundaries
        return allow_touch and eff_space.covers(poly)

    def grow_one_dim(cur, cap, other, grow_width: bool) -> float:
        """Grow one dimension with (1) exponential scout then (2) bsearch up to 'cap'."""
        val = min(max(cur, 1e-9), cap)

        # (1) exponential scout (bounded steps)
        for _ in range(64):
            cand = min(val * 2.0, cap)
            good = ok(cand, other) if grow_width else ok(other, cand)
            if good and cand > val + tol:
                val = cand
                if time_budget_s and (time.perf_counter() - t_start) > time_budget_s:
                    return val
            else:
                break

        # (2) binary search all the way to the global cap
        lo, hi = val, cap
        # If we already know 'cap' fails, shrink hi to a failing bound quickly.
        if not (ok(hi, other) if grow_width else ok(other, hi)):
            # shrink until failure bracketed
            # (keep hi failing, lo passing)
            # try a quick step back from cap to find a passing point
            # if none found, keep current 'val' as lo
            pass
        # Now search [lo, hi] to within tol
        for _ in range(64):
            if (hi - lo) <= tol:
                break
            mid = 0.5 * (lo + hi)
            good = ok(mid, other) if grow_width else ok(other, mid)
            if good:
                lo = mid
            else:
                hi = mid
            if time_budget_s and (time.perf_counter() - t_start) > time_budget_s:
                break

        # micro "edge hug" nudges
        val = lo
        step = tol * 0.5
        for _ in range(10):
            cand = min(val + step, cap)
            good = ok(cand, other) if grow_width else ok(other, cand)
            if good and cand > val:
                val = cand
            else:
                break
        return val

    # init sizes
    w = min(max(w0, 1e-6), w_max)
    h = min(max(h0, 1e-6), h_max)

    prev_area = 0.0
    for _ in range(max_passes):
        # grow width keeping height fixed
        w = grow_one_dim(w, w_max, h, grow_width=True)
        # grow height keeping new width
        h = grow_one_dim(h, h_max, w, grow_width=False)

        area = w * h
        if area <= prev_area + max(1e-6, tol * tol):  # converged
            break
        prev_area = area

        if time_budget_s and (time.perf_counter() - t_start) > time_budget_s:
            break

    return w, h


def largest_empty_rectangle_fast_approx(
    room_polygon: ShpPolygon,
    obstacle_polys: List[ShpPolygon],
    *,
    n_starts: int = 200,  # lowered default for speed
    n_angles: int = 24,  # lowered default; still good coverage
    start_size: float = 0.1,
    max_expand: float = 50.0,
    time_budget_s: Optional[float] = 1.5,  # overall time cap per layout
    rng_seed: int = 42,
) -> Tuple[ShpPolygon, float, float]:
    rng = random.Random(rng_seed)

    free_space = room_polygon
    if obstacle_polys:
        merged = unary_union(obstacle_polys)
        inter = room_polygon.intersection(merged)
        if not inter.is_empty:
            free_space = room_polygon.difference(merged)

    if free_space.is_empty:
        return ShpPolygon(), 0.0, 0.0

    prep_space = prep(free_space)

    # candidate angles
    angles = [i * math.pi / n_angles for i in range(n_angles)]

    # bounds for cheap rejects and global caps
    fs_bounds = free_space.bounds
    minx, miny, maxx, maxy = fs_bounds
    w_cap = min(max_expand, maxx - minx)
    h_cap = min(max_expand, maxy - miny)

    best_poly = None
    best_area = 0.0
    best_theta = 0.0

    t0 = time.perf_counter()

    def over_budget():
        return time_budget_s and (time.perf_counter() - t0) > time_budget_s

    # seed sampler
    def sample_point(max_tries=400):
        for _ in range(max_tries):
            x = rng.uniform(minx, maxx)
            y = rng.uniform(miny, maxy)
            p = Point(x, y)
            if prep_space.contains(p):
                return (x, y)
        rp = free_space.representative_point()
        return (float(rp.x), float(rp.y))

    for _ in range(n_starts):
        if over_budget():
            break
        c = sample_point()
        w0 = start_size * (0.5 + rng.random())
        h0 = start_size * (0.5 + rng.random())

        angs = angles[:]
        rng.shuffle(angs)
        angs = angs[: max(8, n_angles // 2)]  # subset per seed

        for theta in angs:
            if over_budget():
                break
            # inside largest_empty_rectangle_fast_approx, per (seed center c, angle theta):
            poly, area = _largest_box_asymmetric_about_seed(
                prep_space=prep_space,
                free_space=free_space,
                fs_bounds=fs_bounds,
                center=c,
                theta=theta,
                aL0=start_size * 0.5,
                aR0=start_size * 1.5,  # different starts encourage asymmetry
                bD0=start_size * 0.5,
                bU0=start_size * 1.5,
                aL_cap=w_cap,
                aR_cap=w_cap,
                bD_cap=h_cap,
                bU_cap=h_cap,
                tol=1e-3,
                allow_touch=True,
                time_budget_s=(time_budget_s * 0.9 if time_budget_s else None),
                t_start=t0,
            )
            if area > best_area:
                best_area, best_theta, best_poly = area, theta, poly

    if best_poly is None:
        return ShpPolygon(), 0.0, 0.0
    return best_poly, best_area, best_theta


# utils.py — add asymmetric rectangle builder
def _rect_poly_halves(center, aL, aR, bD, bU, theta):
    import numpy as np, math

    cx, cy = center
    c, s = math.cos(theta), math.sin(theta)
    ux = np.array([c, s])  # local +x
    uy = np.array([-s, c])  # local +y
    # vertices in local half-extent coords:
    P = np.array(
        [
            [-aL, -bD],
            [+aR, -bD],
            [+aR, +bU],
            [-aL, +bU],
        ],
        dtype=float,
    )
    R = np.array([[c, -s], [s, c]], dtype=float)
    pts = (P @ R.T) + np.array([cx, cy])
    from shapely.geometry import Polygon as ShpPolygon

    return ShpPolygon(pts)


def _largest_box_asymmetric_about_seed(
    prep_space,
    free_space,
    fs_bounds,
    center,
    theta,
    aL0=0.1,
    aR0=0.1,
    bD0=0.1,
    bU0=0.1,
    aL_cap=50.0,
    aR_cap=50.0,
    bD_cap=50.0,
    bU_cap=50.0,
    tol=1e-3,
    allow_touch=True,
    time_budget_s=None,
    t_start=None,
):
    import time

    if t_start is None:
        t_start = time.perf_counter()
    fs_minx, fs_miny, fs_maxx, fs_maxy = fs_bounds

    def ok(aL, aR, bD, bU):
        poly = _rect_poly_halves(center, aL, aR, bD, bU, theta)
        minx, miny, maxx, maxy = poly.bounds
        if minx < fs_minx or miny < fs_miny or maxx > fs_maxx or maxy > fs_maxy:
            return False
        if prep_space.contains(poly):
            return True
        return allow_touch and free_space.covers(poly)

    def grow_half(val, cap, other_triplet, side):
        # side in {"aL","aR","bD","bU"}
        # exponential then bsearch up to cap with tol
        import time

        lo = max(1e-9, min(val, cap))
        # scout
        for _ in range(48):
            cand = min(lo * 2.0, cap)
            if side == "aL":
                good = ok(cand, *other_triplet)
            elif side == "aR":
                good = ok(other_triplet[0], cand, other_triplet[1], other_triplet[2])
            elif side == "bD":
                good = ok(other_triplet[0], other_triplet[1], cand, other_triplet[2])
            else:
                good = ok(other_triplet[0], other_triplet[1], other_triplet[2], cand)
            if good and cand > lo + tol:
                lo = cand
            else:
                break
            if time_budget_s and (time.perf_counter() - t_start) > time_budget_s:
                return lo
        hi = cap
        for _ in range(48):
            if (hi - lo) <= tol:
                break
            mid = 0.5 * (lo + hi)
            if side == "aL":
                good = ok(mid, *other_triplet)
            elif side == "aR":
                good = ok(other_triplet[0], mid, other_triplet[1], other_triplet[2])
            elif side == "bD":
                good = ok(other_triplet[0], other_triplet[1], mid, other_triplet[2])
            else:
                good = ok(other_triplet[0], other_triplet[1], other_triplet[2], mid)
            if good:
                lo = mid
            else:
                hi = mid
            if time_budget_s and (time.perf_counter() - t_start) > time_budget_s:
                break
        return lo

    aL, aR, bD, bU = aL0, aR0, bD0, bU0
    prev_area = -1.0
    for _ in range(8):  # a few coordinate-ascent passes
        # grow each side independently while holding the others
        aL = grow_half(aL, aL_cap, (aR, bD, bU), "aL")
        aR = grow_half(aR, aR_cap, (aL, bD, bU), "aR")
        bD = grow_half(bD, bD_cap, (aL, aR, bU), "bD")
        bU = grow_half(bU, bU_cap, (aL, aR, bD), "bU")
        area = (aL + aR) * (bD + bU)
        if area <= prev_area + max(1e-6, tol * tol):
            break
        prev_area = area
        if time_budget_s and (time.perf_counter() - t_start) > time_budget_s:
            break

    poly = _rect_poly_halves(center, aL, aR, bD, bU, theta)
    return poly, (aL + aR) * (bD + bU)


def _largest_box_asymmetric_about_seed_wh(
    prep_space,
    free_space,
    fs_bounds,
    center,
    theta,
    aL0=0.1,
    aR0=0.1,
    bD0=0.1,
    bU0=0.1,
    aL_cap=50.0,
    aR_cap=50.0,
    bD_cap=50.0,
    bU_cap=50.0,
    tol=1e-3,
    allow_touch=True,
    time_budget_s=None,
    t_start=None,
):
    import time

    if t_start is None:
        t_start = time.perf_counter()
    fs_minx, fs_miny, fs_maxx, fs_maxy = fs_bounds

    def ok(aL, aR, bD, bU):
        poly = _rect_poly_halves(center, aL, aR, bD, bU, theta)
        minx, miny, maxx, maxy = poly.bounds
        if minx < fs_minx or miny < fs_miny or maxx > fs_maxx or maxy > fs_maxy:
            return False
        if prep_space.contains(poly):
            return True
        return allow_touch and free_space.covers(poly)

    def grow_half(val, cap, other_triplet, side):
        # side in {"aL","aR","bD","bU"}
        # exponential then bsearch up to cap with tol
        import time

        lo = max(1e-9, min(val, cap))
        # scout
        for _ in range(48):
            cand = min(lo * 2.0, cap)
            if side == "aL":
                good = ok(cand, *other_triplet)
            elif side == "aR":
                good = ok(other_triplet[0], cand, other_triplet[1], other_triplet[2])
            elif side == "bD":
                good = ok(other_triplet[0], other_triplet[1], cand, other_triplet[2])
            else:
                good = ok(other_triplet[0], other_triplet[1], other_triplet[2], cand)
            if good and cand > lo + tol:
                lo = cand
            else:
                break
            if time_budget_s and (time.perf_counter() - t_start) > time_budget_s:
                return lo
        hi = cap
        for _ in range(48):
            if (hi - lo) <= tol:
                break
            mid = 0.5 * (lo + hi)
            if side == "aL":
                good = ok(mid, *other_triplet)
            elif side == "aR":
                good = ok(other_triplet[0], mid, other_triplet[1], other_triplet[2])
            elif side == "bD":
                good = ok(other_triplet[0], other_triplet[1], mid, other_triplet[2])
            else:
                good = ok(other_triplet[0], other_triplet[1], other_triplet[2], mid)
            if good:
                lo = mid
            else:
                hi = mid
            if time_budget_s and (time.perf_counter() - t_start) > time_budget_s:
                break
        return lo

    aL, aR, bD, bU = aL0, aR0, bD0, bU0
    prev_area = -1.0
    for _ in range(8):  # a few coordinate-ascent passes
        # grow each side independently while holding the others
        aL = grow_half(aL, aL_cap, (aR, bD, bU), "aL")
        aR = grow_half(aR, aR_cap, (aL, bD, bU), "aR")
        bD = grow_half(bD, bD_cap, (aL, aR, bU), "bD")
        bU = grow_half(bU, bU_cap, (aL, aR, bD), "bU")
        area = (aL + aR) * (bD + bU)
        if area <= prev_area + max(1e-6, tol * tol):
            break
        prev_area = area
        if time_budget_s and (time.perf_counter() - t_start) > time_budget_s:
            break

    poly = _rect_poly_halves(center, aL, aR, bD, bU, theta)
    return poly, (aL + aR), (bD + bU)


# filepath: src/qa_pairs_generation/utils.py
import os
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection


def render_visibility_path(
    data: dict,
    room_polygon,  # shapely Polygon or None (used for bounds)
    obstacles,  # list[shapely Polygon] for objects (visual only)
    path_xy,  # list[(x,y)]
    start_pt,  # (x,y) or None
    goal_pt,  # (x,y) or None
    out_path: str,
    *,
    title: str | None = None,
    show_grid: bool = True,
    show_axes: bool = True,
    dpi: int = 150,
    objects: list | None = None,
    start_label: str | None = None,
    goal_label: str | None = None,
    vis_graph: dict | None = None,  # {node: {neighbor: dist}}
) -> str:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    # colors
    COL_ROOM_OUTLINE = "#444444"
    COL_WALLS = "#000000"
    COL_WINDOW = "#1f77b4"
    COL_DOOR = "#22aa55"
    COL_OBJ_FILL = "#b0b0b0"
    COL_OBJ_EDGE = "#7e7e7e"
    COL_START_POLY = "#2ecc71"
    COL_GOAL_POLY = "#1f77b4"
    COL_PATH = "#e74c3c"
    COL_START = "#2ecc71"
    COL_GOAL = "#1f77b4"
    COL_GRAPH_EDGE = "#8aa4c0"
    COL_GRAPH_NODE = "#6787a7"

    fig, ax = plt.subplots(figsize=(8, 8), dpi=dpi)

    # --- room boundary (dashed) ---
    rb = data.get("room_boundary") or []
    if rb:
        rb_xy = np.array([[p["x"], p["y"]] for p in rb], dtype=float)
        ax.plot(rb_xy[:, 0], rb_xy[:, 1], "--", color=COL_ROOM_OUTLINE, linewidth=1.6, alpha=0.9, label="Room boundary")

    # --- walls (solid thick) ---
    wall_segs = []
    for w in data.get("walls") or (data.get("room", {}) or {}).get("walls") or []:
        s, e = w.get("start"), w.get("end")
        if s and e:
            wall_segs.append([(float(s["x"]), float(s["y"])), (float(e["x"]), float(e["y"]))])
    if wall_segs:
        ax.add_collection(LineCollection(wall_segs, linewidths=2.5, colors=[COL_WALLS], label="Walls"))

    # --- openings: windows & doors (draw polygons) ---
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

    # --- all object polygons (context) ---
    objs = objects or (data.get("objects") or [])
    for o in objs:
        pts = o.get("points") or []
        if len(pts) >= 3:
            xy = np.array([[p["x"], p["y"]] for p in pts], dtype=float)
            ax.fill(xy[:, 0], xy[:, 1], facecolor=COL_OBJ_FILL, edgecolor=COL_OBJ_EDGE, alpha=0.35, linewidth=1.0)

    # --- start/goal polygons highlighted ---
    def _match(objs, name):
        name = (name or "").lower()
        out = []
        for o in objs:
            lab = (o.get("label") or o.get("name") or "").strip().lower()
            if lab == name and len(o.get("points") or []) >= 3:
                arr = np.array([[p["x"], p["y"]] for p in o["points"]], dtype=float)
                out.append(arr)
        return out

    for arr in _match(objs, start_label):
        ax.fill(arr[:, 0], arr[:, 1], facecolor=COL_START_POLY, edgecolor=COL_START_POLY, alpha=0.30, linewidth=1.4, label="Start object")
    for arr in _match(objs, goal_label):
        ax.fill(arr[:, 0], arr[:, 1], facecolor=COL_GOAL_POLY, edgecolor=COL_GOAL_POLY, alpha=0.30, linewidth=1.4, label="Target object")

    # --- connectivity graph (pale) ---
    if vis_graph:
        edges = []
        nx, ny = [], []
        for a, nbrs in vis_graph.items():
            ax_, ay_ = a
            nx.append(ax_)
            ny.append(ay_)
            for b in nbrs.keys():
                edges.append([(ax_, ay_), (b[0], b[1])])
        if edges:
            ax.add_collection(LineCollection(edges, linewidths=1.0, colors=[COL_GRAPH_EDGE], alpha=0.35, zorder=1, label="Visibility graph"))
        if nx:
            ax.scatter(nx, ny, s=8, c=COL_GRAPH_NODE, alpha=0.7, zorder=2)

    # --- shortest path ---
    if path_xy:
        xs = [p[0] for p in path_xy]
        ys = [p[1] for p in path_xy]
        ax.plot(xs, ys, "-", color=COL_PATH, linewidth=2.8, zorder=4, label="Path")

    # --- start/goal markers ---
    if start_pt:
        ax.plot(start_pt[0], start_pt[1], "o", color=COL_START, markersize=6, zorder=5, label="Start")
    if goal_pt:
        ax.plot(goal_pt[0], goal_pt[1], "*", color=COL_GOAL, markersize=10, zorder=5, label="Goal")

    # bounds from everything we drew
    xs, ys = [], []
    if rb:
        xs += rb_xy[:, 0].tolist()
        ys += rb_xy[:, 1].tolist()
    for (x1, y1), (x2, y2) in wall_segs:
        xs += [x1, x2]
        ys += [y1, y2]
    for ent in openings.get("windows") or []:
        for p in ent.get("points") or []:
            xs.append(p["x"])
            ys.append(p["y"])
    for ent in openings.get("doors") or []:
        for p in ent.get("points") or []:
            xs.append(p["x"])
            ys.append(p["y"])
    for o in objs:
        for p in o.get("points") or []:
            xs.append(p["x"])
            ys.append(p["y"])
    if path_xy:
        xs += [p[0] for p in path_xy]
        ys += [p[1] for p in path_xy]
    if start_pt:
        xs.append(start_pt[0])
        ys.append(start_pt[1])
    if goal_pt:
        xs.append(goal_pt[0])
        ys.append(goal_pt[1])
    if (not xs) and room_polygon is not None:
        bx, by = room_polygon.exterior.xy
        xs += list(bx)
        ys += list(by)

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
    if title:
        ax.set_title(title, fontsize=11)

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
