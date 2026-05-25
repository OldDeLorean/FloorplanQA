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
)


def process_single_file(file_path: str, file: str, room_type_arg: str, out_dir: str) -> Dict:
    with open(file_path, "r") as f:
        data = json.load(f)

    # ---- layout_id (get this first to create the seed) ----
    layout_id = data.get("layout_id")
    if layout_id is None:
        layout_id = file.replace(".json", "").replace("real_", "").replace("room_", "")

    # ---- Create a DETERMINISTIC random number generator based on the layout_id ----
    # We use hash() to convert the string ID to an integer for the seed.
    # This ensures the same file ALWAYS gets the same random sequence.
    rng = np.random.default_rng(seed=abs(hash(layout_id)))

    # ---- room_type ----
    room_type = room_type_arg
    if room_type == "unknown":
        room_type = data.get("room_type") or (data.get("room", {}) or {}).get("room_type") or "unknown"

    # ---- objects (include windows/doors as objects) ----
    objects = merge_objects_and_openings(data)
    if len(objects) < 2:
        # It's better to return None or log a warning than to raise an error in parallel code
        print(f"Warning: Skipping {file_path}, it has fewer than 2 objects.")
        return None

    # ---- Use the local, deterministic rng to make the choice ----
    obj1, obj2 = rng.choice(objects, 2, replace=False)

    # ---- centroids ----
    center1 = get_polygon_centroid(obj1["points"])
    center2 = get_polygon_centroid(obj2["points"])
    distance = round(euclidean_distance(center1, center2), 2)

    # ---- render to PNG ----
    render_layout_pair(data, obj1, obj2, center1, center2, distance, out_dir=out_dir, layout_id=layout_id)

    return {
        "layout_id": layout_id,
        "room_type": room_type,
        "object_1": obj1.get("label", "unknown"),
        "object_2": obj2.get("label", "unknown"),
        "N_points_obj_1": len(obj1["points"]),
        "N_points_obj_2": len(obj2["points"]),
        "center_1": center1,
        "center_2": center2,
        "answer": distance,
        "N_objects": len(objects),
    }


def main_pair_distance(
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
