#!/usr/bin/env python3
"""Render a top-down plan and a section of the generated scene.

A visual sanity check for the level layout without opening Unity: reads the scene
YAML, walks the transform hierarchy and draws every mesh as an axis-aligned box.

    python3 tools/render_plan.py   -> build/plan_route.png, build/plan_outdoor.png, build/section.png
"""

from __future__ import annotations

import glob
import math
import os
import re

import yaml
from PIL import Image, ImageDraw, ImageFont

from unity_common import ROOT

SCENE = os.path.join(ROOT, "Assets", "Scenes", "FireSafetyTrainer.unity")
OUT_DIR = os.path.join(ROOT, "build")
UNITY_TAG = re.compile(r"^--- !u!(\d+) &(-?\d+).*$")
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

MAT_COLOURS = {
    "FloorTile": (176, 176, 172),
    "FloorCorridor2": (160, 163, 165),
    "FloorOutdoor": (128, 130, 122),
    "WallPaint": (232, 228, 216),
    "WallLower": (150, 156, 160),
    "CeilingPaint": (245, 245, 240),
    "Concrete": (188, 188, 186),
    "StairPaint": (205, 207, 205),
    "Handrail": (215, 220, 226),
    "DoorMetal": (120, 126, 132),
    "DoorGreen": (40, 110, 75),
    "ExtinguisherRed": (190, 40, 32),
    "ExtinguisherBlack": (55, 55, 55),
    "Metal": (185, 190, 195),
    "DarkMetal": (80, 80, 84),
    "Rubber": (40, 40, 40),
    "Trim": (95, 95, 95),
    "SafetyYellow": (244, 196, 30),
    "SignWhite": (250, 250, 246),
    "Charred": (45, 42, 40),
    "Ash": (110, 108, 105),
    "LampPanel": (255, 248, 225),
    "ExitGlow": (50, 200, 110),
    "AlarmStrobe": (240, 70, 50),
    "FenceMetal": (105, 110, 108),
    "Planter": (105, 88, 64),
    "GreenLeaf": (70, 145, 70),
}

CLASS_GO, CLASS_TR, CLASS_RT, CLASS_RENDERER = 1, 4, 224, 23


def load_documents():
    with open(SCENE, encoding="utf-8") as handle:
        lines = handle.read().split("\n")
    docs, current, buffer = [], None, []
    for line in lines:
        match = UNITY_TAG.match(line)
        if match:
            if current:
                docs.append((current[0], current[1], "\n".join(buffer)))
            current, buffer = (int(match.group(1)), int(match.group(2))), []
        elif current is not None:
            buffer.append(line)
    if current:
        docs.append((current[0], current[1], "\n".join(buffer)))
    parsed = {}
    for class_id, file_id, text in docs:
        try:
            parsed[file_id] = (class_id, yaml.safe_load(text))
        except yaml.YAMLError:
            parsed[file_id] = (class_id, None)
    return parsed


def material_names():
    names = {}
    for path in glob.glob(os.path.join(ROOT, "Assets", "Materials", "*.mat")):
        name = os.path.splitext(os.path.basename(path))[0]
        with open(path + ".meta", encoding="utf-8") as handle:
            match = re.search(r"^guid:\s*([0-9a-f]{32})$", handle.read(), re.MULTILINE)
        if match:
            names[match.group(1)] = name
    return names


def matmul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def matvec(m, v):
    return [sum(m[i][k] * v[k] for k in range(3)) for i in range(3)]


def local_rot(body):
    """Rotation matrix from the quaternion in the scene file."""
    rot = body.get("m_LocalRotation") or {}
    x, y, z, w = rot.get("x", 0), rot.get("y", 0), rot.get("z", 0), rot.get("w", 1)
    return [
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ]


def gather():
    parsed = load_documents()
    game_objects, transforms, renderers = {}, {}, {}
    for file_id, (class_id, data) in parsed.items():
        if not data:
            continue
        if class_id == CLASS_GO:
            game_objects[file_id] = data["GameObject"]
        elif class_id in (CLASS_TR, CLASS_RT):
            transforms[file_id] = data.get("Transform") or data.get("RectTransform")
        elif class_id == CLASS_RENDERER:
            renderers[file_id] = data["MeshRenderer"]
    materials = material_names()
    boxes = []
    points = []

    def walk(tr_id, parent_rot, parent_pos):
        body = transforms.get(tr_id)
        if body is None:
            return
        local_pos = body.get("m_LocalPosition") or {}
        local_scale = body.get("m_LocalScale") or {}
        pos = [local_pos.get("x", 0.0), local_pos.get("y", 0.0), local_pos.get("z", 0.0)]
        scale = [local_scale.get("x", 1.0), local_scale.get("y", 1.0), local_scale.get("z", 1.0)]
        rot = local_rot(body)

        rotated = matvec(parent_rot, pos)
        world_pos = [rotated[i] + parent_pos[i] for i in range(3)]
        world_rot = matmul(parent_rot, rot)
        world_scale = [sum(abs(world_rot[i][j]) * scale[j] for j in range(3)) for i in range(3)]

        go_id = (body.get("m_GameObject") or {}).get("fileID")
        go = game_objects.get(go_id) or {}
        name = go.get("m_Name", "?")
        material = None
        for component in go.get("m_Component") or []:
            component_id = (component.get("component") or {}).get("fileID")
            if component_id in renderers:
                mats = renderers[component_id].get("m_Materials") or []
                if mats:
                    material = materials.get((mats[0] or {}).get("guid"))
        if name and not name.startswith(("Environment", "Light", "Corridor_", "Stair_", "Wall", "Floor", "Ceiling")):
            points.append({"name": name, "pos": world_pos})
        if material is not None:
            boxes.append({
                "name": name,
                "pos": world_pos,
                "size": world_scale,
                "rot": world_rot,
                "material": material,
            })

        for child in body.get("m_Children") or []:
            walk(child.get("fileID"), world_rot, world_pos)

    for tr_id, body in transforms.items():
        if (body.get("m_Father") or {}).get("fileID", 0) == 0:
            walk(tr_id, [[1, 0, 0], [0, 1, 0], [0, 0, 1]], [0, 0, 0])
    return boxes, points


