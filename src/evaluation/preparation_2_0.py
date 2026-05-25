"""
Preparation v2.0 — 5 experimental conditions for VLM rebuttal experiments.

Conditions:
  1. clean_json    — Clean/grid image + JSON layout (both HSSD & Mixed)
  2. image_only    — Clean/grid image only, NO JSON (both HSSD & Mixed)
  3. icons_grid    — YOLO icon image + grid overlay, NO JSON (Mixed only)
  4. icons_json    — YOLO icon image + grid overlay + JSON layout (Mixed only)
  5. text_only     — JSON layout only, NO image (both HSSD & Mixed) — baseline

All conditions include coordinate grids on images.
Runs across 8 question types × 200 rooms per dataset.

Usage:
    python -m src.llm_eval.preparation_2_0
    python -m src.llm_eval.preparation_2_0 --room_types mixed
    python -m src.llm_eval.preparation_2_0 --room_types hssd_data_simplified
"""

import fire
import json
from pathlib import Path
import pandas as pd
from typing import Union, Optional

import base64
from io import BytesIO
from PIL import Image

from src.llm_eval.questions_images import (
    SYSTEM_PROMPTS as SYS_PROMPTS_JSON,
    PROMPTS as PROMPTS_JSON,
)
from src.llm_eval.questions_images_only import (
    SYSTEM_PROMPTS as SYS_PROMPTS_IMG_ONLY,
    PROMPTS as PROMPTS_IMG_ONLY,
)
from src.llm_eval.questions import (
    SYSTEM_PROMPTS as SYS_PROMPTS_TEXT_ONLY,
    PROMPTS as PROMPTS_TEXT_ONLY,
)


# ── Models ────────────────────────────────────────────────────────────────────
MODELS = [
    # (max_tokens, model_id, api_format)
    # api_format: "openai" for OpenAI batch API, "gemini" for Gemini, "anthropic" for Claude
    (8192, "gpt-4.1-mini-2025-04-14", "openai"),
    (8192, "gpt-5-mini-2025-08-07", "openai"),
    (8192, "gemini-3.1-flash-lite-preview", "gemini"),
]

DATASETS = [
    "pair_distance",
    "free_space",
    "max_box",
    "obstruction",
    "shortest_path",
    "view_angle",
    "placement",
    "repositioning",
]

# ── Condition definitions ─────────────────────────────────────────────────────
# Each condition: (name, include_json, image_dir_key, applicable_room_types)
#   image_dir_key: "clean" or "icons_grid"
#   applicable_room_types: which room_types this condition applies to

CONDITIONS = [
    ("clean_json",  True,  "clean",      ["hssd_data_simplified", "mixed"]),
    ("image_only",  False, "clean",      ["hssd_data_simplified", "mixed"]),
    ("icons_grid",  False, "icons_grid", ["mixed"]),
    ("icons_json",  True,  "icons_grid", ["mixed"]),
    ("text_only",   True,  None,         ["hssd_data_simplified", "mixed"]),
]


# ── Image paths ───────────────────────────────────────────────────────────────
# For HSSD:
#   clean: data/hssd_data/images_clean/room_{id}.png
# For Mixed (per room_type):
#   clean: data/generated_data/{room_type}_clean/room_{id}.png
#   icons_grid: data/generated_data/{room_type}_icons_grid/room_{id}.png

def _get_image_path_hssd(layout_id: int, image_type: str) -> Path:
    if image_type == "clean":
        return Path(f"data/hssd_data/images_clean/room_{layout_id}.png")
    raise ValueError(f"HSSD does not support image type: {image_type}")


def _get_image_path_mixed(layout_id: int, room_type: str, image_type: str) -> Path:
    if image_type == "clean":
        return Path(f"data/generated_data/{room_type}_clean/room_{layout_id}.png")
    elif image_type == "icons_grid":
        return Path(f"data/generated_data/{room_type}_icons_grid/room_{layout_id}.png")
    raise ValueError(f"Unknown image type: {image_type}")


def encode_resized_image_base64(
    img_path: Path,
    max_size: tuple[int, int] = (720, 720),
) -> str:
    with Image.open(img_path) as im:
        im = im.convert("RGB")
        im.thumbnail(max_size, Image.LANCZOS)
        buf = BytesIO()
        im.save(buf, format="PNG")
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")


def _format_user_prompt(dataset: str, row: pd.Series, room: dict, room_type: str, include_json: bool, image_type: str = "clean") -> str:
    """Format user prompt — with or without JSON room layout."""
    if image_type is None:
        # text_only: use original text-only prompts
        template = PROMPTS_TEXT_ONLY[dataset]
    elif include_json:
        template = PROMPTS_JSON[dataset]
    else:
        template = PROMPTS_IMG_ONLY[dataset]

    fmt = {
        "room_type": room_type,
        "format": "JSON",
        "obj1": row.get("object_1", ""),
        "obj2": row.get("object_2", ""),
        "clearance": row.get("clearance", ""),
        "object_name": row.get("object_name", ""),
        "object_width": row.get("object_width", ""),
        "object_depth": row.get("object_depth", ""),
        "object_to_move": row.get("object_to_move", ""),
        "direction": row.get("direction", ""),
    }

    if include_json:
        fmt["room"] = json.dumps(room, ensure_ascii=False)

    return template.format(**fmt)


