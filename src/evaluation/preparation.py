import fire
import json
from pathlib import Path
import pandas as pd
from typing import Union

import json

from src.llm_eval.questions import SYSTEM_PROMPTS, PROMPTS

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


### XML ablation
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

_SINGULAR_OVERRIDES = {
    "walls": "wall",
    "objects": "object",
    "points": "point",
    "windows": "window",
    "doors": "door",
    "room_boundary": "point",
}


def _singularize(tag: str) -> str:
    if tag in _SINGULAR_OVERRIDES:
        return _SINGULAR_OVERRIDES[tag]
    return tag[:-1] if tag.endswith("s") and len(tag) > 1 else "item"


def _dict_to_xml(parent: Element, key: str, value):
    """
    Recursively converts Python data to XML by attaching children to `parent`.
    - dict -> nested elements using dict keys as tags
    - list -> repeated elements using singularized key (or 'item') as tag
    - scalar -> <key>text</key>
    """
    if isinstance(value, dict):
        node = SubElement(parent, key)
        for k, v in value.items():
            _dict_to_xml(node, k, v)
    elif isinstance(value, list):
        item_tag = _singularize(key)
        list_parent = SubElement(parent, key)
        for item in value:
            if isinstance(item, (dict, list)):
                _dict_to_xml(list_parent, item_tag, item)
            else:
                item_el = SubElement(list_parent, item_tag)
                item_el.text = "" if item is None else str(item)
    else:
        node = SubElement(parent, key)
        node.text = "" if value is None else str(value)


def room_to_xml(room: dict) -> str:
    """
    Build <room> ... </room> with top-level known fields first to keep it tidy.
    """
    root = Element("room")
    # Put a few common top-level fields first if present
    for top in ("layout_id", "room_type", "units"):
        if top in room:
            _dict_to_xml(root, top, room[top])
    # Add the rest (skipping ones already added)
    for k, v in room.items():
        if k in ("layout_id", "room_type", "units"):
            continue
        _dict_to_xml(root, k, v)

    # Pretty-print without XML declaration
    ugly = tostring(root, encoding="utf-8")
    pretty = minidom.parseString(ugly).toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")
    # Strip the XML declaration line
    lines = [ln for ln in pretty.splitlines() if ln.strip()]
    if lines and lines[0].startswith("<?xml"):
        lines = lines[1:]
    return "\n".join(lines)


def _format_user_prompt(dataset: str, row: pd.Series, room: dict, room_type: str, layout_id: str, layout_dir: str) -> str:
    """Safely format the user prompt for a given dataset."""
    template = PROMPTS[dataset]

    # room_xml = room_to_xml(room)  # <<< convert dict -> XML string

    # choose a strategy
    # # 1) simple, no RNG:
    # room_swapped = swap_object_labels(room, strategy="rotate")

    # 2) deterministic shuffle per layout_id:
    seed = _stable_seed_from_layout(layout_id)
    room_swapped = swap_object_labels(room, strategy="shuffle", seed=seed)

    # Dump the swapped room to disk for inspection / reuse

    swapped_dir = Path(layout_dir) / f"swapped_labels"
    swapped_dir.mkdir(parents=True, exist_ok=True)
    swapped_path = swapped_dir / f"room_{layout_id}.json"
    print(f"Writing swapped room to {swapped_path}...")
    with open(swapped_path, "w", encoding="utf-8") as _f:
        json.dump(room_swapped, _f)

    fmt = {
        "room_type": room_type,
        "room": json.dumps(room_swapped, ensure_ascii=False),  # remains JSON  # <<< embed XML as string
        # optional fields that some prompts expect:
        "obj1": row.get("object_1", ""),
        "obj2": row.get("object_2", ""),
        "format": row.get("format", "XML"),  # <<< default to XML (optional)
        "clearance": row.get("clearance", ""),
        "object_name": row.get("object_name", ""),
        "object_width": row.get("object_width", ""),
        "object_depth": row.get("object_depth", ""),
        "object_to_move": row.get("object_to_move", ""),
        "direction": row.get("direction", ""),
    }
    return template.format(**fmt)


