# max_box_any_angle.py (updated)
import os, json, math
from typing import Dict, Optional
import numpy as np
import pandas as pd
from functools import partial
from shapely.geometry import Polygon as ShpPolygon

from src.qa_pairs_generation.utils import (
    generate_qa_pairs_with_subsampling,
    save_and_info,
    build_room_polygon,
    collect_obstacle_polygons_for_maxbox,
    largest_empty_rectangle_fast_approx,
    render_max_box,
)


def _default_out_dir():
    parent = os.path.basename(os.path.dirname(os.path.realpath(__file__)))
    return f"benchmark/{parent}/images_max_box"


def polygon_corners_list(poly: ShpPolygon, ndigits: int = 3):
    """Return 4 corners (if rectangle) as [[x,y],...] rounded."""
    coords = list(poly.exterior.coords)[:-1]  # drop repeat
    return [[round(x, ndigits), round(y, ndigits)] for x, y in coords]


def process_single_file(
    file_path: str,
    file_name: str,
    room_type_hint: str = "unknown",
    out_dir: Optional[str] = None,
) -> Optional[Dict]:
    """
    Compute the largest empty rectangle at any rotation for one layout file.
    Obstacles: objects (excluding rugs and ceiling fixtures) + openings (doors/windows).
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # ---- layout_id ----
    layout_id = data.get("layout_id")
    if layout_id is None:
        layout_id = file_name.replace(".json", "").replace("real_", "").replace("room_", "")

    # room_type (new format prefers top-level)
    room_type = room_type_hint
    if room_type == "unknown":
        room_type = data.get("room_type") or (data.get("room", {}) or {}).get("room_type") or "unknown"

    # build room polygon (room_boundary preferred; else walls)
    room_polygon = build_room_polygon(data)
    if not room_polygon or room_polygon.is_empty:
        print(f"[{layout_id}] Invalid or empty room polygon, skipping.")
        return None

    # obstacles (objects minus rugs/ceiling + openings)
    obs_polys = collect_obstacle_polygons_for_maxbox(data)

    # any-angle search
    obox, area, angle_rad = largest_empty_rectangle_fast_approx(
        room_polygon=room_polygon,
        obstacle_polys=obs_polys,
        n_starts=300,  # tune: 150–500 is a good range
        n_angles=12,  # tune: 24–48 usually fine
        start_size=0.1,  # meters
        time_budget_s=30.0,  # optional global cap per layout
        rng_seed=42,
    )
    # render
    render_max_box(data=data, room_polygon=room_polygon, obstacles=obs_polys, obox=obox, out_path=out_dir)

    return {
        "layout_id": layout_id,
        "room_type": room_type,
        "answer": round(float(area), 3),  # area in square meters
        "obox_corners": polygon_corners_list(obox, 3),  # oriented rectangle corners
        "angle_deg": round(math.degrees(angle_rad), 3),  # orientation of rectangle
        "N_objects": len(data.get("objects", []) or []),
    }


# ------------------------------
# CLI
# ------------------------------


def main_max_box(
    input_dir: str = "data/hssd_data/new_format",
    output_csv: str = "benchmark/{parent_folder_name}/{parent_folder_name}_qa_hssd_data.csv",
    output_img: str = "benchmark/{parent_folder_name}/{parent_folder_name}_qa_hssd_images/",
    enable_subsampling: bool = False,
    bedrooms_count: int = 80,
    living_rooms_count: int = 80,
    kitchens_count: int = 40,
):
    """
    Find the largest empty axis-aligned rectangle for each layout.

    Args:
      input_dir: root containing JSONs or subdirs per room type.
      output_csv: output CSV path, supports {parent} = name of parent folder.
      enable_subsampling: if True, limits files per room type as below.
      bedrooms_count, living_rooms_count, kitchens_count: caps per room type when subsampling.
    """
    parent = os.path.basename(os.path.dirname(os.path.realpath(__file__)))
    output_csv = output_csv.format(parent_folder_name=parent)
    output_img = output_img.format(parent_folder_name=parent)

    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)

    if enable_subsampling:
        subsample = {
            "bedrooms": bedrooms_count,
            "living_rooms": living_rooms_count,
            "kitchens": kitchens_count,
        }
        print(f"Subsampling: {subsample}")
    else:
        subsample = None
        print("Processing all available files")

    # process_single_file_exact = partial(process_single_file, out_dir=output_img)

    # Now call your generator with that
    qa_pairs = generate_qa_pairs_with_subsampling(input_dir=input_dir, process_single_file=partial(process_single_file, out_dir=output_img), subsample_config=subsample)
    save_and_info(qa_pairs, output_csv)