def _build_system_prompt(dataset: str, include_json: bool, image_type: str) -> str:
    """Build the system prompt with appropriate image description."""
    if image_type is None:
        # text_only: use original text-only system prompts, no image description
        return SYS_PROMPTS_TEXT_ONLY.get(dataset, "")

    if include_json:
        base = SYS_PROMPTS_JSON.get(dataset, "")
        image_desc = (
            " You are given both a structured JSON description of the room layout and a "
            "rendered floorplan image of the same room (top-down view with metric coordinate "
            "grid showing X and Y axes in meters). Use both sources of information. "
        )
    else:
        base = SYS_PROMPTS_IMG_ONLY.get(dataset, "")
        image_desc = (
            " You are given a rendered floorplan image of the room (top-down view with metric "
            "coordinate grid showing X and Y axes in meters). Use the grid to estimate coordinates "
            "and dimensions of objects. No structured text layout is provided — rely on the image. "
        )

    if image_type == "icons_grid":
        image_desc += (
            "The image uses furniture icons (realistic top-down furniture shapes). "
        )
    else:
        image_desc += (
            "The image uses simple black outlines on white background with text labels. "
        )

    return (base.strip() + image_desc) if base else image_desc.strip()


def _build_request_openai(
    custom_id: str,
    model_id: str,
    max_tokens: int,
    sys_prompt: str,
    user_prompt: str,
    b64_image: Optional[str],
) -> dict:
    """Build OpenAI batch API request."""
    user_content_items = [{"type": "input_text", "text": user_prompt}]
    if b64_image is not None:
        user_content_items.append({
            "type": "input_image",
            "image_url": f"data:image/png;base64,{b64_image}",
            "detail": "high",
        })

    return {
        "custom_id": custom_id,
        "method": "POST",
        "url": "/v1/responses",
        "body": {
            "model": model_id,
            "input": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_content_items},
            ],
            "max_output_tokens": max_tokens,
        },
    }


def _build_request_gemini(
    custom_id: str,
    model_id: str,
    max_tokens: int,
    sys_prompt: str,
    user_prompt: str,
    b64_image: Optional[str],
) -> dict:
    """Build Gemini-style request (for use with OpenAI-compatible batch or custom runner)."""
    # Gemini via OpenRouter or direct API — adjust as needed for your runner
    user_content_items = [{"type": "input_text", "text": user_prompt}]
    if b64_image is not None:
        user_content_items.append({
            "type": "input_image",
            "image_url": f"data:image/png;base64,{b64_image}",
            "detail": "high",
        })

    return {
        "custom_id": custom_id,
        "method": "POST",
        "url": "/v1/responses",
        "body": {
            "model": model_id,
            "input": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_content_items},
            ],
            "max_output_tokens": max_tokens,
        },
    }


def _build_request_anthropic(
    custom_id: str,
    model_id: str,
    max_tokens: int,
    sys_prompt: str,
    user_prompt: str,
    b64_image: Optional[str],
) -> dict:
    """Build Anthropic Message Batches API request."""
    content = [{"type": "text", "text": user_prompt}]
    if b64_image is not None:
        content.insert(0, {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": b64_image,
            },
        })

    return {
        "custom_id": custom_id,
        "params": {
            "model": model_id,
            "max_tokens": max_tokens,
            "system": sys_prompt,
            "messages": [{"role": "user", "content": content}],
        },
    }


BUILD_REQUEST = {
    "openai": _build_request_openai,
    "gemini": _build_request_gemini,
    "anthropic": _build_request_anthropic,
}


def _infer_room_type(layout_id):
    """Infer room type from layout_id for mixed dataset."""
    lid = int(layout_id)
    if 0 <= lid <= 74:
        return "living_rooms"
    elif 75 <= lid <= 149:
        return "bedrooms"
    elif 150 <= lid <= 199:
        return "kitchens"
    raise ValueError(f"Unknown layout_id range: {layout_id}")


