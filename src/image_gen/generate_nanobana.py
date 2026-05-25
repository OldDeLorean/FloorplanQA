"""
Generate realistic floorplan images using Nano Banana 2 (Gemini 3.1 Flash Image Preview).

Supports two modes:
  - t2i: Text-to-image (JSON description -> realistic floorplan)
  - i2i: Image-to-image (schematic render + prompt -> realistic floorplan)

Usage:
    # T2I mode - generate from JSON descriptions
    python -m src.image_gen.generate_nanobana --mode t2i

    # I2I mode - transform schematic renders into realistic images
    python -m src.image_gen.generate_nanobana --mode i2i

    # Single room test
    python -m src.image_gen.generate_nanobana --mode t2i --ids 0

    # Dry run (print prompts, don't call API)
    python -m src.image_gen.generate_nanobana --mode t2i --dry_run

Requires: pip install google-genai Pillow
Env var: GOOGLE_API_KEY

Default model: gemini-3.1-flash-image-preview (Nano Banana 2)
Pricing: ~$0.067/image at 1K, 50% off with batch API
"""

import json
import time
import traceback
from pathlib import Path

import fire
from PIL import Image

from src.image_gen.prompts import build_t2i_prompt, build_i2i_prompt


# Mixed dataset room type -> (dir_name, id_start, id_end)
ROOM_TYPES = [
    ("living_rooms", 0, 74),
    ("bedrooms", 75, 149),
    ("kitchens", 150, 199),
]

BASE_DATA = Path("data/generated_data")


def _parse_ids(ids: str | None) -> set[int] | None:
    if ids is None:
        return None
    ids = str(ids)
    result = set()
    for part in ids.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-")
            result.update(range(int(lo), int(hi) + 1))
        else:
            result.add(int(part))
    return result


def _get_all_rooms(id_filter: set[int] | None = None) -> list[dict]:
    """Get all Mixed dataset rooms with metadata."""
    rooms = []
    for room_type, start, end in ROOM_TYPES:
        for rid in range(start, end + 1):
            if id_filter is not None and rid not in id_filter:
                continue
            json_path = BASE_DATA / room_type / f"room_{rid}.json"
            schematic_path = BASE_DATA / f"{room_type}_clean" / f"room_{rid}.png"
            rooms.append({
                "layout_id": rid,
                "room_type": room_type,
                "json_path": json_path,
                "schematic_path": schematic_path,
            })
    return rooms


def generate(
    mode: str = "t2i",
    out_dir: str = "data/generated_images/nanobana",
    ids: str | None = None,
    dry_run: bool = False,
    delay: float = 1.0,
    model_id: str = "gemini-3.1-flash-image-preview",
):
    """Generate realistic floorplan images using Nano Banana.

    Args:
        mode: "t2i" for text-to-image, "i2i" for image-to-image
        out_dir: Output directory for generated images
        ids: Comma-separated or range of layout IDs (e.g., "0-5,10"). None = all.
        dry_run: If True, print prompts without calling API
        delay: Seconds between API calls (rate limiting)
        model_id: Gemini model ID
    """
    assert mode in ("t2i", "i2i"), f"Mode must be 't2i' or 'i2i', got: {mode}"

    out_path = Path(out_dir) / mode
    out_path.mkdir(parents=True, exist_ok=True)

    id_filter = _parse_ids(ids)
    rooms = _get_all_rooms(id_filter)
    print(f"Mode: {mode} | Model: {model_id} | Rooms: {len(rooms)} | Output: {out_path}")

    if not dry_run:
        from google import genai
        from google.genai import types

        client = genai.Client()

    generated = 0
    skipped = 0
    errors = []

    for room_info in rooms:
        rid = room_info["layout_id"]
        img_out = out_path / f"room_{rid}.png"

        if img_out.exists():
            skipped += 1
            continue

        # Load room JSON
        with open(room_info["json_path"]) as f:
            room = json.load(f)

        if mode == "t2i":
            prompt = build_t2i_prompt(room)
            contents = [prompt]
        else:  # i2i
            prompt = build_i2i_prompt(room)
            schematic = Image.open(room_info["schematic_path"])
            contents = [prompt, schematic]

        if dry_run:
            print(f"\n{'='*60}")
            print(f"Room {rid} ({room_info['room_type']}):")
            print(prompt)
            continue

        try:
            response = client.models.generate_content(
                model=model_id,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                ),
            )

            # Extract and save image from response
            saved = False
            for candidate in response.candidates:
                for part in candidate.content.parts:
                    if part.inline_data is not None:
                        # Decode image bytes and save
                        import io
                        img_bytes = part.inline_data.data
                        img = Image.open(io.BytesIO(img_bytes))
                        img.save(str(img_out))
                        saved = True
                        break
                if saved:
                    break

            if saved:
                generated += 1
                print(f"[OK] room_{rid} -> {img_out}")
            else:
                errors.append((rid, "No image in response"))
                print(f"[WARN] room_{rid}: No image returned")

        except Exception as e:
            errors.append((rid, str(e)))
            print(f"[ERR] room_{rid}: {e}")
            traceback.print_exc()

        time.sleep(delay)

    print(f"\nDone: {generated} generated, {skipped} skipped, {len(errors)} errors")
    if errors:
        print("Errors:")
        for rid, msg in errors:
            print(f"  room_{rid}: {msg}")


if __name__ == "__main__":
    fire.Fire(generate)
