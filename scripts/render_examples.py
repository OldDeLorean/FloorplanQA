"""Render the bundled example layouts in all three styles.

Produces, for each of {living_room, bedroom, kitchen}:
  - <name>_simple_boxes.png  (vector simple-box rendering with text labels)
  - <name>_icons.png          (schematic icons with transparent background)
  - <name>_icons_vector.svg   (fully-vector SVG with inlined icon paths)

The schematic icon and vector-SVG renderings need the YoloFloorplan icon root
(set via --icon-root or YOLO_ICON_ROOT env var). Without it those two outputs
are skipped and only the simple-box PNG is produced.

Usage:
    python scripts/render_examples.py --out figures/
    python scripts/render_examples.py --out figures/ --icon-root /path/to/YoloFloorplan
"""

import argparse
import json
import os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXAMPLES = REPO / "data" / "examples"


def render_all(out_dir: Path, icon_root: str | None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    from src.rendering.render_clean_floorplan import render_clean

    have_icons = icon_root and Path(icon_root).exists()
    if have_icons:
        from src.rendering.render_showcase import render_showcase
        from src.rendering.render_vector_svg import render_vector_svg

    for json_path in sorted(EXAMPLES.glob("*.json")):
        stem = json_path.stem
        print(f"\n=== {stem} ===")

        data = json.loads(json_path.read_text())
        boxes_png = out_dir / f"{stem}_simple_boxes.png"
        render_clean(data, boxes_png)
        print(f"  wrote {boxes_png}")

        if not have_icons:
            print(f"  (skipped icons/vector — icon-root not set or missing)")
            continue

        icons_png = out_dir / f"{stem}_icons.png"
        render_showcase(json_path, icons_png, icon_root, room_id=0)
        print(f"  wrote {icons_png}")

        icons_svg = out_dir / f"{stem}_icons_vector.svg"
        render_vector_svg(json_path, icons_svg, icon_root, room_id=0)
        print(f"  wrote {icons_svg}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=REPO / "figures",
                    help="Output directory (default: ./figures).")
    ap.add_argument("--icon-root", default=os.environ.get("YOLO_ICON_ROOT"),
                    help="Root of the icon library (stock_icons_cropped_*). "
                         "Defaults to YOLO_ICON_ROOT env var.")
    args = ap.parse_args()
    render_all(args.out, args.icon_root)


if __name__ == "__main__":
    main()