def footprint(box):
    """Axis-aligned X/Z extent of a box, allowing for 90-degree rotations."""
    half = [box["size"][0] / 2.0, box["size"][2] / 2.0]
    corners = []
    for sx in (-1, 1):
        for sz in (-1, 1):
            p = matvec(box["rot"], [sx * half[0], 0.0, sz * half[1]])
            corners.append((box["pos"][0] + p[0], box["pos"][2] + p[2]))
    xs = [c[0] for c in corners]
    zs = [c[1] for c in corners]
    return min(xs), min(zs), max(xs), max(zs)


def elevation(box):
    half = [box["size"][1] / 2.0, box["size"][2] / 2.0]
    corners = []
    for sy in (-1, 1):
        for sz in (-1, 1):
            p = matvec(box["rot"], [0.0, sy * half[0], sz * half[1]])
            corners.append((box["pos"][2] + p[2], box["pos"][1] + p[1]))
    zs = [c[0] for c in corners]
    ys = [c[1] for c in corners]
    return min(zs), min(ys), max(zs), max(ys)


def colour_for(box):
    material = box["material"]
    if material.startswith("Sign_"):
        return (25, 130, 80)
    return MAT_COLOURS.get(material, (205, 205, 205))


def render(boxes, points, path, bounds, project, width, label, minimum=0.06, markers=(),
           y_axis="down"):
    lo_a, lo_b, hi_a, hi_b = bounds
    span = hi_a - lo_a
    scale = width / span
    height = max(160, int((hi_b - lo_b) * scale) + 46)
    image = Image.new("RGB", (width, height), (252, 252, 250))
    draw = ImageDraw.Draw(image, "RGBA")

    def to_px(a, b):
        if y_axis == "up":          # sections: larger value higher on the image
            return ((a - lo_a) * scale + 14, (hi_b - b) * scale + 26)
        return ((a - lo_a) * scale + 14, (b - lo_b) * scale + 26)

    ordered = sorted(boxes, key=lambda b: (b["pos"][1] > 2.4, b["size"][1]))
    for box in ordered:
        if min(box["size"]) < minimum:
            continue
        a0, b0, a1, b1 = project(box)
        p0 = to_px(a0, b0)
        p1 = to_px(a1, b1)
        if abs(p1[0] - p0[0]) < 1 and abs(p1[1] - p0[1]) < 1:
            continue
        fill = colour_for(box)
        alpha = 235 if box["size"][1] < 2.4 else 120
        draw.rectangle([min(p0[0], p1[0]), min(p0[1], p1[1]),
                        max(p0[0], p1[0]), max(p0[1], p1[1])], fill=fill + (alpha,),
                       outline=(70, 70, 70, 110))

    small = ImageFont.truetype(FONT_BOLD, 13)
    for point in points:
        name, pos = point["name"], point["pos"]
        for marker in markers:
            if marker.lower() in name.lower():
                px = to_px(pos[0], pos[2])
                draw.ellipse([px[0] - 4, px[1] - 4, px[0] + 4, px[1] + 4],
                             fill=(200, 25, 25, 255))
                draw.text((px[0] + 6, px[1] - 6), name, font=small, fill=(150, 10, 10, 255))
                break

    font = ImageFont.truetype(FONT_BOLD, 20)
    draw.rectangle([0, height - 34, width, height], fill=(255, 255, 255, 255))
    draw.text((14, height - 30), label, font=font, fill=(20, 20, 20))
    image.save(path)
    print("wrote", os.path.relpath(path, ROOT))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    boxes, points = gather()
    print("mesh objects:", len(boxes), "named objects:", len(points))

    route = ("PlayerStart", "Alarm", "Flame", "Fire", "Smoke", "Checkpoint", "ExitDoor",
             "StoreDoor", "Lift", "Assembly")
    render(boxes, points, os.path.join(OUT_DIR, "plan_route.png"), (-5.0, -4.5, 7.0, 45.0),
           footprint, 560,
           "Plan X/Z  -  corridor 1 (top) -> stair -> corridor 2 (bottom)", markers=route)
    render(boxes, points, os.path.join(OUT_DIR, "plan_outdoor.png"), (-9.0, 42.0, 9.0, 60.0),
           footprint, 760,
           "Plan X/Z  -  exit, assembly point", markers=route)
    render(boxes, points, os.path.join(OUT_DIR, "section.png"), (-3.0, -4.2, 46.0, 3.5),
           elevation, 1500,
           "Section Z/Y  -  stairs down from corridor 1 to corridor 2", y_axis="up")
    render(boxes, points, os.path.join(OUT_DIR, "section_stairs.png"), (17.0, -4.2, 33.0, 3.6),
           elevation, 900,
           "Section Z/Y  -  stairwell close-up", y_axis="up")


if __name__ == "__main__":
    main()
