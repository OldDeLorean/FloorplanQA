pair_distance_question = """
Given the layout of a {room_type} in {format}, calculate the Euclidean distance in meters between the centroids of '{obj1}' and '{obj2}'.

Room layout:
{room}

Begin with printing a layout_id, then a concise checklist (3-7 bullets) of the conceptual steps necessary for calculating the Euclidean distance. Then, carefully walk through each reasoning step required to calculate the distance.

If the format, object names, or required input data are missing, invalid, or inconsistent, reply with:
*Final answer*: ERROR

Limit your output to the step-by-step reasoning only, and do not include any internal reasoning unless explicitly requested. Clearly state the final answer on the last line using the exact format specified below.

### Output Format
Respond in the following strict format:

layout_id: id

<step-by-step calculations>

*Final answer*: <distance>

Where <distance> is a float rounded to three decimal places, representing the distance in meters. For example: *Final answer*: 5.610
"""

free_space_question = """
Given the {room_type} layout in {format}, calculate the total non-occupied (free) floor area in square meters (m²).

Room layout:
{room}

Begin with printing a layout_id, then a concise checklist (3-7 bullets) of the conceptual steps necessary for calculating the free space. Then, carefully walk through each reasoning step required to calculate the area.

If the format, object names, or required input data are missing, invalid, or inconsistent, reply with:
*Final answer*: ERROR

Limit your output to the step-by-step reasoning only, and do not include any internal reasoning unless explicitly requested. Clearly state the final answer on the last line using the exact format specified below.

### Output Format
Respond in the following strict format:

layout_id: id

<step-by-step calculations>

*Final answer*: <area>

Where <area> is a float rounded to three decimal places, representing the free area in m². For example: *Final answer*: 12.347
"""

max_box_question = """
Given the {room_type} layout in {format}, calculate the area in square meters (m²) of the largest rectangle that can fit inside the room. The rectangle may be rotated at any angle.
Rectangle must not overlap with other objects and openings apart from floor soft coverings, but may occupy all free space. Ignore passages, door swings, or clearance requirements.

Room layout:
{room}

Begin with printing a layout_id, then a concise checklist (3-7 bullets) of the conceptual steps necessary for finding the largest rectangle. Then, carefully walk through each reasoning step required to calculate the area.

If the format, object names, or required input data are missing, invalid, or inconsistent, reply with:
*Final answer*: ERROR

Limit your output to the step-by-step reasoning only, and do not include any internal reasoning unless explicitly requested. Clearly state the final answer on the last line using the exact format specified below.

### Output Format
Respond in the following strict format:

layout_id: id

<step-by-step calculations>

*Final answer*: <area>

Where <area> is a float rounded to three decimal places, representing the maximum rectangle area in m². For example: *Final answer*: 8.920
"""

obstruction_prompt = """
Given the {room_type} layout in {format}, find all objects that intersect the vector from the centroid of the '{obj1}' to the centroid of the '{obj2}'. Do not include the starting or ending objects themselves.

Room layout:
{room}

Begin with printing a layout_id, then a concise checklist (3-7 bullets) of the conceptual steps necessary for finding intersecting objects. Then, carefully walk through each reasoning step required to identify them.

If the format, object names, or required input data are missing, invalid, or inconsistent, reply with:
*Final answer*: ERROR

Limit your output to the step-by-step reasoning only, and do not include any internal reasoning unless explicitly requested. Clearly state the final answer on the last line using the exact format specified below.

### Output Format
Respond in the following strict format:

layout_id: id

<step-by-step calculations>

*Final answer*: [object_label_1, object_label_2, ...]

Where the list contains the labels of all intersecting objects in order of intersection. If no objects intersect, return an empty list: *Final answer*: []
"""

shortest_path = """
Given the {room_type} layout in {format} format below, determine the shortest valid path that maintains a clearance of {clearance} m from all other objects, starting from the centroid of '{obj1}' and ending at the centroid of '{obj2}'.

Room layout:
{room}

Begin with printing a layout_id, then a concise checklist (3-7 bullets) of the conceptual steps necessary for calculating the valid shortest path. Then, carefully walk through each reasoning step required to identify the path.

If the format, object names, or required input data are missing, invalid, or inconsistent, reply with:
*Final answer*: ERROR

Limit your output to the step-by-step reasoning only, and do not include any internal reasoning unless explicitly requested. Clearly state the final answer on the last line using the exact format specified below.

### Output Format
Respond in the following strict format:

layout_id: id

<step-by-step calculations>

*Final answer*: [(x_start, y_start), (x_1, y_1), ..., (x_finish, y_finish)]
"""

