"""
Preparation v3.0 — VLM evaluation on AI-generated floorplan images.

Conditions:
  1. genimg_json     — AI-generated image + JSON layout
  2. genimg_only     — AI-generated image only, NO JSON

Image sources (2 generation models × user picks 1 gen method):
  - nanobana/{t2i|i2i}/room_{id}.png
  - qwen/{t2i|i2i}/room_{id}.png

VLM models: GPT-4.1-mini, GPT-5-mini, Gemini 3.1 Flash Lite
Dataset: Mixed only (200 rooms: living 0-74, bed 75-149, kitchen 150-199)

Usage:
    # Generate all batch files for a specific generation model + method
    python -m src.image_gen.preparation_3_0 --gen_model nanobana --gen_method t2i

    # Or for qwen
    python -m src.image_gen.preparation_3_0 --gen_model qwen --gen_method i2i

    # Specific conditions or datasets
    python -m src.image_gen.preparation_3_0 --gen_model nanobana --gen_method t2i --conditions genimg_json --datasets pair_distance

    # Limit rows for testing
    python -m src.image_gen.preparation_3_0 --gen_model nanobana --gen_method t2i --max_rows 5
"""

import fire
import json
from pathlib import Path
import pandas as pd
from typing import Optional

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

import re

def _adapt_prompt_for_genimg(prompt: str) -> str:
    """Remove references to coordinate grids/axes from image-only prompts,
    since AI-generated images have no grids or text labels."""
    # Remove grid-specific instructions
    prompt = re.sub(
        r"Use the coordinate grid on the image axes to estimate[^.]*\.",
        "Estimate object positions and dimensions from the visual content of the image.",
        prompt,
    )
    prompt = re.sub(
        r"\(top-down view with metric coordinate grid\)",
        "(top-down view)",
        prompt,
    )
    prompt = re.sub(
        r"Use the coordinate grid[^.]*\.",
        "Estimate dimensions from the visual content.",
        prompt,
    )
    return prompt


