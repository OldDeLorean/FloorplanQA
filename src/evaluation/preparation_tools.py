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


def _format_user_prompt(dataset: str, row: pd.Series, room: dict, room_type: str, layout_id: str, layout_dir: str) -> str:
    """Safely format the user prompt for a given dataset."""
    template = PROMPTS[dataset]

    # room_xml = room_to_xml(room)  # <<< convert dict -> XML string

    # choose a strategy
    # # 1) simple, no RNG:
    # room_swapped = swap_object_labels(room, strategy="rotate")

    # # 2) deterministic shuffle per layout_id:
    # seed = _stable_seed_from_layout(layout_id)
    # room_swapped = swap_object_labels(room, strategy="shuffle", seed=seed)

    # Dump the swapped room to disk for inspection / reuse

    # swapped_dir = Path(layout_dir) / f"swapped_labels"
    # swapped_dir.mkdir(parents=True, exist_ok=True)
    # swapped_path = swapped_dir / f"room_{layout_id}.json"
    # print(f"Writing swapped room to {swapped_path}...")
    # with open(swapped_path, "w", encoding="utf-8") as _f:
    #     json.dump(room_swapped, _f)

    fmt = {
        "room_type": room_type,
        "room": json.dumps(room, ensure_ascii=False),  # remains JSON  # <<< embed XML as string
        # optional fields that some prompts expect:
        "obj1": row.get("object_1", ""),
        "obj2": row.get("object_2", ""),
        "format": row.get("format", "JSON"),  # <<< default to JSON (optional)
        "clearance": row.get("clearance", ""),
        "object_name": row.get("object_name", ""),
        "object_width": row.get("object_width", ""),
        "object_depth": row.get("object_depth", ""),
        "object_to_move": row.get("object_to_move", ""),
        "direction": row.get("direction", ""),
    }
    return template.format(**fmt)


# def create_jsonl_for_batch(
#     df: pd.DataFrame,
#     dataset: str,
#     room_type: str,
#     max_tokens: int,
#     layout_dir: Union[str, Path],
#     model_id: str,
#     output_jsonl_path: Union[str, Path],
# ) -> None:
#     requests = []
#     layout_dir = Path(layout_dir)
#     output_jsonl_path = Path(output_jsonl_path)

#     sys_prompt = SYSTEM_PROMPTS.get(dataset, None)

#     for _, row in df.iterrows():
#         layout_id = row["layout_id"]

#         layout_path = layout_dir / f"room_{layout_id}.json"
#         with open(layout_path, "r", encoding="utf-8") as f:
#             room = json.load(f)

#         user_prompt = _format_user_prompt(dataset, row, room, room_type, layout_id, layout_dir)

#         messages = []
#         if sys_prompt:  # only include when defined
#             messages.append({"role": "system", "content": sys_prompt})
#         messages.append({"role": "user", "content": user_prompt})

#         if "gpt-5" in model_id:
#             request_entry = {
#                 "custom_id": f"request-{row['layout_id']}",
#                 "method": "POST",
#                 "url": "/v1/chat/completions",
#                 "body": {
#                     "model": model_id,
#                     "messages": messages,
#                     "max_completion_tokens": max_tokens,
#                     "verbosity": "low",
#                     "reasoning_effort": "minimal",
#                     "response_format": {"type": "text"},
#                 },
#             }
#         else:
#             request_entry = {
#                 "custom_id": f"request-{row['layout_id']}",
#                 "method": "POST",
#                 "url": "/v1/chat/completions",
#                 "body": {
#                     "model": model_id,
#                     "messages": messages,
#                     "max_tokens": max_tokens,
#                     "temperature": 0.0,
#                 },
#             }

#         requests.append(request_entry)

#     print(f"Writing {len(requests)} requests to {output_jsonl_path}...")

#     # with open(output_jsonl_path, "w", encoding="utf-8") as outfile:
#     #     for request in requests:
#     #         json.dump(request, outfile)
#     #         outfile.write("\n")