view_angle = """
Given the {room_type} layout in {format} format below, compute the smallest absolute angle in degrees (0°–180°) between the vector from the centroid of the '{obj1}' to the centroid of the '{obj2}' and the global north vector (0, 1).

Room layout:
{room}

Begin with printing a layout_id, then a concise checklist (3-7 bullets) of the conceptual steps necessary for calculating the angle. Then, carefully walk through each reasoning step required to compute it.

If the format, object names, or required input data are missing, invalid, or inconsistent, reply with:
*Final answer*: ERROR

Limit your output to the step-by-step reasoning only, and do not include any internal reasoning unless explicitly requested. Clearly state the final answer on the last line using the exact format specified below.

### Output Format
Respond in the following strict format:

layout_id: id

<step-by-step calculations>

*Final answer*: <angle_deg>

Where <angle_deg> is a float rounded to three decimal places, representing the smallest absolute angle in degrees. For example: *Final answer*: 47.253
"""

placement = """
Given the {room_type} layout in {format} format below, check if the rectangle object '{object_name}' (Width={object_width}m, Depth={object_depth}m) can fit fully inside the room. The rectangle may be rotated at any angle.
Rectangle must not overlap with other objects and openings apart from floor soft coverings, but may occupy all free space. Ignore passages, door swings, or clearance requirements.

Room layout:
{room}

Begin with a concise checklist (3-7 bullets) of the conceptual steps necessary for determining if placement is possible. Then, carefully walk through each reasoning step required to evaluate fit.

If the format, object names, or required input data are missing, invalid, or inconsistent, reply with:
*Final answer*: ERROR

Limit your output to the step-by-step reasoning only, and do not include any internal reasoning unless explicitly requested. Clearly state the final answer on the last line using the exact format specified below.

### Output Format
Respond in the following strict format:

layout_id: id

<step-by-step calculations>

*Final answer*: True/False
"""

repositioning = """
Given the {room_type} layout in {format} format below, calculate how far the object '{object_to_move}' can be moved in the '{direction}' direction until it touches another object or the boundary of a room.
Use the Euclidean distance in meters between the centroids of the object's initial position and its new position after the movement.
The object must remain fully within room boundaries and not overlap any objects during the move apart from floor soft coverings.

Room layout:
{room}

Begin with a concise checklist (3-7 bullets) of the conceptual steps necessary for calculating the maximum valid movement. Then, carefully walk through each reasoning step required to compute the distance.

If the format, object names, direction, or required input data are missing, invalid, or inconsistent, reply with:
*Final answer*: ERROR

Limit your output to the step-by-step reasoning only, and do not include any internal reasoning unless explicitly requested. Clearly state the final answer on the last line using the exact format specified below.

### Output Format
Respond in the following strict format:

layout_id: id

<step-by-step calculations>

*Final answer*: <distance>

Where <distance> is a float rounded to three decimal places, representing meters moved (return 0.000 if already touching in that direction).
"""


# The door, window, nightstand, table lamp, chair, and mirror have relatively small areas and will not significantly impact the overall free area calculation.

SYSTEM_PROMPT = "Even if the task seems complex, always try to provide a final answer. Do not respond with 'ERROR' because of complexity. If needed, use the shoelace formula to calculate centroids. "

SYSTEM_PROMPTS = {
    "free_space": SYSTEM_PROMPT
    + (
        "Ignore ceiling-only fixtures (lights, chandeliers, fans, pendants, etc.) and all openings (doors and windows). "
        "Consider all other objects when performing calculations."
    ),
    "max_box": SYSTEM_PROMPT
    + ("Ignore ceiling-only fixtures (lights, chandeliers, fans, pendants, etc.). " "Rectangle may overlap floor soft coverings (rug, carpet, mat, doormat, runner, etc.)."),
    "shortest_path": SYSTEM_PROMPT
    + ("Ignore ceiling-only fixtures (lights, chandeliers, fans, pendants, etc.). Path may overlap floor soft coverings (rug, carpet, mat, doormat, runner, etc.)."),
    "pair_distance": SYSTEM_PROMPT,
    "obstruction": SYSTEM_PROMPT,
    "view_angle": SYSTEM_PROMPT,
    "placement": SYSTEM_PROMPT + ("Rectangle may overlap floor soft coverings (rug, carpet, mat, doormat, runner, etc.)."),
    "repositioning": SYSTEM_PROMPT + ("Object may overlap floor soft coverings (rug, carpet, mat, doormat, runner, etc.)."),
}

PROMPTS = {
    "pair_distance": pair_distance_question,
    "free_space": free_space_question,
    "max_box": max_box_question,
    "obstruction": obstruction_prompt,
    "shortest_path": shortest_path,
    "view_angle": view_angle,
    "placement": placement,
    "repositioning": repositioning,
}
