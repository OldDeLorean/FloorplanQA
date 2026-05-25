# free_space_qapairs.py (updated)
import os
import json
import pandas as pd
from typing import Dict
from functools import partial
from shapely.ops import unary_union
from src.qa_pairs_generation.utils import (
    generate_qa_pairs_with_subsampling,
    save_and_info,
    build_room_polygon,
    collect_occupied_polygons,
    render_free_space_green,
    collect_opening_polygons,
)


def calculate_non_occupied_area_and_geom(room_data: dict):
    room_polygon = build_room_polygon(room_data)
    if room_polygon is None or room_polygon.is_empty:
        raise ValueError("Could not reconstruct a valid room polygon from the data.")

    # Objects that count (ceiling fixtures skipped)
    occ_objs = collect_occupied_polygons(room_data)

    # Openings (doors + windows) — subtract their footprint too, if any part lies inside
    # occ_openings = collect_opening_polygons(room_data)
    occ_openings = None

    occupied_shapes = []
    if occ_objs:
        occupied_shapes.extend(occ_objs)
    if occ_openings:
        occupied_shapes.extend(occ_openings)

    if occupied_shapes:
        merged_occ = unary_union(occupied_shapes)
        occ_in_room = room_polygon.intersection(merged_occ)
    else:
        occ_in_room = None

    if not occ_in_room or occ_in_room.is_empty:
        free_geom = room_polygon
    else:
        free_geom = room_polygon.difference(occ_in_room)

    free_area = round(free_geom.area, 2)
    return free_area, free_geom


def process_single_file(file_path: str, file: str, room_type: str, out_dir: str = None) -> Dict:
    """
    Process a single JSON file and return QA pair data (new/old format compatible).
    Also renders the free space overlay (green) to PNG.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # layout_id
    layout_id = data.get("layout_id")
    if layout_id is None:
        layout_id = file.replace(".json", "").replace("real_", "").replace("room_", "")

    # room_type (prefer top-level new format; fallback to old)
    if room_type == "unknown":
        room_type = data.get("room_type") or (data.get("room", {}) or {}).get("room_type") or "unknown"

    # compute free area + geometry
    non_occupied_area, free_geom = calculate_non_occupied_area_and_geom(data)

    # render green free space
    saved_to = render_free_space_green(data, free_geom, out_dir=out_dir, layout_id=str(layout_id))

    # number of objects (counting all entries in data['objects'], even if some were excluded from area)
    n_objects = len(data.get("objects", []) or [])

    return {
        "layout_id": layout_id,
        "room_type": room_type,
        "answer": non_occupied_area,  # same output field name you used
        "N_objects": n_objects,
    }


def main_free_space(
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
