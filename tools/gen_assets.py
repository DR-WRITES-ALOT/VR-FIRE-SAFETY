#!/usr/bin/env python3
"""Generate the project's textures, audio, materials and .meta files.

Run from the repository root:

    python3 tools/gen_assets.py

Everything is produced procedurally so the project stays free of third-party
art/audio assets. Output goes to Assets/Textures/Signs, Assets/Resources/Audio and
Assets/Materials.
"""

from __future__ import annotations

import math
import os
import struct
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from unity_common import (
    ROOT,
    col,
    fmt,
    guid_for,
    project_path,
    sync_all_metas,
    v3,
    write_meta,
    write_text,
)

FONT_DIR = os.path.join(ROOT, "Assets", "Fonts")
SIGN_DIR = "Assets/Textures/Signs"

GREEN = (11, 122, 59)
DARK_GREEN = (0, 92, 43)
WHITE = (245, 245, 240)
RED = (196, 30, 36)
DARK = (28, 28, 30)
YELLOW = (246, 190, 20)
BLUE = (20, 70, 150)


# --------------------------------------------------------------------------- #
# Drawing helpers
# --------------------------------------------------------------------------- #

def font(size: int, bold: bool = True):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


def fit_font(draw, text, max_width, max_height, start=90, bold=True):
    size = start
    while size > 8:
        f = font(size, bold)
        box = draw.multiline_textbbox((0, 0), text, font=f, spacing=int(size * 0.25))
        if box[2] - box[0] <= max_width and box[3] - box[1] <= max_height:
            return f
        size -= 2
    return font(8, bold)


def center_text(draw, text, box, f, fill, spacing=None):
    x0, y0, x1, y1 = box
    spacing = spacing if spacing is not None else int(f.size * 0.22)
    box_t = draw.multiline_textbbox((0, 0), text, font=f, align="center", spacing=spacing)
    tw, th = box_t[2] - box_t[0], box_t[3] - box_t[1]
    draw.multiline_text(
        (x0 + (x1 - x0 - tw) / 2, y0 + (y1 - y0 - th) / 2 - box_t[1]),
        text,
        font=f,
        fill=fill,
        align="center",
        spacing=spacing,
    )


