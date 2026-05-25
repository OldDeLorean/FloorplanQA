"""Render a floorplan to a fully-vector SVG with inlined SVG furniture icons.

The default `render_icons_with_grid` pipeline places icons via matplotlib's
`imshow`, which rasterises them at savefig time. This module bypasses imshow:

  1. It monkey-patches `place_icon` to drop a uniquely-gid'd invisible
     Rectangle at each icon's transformed position.
  2. It runs the normal renderer with `savefig(*.svg)` — matplotlib writes a
     <g id="ICONVEC_N"><path d="..."/></g> per placeholder with the 4 corners
     already converted to SVG user coordinates.
  3. It then parses the SVG, reads the 4 corners from each `d=` attribute to
     derive (cx, cy, w, h, angle), and replaces the placeholder children with
     the inlined contents of the matching SVG icon under a composed transform
     `translate(cx,cy) rotate(deg) translate(-w/2,-h/2) scale(w/vbw,h/vbh)
      translate(-vbx,-vby)`.

The PNG icon directory layout `stock_icons_cropped_<theme>_png` is expected to
have a parallel SVG dir `stock_icons_cropped_<theme>` with the same icon stems
(suffix `_FINAL.png` -> `.svg`).

Usage:
    python -m src.rendering.render_vector_svg \
        --scene data/examples/living_room_0.json \
        --icon-root /path/to/YoloFloorplan \
        --out room_0_vector.svg
"""

from __future__ import annotations

import argparse
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # noqa: E402
from matplotlib.patches import Rectangle
from matplotlib.transforms import Affine2D

import src.rendering.render_icons_with_grid as R
from src.rendering.render_showcase import render_showcase, YOLO_ROOT  # noqa: F401


_SVG_NS = "http://www.w3.org/2000/svg"
_GID_PREFIX = "ICONVEC_"
_NUM_RE = re.compile(r"(-?\d+\.?\d*(?:[eE][-+]?\d+)?)")


def _png_to_svg(png_path: str) -> Path:
    """Map an icon PNG path to its SVG sibling."""
    p = Path(png_path)
    svg_parent = Path(str(p.parent).replace("_png", ""))
    name = p.stem.replace("_FINAL", "")
    return svg_parent / f"{name}.svg"


def _parse_corners(d: str):
    nums = [float(x) for x in _NUM_RE.findall(d)]
    if len(nums) < 8:
        return None
    return [(nums[i], nums[i + 1]) for i in range(0, 8, 2)]


def render_vector_svg(scene_json: Path, out_svg: Path,
                      icon_root: str | None = None,
                      room_id: int = 0,
                      theme: str = "black") -> Path:
    """Render `scene_json` to a fully-vector SVG at `out_svg`.

    `icon_root` defaults to the project-wide YOLO_ROOT.
    `theme` picks one of the icon themes ("black", "blue", "green").
    """
    icon_root = icon_root or YOLO_ROOT

    # 1) force theme
    R.choose_theme_for_image = lambda r: (
        theme, Path(r) / R.THEME_DIRS[theme][0], R.THEME_DIRS[theme][1])

    # 2) record which PNG path produced which loaded image array
    path_by_id: dict[int, str] = {}
    orig_load = R.load_png_as_image

    def _load(p):
        a = orig_load(p)
        path_by_id[id(a)] = str(p)
        return a
    R.load_png_as_image = _load

    # 3) replace place_icon: drop a gid'd placeholder rect, skip imshow
    svg_by_gid: dict[str, str] = {}

    def _place(ax, img_rgba, cx, cy, width, height, angle_rad,
               mode="stretch", zorder=15):
        png_path = path_by_id.get(id(img_rgba))
        svg_path = _png_to_svg(png_path) if png_path else None
        if svg_path is None or not svg_path.exists():
            return None
        gid = f"{_GID_PREFIX}{len(svg_by_gid)}"
        svg_by_gid[gid] = str(svg_path)
        rect = Rectangle(
            (-width / 2, -height / 2), width, height,
            fill=False, edgecolor="none", linewidth=0, zorder=zorder,
            transform=Affine2D().rotate(angle_rad).translate(cx, cy) + ax.transData,
        )
        rect.set_gid(gid)
        ax.add_patch(rect)
        return rect
    R.place_icon = _place

    # 4) render base SVG (no embedded raster icons, just gid'd placeholders)
    render_showcase(scene_json, out_svg, icon_root, room_id=room_id)

    # 5) post-process: inline each SVG icon at the right transform
    ET.register_namespace("", _SVG_NS)
    tree = ET.parse(out_svg)
    root = tree.getroot()

    for g in list(root.iter(f"{{{_SVG_NS}}}g")):
        gid = g.get("id", "")
        if not gid.startswith(_GID_PREFIX):
            continue
        path = g.find(f"{{{_SVG_NS}}}path")
        if path is None:
            continue
        corners = _parse_corners(path.get("d", ""))
        if not corners:
            continue
        p0, p1, _, p3 = corners
        cx = sum(p[0] for p in corners) / 4
        cy = sum(p[1] for p in corners) / 4
        w = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        h = math.hypot(p3[0] - p0[0], p3[1] - p0[1])
        ang = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))

        icon_root_el = ET.parse(svg_by_gid[gid]).getroot()
        vb = icon_root_el.get("viewBox")
        if not vb:
            continue
        vbx, vby, vbw, vbh = [float(x) for x in vb.split()]
        sx, sy = w / vbw, h / vbh

        transform = (
            f"translate({cx:.4f},{cy:.4f}) rotate({ang:.4f}) "
            f"translate({-w/2:.4f},{-h/2:.4f}) scale({sx:.6f},{sy:.6f}) "
            f"translate({-vbx:.4f},{-vby:.4f})"
        )
        for child in list(g):
            g.remove(child)
        g.set("transform", transform)
        for child in list(icon_root_el):
            g.append(child)

    tree.write(out_svg)
    return out_svg


def _main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scene", required=True, type=Path,
                    help="Path to the layout JSON.")
    ap.add_argument("--out", required=True, type=Path,
                    help="Output SVG path.")
    ap.add_argument("--icon-root", default=None,
                    help="Root dir holding the stock_icons_* subdirectories.")
    ap.add_argument("--theme", default="black", choices=["black", "blue", "green"])
    ap.add_argument("--room-id", type=int, default=0,
                    help="Room id used by render_showcase for angle overrides.")
    args = ap.parse_args()
    out = render_vector_svg(args.scene, args.out, args.icon_root,
                            args.room_id, args.theme)
    print(f"wrote {out}")


if __name__ == "__main__":
    _main()