# ── VLM Models (same as v2.0) ────────────────────────────────────────────────
MODELS = [
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

# Conditions: (name, include_json)
CONDITIONS = [
    ("genimg_json", True),
    ("genimg_only", False),
]


def _infer_room_type(layout_id: int) -> str:
    if 0 <= layout_id <= 74:
        return "living_rooms"
    elif 75 <= layout_id <= 149:
        return "bedrooms"
    elif 150 <= layout_id <= 199:
        return "kitchens"
    raise ValueError(f"Unknown layout_id range: {layout_id}")


def _get_gen_image_path(layout_id: int, gen_model: str, gen_method: str) -> Path:
    """Get path to AI-generated image."""
    return Path(f"data/generated_images/{gen_model}/{gen_method}/room_{layout_id}.png")


def encode_image_base64(img_path: Path, max_size: tuple[int, int] = (720, 720)) -> str:
    """Encode image as base64, resized to max_size (matching v2.0)."""
    with Image.open(img_path) as im:
        im = im.convert("RGB")
        im.thumbnail(max_size, Image.LANCZOS)
        buf = BytesIO()
        im.save(buf, format="PNG")
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")


def _room_dimensions(room: dict) -> tuple[float, float]:
    """Get room width and height from boundary."""
    boundary = room.get("room_boundary", [])
    if not boundary:
        return 0, 0
    xs = [p["x"] for p in boundary]
    ys = [p["y"] for p in boundary]
    return round(max(xs) - min(xs), 2), round(max(ys) - min(ys), 2)


def _format_user_prompt(
    dataset: str, row: pd.Series, room: dict, room_type: str, include_json: bool
) -> str:
    """Format user prompt for generated image conditions."""
    if include_json:
        template = PROMPTS_JSON[dataset]
    else:
        # Adapt image-only prompts: remove grid/axis references for generated images
        template = _adapt_prompt_for_genimg(PROMPTS_IMG_ONLY[dataset])

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

    prompt = template.format(**fmt)

    # For genimg_only: append room dimensions as scale reference
    if not include_json:
        w, h = _room_dimensions(room)
        prompt += (
            f"\n\nRoom dimensions: {w}m wide x {h}m tall. "
            f"The coordinate origin (0,0) is at the bottom-left corner of the room. "
            f"X-axis goes right, Y-axis goes up."
        )

    return prompt


def _build_system_prompt(dataset: str, include_json: bool) -> str:
    """Build system prompt for generated image conditions."""
    if include_json:
        base = SYS_PROMPTS_JSON.get(dataset, "")
        image_desc = (
            " You are given both a structured JSON description of the room layout and a "
            "rendered floorplan image of the same room (realistic top-down view). "
            "The image is an AI-generated realistic rendering — furniture positions may have "
            "minor visual inaccuracies compared to the JSON data. When in doubt, trust the JSON. "
            "Use both sources of information. "
        )
    else:
        base = SYS_PROMPTS_IMG_ONLY.get(dataset, "")
        image_desc = (
            " You are given a rendered floorplan image of the room (realistic top-down view). "
            "The image is an AI-generated realistic rendering. There are NO coordinate grids or "
            "text labels on the image — you must estimate object positions and dimensions from "
            "the visual content alone. No structured text layout is provided — rely on the image. "
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


BUILD_REQUEST = {
    "openai": _build_request_openai,
    "gemini": _build_request_gemini,
}


def generate_batches(
    gen_model: str = "nanobana",
    gen_method: str = "t2i",
    output_base: str = "qa_jsonl_genimg",
    input_csv_template: str = "benchmark/{dataset}/{dataset}_qa_{room_type}.csv",
    datasets: str = "",
    conditions: str = "",
    max_rows: int = 0,
    force: bool = False,
):
    """Generate all JSONL batch files for v3.0 generated-image experiments.

    Args:
        gen_model: Image generation model ("nanobana" or "qwen")
        gen_method: Generation method ("t2i" or "i2i")
        output_base: Base output directory for JSONL files
        datasets: Comma-separated list of QA datasets (default: all 8)
        conditions: Comma-separated conditions to generate (default: all)
        max_rows: Limit rows per dataset (0 = all)
        force: Overwrite existing files
    """
    assert gen_model in ("nanobana", "qwen"), f"gen_model must be 'nanobana' or 'qwen'"
    assert gen_method in ("t2i", "i2i"), f"gen_method must be 't2i' or 'i2i'"

    if datasets:
        dataset_list = [d.strip() for d in datasets.split(",") if d.strip()]
    else:
        dataset_list = DATASETS

    if conditions:
        cond_filter = {c.strip() for c in conditions.split(",") if c.strip()}
    else:
        cond_filter = None

    # Load Mixed dataset (all 200 rooms)
    for dataset in dataset_list:
        dfs = []
        for rt, start_id, end_id in [("living_rooms", 0, 74), ("bedrooms", 75, 149), ("kitchens", 150, 199)]:
            csv_path = input_csv_template.format(dataset=dataset, room_type=rt)
            df_temp = pd.read_csv(csv_path)
            df_sampled = df_temp.iloc[start_id:end_id + 1]
            dfs.append(df_sampled)
        df = pd.concat(dfs, ignore_index=True).reset_index(drop=True)

        if max_rows > 0:
            df = df.head(max_rows)

        for cond_name, include_json in CONDITIONS:
            if cond_filter and cond_name not in cond_filter:
                continue

            for max_tokens, model_id, api_format in MODELS:
                model_name = model_id.split("/")[-1]
                out_dir = Path(output_base) / gen_model / gen_method / dataset / cond_name
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / f"{model_name}_{max_tokens}.jsonl"

                if not force and out_path.exists():
                    print(f"[SKIP] Already exists: {out_path}")
                    continue

                requests = []
                missing_images = 0

                for _, row in df.iterrows():
                    layout_id = row["layout_id"]
                    rt = _infer_room_type(layout_id)
                    rt_display = rt.rstrip("s").replace("_", " ")

                    # Load room JSON
                    json_path = Path(f"data/generated_data/{rt}") / f"room_{layout_id}.json"
                    with open(json_path) as f:
                        room = json.load(f)

                    user_prompt = _format_user_prompt(
                        dataset=dataset,
                        row=row,
                        room=room,
                        room_type=rt_display,
                        include_json=include_json,
                    )
                    sys_prompt = _build_system_prompt(dataset, include_json)

                    # Load generated image
                    img_path = _get_gen_image_path(layout_id, gen_model, gen_method)
                    b64_image = None
                    if img_path.exists():
                        try:
                            b64_image = encode_image_base64(img_path)
                        except Exception as e:
                            print(f"[WARN] Image error {layout_id}: {e}")
                            missing_images += 1
                    else:
                        missing_images += 1

                    if b64_image is None:
                        print(f"[WARN] Missing generated image: {img_path}")
                        continue

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

                print(
                    f"[{gen_model}/{gen_method}/{dataset}/{cond_name}] "
                    f"{model_name}: {len(requests)} requests -> {out_path}"
                    f"{f' ({missing_images} missing images)' if missing_images else ''}"
                )


if __name__ == "__main__":
    fire.Fire(generate_batches)