def rounded(draw, box, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def draw_runner(draw, cx, cy, s, color, facing=1):
    """Very simple running figure pictogram (scaled by s)."""
    lw = max(3, int(s * 0.16))
    head_r = s * 0.15
    draw.ellipse(
        [cx + facing * s * 0.10 - head_r, cy - s * 0.62 - head_r,
         cx + facing * s * 0.10 + head_r, cy - s * 0.62 + head_r],
        fill=color,
    )
    torso_top = (cx + facing * s * 0.04, cy - s * 0.42)
    hip = (cx - facing * s * 0.04, cy + s * 0.02)
    draw.line([torso_top, hip], fill=color, width=lw)
    # arms
    draw.line([(cx + facing * s * 0.02, cy - s * 0.32), (cx + facing * s * 0.34, cy - s * 0.12)], fill=color, width=lw)
    draw.line([(cx + facing * s * 0.02, cy - s * 0.28), (cx - facing * s * 0.30, cy - s * 0.10)], fill=color, width=lw)
    # legs
    draw.line([hip, (cx + facing * s * 0.36, cy + s * 0.28), (cx + facing * s * 0.42, cy + s * 0.60)], fill=color, width=lw, joint="curve")
    draw.line([hip, (cx - facing * s * 0.26, cy + s * 0.20), (cx - facing * s * 0.40, cy + s * 0.52)], fill=color, width=lw, joint="curve")


def draw_bell(draw, cx, cy, s, color):
    lw = max(3, int(s * 0.10))
    draw.arc([cx - s, cy - s * 0.9, cx + s, cy + s * 0.9], start=200, end=340, fill=color, width=lw)
    draw.line([(cx - s * 0.82, cy + s * 0.45), (cx + s * 0.82, cy + s * 0.45)], fill=color, width=lw)
    draw.line([(cx - s, cy + s * 0.45), (cx - s, cy + s * 0.65)], fill=color, width=lw)
    draw.line([(cx + s, cy + s * 0.45), (cx + s, cy + s * 0.65)], fill=color, width=lw)
    draw.ellipse([cx - s * 0.14, cy + s * 0.55, cx + s * 0.14, cy + s * 0.83], fill=color)


def draw_flame(draw, cx, cy, s, fill=(240, 100, 20)):
    pts = []
    for i in range(30):
        t = i / 29.0
        angle = math.pi * 2 * t
        r = s * (0.7 + 0.3 * math.sin(angle * 3))
        x = cx + math.cos(angle) * r * 0.65
        y = cy - math.sin(angle) * r * (1.25 if math.sin(angle) > 0 else 0.8)
        pts.append((x, y))
    draw.polygon(pts, fill=fill)


def draw_lift(draw, cx, cy, s, color):
    lw = max(3, int(s * 0.08))
    draw.rectangle([cx - s * 0.6, cy - s * 0.8, cx + s * 0.6, cy + s * 0.8], outline=color, width=lw)
    draw.line([(cx, cy - s * 0.8), (cx, cy + s * 0.8)], fill=color, width=lw)
    draw.line([(cx - s * 0.28, cy - s * 0.1), (cx - s * 0.28, cy + s * 0.45)], fill=color, width=lw)
    draw.polygon([(cx - s * 0.42, cy + s * 0.2), (cx - s * 0.14, cy + s * 0.2), (cx - s * 0.28, cy + s * 0.5)], fill=color)
    draw.line([(cx + s * 0.28, cy + s * 0.45), (cx + s * 0.28, cy - s * 0.1)], fill=color, width=lw)
    draw.polygon([(cx + s * 0.14, cy + s * 0.15), (cx + s * 0.42, cy + s * 0.15), (cx + s * 0.28, cy - s * 0.15)], fill=color)


def arrow(draw, x0, y0, x1, y1, color, width):
    draw.line([(x0, y0), (x1, y1)], fill=color, width=width)
    ang = math.atan2(y1 - y0, x1 - x0)
    head = width * 2.2
    for delta in (2.6, -2.6):
        draw.line(
            [(x1, y1), (x1 + head * math.cos(ang + delta / 2 * 2), y1 + head * math.sin(ang + delta / 2 * 2))],
            fill=color,
            width=width,
        )


def wrap_lines(draw, text, f, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        trial = (current + " " + word).strip()
        box = draw.textbbox((0, 0), trial, font=f)
        if box[2] - box[0] <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def fit_line(draw, text, x0, y0, x1, y1, start=48, bold=True, fill=(0, 0, 0), spacing=None,
             max_lines=1):
    """Draw text fitted inside the box, centred, wrapping to at most max_lines."""
    size = start
    while size > 8:
        f = font(size, bold)
        lines = wrap_lines(draw, text, f, max(20, (x1 - x0)))
        gap = int(size * 0.25) if spacing is None else spacing
        block = "\n".join(lines)
        box = draw.multiline_textbbox((0, 0), block, font=f, spacing=gap)
        if len(lines) <= max_lines and box[2] - box[0] <= x1 - x0 and box[3] - box[1] <= y1 - y0:
            center_text(draw, block, (x0, y0, x1, y1), f, fill, gap)
            return f
        size -= 2
    center_text(draw, text, (x0, y0, x1, y1), font(8, bold), fill, spacing or 2)
    return font(8, bold)


def new_sign(w, h, bg):
    img = Image.new("RGB", (w, h), bg)
    return img, ImageDraw.Draw(img)


def save_sign(name, img):
    rel = f"{SIGN_DIR}/{name}.png"
    os.makedirs(project_path(SIGN_DIR), exist_ok=True)
    img.save(project_path(rel), optimize=True)
    write_meta(rel, "texture")
    return rel


# --------------------------------------------------------------------------- #
# Signage
# --------------------------------------------------------------------------- #

def sign_exit(name="exit_right", facing=1):
    img, d = new_sign(1024, 512, GREEN)
    rounded(d, (16, 16, 1008, 496), 28, outline=WHITE, width=8)
    draw_runner(d, 430, 250, 150, WHITE, facing=-facing)
    # door
    d.rectangle([640, 150, 760, 400], outline=WHITE, width=12)
    d.rectangle([650, 160, 750, 400], fill=(11, 122, 59))
    d.ellipse([716, 265, 732, 281], fill=WHITE)
    arrow(d, 790, 275, 930, 275, WHITE, 16)
    f = font(92)
    center_text(d, "EXIT", (60, 380, 500, 480), f, WHITE)
    return save_sign(name, img)


def sign_exit_plain():
    img, d = new_sign(1024, 512, GREEN)
    rounded(d, (16, 16, 1008, 496), 28, outline=WHITE, width=8)
    draw_runner(d, 430, 250, 150, WHITE, facing=-1)
    d.rectangle([640, 150, 760, 400], outline=WHITE, width=12)
    d.rectangle([650, 160, 750, 400], fill=GREEN)
    d.ellipse([716, 265, 732, 281], fill=WHITE)
    center_text(d, "EXIT", (60, 380, 500, 480), font(92), WHITE)
    return save_sign("exit_sign", img)


def sign_training_fire():
    img, d = new_sign(512, 512, (250, 246, 236))
    rounded(d, (12, 12, 500, 500), 20, outline=(226, 150, 20), width=14)
    draw_flame(d, 256, 190, 110, fill=(226, 120, 25))
    fit_line(d, "TRAINING FIRE", 30, 300, 482, 356, start=44, fill=DARK)
    fit_line(d, "Contained in a metal bin", 30, 358, 482, 400, start=24, bold=False, fill=(70, 70, 70))
    fit_line(d, "Do not touch", 30, 402, 482, 452, start=30, fill=(196, 30, 36))
    return save_sign("training_fire", img)


def sign_references():
    img, d = new_sign(1024, 768, WHITE)
    d.rectangle([0, 0, 1024, 104], fill=(40, 40, 45))
    center_text(d, "REFERENCES", (20, 12, 1004, 92), font(52), WHITE)
    from gen_assets_refs import REFERENCE_LINES
    for i, (line, sub) in enumerate(REFERENCE_LINES):
        column = i // 5
        row = i % 5
        x = 34 + column * 500
        y = 124 + row * 116
        d.multiline_text((x, y), line, font=font(19), fill=DARK, spacing=2)
        if len(sub) > 52:
            sub = sub[:49] + "..."
        d.multiline_text((x, y + 46), sub, font=font(15, bold=False), fill=(85, 85, 85))
    fit_line(d, "This simulation is educational only and is not a substitute for certified training.",
             30, 714, 994, 752, start=21, bold=False, fill=(90, 90, 90))
    return save_sign("references", img)


def sign_assembly():
    img, d = new_sign(1024, 768, GREEN)
    rounded(d, (16, 16, 1008, 752), 30, outline=WHITE, width=10)
    # three people
    for i, x in enumerate((300, 512, 724)):
        draw_runner(d, x, 300, 96, WHITE, facing=1 if i % 2 else -1)
    f = font(86)
    center_text(d, "ASSEMBLY POINT", (40, 430, 984, 560), f, WHITE)
    f2 = font(44)
    center_text(d, "Report here after evacuation", (40, 560, 984, 640), f2, WHITE)
    return save_sign("assembly_point", img)


def sign_assembly_direction():
    img, d = new_sign(1024, 320, GREEN)
    rounded(d, (10, 10, 1014, 310), 18, outline=WHITE, width=6)
    arrow(d, 50, 160, 210, 160, WHITE, 22)
    fit_line(d, "ASSEMBLY POINT", 236, 40, 1000, 270, start=104, fill=WHITE)
    return save_sign("assembly_direction", img)


def sign_fire_action():
    img, d = new_sign(768, 1024, WHITE)
    d.rectangle([0, 0, 768, 190], fill=RED)
    f = font(80)
    center_text(d, "IN CASE OF FIRE", (20, 20, 748, 170), f, WHITE)
    lines = [
        ("1", "RAISE THE ALARM"),
        ("2", "CALL 112"),
        ("3", "EVACUATE BY THE STAIRS"),
        ("4", "DO NOT USE THE LIFT"),
        ("5", "GO TO THE ASSEMBLY POINT"),
    ]
    y = 250
    for num, text in lines:
        d.ellipse([50, y, 140, y + 90], fill=DARK)
        center_text(d, num, (50, y, 140, y + 90), font(52), WHITE)
        f = fit_font(d, text, 560, 120, start=52)
        d.multiline_text((172, y + 45 - f.size * 0.6), text, font=f, fill=DARK)
        y += 140
    f = font(34, bold=False)
    d.multiline_text((50, y + 20), "Keep low if smoke is present, but never\nenter dense smoke. Close doors behind you.",
                     font=f, fill=DARK, spacing=8)
    return save_sign("fire_action_notice", img)


def sign_alarm_point():
    img, d = new_sign(512, 512, RED)
    rounded(d, (14, 14, 498, 498), 22, outline=WHITE, width=8)
    draw_bell(d, 256, 200, 110, WHITE)
    f = font(58)
    center_text(d, "FIRE ALARM", (30, 330, 482, 410), f, WHITE)
    f2 = font(34)
    center_text(d, "PULL THE HANDLE", (30, 410, 482, 470), f2, WHITE)
    return save_sign("alarm_point", img)


def sign_pass():
    img, d = new_sign(1024, 768, WHITE)
    d.rectangle([0, 0, 1024, 130], fill=RED)
    center_text(d, "PASS: USE AN EXTINGUISHER", (20, 15, 1004, 118), fit_font(d, "PASS: USE AN EXTINGUISHER", 950, 90, start=64), WHITE)
    panels = [
        ("PULL", "the pin"),
        ("AIM", "at the base"),
        ("SQUEEZE", "the handle"),
        ("SWEEP", "across the base"),
    ]
    box_w, box_h = 236, 520
    for i, (title, sub) in enumerate(panels):
        x0 = 26 + i * (box_w + 12)
        rounded(d, (x0, 160, x0 + box_w, 160 + box_h), 18, fill=(242, 242, 238), outline=(200, 200, 196), width=3)
        cx = x0 + box_w / 2
        cy = 330
        if i == 0:
            # pin pulled from handle
            d.rectangle([cx - 70, cy - 20, cx + 70, cy + 40], outline=DARK, width=8)
            d.line([(cx + 80, cy - 70), (cx + 20, cy - 10)], fill=DARK, width=10)
            d.ellipse([cx + 70, cy - 92, cx + 110, cy - 52], outline=DARK, width=8)
        elif i == 1:
            draw_flame(d, cx, cy + 30, 90)
            d.line([(cx - 100, cy - 80), (cx - 20, cy + 40)], fill=DARK, width=12)
            d.rectangle([cx - 115, cy - 105, cx - 80, cy - 60], fill=DARK)
        elif i == 2:
            d.rectangle([cx - 60, cy - 70, cx + 20, cy + 20], outline=DARK, width=8)
            d.line([(cx - 60, cy - 30), (cx + 20, cy - 30)], fill=DARK, width=8)
            d.arc([cx - 30, cy + 5, cx + 70, cy + 90], start=200, end=340, fill=DARK, width=10)
        else:
            draw_flame(d, cx + 50, cy + 30, 70)
            d.arc([cx - 130, cy - 40, cx + 130, cy + 140], start=200, end=270, fill=DARK, width=12)
            arrow(d, cx - 90, cy + 60, cx - 20, cy - 10, DARK, 10)
        f = fit_font(d, title, box_w - 20, 60, start=46)
        center_text(d, title, (x0 + 8, 545, x0 + box_w - 8, 605), f, RED)
        f2 = fit_font(d, sub, box_w - 20, 60, start=32)
        center_text(d, sub, (x0 + 8, 605, x0 + box_w - 8, 660), f2, DARK)
    note = "Only for small, contained fires - alarm raised, escape route clear, you are trained."
    center_text(d, note, (30, 690, 994, 740), fit_font(d, note, 950, 46, start=26, bold=False), DARK)
    return save_sign("pass_poster", img)


def sign_extinguisher_types():
    img, d = new_sign(1024, 768, WHITE)
    d.rectangle([0, 0, 1024, 120], fill=DARK)
    center_text(d, "KNOW YOUR EXTINGUISHER", (20, 10, 1004, 110), font(62), WHITE)
    rows = [
        ("WATER", "Class A solids only", (30, 90, 170)),
        ("FOAM", "Class A and B, within rating", (200, 120, 20)),
        ("ABC POWDER", "Class A, B and C, within rating", (196, 30, 36)),
        ("CO2", "Flammable liquids, electrical", (60, 60, 64)),
        ("WET CHEMICAL", "Cooking oil and fat fires (Class F)", (150, 90, 30)),
        ("CLASS D POWDER", "Combustible metals only", (90, 70, 150)),
    ]
    y = 150
    for name, desc, colour in rows:
        d.rectangle([40, y, 90, y + 82], fill=colour)
        d.multiline_text((112, y + 6), name, font=font(44), fill=DARK)
        d.multiline_text((112, y + 54), desc, font=font(28, bold=False), fill=(70, 70, 70))
        y += 96
    fit_line(d, "Indian classes: A solids, B flammable liquids, C flammable gases, D metals, F cooking oils.",
             30, 724, 994, 760, start=24, bold=False, fill=(60, 60, 60))
    return save_sign("extinguisher_types_poster", img)


def sign_mask_poster():
    img, d = new_sign(1024, 768, WHITE)
    d.rectangle([0, 0, 1024, 116], fill=DARK)
    fit_line(d, "MASKS DO NOT GIVE YOU CLEAN AIR", 20, 10, 1004, 106, start=54, fill=WHITE)
    cards = [
        ("Cloth / surgical", ["No protection", "from fire smoke"], RED),
        ("N95 / KN95", ["Particles only", "not toxic gases"], RED),
        ("Fire escape hood", ["Short escape", "only"], (190, 110, 15)),
        ("Firefighter SCBA", ["Trained", "firefighters"], GREEN),
    ]
    w, h = 236, 470
    for i, (title, subs, colour) in enumerate(cards):
        x0 = 14 + i * (w + 8)
        rounded(d, (x0, 150, x0 + w, 150 + h), 16, fill=(244, 244, 240), outline=(205, 205, 200), width=3)
        cx = x0 + w / 2
        d.ellipse([cx - 56, 210, cx + 56, 330], outline=DARK, width=8)
        if i == 0:
            d.rectangle([cx - 62, 262, cx + 62, 312], fill=(222, 222, 216), outline=DARK, width=6)
        elif i == 1:
            d.rounded_rectangle([cx - 56, 268, cx + 56, 318], radius=18, fill=WHITE, outline=DARK, width=6)
            d.arc([cx - 56, 288, cx + 56, 344], start=200, end=340, fill=DARK, width=6)
        elif i == 2:
            d.arc([cx - 74, 186, cx + 74, 354], start=180, end=360, fill=colour, width=12)
            d.rectangle([cx - 56, 268, cx + 56, 318], fill=WHITE, outline=DARK, width=6)
        else:
            d.rounded_rectangle([cx + 58, 224, cx + 92, 340], radius=16, fill=(70, 90, 110), outline=DARK, width=5)
            d.line([(cx + 70, 224), (cx + 70, 190)], fill=DARK, width=8)
            d.rectangle([cx - 56, 268, cx + 56, 318], fill=WHITE, outline=DARK, width=6)
        fit_line(d, title, x0 + 8, 346, x0 + w - 8, 418, start=30, fill=DARK, max_lines=2)
        for j, sub in enumerate(subs):
            fit_line(d, sub, x0 + 8, 422 + j * 38, x0 + w - 8, 456 + j * 38, start=24, fill=colour,
                     bold=False, max_lines=2)
    d.line([(30, 634), (994, 634)], fill=(190, 190, 186), width=3)
    fit_line(d, "None of these filter carbon monoxide or add oxygen.", 30, 644, 994, 690, start=32, fill=DARK)
    fit_line(d, "Never delay evacuation to look for a mask. Only firefighters in full protective equipment enter a smoke-filled building.",
             30, 694, 994, 754, start=25, bold=False, fill=DARK, max_lines=2)
    return save_sign("mask_poster", img)


def sign_extinguisher_label(name, title, subtitle, colour, classes):
    img, d = new_sign(512, 256, (245, 245, 240))
    rounded(d, (6, 6, 506, 250), 14, outline=(210, 210, 205), width=4)
    d.rectangle([6, 6, 96, 250], fill=colour)
    for i, letter in enumerate(classes):
        d.ellipse([20, 30 + i * 62, 84, 94 + i * 62], fill=WHITE)
        center_text(d, letter, (20, 30 + i * 62, 84, 94 + i * 62), font(34), colour)
    f = fit_font(d, title, 370, 90, start=54)
    d.multiline_text((120, 40), title, font=f, fill=DARK)
    f2 = fit_font(d, subtitle, 370, 100, start=30)
    d.multiline_text((120, 140), subtitle, font=f2, fill=(70, 70, 70), spacing=4)
    return save_sign(name, img)


def sign_call_112():
    img, d = new_sign(512, 512, RED)
    rounded(d, (14, 14, 498, 498), 22, outline=WHITE, width=8)
    # handset
    d.arc([150, 130, 362, 300], start=200, end=340, fill=WHITE, width=26)
    d.rounded_rectangle([140, 120, 196, 190], radius=18, fill=WHITE)
    d.rounded_rectangle([316, 120, 372, 190], radius=18, fill=WHITE)
    fit_line(d, "112", 40, 280, 472, 410, start=120, fill=WHITE)
    fit_line(d, "EMERGENCY", 40, 400, 472, 452, start=42, fill=WHITE)
    return save_sign("call_112", img)


def sign_no_lift():
    img, d = new_sign(768, 1024, WHITE)
    d.rectangle([0, 0, 768, 150], fill=RED)
    center_text(d, "DO NOT USE THE LIFT", (20, 20, 748, 130), font(58), WHITE)
    draw_lift(d, 384, 470, 170, DARK)
    d.ellipse([170, 250, 598, 678], outline=RED, width=26)
    d.line([(230, 320), (540, 610)], fill=RED, width=26)
    f = font(52)
    center_text(d, "USE THE STAIRS", (30, 730, 738, 820), f, GREEN)
    f2 = font(30, bold=False)
    center_text(d, "Lifts can stop or open onto the fire floor.", (30, 830, 738, 900), f2, DARK)
    return save_sign("no_lift", img)


def sign_stairs():
    img, d = new_sign(768, 512, GREEN)
    rounded(d, (12, 12, 756, 500), 24, outline=WHITE, width=8)
    fit_line(d, "STAIRS", 40, 40, 560, 150, start=92, fill=WHITE)
    fit_line(d, "KEEP RIGHT - HOLD THE HANDRAIL", 40, 160, 560, 250, start=36, fill=WHITE, max_lines=2)
    for i in range(4):
        d.rectangle([50 + i * 62, 440 - i * 46, 112 + i * 62, 492 - i * 46], fill=WHITE)
    arrow(d, 660, 430, 660, 180, WHITE, 20)
    return save_sign("stairs_sign", img)


def sign_fire_door():
    img, d = new_sign(768, 512, BLUE)
    rounded(d, (12, 12, 756, 500), 20, outline=WHITE, width=8)
    f = font(64)
    center_text(d, "FIRE DOOR", (40, 70, 728, 190), f, WHITE)
    f2 = font(46)
    center_text(d, "KEEP CLOSED", (40, 210, 728, 320), f2, YELLOW)
    f3 = font(30, bold=False)
    center_text(d, "Close doors behind you to slow smoke.", (40, 340, 728, 450), f3, WHITE)
    return save_sign("fire_door", img)


def sign_smoke_warning():
    img, d = new_sign(768, 512, (250, 246, 236))
    rounded(d, (12, 12, 756, 500), 20, outline=RED, width=14)
    # smoke puffs
    for i, (x, y, r) in enumerate([(240, 250, 80), (350, 210, 95), (470, 255, 85), (560, 300, 55)]):
        d.ellipse([x - r, y - r, x + r, y + r], outline=(110, 110, 115), width=12)
    fit_line(d, "DENSE SMOKE", 30, 34, 738, 140, start=66, fill=RED)
    fit_line(d, "DO NOT ENTER", 30, 352, 738, 432, start=48, fill=DARK)
    fit_line(d, "Smoke is toxic. Close the door and use the escape route.",
             24, 434, 744, 492, start=26, bold=False, fill=DARK)
    return save_sign("smoke_warning", img)


def sign_first_aid():
    img, d = new_sign(768, 1024, WHITE)
    d.rectangle([0, 0, 768, 150], fill=(198, 40, 40))
    d.rectangle([50, 55, 150, 105], fill=WHITE)
    d.rectangle([84, 26, 116, 134], fill=WHITE)
    fit_line(d, "FIRST AID", 170, 14, 750, 136, start=64, fill=WHITE)
    sections = [
        ("BURNS", ["Cool under cool running", "water for 20 minutes.", "No ice, paste, oil or turmeric.", "Do not burst blisters.", "Cover loosely, call 112 if severe."]),
        ("SMOKE INHALATION", ["Never re-enter to rescue.", "Move to fresh air only if safe.", "Call 112, monitor breathing.", "Unresponsive and not breathing", "normally? Follow dispatch CPR advice."]),
    ]
    y = 190
    for title, lines in sections:
        d.multiline_text((52, y), title, font=font(38), fill=(198, 40, 40))
        y += 58
        for line in lines:
            d.multiline_text((52, y), line, font=font(26, bold=False), fill=DARK)
            y += 40
        y += 40
    return save_sign("first_aid_poster", img)


def sign_info_board():
    img, d = new_sign(1024, 640, (242, 242, 238))
    d.rectangle([0, 0, 1024, 110], fill=(40, 40, 45))
    center_text(d, "FIRE SAFETY TRAINING POINT", (20, 12, 1004, 100), font(56), WHITE)
    f = font(30, bold=False)
    text = (
        "This corridor is part of a training route.\n\n"
        "1  Raise the alarm at the red call point.\n"
        "2  Read the mask and extinguisher guidance.\n"
        "3  Practise PASS only on the small contained fire.\n"
        "4  Evacuate by the stairs to the assembly point.\n\n"
        "Lift access is not used during an evacuation."
    )
    d.multiline_text((60, 150), text, font=f, fill=DARK, spacing=10)
    return save_sign("info_board", img)


def generate_signs():
    signs = [sign_exit("exit_right", 1), sign_exit("exit_left", -1), sign_exit_plain(),
             sign_training_fire(), sign_references(), sign_assembly(),
             sign_assembly_direction(), sign_fire_action(), sign_alarm_point(), sign_pass(),
             sign_extinguisher_types(), sign_mask_poster(), sign_no_lift(), sign_stairs(),
             sign_fire_door(), sign_smoke_warning(), sign_first_aid(), sign_info_board(),
             sign_call_112()]
    signs.append(sign_extinguisher_label("ext_water", "WATER", "Class A solids", (30, 90, 170), "A"))
    signs.append(sign_extinguisher_label("ext_foam", "FOAM", "Class A and B", (200, 120, 20), "AB"))
    signs.append(sign_extinguisher_label("ext_abc", "ABC POWDER", "Class A, B and C", (196, 30, 36), "ABC"))
    signs.append(sign_extinguisher_label("ext_co2", "CO2", "Liquids; electrical", (60, 60, 64), "B"))
    signs.append(sign_extinguisher_label("ext_wet", "WET CHEMICAL", "Cooking oil / fat", (150, 90, 30), "F"))
    signs.append(sign_extinguisher_label("ext_d", "CLASS D POWDER", "Combustible metals", (90, 70, 150), "D"))
    return signs


# --------------------------------------------------------------------------- #
# Audio
# --------------------------------------------------------------------------- #

SAMPLE_RATE = 44100


def save_wav(name, samples, sr=SAMPLE_RATE):
    rel = f"Assets/Resources/Audio/{name}.wav"
    os.makedirs(project_path("Assets/Resources/Audio"), exist_ok=True)
    data = np.clip(samples, -1.0, 1.0)
    data = (data * 32000).astype("<i2")
    with wave.open(project_path(rel), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sr)
        handle.writeframes(data.tobytes())
    write_meta(rel, "audio")
    return rel


def fade(samples, attack=0.01, release=0.05):
    n = len(samples)
    a = max(1, int(attack * SAMPLE_RATE))
    r = max(1, int(release * SAMPLE_RATE))
    env = np.ones(n)
    env[:a] = np.linspace(0, 1, a)
    env[-r:] = np.linspace(1, 0, r)
    return samples * env


def lowpass(samples, alpha=0.15):
    out = np.copy(samples)
    for i in range(1, len(out)):
        out[i] = out[i - 1] + alpha * (out[i] - out[i - 1])
    return out


def make_audio():
    rng = np.random.default_rng(7)
    t = np.arange(int(4.0 * SAMPLE_RATE)) / SAMPLE_RATE
    # Two-tone evacuation hooter: 700 Hz / 950 Hz, alternating twice, loop-safe.
    tone = np.where((t % 2.0) < 1.0, 700.0, 950.0)
    phase = 2 * np.pi * np.cumsum(tone) / SAMPLE_RATE
    siren = 0.34 * np.sin(phase)
    pulse = np.minimum(1.0, 6.0 * np.minimum(t % 1.0, 1.0 - (t % 1.0)))
    siren *= 0.65 + 0.35 * pulse
    save_wav("alarm_loop", siren)

    # Fire crackle: filtered noise with random pops and a low rumble.
    n = int(6.0 * SAMPLE_RATE)
    tt = np.arange(n) / SAMPLE_RATE
    noise = rng.normal(0, 1, n)
    crackle = lowpass(noise, 0.25) * 0.18
    pops = (rng.random(n) > 0.9994).astype(float)
    pops = lowpass(pops, 0.4) * 1.2
    rumble = 0.05 * np.sin(2 * np.pi * 58 * tt) + 0.03 * np.sin(2 * np.pi * 91 * tt)
    fire = crackle + pops + rumble
    save_wav("fire_crackle", fade(fire, 0.5, 0.8))

    # Extinguisher discharge hiss.
    n = int(3.0 * SAMPLE_RATE)
    tt = np.arange(n) / SAMPLE_RATE
    hiss = lowpass(rng.normal(0, 1, n), 0.6)
    hiss = np.convolve(hiss, np.ones(6) / 6, mode="same")
    env = np.minimum(1.0, tt / 0.15) * np.exp(-np.maximum(0.0, tt - 0.6) * 0.9)
    save_wav("extinguisher_hiss", fade(hiss * env * 0.7, 0.02, 0.2))

    # UI click.
    n = int(0.09 * SAMPLE_RATE)
    tt = np.arange(n) / SAMPLE_RATE
    click = np.sin(2 * np.pi * 1250 * tt) * np.exp(-tt * 55) * 0.5
    save_wav("ui_click", fade(click, 0.002, 0.02))

    # Success chime.
    n = int(2.2 * SAMPLE_RATE)
    tt = np.arange(n) / SAMPLE_RATE
    chime = np.zeros(n)
    for i, freq in enumerate((523.25, 659.25, 783.99)):
        start = i * 0.22
        env = np.where(tt >= start, np.exp(-np.maximum(0.0, tt - start) * 2.2), 0.0)
        chime += 0.22 * np.sin(2 * np.pi * freq * tt) * env
    save_wav("success_chime", fade(chime, 0.005, 0.4))

    # Heavy door closing thud.
    n = int(0.8 * SAMPLE_RATE)
    tt = np.arange(n) / SAMPLE_RATE
    thud = np.sin(2 * np.pi * 72 * tt) * np.exp(-tt * 9) * 0.7
    thud += lowpass(rng.normal(0, 1, n), 0.1) * np.exp(-tt * 25) * 0.25
    save_wav("door_close", fade(thud, 0.002, 0.1))


# --------------------------------------------------------------------------- #
# Materials
# --------------------------------------------------------------------------- #

STANDARD_SHADER = "{fileID: 46, guid: 0000000000000000f000000000000000, type: 0}"
TEX_ENVS = ["_MainTex", "_BumpMap", "_EmissionMap", "_MetallicGlossMap", "_OcclusionMap",
            "_ParallaxMap", "_DetailMask", "_DetailAlbedoMap", "_DetailNormalMap", "_SpecGlossMap"]


def material_yaml(name, color, metallic=0.0, glossiness=0.3, emission=None, texture_guid=None,
                  emission_texture=None):
    lines = ["%YAML 1.1", "%TAG !u! tag:unity3d.com,2011:", "--- !u!21 &2100000", "Material:",
             "  serializedVersion: 8", "  m_ObjectHideFlags: 0",
             "  m_CorrespondingSourceObject: {fileID: 0}", "  m_PrefabInstance: {fileID: 0}",
             "  m_PrefabAsset: {fileID: 0}", f"  m_Name: {name}",
             f"  m_Shader: {STANDARD_SHADER}", "  m_Parent: {fileID: 0}",
             "  m_ModifiedSerializedProperties: 0"]
    keywords = []
    if emission is not None:
        keywords.append("_EMISSION")
    lines.append("  m_ValidKeywords:" + ("" if keywords else " []"))
    for keyword in keywords:
        lines.append("  - " + keyword)
    lines += ["  m_InvalidKeywords: []",
              "  m_LightmapFlags: 4", "  m_EnableInstancingVariants: 0", "  m_DoubleSidedGI: 0",
              "  m_CustomRenderQueue: -1", "  stringTagMap: {}", "  disabledShaderPasses: []",
              "  m_LockedProperties: ", "  m_SavedProperties:", "    serializedVersion: 3", "    m_TexEnvs:"]
    for env in TEX_ENVS:
        tex = "{fileID: 0}"
        if env == "_MainTex" and texture_guid:
            tex = f"{{fileID: 2800000, guid: {texture_guid}, type: 3}}"
        if env == "_EmissionMap" and emission_texture:
            tex = f"{{fileID: 2800000, guid: {emission_texture}, type: 3}}"
        lines += [f"    - {env}:", f"        m_Texture: {tex}",
                  "        m_Scale: {x: 1, y: 1}", "        m_Offset: {x: 0, y: 0}"]
    lines += ["    m_Ints: []", "    m_Floats:",
              "    - _BumpScale: 1", f"    - _Metallic: {fmt(metallic)}",
              f"    - _Glossiness: {fmt(glossiness)}", "    - _OcclusionStrength: 1",
              "    - _Parallax: 0.02", "    - _DetailNormalMapScale: 1", "    - _UVSec: 0",
              "    - _Mode: 0", "    - _SrcBlend: 1", "    - _DstBlend: 0", "    - _ZWrite: 1",
              "    - _GlossMapScale: 1", "    - _SmoothnessTextureChannel: 0",
              "    - _SpecularHighlights: 1", "    - _GlossyReflections: 1",
              "    - _EmissionScaleUI: 1",
              "    m_Colors:", f"    - _Color: {col(*color)}",
              f"    - _EmissionColor: {col(*(emission or (0, 0, 0)))}",
              "  m_BuildTextureStacks: []"]
    return "\n".join(lines) + "\n"


PALETTE = {
    "FloorTile": dict(color=(0.55, 0.55, 0.53), glossiness=0.32),
    "FloorCorridor2": dict(color=(0.50, 0.51, 0.52), glossiness=0.28),
    "FloorOutdoor": dict(color=(0.40, 0.41, 0.38), glossiness=0.12),
    "WallPaint": dict(color=(0.82, 0.81, 0.76), glossiness=0.15),
    "WallLower": dict(color=(0.35, 0.37, 0.38), glossiness=0.2),
    "CeilingPaint": dict(color=(0.90, 0.90, 0.88), glossiness=0.1),
    "Concrete": dict(color=(0.47, 0.47, 0.46), glossiness=0.18),
    "StairPaint": dict(color=(0.58, 0.59, 0.58), glossiness=0.2),
    "Handrail": dict(color=(0.72, 0.74, 0.76), metallic=0.85, glossiness=0.65),
    "DoorMetal": dict(color=(0.36, 0.37, 0.38), metallic=0.55, glossiness=0.45),
    "DoorGreen": dict(color=(0.08, 0.30, 0.19), metallic=0.1, glossiness=0.35),
    "ExtinguisherRed": dict(color=(0.62, 0.04, 0.03), metallic=0.15, glossiness=0.55),
    "ExtinguisherBlack": dict(color=(0.05, 0.05, 0.05), glossiness=0.3),
    "Metal": dict(color=(0.62, 0.64, 0.67), metallic=0.8, glossiness=0.6),
    "DarkMetal": dict(color=(0.16, 0.16, 0.17), metallic=0.7, glossiness=0.45),
    "Rubber": dict(color=(0.05, 0.05, 0.05), glossiness=0.1),
    "Trim": dict(color=(0.16, 0.16, 0.16), glossiness=0.2),
    "SafetyYellow": dict(color=(0.95, 0.72, 0.05), glossiness=0.3),
    "SignWhite": dict(color=(0.95, 0.95, 0.95), glossiness=0.2),
    "Charred": dict(color=(0.10, 0.09, 0.08), glossiness=0.05),
    "Ash": dict(color=(0.35, 0.34, 0.32), glossiness=0.05),
    "LampPanel": dict(color=(1.0, 0.97, 0.9), emission=(1.4, 1.32, 1.15), glossiness=0.3),
    "ExitGlow": dict(color=(0.1, 0.7, 0.3), emission=(0.4, 1.4, 0.6), glossiness=0.3),
    "AlarmStrobe": dict(color=(0.8, 0.1, 0.05), emission=(1.6, 0.25, 0.1), glossiness=0.4),
    "SmokeDark": dict(color=(0.12, 0.12, 0.13), glossiness=0.05),
    "FenceMetal": dict(color=(0.28, 0.30, 0.29), metallic=0.5, glossiness=0.4),
    "Planter": dict(color=(0.30, 0.25, 0.18), glossiness=0.1),
    "GreenLeaf": dict(color=(0.16, 0.40, 0.16), glossiness=0.2),
}


def generate_materials(sign_textures):
    os.makedirs(project_path("Assets/Materials"), exist_ok=True)
    for name, spec in PALETTE.items():
        rel = f"Assets/Materials/{name}.mat"
        write_text(rel, material_yaml(name, **spec))
        write_meta(rel, "material")
    for sign in sign_textures:
        base = os.path.basename(sign)[:-4]
        name = "Sign_" + base
        rel = f"Assets/Materials/{name}.mat"
        tex_guid = guid_for(sign)
        write_text(rel, material_yaml(name, (1, 1, 1), glossiness=0.25,
                                      emission=(0.55, 0.55, 0.55),
                                      texture_guid=tex_guid, emission_texture=tex_guid))
        write_meta(rel, "material")


def main():
    signs = generate_signs()
    make_audio()
    generate_materials(signs)
    sync_all_metas()
    print(f"Generated {len(signs)} sign textures, 6 audio clips and "
          f"{len(PALETTE) + len(signs)} materials.")


if __name__ == "__main__":
    main()