def create_jsonl_for_batch(
    df: pd.DataFrame,
    dataset: str,
    room_type: str,
    max_tokens: int,
    layout_dir: Union[str, Path],
    model_id: str,
    output_jsonl_path: Union[str, Path],
) -> None:
    requests = []
    layout_dir = Path(layout_dir)
    output_jsonl_path = Path(output_jsonl_path)

    sys_prompt = SYSTEM_PROMPTS.get(dataset, None)

    for _, row in df.iterrows():
        layout_id = row["layout_id"]

        layout_path = layout_dir / f"room_{layout_id}.json"
        with open(layout_path, "r", encoding="utf-8") as f:
            room = json.load(f)

        # prompt = row["question"].format(room=room)

        # rug_prompt = ""
        # if room_type in ["living_room", "bedroom"]:
        #     rug_prompt = "You may overlap objects with the rug (place them above) or move objects through the rug."

        # system_prompt = "You are a spatial assistant. " "For simplicity, assume that windows have zero thickness in all cases. " f"{rug_prompt}"

        user_prompt = _format_user_prompt(dataset, row, room, room_type, layout_id, layout_dir)

        messages = []
        if sys_prompt:  # only include when defined
            messages.append({"role": "system", "content": sys_prompt})
        messages.append({"role": "user", "content": user_prompt})

        if "gpt-5" in model_id:
            request_entry = {
                "custom_id": f"request-{row['layout_id']}",
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": model_id,
                    "messages": messages,
                    "max_completion_tokens": max_tokens,
                    "verbosity": "low",
                    "reasoning_effort": "minimal",
                    "response_format": {"type": "text"},
                },
            }
        else:
            request_entry = {
                "custom_id": f"request-{row['layout_id']}",
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": model_id,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.0,
                },
            }

        requests.append(request_entry)

    print(f"Writing {len(requests)} requests to {output_jsonl_path}...")

    # with open(output_jsonl_path, "w", encoding="utf-8") as outfile:
    #     for request in requests:
    #         json.dump(request, outfile)
    #         outfile.write("\n")


def generate_batches(
    layout_dir_template: str = "data/generated_data/{room_type}",
    input_csv_template: str = "benchmark/{dataset}/{dataset}_qa_{room_type}.csv",
    output_jsonl_template: str = "qa_jsonl_ablation/swap_labels/{dataset}/{room_type}/{model_name}_{max_tokens}.jsonl",
):
    # Gemini models
    models_list = [
        # (12288, "gemini-2.5-flash"),
        # (12288, "gemini-2.5-pro"),
        # (12288, "claude-sonnet-4-20250514"),
        # OpenAI
        # (4096, "gpt-5-2025-08-07"),
        # (8192, "gpt-5-mini-2025-08-07"),
        # (12288, "gpt-4.1-2025-04-14"),
        # (8192, "gpt-4.1-mini-2025-04-14"),
        # reasoning
        (12288, "openai/gpt-oss-120b"),
        # (12288, "deepseek-ai/DeepSeek-R1-0528"),
        # (8192, "Qwen/Qwen3-30B-A3B-Thinking-2507"),
        (8192, "openai/gpt-oss-20b"),
        # non
        # (12288, "moonshotai/Kimi-K2-Instruct"),
        # (12288, "Qwen/Qwen3-Coder-480B-A35B-Instruct"),
        (12288, "Qwen/Qwen3-235B-A22B-Instruct-2507"),
        # (8192, "Qwen/Qwen3-30B-A3B-Instruct-2507"),
        # (8192, "mistralai/Devstral-Small-2505"),
    ]

    # for room_type in ["living_rooms", "bedrooms", "kitchens", "hssd_data_simplified"]:
    for room_type in ["hssd_data_simplified"]:
        for dataset in [
            # "shortest_path",
            "obstruction",
            "view_angle",
            # "max_box",
            # "free_space",
            # "pair_distance",
            # "placement",
            "repositioning",
        ]:
            if room_type == "hssd_data_simplified":
                layout_dir = "data/hssd_data/json_simplified"
            else:
                layout_dir = layout_dir_template.format(room_type=room_type)
            input_csv_path = input_csv_template.format(dataset=dataset, room_type=room_type)

            # TODO: Remove 100 limit after testing
            df = pd.read_csv(input_csv_path)
            print(df[:1])

            for max_tokens, model_id in models_list:
                model_name = model_id.split("/")[-1]
                output_jsonl_path = output_jsonl_template.format(dataset=dataset, room_type=room_type, model_name=model_name, max_tokens=max_tokens)
                output_jsonl_path = Path(output_jsonl_path)
                output_jsonl_path.parent.mkdir(parents=True, exist_ok=True)

                create_jsonl_for_batch(
                    df=df, dataset=dataset, room_type=room_type, max_tokens=max_tokens, layout_dir=layout_dir, model_id=model_id, output_jsonl_path=output_jsonl_path
                )

            print(f"Batch JSONL files written for dataset '{dataset}' and room type '{room_type}'.")
