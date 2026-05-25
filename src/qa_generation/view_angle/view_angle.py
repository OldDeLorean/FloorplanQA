# filepath: src/qa_pairs_generation/alignment/new_alignment.py
import os, json, math
from typing import Dict, List, Tuple, Optional
from functools import partial
import numpy as np
from pathlib import Path
from shapely.geometry import Polygon as ShpPolygon, Point, LineString
from shapely.ops import unary_union, linemerge, polygonize
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


from src.qa_pairs_generation.utils import build_room_polygon, get_polygon_centroid, merge_objects_and_openings, _label, generate_qa_pairs_with_subsampling, save_and_info

# ---------------- helpers ----------------


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


def _norm(v: Tuple[float, float]) -> Tuple[float, float]:
    x, y = v
    m = math.hypot(x, y)
    return (0.0, 0.0) if m == 0 else (x / m, y / m)


def _dot(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1]


def _angle_deg_from_dot(dp: float) -> float:
    dp_clamped = max(min(dp, 1.0), -1.0)
    return math.degrees(math.acos(dp_clamped))


# ---------------- facing strategies ----------------


def facing_vector_north(_: ShpPolygon, __: Tuple[float, float]) -> Tuple[float, float]:
    """Global 'north' = +Y."""
    return (0.0, 1.0)


# ---------------- core computation ----------------


def compute_alignment_new(
    data: Dict,
    reference_label: str,
    target_label: str,
    ref,
    tgt,
    *,
    mode: str = "facing_to_wall",  # or "north"
) -> Tuple[float, float]:
    """
    Returns (dot_product, angle_deg) where:
      - v_dir = normalized vector from reference center to target center
      - v_face = facing vector per mode
    dot = v_face · v_dir; angle = arccos(dot)
    """
    room = build_room_polygon(data)

    ref_cent = get_polygon_centroid(ref["points"])
    tgt_cent = get_polygon_centroid(tgt["points"])
    v_dir = _norm((tgt_cent[0] - ref_cent[0], tgt_cent[1] - ref_cent[1]))

    v_face = facing_vector_north(room, ref_cent)

    dp = _dot(_norm(v_face), v_dir)
    ang = _angle_deg_from_dot(dp)
    return dp, ang


# ---------------- rendering (view angle) ----------------
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from typing import Dict, Tuple, List
from pathlib import Path

# This implementation assumes the helper functions `build_room_polygon`,
# `merge_objects_and_openings`, `_poly`, `_norm`, and `_label` are
# available in the same scope, as they are in the provided file.


# filepath: src/qa_pairs_generation/alignment/new_alignment.py

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from typing import Dict, Tuple, List, Optional
from pathlib import Path
from shapely.geometry import Polygon as ShpPolygon, MultiPolygon, GeometryCollection

# This implementation assumes the other functions from your file like
# `build_room_polygon`, `_poly`, `_norm`, etc., are in the same scope.


def render_angle(
    data: Dict,
    obj1: Dict,
    obj2: Dict,
    center1: Tuple[float, float],
    center2: Tuple[float, float],
    ang: float,
    out_png: Path,
):
    """
    Renders and saves a top-down visualization of the room, highlighting two objects
    and the angle between the reference object's facing vector (North) and the
    direction vector to the target object.
    """
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_aspect("equal", adjustable="box")

    def _draw_geometry(geom: Optional[ShpPolygon], **kwargs):
        """Helper to draw a shapely geometry which may be a collection."""
        if not geom or geom.is_empty:
            return

        # If it's a collection, iterate through its parts and draw them
        if isinstance(geom, (MultiPolygon, GeometryCollection)):
            for part in geom.geoms:
                if isinstance(part, ShpPolygon) and not part.is_empty:
                    ax.add_patch(patches.Polygon(list(part.exterior.coords), closed=True, **kwargs))
        # If it's a simple polygon, draw it directly
        elif isinstance(geom, ShpPolygon):
            ax.add_patch(patches.Polygon(list(geom.exterior.coords), closed=True, **kwargs))

    # 1. Draw the room polygon
    room_poly_shp = build_room_polygon(data)
    if room_poly_shp and not room_poly_shp.is_empty:
        # Use the helper to draw the room itself, in case it's also complex
        _draw_geometry(room_poly_shp, fc="whitesmoke", ec="gray", lw=2, zorder=1)
        min_x, min_y, max_x, max_y = room_poly_shp.bounds
        padding_x = (max_x - min_x) * 0.1
        padding_y = (max_y - min_y) * 0.1
        ax.set_xlim(min_x - padding_x, max_x + padding_x)
        ax.set_ylim(min_y - padding_y, max_y + padding_y)
        scale_factor = max(max_x - min_x, max_y - min_y) * 0.15
    else:
        scale_factor = 1.0

    # 2. Draw all objects
    all_objs = merge_objects_and_openings(data)
    for obj in all_objs:
        obj_poly = _poly(obj["points"])
        _draw_geometry(obj_poly, fc="lightgray", ec="black", lw=1, zorder=2)

    # 3. Highlight the reference and target objects
    ref_poly = _poly(obj1["points"])
    _draw_geometry(ref_poly, fc="mediumseagreen", ec="darkgreen", lw=1.5, zorder=3)
    if ref_poly:
        ax.text(center1[0], center1[1], "Ref", color="white", ha="center", va="center", fontsize=10, fontweight="bold", zorder=5)

    tgt_poly = _poly(obj2["points"])
    _draw_geometry(tgt_poly, fc="indianred", ec="darkred", lw=1.5, zorder=3)
    if tgt_poly:
        ax.text(center2[0], center2[1], "Tgt", color="white", ha="center", va="center", fontsize=10, fontweight="bold", zorder=5)

    # 4. Define and draw vectors (This part is unchanged)
    v_dir_raw = (center2[0] - center1[0], center2[1] - center1[1])
    v_dir_norm = _norm(v_dir_raw)
    v_face_norm = (0.0, 1.0)

    ax.arrow(
        center1[0],
        center1[1],
        v_dir_norm[0] * scale_factor,
        v_dir_norm[1] * scale_factor,
        head_width=scale_factor * 0.1,
        head_length=scale_factor * 0.15,
        fc="royalblue",
        ec="royalblue",
        lw=2,
        zorder=4,
        length_includes_head=True,
    )

    ax.arrow(
        center1[0],
        center1[1],
        v_face_norm[0] * scale_factor,
        v_face_norm[1] * scale_factor,
        head_width=scale_factor * 0.1,
        head_length=scale_factor * 0.15,
        fc="darkorange",
        ec="darkorange",
        lw=2,
        zorder=4,
        length_includes_head=True,
    )

    # 5. Draw the angle arc and text (This part is unchanged)
    angle_face = 90.0
    cross_product_z = -v_dir_norm[0]

    if cross_product_z >= 0:
        theta1, theta2 = angle_face, angle_face + ang
    else:
        theta1, theta2 = angle_face - ang, angle_face

    arc = patches.Arc(center1, width=scale_factor, height=scale_factor, angle=0, theta1=theta1, theta2=theta2, color="black", linewidth=1.5, linestyle="--", zorder=4)
    ax.add_patch(arc)

    mid_angle_rad = np.deg2rad((theta1 + theta2) / 2)
    text_x = center1[0] + np.cos(mid_angle_rad) * scale_factor * 0.6
    text_y = center1[1] + np.sin(mid_angle_rad) * scale_factor * 0.6
    ax.text(text_x, text_y, f"{ang:.1f}°", ha="center", va="center", fontsize=12, fontweight="bold", backgroundcolor=(1, 1, 1, 0.7), zorder=6)

    # 6. Finalize and save the plot (This part is unchanged)
    ax.set_title(f"Alignment: '{_label(obj1)}' to '{_label(obj2)}'", fontsize=14)
    ax.axis("off")
    fig.tight_layout()
    plt.savefig(out_png, bbox_inches="tight", pad_inches=0.1, dpi=150)
    plt.close(fig)


