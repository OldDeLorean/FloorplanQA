# filepath: src/qa_pairs_generation/shortest_path/pathfinder.py
from __future__ import annotations
from typing import Dict, List, Tuple, Optional
import math
import heapq

from shapely.geometry import Polygon as ShpPolygon, Point, LineString
from shapely.ops import unary_union
from src.qa_pairs_generation.utils import build_room_polygon, get_polygon_centroid, is_rug_label, is_light_label, _label
from shapely.geometry.base import BaseGeometry


# ---------- helpers ----------


def _intersections_only_at_endpoints(
    seg: LineString,
    union_polys: Optional[BaseGeometry],
    a: Tuple[float, float],
    b: Tuple[float, float],
) -> bool:
    """
    True if seg ∩ union_polys is empty OR consists only of the endpoints {a,b}.
    Blocks any interior crossing (lines/areas or points not equal to endpoints).
    """
    if union_polys is None or union_polys.is_empty:
        return True

    inter = seg.intersection(union_polys)
    if inter.is_empty:
        return True

    allowed = {a, b}

    def _is_allowed_point(pt_geom) -> bool:
        ip = _round_xy(pt_geom.x, pt_geom.y)
        return ip in allowed

    gtype = inter.geom_type
    if gtype == "Point":
        return _is_allowed_point(inter)
    if gtype == "MultiPoint":
        return all(_is_allowed_point(pt) for pt in inter.geoms)
    if gtype == "GeometryCollection":
        for g in inter.geoms:
            if g.geom_type == "Point":
                if not _is_allowed_point(g):
                    return False
            else:
                return False
        return True

    return False


def _points_to_polygon(points: List[Dict[str, float]]) -> Optional[ShpPolygon]:
    if not points:
        return None
    coords = [(float(p["x"]), float(p["y"])) for p in points]
    if len(coords) >= 3:
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        poly = ShpPolygon(coords)
        if poly.is_valid and not poly.is_empty and poly.area > 0:
            return poly
    return None


def _round_xy(x: float, y: float, nd: int = 6) -> Tuple[float, float]:
    return (round(float(x), nd), round(float(y), nd))


# ---------- graph construction (room-constrained + object-blocked with clearance) ----------


def build_graph_blocked_by_objects(
    data: Dict,
    objects: List[Dict],
    start_label: str,
    goal_label: str,
    clearance: float = 0.1,
):
    """
    Builds a visibility graph including room corners for optimal pathing.
    """
    room = build_room_polygon(data)
    start_lab_l = (start_label or "").lower()
    goal_lab_l = (goal_label or "").lower()

    # 1. NEW: Add vertices from a shrunken "pathable" room polygon
    room_corner_nodes: List[Tuple[float, float]] = []
    if room:
        pathable_room_poly = room.buffer(-clearance)
        if not pathable_room_poly.is_empty:
            polys = [pathable_room_poly] if pathable_room_poly.geom_type == "Polygon" else list(pathable_room_poly.geoms)
            for poly in polys:
                room_corner_nodes.extend(_round_xy(x, y) for x, y in list(poly.exterior.coords))

    # 2. Get centers and object polygons
    start_obj = next((o for o in objects if _label(o).lower() == start_lab_l), None)
    goal_obj = next((o for o in objects if _label(o).lower() == goal_lab_l), None)
    sp = _round_xy(*get_polygon_centroid(start_obj["points"])) if start_obj else None
    gp = _round_xy(*get_polygon_centroid(goal_obj["points"])) if goal_obj else None

    # 3. Collect buffered polygons and their vertices from objects
    all_buffered_verts: List[Tuple[float, float]] = []
    polys_blocking_buffered: List[ShpPolygon] = []
    verts_by_label: Dict[str, List[Tuple[float, float]]] = {}
    start_buffered_poly, goal_buffered_poly = None, None

    for o in objects:
        lab_l = _label(o).lower()
        poly = _points_to_polygon(o.get("points") or [])
        if poly is None or is_rug_label(lab_l) or is_light_label(lab_l):
            continue

        buffered_poly = poly.buffer(clearance, join_style=2)
        if buffered_poly.is_empty:
            continue
        polys_blocking_buffered.append(buffered_poly)

        if lab_l == start_lab_l:
            start_buffered_poly = buffered_poly
        if lab_l == goal_lab_l:
            goal_buffered_poly = buffered_poly

        verts = [_round_xy(x, y) for x, y in list(buffered_poly.exterior.coords)]
        verts_by_label[lab_l] = verts
        all_buffered_verts.extend(verts)

    # 4. Create different versions of the blocking geometry
    full_union = unary_union(polys_blocking_buffered) if polys_blocking_buffered else None
    if full_union:
        clean_union = full_union.buffer(0)
        epsilon = 1e-2
        full_blocking_union = clean_union.buffer(-epsilon)
        blocking_union_for_start = clean_union.difference(start_buffered_poly).buffer(-epsilon) if start_buffered_poly else full_blocking_union
        blocking_union_for_goal = clean_union.difference(goal_buffered_poly).buffer(-epsilon) if goal_buffered_poly else full_blocking_union

        blocking_union_minus_start_goal = (
            clean_union.difference(start_buffered_poly).difference(goal_buffered_poly).buffer(-epsilon) if start_buffered_poly and goal_buffered_poly else full_blocking_union
        )
    else:
        full_blocking_union, blocking_union_for_start, blocking_union_for_goal, blocking_union_minus_start_goal = None, None, None, None

    # 5. Define all nodes and initialize graph
    # UPDATED: Now includes room_corner_nodes
    vertex_nodes = list(set(all_buffered_verts + room_corner_nodes))
    nodes = list(vertex_nodes)
    if sp:
        nodes.append(sp)
    if gp:
        nodes.append(gp)
    nodes = list(set(nodes))
    G: Dict[Tuple[float, float], Dict[Tuple[float, float], float]] = {n: {} for n in nodes}

    # --- Phase 1: Add Guaranteed "Exit" Edges ---
    if sp:
        for vert in verts_by_label.get(start_lab_l, []):
            if vert in G:
                d = Point(sp).distance(Point(vert))
                G[sp][vert] = d
                G[vert][sp] = d
    if gp:
        for vert in verts_by_label.get(goal_lab_l, []):
            if vert in G:
                d = Point(gp).distance(Point(vert))
                G[gp][vert] = d
                G[vert][gp] = d

    # --- Phase 2: Center-Specific Visibility Checks ---
    if sp:
        for node in nodes:
            if node == sp or node in G[sp]:
                continue
            seg = LineString([sp, node])
            if (room is None or room.covers(seg)) and _intersections_only_at_endpoints(seg, blocking_union_minus_start_goal, sp, node):
                d = seg.length
                G[sp][node] = d
                G[node][sp] = d
    if gp:
        for node in nodes:
            if node == gp or node in G[gp]:
                continue
            seg = LineString([gp, node])
            if (room is None or room.covers(seg)) and _intersections_only_at_endpoints(seg, blocking_union_minus_start_goal, gp, node):
                d = seg.length
                G[gp][node] = d
                G[node][gp] = d

    # --- Phase 3: General Visibility Checks for all vertex nodes ---
    # UPDATED: The loop now implicitly includes room corners via vertex_nodes
    for i in range(len(vertex_nodes)):
        a = vertex_nodes[i]
        for j in range(i + 1, len(vertex_nodes)):
            b = vertex_nodes[j]
            if b in G[a]:
                continue
            seg = LineString([a, b])
            if (room is None or room.covers(seg)) and _intersections_only_at_endpoints(seg, full_blocking_union, a, b):
                d = seg.length
                G[a][b] = d
                G[b][a] = d

    return G, sp, gp, room, blocking_union_minus_start_goal


