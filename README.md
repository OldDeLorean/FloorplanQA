# FloorplanQA

<p align="center">
  <img src="docs/assets/logo-icml.svg" alt="ICML 2026" height="64">
</p>

> **Accepted at ICML 2026** (Seoul, South Korea). Project page: <https://olddelorean.github.io/FloorplanQA/> · Citation at the bottom of this README.

Code release for **FloorplanQA**, a benchmark of spatial-reasoning questions over
top-down floorplan layouts. The repository contains the layout-rendering
pipelines, the question-generation code for the eight task families, the
prompt-building code used to evaluate LLMs and VLMs, and example layouts to
verify the pipeline end-to-end.

> Layouts are released on [Hugging Face](https://huggingface.co/papers/2507.07644).
> This repository contains the **code only** plus example layouts.

## What's here

```
src/
  rendering/           Top-down rendering of layout JSON
  image_gen/           AI-generated photorealistic top-down images
    generate_nanobana.py        Gemini 3.1 Flash Image (Nano Banana 2) i2i
    prompts.py                  T2I / I2I prompt builders
    preparation_3_0.py          Builds VLM eval batches for image conditions
  qa_generation/       One module per task family
    pair_distance/  free_space/  max_box/  view_angle/
    obstruction/    placement/   repositioning/  shortest_path/
  evaluation/          Prompt assembly for the LLM / VLM evaluation
    preparation.py              JSON-only baseline
    preparation_2_0.py          JSON + image conditions
    preparation_tools.py        Python-Code-Interpreter (tool-augmented)
    questions*.py               Per-condition question/prompt builders
data/examples/         Example layouts (one per generated room type + one HSSD)
scripts/render_examples.py     End-to-end rendering demo
figures/               Example renders of `living_room_0`
```

## Installation

```bash
conda create -n floorplanqa python=3.10
conda activate floorplanqa
pip install -r requirements.txt
```

## Quick start

Render the bundled example layouts:

```bash
python scripts/render_examples.py --out figures/
```

## Question generation

Each module under `src/qa_generation/<task>/` exposes a `generate(layout, ...)`
function returning a list of `(question, answer)` pairs (or, for
`shortest_path`, full valid paths). `utils.py` holds shared geometry helpers.

## Evaluation

`src/evaluation/preparation*.py` assemble the per-model prompt batches:

- `preparation.py` — JSON-only baseline (the strongest condition in the paper).
- `preparation_2_0.py` — JSON + image conditions (Boxes / Icons).
- `preparation_tools.py` — Python Code Interpreter augmentation.
- `src/image_gen/preparation_3_0.py` — VLM batches with AI-generated images.

`questions*.py` build the prompt strings; one variant per input condition.

## Image generation

`src/image_gen/generate_nanobana.py` calls Gemini 3.1 Flash Image in
image-to-image mode to convert each schematic render into a photorealistic
top-down view while keeping furniture positions fixed. Requires
`GOOGLE_API_KEY` to be set.

## License

Released under the MIT license (see `LICENSE`).

## Citation

If you use FloorplanQA in your work, please cite:

```bibtex
@inproceedings{rodionov2025floorplanqa,
  title     = {FloorplanQA: A Benchmark for Spatial Reasoning in LLMs
               using Structured Representations},
  author    = {Rodionov, Fedor and Eldesokey, Abdelrahman and Birsak, Michael
               and Femiani, John and Ghanem, Bernard and Wonka, Peter},
  booktitle = {Proceedings of the 43rd International Conference on Machine Learning (ICML)},
  year      = {2025},
  address   = {Seoul, South Korea}
}
```
