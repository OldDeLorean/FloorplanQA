# filepath: src/qa_pairs_generation/object_fit/object_fit.py
import os
import json
import math
import time
from functools import partial
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

import numpy as np
import pandas as pd
from pathlib import Path
import shapely
from shapely.geometry import Polygon as ShpPolygon, Point, box
from shapely.prepared import prep
from shapely.ops import unary_union
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from shapely.validation import make_valid

# Assuming these utilities are in a shared location
from src.qa_pairs_generation.utils import (
    build_room_polygon,
    # _poly,
    merge_objects_and_openings,
    generate_qa_pairs_with_subsampling,
    save_and_info,
    _label,
    _rot_mat,
    _rect_poly,
    # _grow_axis,
    # _largest_box_asymmetric_about_seed_wh,
    is_rug_label,
    is_light_label,
)
from src.qa_pairs_generation.placement.objects import kitchen_objects, living_room_objects, bedroom_objects

# ---------------- Object Definitions ----------------


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


@dataclass
class RoomObject:
    name: str
    width: float
    depth: float


# ---------------- New Core Logic ----------------


# ---------------- New Asymmetric Growth Implementation ----------------


def _rect_poly_asymmetric(seed_point: Tuple[float, float], theta: float, extents: Tuple[float, float, float, float]) -> ShpPolygon:
    """
    Creates a rotated polygon from a seed point and 4 directional extents.
    """
    aL, aR, bD, bU = extents  # left, right, down, up

    # Calculate final width, height, and the new center
    W = aL + aR
    H = bD + bU
    center_offset_local = np.array([0.5 * (aR - aL), 0.5 * (bU - bD)])

    # Rotate the offset and add to the original seed point
    R = _rot_mat(theta)
    center = np.array(seed_point) + (center_offset_local @ R.T)

    # Build the polygon corners
    hw, hh = 0.5 * W, 0.5 * H
    local_corners = np.array([[-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh]])

    rotated_corners = (local_corners @ R.T) + center
    return ShpPolygon(rotated_corners)


def _largest_box_asymmetric_about_seed(
    prep_space: shapely.prepared.PreparedGeometry,
    seed_point: Tuple[float, float],
    theta: float,
    aL0: float,
    aR0: float,
    bD0: float,
    bU0: float,
    aL_cap: float,
    aR_cap: float,
    bD_cap: float,
    bU_cap: float,
    tol: float = 1e-3,
    max_passes: int = 10,
) -> Tuple[ShpPolygon, float, float]:
    """
    Grows a rectangle asymmetrically from a seed point using coordinate ascent.
    """
    extents = [aL0, aR0, bD0, bU0]
    caps = [aL_cap, aR_cap, bD_cap, bU_cap]

    def is_valid(current_extents: List[float]) -> bool:
        """Checks if a rectangle with given extents is valid."""
        poly = _rect_poly_asymmetric(seed_point, theta, tuple(current_extents))
        # Use the fast prepared geometry check
        return prep_space.contains(poly)

    # --- Coordinate Ascent Loop ---
    # Iteratively grow each of the 4 extents until they converge.
    for _ in range(max_passes):
        prev_area = (extents[0] + extents[1]) * (extents[2] + extents[3])

        # For each of the 4 directions (aL, aR, bD, bU)...
        for i in range(4):
            # Binary search for the max extent in this one direction
            lo, hi = 0.0, caps[i]

            # Keep other 3 extents fixed during the search
            fixed_extents = list(extents)

            for _ in range(32):  # 32 iterations is enough for high precision
                if hi - lo < tol:
                    break
                mid = (lo + hi) / 2.0
                fixed_extents[i] = mid
                if is_valid(fixed_extents):
                    lo = mid  # This size is valid, try larger
                else:
                    hi = mid  # This size is invalid, try smaller

            extents[i] = lo

        # Check for convergence to stop early
        current_area = (extents[0] + extents[1]) * (extents[2] + extents[3])
        if abs(current_area - prev_area) < tol**2:
            break

    final_poly = _rect_poly_asymmetric(seed_point, theta, tuple(extents))
    final_width = extents[0] + extents[1]
    final_height = extents[2] + extents[3]

    return final_poly, final_width, final_height


# rng = np.random.default_rng(seed=abs(hash(rng_seed)))
# shuffled_angles = rng.choice(angles, len(angles), replace=False)