def generate_batches(
    room_types: str = "hssd_data_simplified,mixed",
    output_base: str = "qa_jsonl_images_v2",
    input_csv_template: str = "benchmark/{dataset}/{dataset}_qa_{room_type}.csv",
    datasets: str = "",
    max_rows: int = 0,
    conditions: str = "",
    force: bool = False,
):
    """Generate all JSONL batch files for v2.0 experiments.

    Args:
        datasets: comma-separated list of datasets to generate (default: all).
        max_rows: if > 0, limit to first N rows per dataset (for test runs).
        conditions: comma-separated list of conditions to generate (default: all).
        force: if False, skip files that already exist.
    """

    if isinstance(room_types, tuple):
        room_type_list = list(room_types)
    else:
        room_type_list = [r.strip() for r in room_types.split(",")]
    if isinstance(datasets, tuple):
        dataset_list = list(datasets)
    elif datasets:
        dataset_list = [d.strip() for d in datasets.split(",") if d.strip()]
    else:
        dataset_list = DATASETS
    if isinstance(conditions, tuple):
        cond_filter = set(conditions)
    elif conditions:
        cond_filter = {c.strip() for c in conditions.split(",") if c.strip()}
    else:
        cond_filter = None  # all conditions

    for room_type in room_type_list:
        for dataset in dataset_list:
            # Load data
            if room_type == "hssd_data_simplified":
                csv_path = input_csv_template.format(dataset=dataset, room_type=room_type)
                df = pd.read_csv(csv_path)
            elif room_type == "mixed":
                dfs = []
                for rt, start_id, end_id in [("living_rooms", 0, 74), ("bedrooms", 75, 149), ("kitchens", 150, 199)]:
                    csv_path = input_csv_template.format(dataset=dataset, room_type=rt)
                    df_temp = pd.read_csv(csv_path)
                    df_sampled = df_temp.iloc[start_id:end_id + 1]
                    dfs.append(df_sampled)
                df = pd.concat(dfs, ignore_index=True).reset_index(drop=True)
            else:
                csv_path = input_csv_template.format(dataset=dataset, room_type=room_type)
                df = pd.read_csv(csv_path)

            if max_rows > 0:
                df = df.head(max_rows)

            for cond_name, include_json, image_type, applicable in CONDITIONS:
                if room_type not in applicable:
                    continue
                if cond_filter and cond_name not in cond_filter:
                    continue

                for max_tokens, model_id, api_format in MODELS:
                    model_name = model_id.split("/")[-1]
                    out_dir = Path(output_base) / dataset / room_type / cond_name
                    out_dir.mkdir(parents=True, exist_ok=True)
                    out_path = out_dir / f"{model_name}_{max_tokens}.jsonl"

                    if not force and out_path.exists():
                        print(f"[SKIP] Already exists: {out_path}")
                        continue

                    requests = []
                    for _, row in df.iterrows():
                        layout_id = row["layout_id"]

                        # Load room JSON
                        if room_type == "hssd_data_simplified":
                            json_path = Path("data/hssd_data/json_simplified") / f"room_{layout_id}.json"
                            rt_display = row.get("room_type", "room")
                        elif room_type == "mixed":
                            rt = _infer_room_type(layout_id)
                            json_path = Path(f"data/generated_data/{rt}") / f"room_{layout_id}.json"
                            rt_display = rt.rstrip("s").replace("_", " ")
                        else:
                            rt = room_type
                            json_path = Path(f"data/generated_data/{rt}") / f"room_{layout_id}.json"
                            rt_display = rt.rstrip("s").replace("_", " ")

                        with open(json_path) as f:
                            room = json.load(f)

                        user_prompt = _format_user_prompt(
                            dataset=dataset,
                            row=row,
                            room=room,
                            room_type=rt_display,
                            include_json=include_json,
                            image_type=image_type,
                        )

                        sys_prompt = _build_system_prompt(dataset, include_json, image_type)

                        # Load image (skip for text_only)
                        b64_image = None
                        if image_type is not None:
                            if room_type == "hssd_data_simplified":
                                img_path = _get_image_path_hssd(layout_id, image_type)
                            elif room_type == "mixed":
                                rt = _infer_room_type(layout_id)
                                img_path = _get_image_path_mixed(layout_id, rt, image_type)
                            else:
                                img_path = _get_image_path_mixed(layout_id, room_type, image_type)

                            if img_path.exists():
                                try:
                                    b64_image = encode_resized_image_base64(img_path)
                                except Exception as e:
                                    print(f"[WARN] Image error {layout_id}: {e}")
                            else:
                                print(f"[WARN] Image not found: {img_path}")

                        builder = BUILD_REQUEST[api_format]
                        req = builder(
                            custom_id=f"request-{layout_id}",
                            model_id=model_id,
                            max_tokens=max_tokens,
                            sys_prompt=sys_prompt,
                            user_prompt=user_prompt,
                            b64_image=b64_image,
                        )
                        requests.append(req)

                    with open(out_path, "w") as outfile:
                        for req in requests:
                            json.dump(req, outfile)
                            outfile.write("\n")

                    print(f"[{room_type}/{dataset}/{cond_name}] {model_name}: {len(requests)} requests -> {out_path}")


if __name__ == "__main__":
    fire.Fire(generate_batches)