# ---------------- QA generator (new format) ----------------


def process_single_file(file_path: str, file: str, room_type_arg: str, out_dir: str) -> Dict:
    with open(file_path, "r") as f:
        data = json.load(f)

    # ---- layout_id ----
    layout_id = data.get("layout_id")
    if layout_id is None:
        layout_id = file.replace(".json", "").replace("real_", "").replace("room_", "")

    with open(f"data/hssd_data/json_simplified/swapped_labels/room_{layout_id}.json", "r") as f:
        swapped_labels_data = json.load(f)

    # # 2) deterministic shuffle per layout_id:
    # seed = _stable_seed_from_layout(layout_id)
    # data = swap_object_labels(data, strategy="shuffle", seed=seed)

    # ---- room_type ----
    room_type = room_type_arg
    if room_type == "unknown":
        room_type = data.get("room_type") or (data.get("room", {}) or {}).get("room_type") or "unknown"

    # ---- objects (include windows/doors as objects) ----
    objects = merge_objects_and_openings(data)
    if len(objects) < 2:
        raise ValueError(f"Need at least 2 objects (incl. windows/doors) in {file_path}")

    seed = int(hashlib.md5(str(layout_id).encode()).hexdigest(), 16) % (2**32)
    rng = np.random.default_rng(seed=seed)
    rng = np.random.default_rng(seed=abs(hash(layout_id)))
    obj1, obj2 = rng.choice(objects, 2, replace=False)

    # ---- centroids ----
    center1 = get_polygon_centroid(obj1["points"])
    center2 = get_polygon_centroid(obj2["points"])

    # dp, ang = compute_alignment_new(data, reference_label=_label(obj1), target_label=_label(obj2), ref=obj1, tgt=obj2)

    swapped_labels_objects = merge_objects_and_openings(swapped_labels_data)
    obj1 = next((obj for obj in swapped_labels_objects if _label(obj) == _label(obj1)), obj1)
    obj2 = next((obj for obj in swapped_labels_objects if _label(obj) == _label(obj2)), obj2)

    dp, ang = compute_alignment_new(swapped_labels_data, reference_label=_label(obj1), target_label=_label(obj2), ref=obj1, tgt=obj2)

    print(f"Layout {layout_id}: '{_label(obj1)}' to '{_label(obj2)}' -> angle {ang:.2f}°, dp {dp:.4f}. Centers: {center1}, {center2}")

    # render (no try/except)
    out_png = Path(out_dir) / f"{layout_id}.png"
    out_png.parent.mkdir(parents=True, exist_ok=True)

    render_angle(data, obj1, obj2, center1, center2, ang, out_png)

    return {
        "layout_id": layout_id,
        "room_type": room_type,
        "object_1": obj1.get("label", "unknown"),
        "object_2": obj2.get("label", "unknown"),
        "N_points_obj_1": len(obj1["points"]),
        "N_points_obj_2": len(obj2["points"]),
        "center_1": center1,
        "center_2": center2,
        "answer": round(ang, 3),
        "N_objects": len(objects),
    }


def main_view_angle(
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