def find_fitting_rectangle(
    room_polygon: ShpPolygon,
    obstacle_polys: List[ShpPolygon],
    object_to_place: RoomObject,
    *,
    n_starts: int = 300,
    n_angles: int = 24,
    start_size: float = 0.1,
    time_budget_s: Optional[float] = 3.0,
    rng_seed: int = 42,
) -> Optional[Tuple[ShpPolygon, float]]:
    """
    Searches for ANY empty rectangle that can fit the given object, ensuring
    the rendered polygon matches the object's orientation.
    """
    rng = np.random.default_rng(seed=abs(hash(rng_seed)))
    free_space = room_polygon.difference(unary_union(obstacle_polys)) if obstacle_polys else room_polygon
    if free_space.is_empty:
        return None

    obj_w, obj_d = object_to_place.width, object_to_place.depth
    prep_space = prep(free_space)
    angles = [i * math.pi / n_angles for i in range(n_angles)]
    fs_bounds = free_space.bounds
    minx, miny, maxx, maxy = fs_bounds
    w_cap, h_cap = maxx - minx, maxy - miny
    t0 = time.perf_counter()

    def over_budget():
        return time_budget_s and (time.perf_counter() - t0) > time_budget_s

    def sample_point(max_tries=100):
        for _ in range(max_tries):
            p = Point(rng.uniform(minx, maxx), rng.uniform(miny, maxy))
            if prep_space.contains(p):
                return (p.x, p.y)
        return free_space.representative_point().coords[0]

    for _ in range(n_starts):
        if over_budget():
            break
        seed_point = sample_point()
        shuffled_angles = rng.choice(angles, len(angles), replace=False)

        for theta in shuffled_angles:
            if over_budget():
                break

            grown_poly, grown_w, grown_h = _largest_box_asymmetric_about_seed(
                prep_space=prep_space,
                seed_point=seed_point,
                theta=theta,
                aL0=start_size,
                aR0=start_size,
                bD0=start_size,
                bU0=start_size,
                aL_cap=w_cap,
                aR_cap=w_cap,
                bD_cap=h_cap,
                bU_cap=h_cap,
            )

            fits_normal = obj_w <= grown_w and obj_d <= grown_h
            fits_rotated = obj_d <= grown_w and obj_w <= grown_h

            if fits_normal or fits_rotated:
                # --- THIS IS THE CORRECTED LOGIC ---
                final_center = grown_poly.centroid.coords[0]

                # Default to the object's normal dimensions
                render_w, render_h = obj_w, obj_d

                # If it ONLY fits when rotated, swap the dimensions for rendering.
                if not fits_normal and fits_rotated:
                    render_w, render_h = obj_d, obj_w

                placed_poly = _rect_poly(final_center, render_w, render_h, theta)
                # --- END OF CORRECTION ---

                return placed_poly, theta

    return None


# ---------------- Updated Top-Level Logic ----------------


def compute_object_fit_advanced(data: Dict, object_to_place: RoomObject) -> Tuple[bool, Optional[ShpPolygon]]:
    """
    Top-level wrapper that now filters out rugs before checking for fit.
    """
    room_poly = build_room_polygon(data)
    if not room_poly or room_poly.is_empty:
        return False, None

    # **NEW LOGIC**: Filter obstacles, ignoring rugs.
    obstacles_to_consider = []
    for obj in merge_objects_and_openings(data):
        if not is_rug_label(_label(obj)) and not is_light_label(_label(obj)):
            poly = _poly(obj["points"])
            if poly:
                obstacles_to_consider.append(poly)

    # Call the search function with the filtered list of obstacles
    result = find_fitting_rectangle(room_polygon=room_poly, obstacle_polys=obstacles_to_consider, object_to_place=object_to_place)

    if result:
        placed_poly, _ = result
        return True, placed_poly

    return False, None


# ---------------- Rendering ----------------