# ---------- dijkstra ----------


def dijkstra_shortest_path(
    graph: Dict[Tuple[float, float], Dict[Tuple[float, float], float]],
    start: Tuple[float, float],
    goal: Tuple[float, float],
) -> List[Tuple[float, float]]:
    """Standard Dijkstra's algorithm to find the shortest path in a weighted graph."""
    if start not in graph or goal not in graph:
        return []
    INF = float("inf")
    dist = {n: INF for n in graph}
    prev: Dict[Tuple[float, float], Optional[Tuple[float, float]]] = {n: None for n in graph}
    dist[start] = 0.0
    h = [(0.0, start)]

    while h:
        d, u = heapq.heappop(h)
        if d > dist[u]:
            continue
        if u == goal:
            break
        for v, weight in graph[u].items():
            new_dist = d + weight
            if new_dist < dist[v]:
                dist[v] = new_dist
                prev[v] = u
                heapq.heappush(h, (new_dist, v))

    if prev.get(goal) is None and start != goal:
        return []
    path = []
    curr = goal
    while curr is not None:
        path.append(curr)
        curr = prev[curr]
    path.reverse()
    return path if path and path[0] == start else []


# ---------- public API ----------


def find_path_room_constrained_blocked(
    data: Dict,
    objects: List[Dict],
    start_label: str,
    goal_label: str,
    clearance: float = 0.1,
):
    """
    Finds a path with clearance from objects.

    Returns:
        A tuple containing: (path_xy, room_polygon, buffered_object_polys,
         start_pt, goal_pt, graph)
    """
    G, sp, gp, room_poly, obj_polys_buffered = build_graph_blocked_by_objects(
        data,
        objects,
        start_label,
        goal_label,
        clearance=clearance,
    )
    path = dijkstra_shortest_path(G, sp, gp) if (sp and gp) else []
    return path, room_poly, obj_polys_buffered, sp, gp, G


def is_path_valid(
    path_to_check: List[Tuple[float, float]],
    room_polygon: Optional[ShpPolygon],
    object_polys_buffered: List[ShpPolygon],
) -> bool:
    """
    Verifies if a given path is valid according to the environment rules.

    A path is a sequence of connected line segments. It is valid if every
    segment is fully contained within the room and does not intersect the
    interior of any buffered object polygon.

    Args:
        path_to_check: A list of (x, y) coordinates representing the path.
        room_polygon: The Shapely Polygon of the room.
        object_polys_buffered: A list of buffered polygons for all obstacles.

    Returns:
        True if the path is valid, False otherwise.
    """
    # An empty path or a single-point path is trivially valid.
    if not path_to_check or len(path_to_check) < 2:
        return True

    # Pre-calculate the single blocking union for efficient checks.
    # We apply the same cleaning logic used in the graph builder.
    union = unary_union(object_polys_buffered) if object_polys_buffered else None
    if union:
        clean_union = union.buffer(0)
        epsilon = 1e-2
        blocking_union = clean_union.buffer(-epsilon)
    else:
        blocking_union = None

    # Check each segment of the path.
    for i in range(len(path_to_check) - 1):
        a = path_to_check[i]
        b = path_to_check[i + 1]
        seg = LineString([a, b])

        # Rule 1: Segment must be entirely within the room.
        if room_polygon and not room_polygon.covers(seg):
            print(f"Validation failed: Segment {a} -> {b} goes outside the room.")
            return False

        # Rule 2: Segment must not cross through any obstacle's clearance zone.
        if not _intersections_only_at_endpoints(seg, blocking_union, a, b):
            print(f"Validation failed: Segment {a} -> {b} intersects an obstacle.")
            return False

    # If all segments passed, the path is valid.
    return True