def create_jsonl_for_batch(
    df: pd.DataFrame,
    dataset: str,
    room_type: str,
    max_tokens: int,
    layout_dir: Union[str, Path],
    model_id: str,
    output_jsonl_path: Union[str, Path],
    use_code_interpreter: bool = False,  # 👈 NEW FLAG
) -> None:
    """
    Build a JSONL file of batch requests.

    - If `use_code_interpreter` is False (default):
        Uses /v1/chat/completions (your current behavior).
    - If `use_code_interpreter` is True:
        Uses /v1/responses with the built-in Python tool.
    """
    requests = []
    layout_dir = Path(layout_dir)
    output_jsonl_path = Path(output_jsonl_path)

    sys_prompt = SYSTEM_PROMPTS.get(dataset, None)

    for _, row in df.iterrows():
        layout_id = row["layout_id"]

        layout_path = layout_dir / f"room_{layout_id}.json"
        with open(layout_path, "r", encoding="utf-8") as f:
            room = json.load(f)

        user_prompt = _format_user_prompt(
            dataset=dataset,
            row=row,
            room=room,
            room_type=room_type,
            layout_id=layout_id,
            layout_dir=layout_dir,
        )

        # -------------------------
        # 1) Build chat-style messages
        # -------------------------
        messages = []
        if sys_prompt:  # only include when defined
            messages.append({"role": "system", "content": sys_prompt})
        messages.append({"role": "user", "content": user_prompt})

        # -------------------------
        # 2) Branch: with vs without code interpreter
        # -------------------------
        if use_code_interpreter:
            # Safely handle sys_prompt possibly being None
            if sys_prompt:
                sys_prompt_upd = sys_prompt.strip() + " You may write and run Python code to help you."
            else:
                sys_prompt_upd = "You may write and run Python code to help you."

            # # You can either merge into one string, or keep a messages-like structure.
            # # Here we keep roles, which Responses API supports in `input`.
            input_items = [
                {"role": "system", "content": sys_prompt_upd},
                {"role": "user", "content": user_prompt},
            ]

            request_entry = {
                "custom_id": f"request-{row['layout_id']}",
                "method": "POST",
                "url": "/v1/responses",  # 👈 Responses endpoint, not chat/completions
                "body": {
                    "model": model_id,
                    "input": input_items,  # 👈 `input`, not `messages`
                    "tools": [
                        {
                            "type": "code_interpreter",
                            "container": {"type": "auto"},
                        }
                    ],
                    "tool_choice": "required",  # force it to actually use Python
                    "max_output_tokens": max_tokens,
                },
            }
            # input_items = [
            #     {
            #         "role": "user",
            #         "content": user_prompt,
            #     }
            # ]

            # request_entry = {
            #     "custom_id": f"request-{row['layout_id']}",
            #     "method": "POST",
            #     "url": "/v1/messages",  # or full URL: "https://api.anthropic.com/v1/messages"
            #     "body": {
            #         "model": model_id,  # e.g. "claude-3.5-sonnet-20241022"
            #         "max_tokens": max_tokens,
            #         "system": sys_prompt_upd,  # system prompt here
            #         "messages": input_items,
            #         "tools": [
            #             {
            #                 "type": "code_execution_20250825",
            #                 "name": "code_execution",
            #             }
            #         ],
            #         "tool_choice": {
            #             "type": "tool",
            #             "name": "code_execution",
            #         },
            #     },
            #     "headers": {
            #         "content-type": "application/json",
            #         # 👇 this is the "betas" from the SDK example
            #         "anthropic-beta": "code-execution-2025-08-25",
            #     },
            # }

        # else:
        #     # Your original behavior, slightly refactored.
        #     if "gpt-5" in model_id:
        #         request_entry = {
        #             "custom_id": custom_id,
        #             "method": "POST",
        #             "url": "/v1/chat/completions",
        #             "body": {
        #                 "model": model_id,
        #                 "messages": messages,
        #                 "max_completion_tokens": max_tokens,
        #                 "verbosity": "low",
        #                 "reasoning_effort": "minimal",
        #                 "response_format": {"type": "text"},
        #             },
        #         }
        #     else:
        #         request_entry = {
        #             "custom_id": custom_id,
        #             "method": "POST",
        #             "url": "/v1/chat/completions",
        #             "body": {
        #                 "model": model_id,
        #                 "messages": messages,
        #                 "max_tokens": max_tokens,
        #                 "temperature": 0.0,
        #             },
        #         }

        requests.append(request_entry)

        with open(output_jsonl_path, "w", encoding="utf-8") as outfile:
            for request in requests:
                json.dump(request, outfile)
                outfile.write("\n")

    print(f"Writing {len(requests)} requests to {output_jsonl_path}...")


def generate_batches(
    layout_dir_template: str = "data/generated_data/{room_type}",
    input_csv_template: str = "benchmark/{dataset}/{dataset}_qa_{room_type}.csv",
    output_jsonl_template: str = "qa_jsonl_tools/{dataset}/{room_type}/{model_name}_{max_tokens}.jsonl",
):
    # Gemini models
    models_list = [
        # (12288, "gemini-2.5-flash"),
        # (12288, "gemini-2.5-pro"),
        # (12288, "claude-sonnet-4-20250514"),
        # OpenAI
        # (4096, "gpt-5-2025-08-07"),
        # (8192, "gpt-5-mini-2025-08-07"),
        (12288, "gpt-4.1-2025-04-14"),
        (8192, "gpt-4.1-mini-2025-04-14"),
        # reasoning
        # (12288, "openai/gpt-oss-120b"),
        # (12288, "deepseek-ai/DeepSeek-R1-0528"),
        # (8192, "Qwen/Qwen3-30B-A3B-Thinking-2507"),
        # (8192, "openai/gpt-oss-20b"),
        # non
        # (12288, "moonshotai/Kimi-K2-Instruct"),
        # (12288, "Qwen/Qwen3-Coder-480B-A35B-Instruct"),
        # (12288, "Qwen/Qwen3-235B-A22B-Instruct-2507"),
        # (8192, "Qwen/Qwen3-30B-A3B-Instruct-2507"),
        # (8192, "mistralai/Devstral-Small-2505"),
    ]

    # for room_type in ["living_rooms", "bedrooms", "kitchens", "hssd_data_simplified"]:
    for room_type in ["hssd_data_simplified"]:
        for dataset in [
            "shortest_path",
            "obstruction",
            "view_angle",
            "max_box",
            "free_space",
            "pair_distance",
            "placement",
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

                print(f"Generating batch for dataset '{dataset}', room type '{room_type}', model '{model_id}'...")
                print(f"Output path: {output_jsonl_path}")
                print(len(df), "requests to generate.")

                create_jsonl_for_batch(
                    df=df,
                    dataset=dataset,
                    room_type=room_type,
                    max_tokens=max_tokens,
                    layout_dir=layout_dir,
                    model_id=model_id,
                    output_jsonl_path=output_jsonl_path,
                    use_code_interpreter=True,  # 👈 turn it on
                )

            print(f"Batch JSONL files written for dataset '{dataset}' and room type '{room_type}'.")
