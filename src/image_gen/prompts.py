"""
Prompt builders for T2I and I2I floorplan generation.

T2I: text description from JSON -> image generation model -> realistic floorplan image
I2I: schematic image + text prompt -> image generation model -> realistic floorplan image
"""

import json
from pathlib import Path


def _bbox_from_points(points: list[dict]) -> dict:
    """Compute center, width, height from corner points."""
    xs = [p["x"] for p in points]
    ys = [p["y"] for p in points]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    return {
        "center_x": round((x_min + x_max) / 2, 2),
        "center_y": round((y_min + y_max) / 2, 2),
        "width": round(x_max - x_min, 2),
        "height": round(y_max - y_min, 2),
        "x_min": round(x_min, 2),
        "y_min": round(y_min, 2),
        "x_max": round(x_max, 2),
        "y_max": round(y_max, 2),
    }


def _room_dimensions(room: dict) -> tuple[float, float]:
    """Get room width and height from boundary."""
    boundary = room.get("room_boundary", [])
    if not boundary:
        return 0, 0
    xs = [p["x"] for p in boundary]
    ys = [p["y"] for p in boundary]
    return round(max(xs) - min(xs), 2), round(max(ys) - min(ys), 2)


def build_t2i_prompt(room: dict) -> str:
    """Build text-to-image prompt from room JSON.

    Describes the room layout in natural language with exact positions,
    asking the model to generate a realistic top-down floorplan rendering.
    """
    room_type = room.get("room_type", "room").replace("_", " ")
    w, h = _room_dimensions(room)

    # Build object descriptions
    obj_lines = []
    for obj in room.get("objects", []):
        bbox = _bbox_from_points(obj["points"])
        obj_lines.append(
            f"- {obj['label']}: {bbox['width']}m x {bbox['height']}m, "
            f"positioned at center ({bbox['center_x']}, {bbox['center_y']})"
        )

    # Build door/window descriptions
    opening_lines = []
    for door in room.get("openings", {}).get("doors", []):
        bbox = _bbox_from_points(door["points"])
        opening_lines.append(
            f"- {door['label']}: at ({bbox['center_x']}, {bbox['center_y']}), "
            f"{bbox['width']}m x {bbox['height']}m"
        )
    for win in room.get("openings", {}).get("windows", []):
        bbox = _bbox_from_points(win["points"])
        opening_lines.append(
            f"- {win['label']}: at ({bbox['center_x']}, {bbox['center_y']}), "
            f"{bbox['width']}m x {bbox['height']}m"
        )

    objects_text = "\n".join(obj_lines) if obj_lines else "No objects"
    openings_text = "\n".join(opening_lines) if opening_lines else "No openings"

    prompt = f"""Generate a realistic top-down floorplan image of a {room_type}.

Room dimensions: {w}m wide x {h}m tall.

CRITICAL RULES:
- This MUST be a top-down (bird's eye) view looking straight down at the floor.
- Use realistic furniture textures and colors (wood, fabric, etc.) as seen from above.
- Walls should be visible as thick borders around the room perimeter.
- Each piece of furniture must be placed at EXACTLY the specified position and size.
- The coordinate system: (0,0) is bottom-left, X goes right, Y goes up.
- Do NOT add any objects or furniture that are not listed below.
- Do NOT move or resize any objects from their specified positions.
- Do NOT add text labels, annotations, grid lines, or axis markers.

Furniture (name: width x height, center position):
{objects_text}

Openings (doors and windows):
{openings_text}

Style: Clean, photorealistic top-down architectural rendering. White/light floor, visible wall boundaries, realistic furniture appearances from above. No perspective, no 3D effects, no shadows from side lighting — only a flat overhead view."""

    return prompt


def build_i2i_prompt(room: dict) -> str:
    """Build image-to-image prompt for transforming a schematic into a realistic render.

    The schematic image is provided alongside this prompt.
    """
    room_type = room.get("room_type", "room").replace("_", " ")
    w, h = _room_dimensions(room)

    n_objects = len(room.get("objects", []))

    prompt = f"""Transform this schematic floorplan diagram into a realistic top-down floorplan rendering.

This is a {room_type}, {w}m x {h}m, with {n_objects} pieces of furniture.

CRITICAL RULES:
- Keep EVERY object in EXACTLY the same position and size as shown in the schematic.
- Replace the simple black outlines with realistic top-down furniture textures (wood grain, fabric patterns, etc.).
- Replace the white background with a realistic floor texture (hardwood, tile, etc.).
- Keep the walls as solid borders but make them look realistic (painted drywall).
- Do NOT move, resize, add, or remove any furniture.
- Do NOT add text labels, grid lines, axis markers, or annotations.
- Maintain the exact same top-down (bird's eye) perspective.
- Do NOT add any 3D perspective effects.

Style: Clean, photorealistic top-down architectural rendering as seen from directly above."""

    return prompt


def build_t2i_prompt_for_web_test(room_json_path: str) -> str:
    """Convenience: load a room JSON and print the T2I prompt for web UI testing."""
    with open(room_json_path) as f:
        room = json.load(f)
    return build_t2i_prompt(room)


def build_i2i_prompt_for_web_test(room_json_path: str) -> str:
    """Convenience: load a room JSON and print the I2I prompt for web UI testing."""
    with open(room_json_path) as f:
        room = json.load(f)
    return build_i2i_prompt(room)


if __name__ == "__main__":
    import fire
    fire.Fire({
        "t2i": build_t2i_prompt_for_web_test,
        "i2i": build_i2i_prompt_for_web_test,
    })