def render_fit(data: Dict, object_to_place: RoomObject, fit_found: bool, placed_poly: Optional[ShpPolygon], out_png: Path):
    """
    Renders and saves a top-down visualization of the object fit test.

    It draws the room, existing objects, and then conditionally renders the
    result: a green polygon for a successful fit or a red title for a failure.
    """
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_aspect("equal", adjustable="box")

    def _draw_geometry(geom: Optional[ShpPolygon], **kwargs):
        """Helper to safely draw a shapely polygon or multipolygon."""
        if not geom or geom.is_empty:
            return
        # Ensure we can handle multipolygons if they arise
        geoms = geom.geoms if hasattr(geom, "geoms") else [geom]
        for part in geoms:
            if isinstance(part, ShpPolygon) and not part.is_empty:
                ax.add_patch(patches.Polygon(list(part.exterior.coords), closed=True, **kwargs))

    # 1. Draw the room and set boundaries
    room_poly = build_room_polygon(data)
    if room_poly:
        _draw_geometry(room_poly.buffer(0), fc="whitesmoke", ec="gray", lw=2, zorder=1)
        min_x, min_y, max_x, max_y = room_poly.bounds
        ax.set_xlim(min_x - 1, max_x + 1)
        ax.set_ylim(min_y - 1, max_y + 1)

    # 2. Draw all existing objects as obstacles
    for obj in merge_objects_and_openings(data):
        _draw_geometry(_poly(obj["points"]), fc="lightgray", ec="black", lw=1, zorder=2)

    # 3. Render the result of the fit test
    title = f"Fit test for: {object_to_place.name} ({object_to_place.width}m x {object_to_place.depth}m)"
    if fit_found and placed_poly:
        # SUCCESS: Draw the new object in green in its found location
        _draw_geometry(placed_poly, fc="mediumseagreen", ec="darkgreen", alpha=0.8, lw=1.5, zorder=3)
        ax.set_title(f"SUCCESS: {title}", color="green", fontsize=14)
    else:
        # FAILURE: Do not draw the new object, show a red failure title
        ax.set_title(f"FAILURE: {title}", color="red", fontsize=14)

    # 4. Finalize and save the plot
    ax.axis("off")
    plt.savefig(out_png, bbox_inches="tight", dpi=150)
    plt.close(fig)


# ---------------- QA Generation ----------------


def process_single_file(file_path: str, file: str, room_type_arg: str, all_objects: List, out_dir: str) -> Dict:
    with open(file_path, "r") as f:
        data = json.load(f)

    # ---- room_type ----
    room_type = room_type_arg
    if room_type == "unknown":
        room_type = data.get("room_type") or (data.get("room", {}) or {}).get("room_type") or "unknown"

    # ---- layout_id ----
    layout_id = data.get("layout_id")
    if layout_id is None:
        layout_id = file.replace(".json", "").replace("real_", "").replace("room_", "")

    objects = merge_objects_and_openings(data)

    # Select a random object to test placement for
    rng = np.random.default_rng(seed=abs(hash(layout_id)))
    object_to_place = rng.choice(all_objects)

    # Core logic
    fit_found, placed_poly = compute_object_fit_advanced(data, object_to_place)

    # Render visualization
    out_png = Path(out_dir) / f"{layout_id}.png"
    out_png.parent.mkdir(parents=True, exist_ok=True)
    render_fit(data, object_to_place, fit_found, placed_poly, out_png)

    return {
        "layout_id": layout_id,
        "room_type": room_type,
        "object_name": object_to_place.name,
        "object_width": object_to_place.width,
        "object_depth": object_to_place.depth,
        "answer": fit_found,
        "N_objects": len(objects),
    }


def main_placement(
    input_dir: str = "data/hssd_data/new_format",
    output_csv: str = "benchmark/{parent_folder_name}/{parent_folder_name}_qa_hssd_data.csv",
    output_img: str = "benchmark/{parent_folder_name}/{parent_folder_name}_qa_hssd_images/",
    enable_subsampling: bool = False,
    bedrooms_count: int = 80,
    living_rooms_count: int = 80,
    kitchens_count: int = 40,
):
    """Main function to generate object fit QA pairs."""
    parent_folder_name = os.path.basename(os.path.dirname(os.path.realpath(__file__)))
    output_csv = output_csv.format(parent_folder_name=parent_folder_name)
    output_img = output_img.format(parent_folder_name=parent_folder_name)
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)

    # Configure subsampling
    subsample_config = None
    if enable_subsampling:
        subsample_config = {"bedrooms": bedrooms_count, "living_rooms": living_rooms_count, "kitchens": kitchens_count}
        print(f"Subsampling enabled: {subsample_config}")
    else:
        print("Processing all available files")

    if "kitchen" in input_dir:
        ALL_OBJECTS = kitchen_objects
    elif "living_room" in input_dir:
        ALL_OBJECTS = living_room_objects
    elif "bedroom" in input_dir:
        ALL_OBJECTS = bedroom_objects
    else:
        # A combined list of all potential objects to place
        ALL_OBJECTS = kitchen_objects + living_room_objects + bedroom_objects

    print(len(ALL_OBJECTS), "objects available for placement tests.")

    # Use partial to pass the fixed 'all_objects' list to the processor
    processor = partial(process_single_file, all_objects=ALL_OBJECTS, out_dir=output_img)

    qa_pairs = generate_qa_pairs_with_subsampling(input_dir=input_dir, process_single_file=processor, subsample_config=subsample_config)

    save_and_info(qa_pairs, output_csv=output_csv)
