# filepath: src/qa_pairs_generation/paths/process_single_file_visibility.py
import json, os, numpy as np
from pathlib import Path
from typing import Dict, Optional, List
from src.qa_pairs_generation.utils import generate_qa_pairs_with_subsampling, save_and_info, render_visibility_path, merge_objects_and_openings, _label

# in your runner
from functools import partial
from src.qa_pairs_generation.shortest_path.pathfinder import (
    find_path_room_constrained_blocked,
)

# Preferred labels per room type (used only if room_type is known)
CHOICE_OPTIONS = {
    "kitchens": ["stove", "fridge", "sink", "dishwasher", "door", "window", "table"],
    "living_rooms": ["door", "window", "sofa", "loveseat", "armchair", "coffee_table", "side_table", "tv_stand", "television", "bookshelf", "fireplace"],
    "bedrooms": ["door", "window", "bed", "dresser", "wardrobe", "desk", "bookshelf", "chair"],
}


def _eligible_labels(objects: List[Dict], room_type: Optional[str]) -> List[str]:
    """
    Filter labels by room_type pool (if provided), else return all.
    Rugs are excluded from candidates.
    """
    pool = CHOICE_OPTIONS.get((room_type or "").lower(), None)
    labels = []
    for o in objects:
        lab = _label(o)
        if not lab:
            continue
        if "rug" in lab.lower():
            continue
        if pool:
            if any(tok in lab.lower() for tok in pool):
                labels.append(lab)
        else:
            labels.append(lab)
    # fallback -> all non-rug labels if filtered empty
    if not labels:
        labels = [_label(o) for o in objects if "rug" not in _label(o).lower()]
    return labels


def process_single_file(file_path: str, file: str, room_type: str, out_dir: str) -> Optional[Dict]:

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    layout_id = str(data.get("layout_id"))
    rng = np.random.default_rng(seed=abs(hash(layout_id)))

    objects = merge_objects_and_openings(data)

    room_type_resolved = room_type
    if room_type_resolved == "unknown":
        room_type_resolved = data.get("room_type") or (data.get("room", {}) or {}).get("room_type") or "unknown"

    labels_all = [_label(o) for o in objects if _label(o)]
    if len(labels_all) < 2:
        return None

    start_label = goal_label = None
    pool = _eligible_labels(objects, room_type_resolved)
    if len(pool) >= 2:
        i, j = rng.choice(len(pool), 2, replace=False)
        start_label, goal_label = pool[i], pool[j]
    else:
        i, j = rng.choice(len(labels_all), 2, replace=False)
        start_label, goal_label = labels_all[i], labels_all[j]

    print(f"Chosen pair: {start_label} → {goal_label} in room type '{room_type_resolved}')")

    # build path & graph (fully connected, no obstacles)
    clearance = 0.1  # meters
    path, room_poly, obj_polys, sp, gp, G = find_path_room_constrained_blocked(data, objects, start_label=start_label, goal_label=goal_label, clearance=clearance)

    # render (no try/except)
    out_png = Path(out_dir) / f"{layout_id}.png"
    out_png.parent.mkdir(parents=True, exist_ok=True)
    title = f"{layout_id}  |  {start_label} → {goal_label}  (ALL-POINTS GRAPH)"
    render_visibility_path(
        data=data,
        room_polygon=room_poly,
        obstacles=obj_polys,
        path_xy=path,
        start_pt=sp,
        goal_pt=gp,
        out_path=out_png,
        title=f"{layout_id}  |  {start_label} → {goal_label} (room-constrained, object-blocked)",
        show_grid=True,
        show_axes=True,
        dpi=150,
        objects=objects,
        start_label=start_label,
        goal_label=goal_label,
        vis_graph=G,
    )

    return {
        "layout_id": layout_id,
        "room_type": room_type_resolved,
        "object_1": start_label,
        "object_2": goal_label,
        "clearance": clearance,
        "path_len": len(path),
        "answer": path,
        "N_objects": len(objects),
    }


def main_shortest_path(
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
