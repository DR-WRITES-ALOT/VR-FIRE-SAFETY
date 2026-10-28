#!/usr/bin/env python3
"""Draws Unity-Editor-style images for the project documentation.

These are *reconstructions*: the same layout, panels, colours and content as the real
project, drawn with Pillow because this environment has no Unity Editor to capture from.
They are labelled as reconstructions in the documentation.

Run: python3 tools/make_docs_shots.py   ->  docs/images/*.png
"""

from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "images")
FONT_REG = os.path.join(ROOT, "Assets", "Fonts", "DejaVuSans.ttf")
FONT_BOLD = os.path.join(ROOT, "Assets", "Fonts", "DejaVuSans-Bold.ttf")

W, H = 1600, 900

# palette ---------------------------------------------------------------
EDIT_BG = (56, 56, 56)
EDIT_PANEL = (40, 40, 40)
EDIT_PANEL_2 = (46, 46, 46)
EDIT_BAR = (58, 58, 58)
EDIT_TOPBAR = (28, 28, 28)
EDIT_LINE = (26, 26, 26)
TEXT = (198, 198, 198)
TEXT_DIM = (140, 140, 140)
TEXT_BRIGHT = (228, 228, 228)
SELECT = (44, 93, 135)
SELECT_DIM = (48, 66, 84)
UNITY_BLUE = (33, 150, 243)
AMBER = (242, 160, 61)
RED = (217, 58, 43)
GREEN = (63, 191, 127)
WHITE = (236, 241, 246)
HUD_BG = (14, 19, 26)


def font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def text(draw, xy, s, size=14, colour=TEXT, bold=False, anchor="la"):
    draw.text(xy, s, font=font(size, bold), fill=colour, anchor=anchor)


def rect(draw, box, fill=None, outline=None, width=1, radius=0):
    if radius:
        draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
    else:
        draw.rectangle(box, fill=fill, outline=outline, width=width)


def lerp(a, b, t):
    return a + (b - a) * t


# --------------------------------------------------------------------- #
# The 3D corridor, drawn in perspective
# --------------------------------------------------------------------- #

class View:
    def __init__(self, x0, y0, x1, y1):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        w, h = x1 - x0, y1 - y0
        self.fl = x0 + w * 0.30
        self.fr = x1 - w * 0.30
        self.ft = y0 + h * 0.335
        self.fb = self.ft + h * 0.235
        self.cx = (x0 + x1) / 2
        self.cy = (self.ft + self.fb) / 2

    def wall(self, side, t, v):
        """side: -1 left, +1 right; t depth 0..1; v 0 floor .. 1 ceiling."""
        x = lerp(self.x0 if side < 0 else self.x1, self.fl if side < 0 else self.fr, t)
        y_floor = lerp(self.y1, self.fb, t)
        y_ceil = lerp(self.y0, self.ft, t)
        return (x, lerp(y_floor, y_ceil, v))

    def floor(self, t, u):
        """t depth, u across (0 left edge .. 1 right edge)."""
        xl = lerp(self.x0, self.fl, t)
        xr = lerp(self.x1, self.fr, t)
        y = lerp(self.y1, self.fb, t)
        return (lerp(xl, xr, u), y)

    def ceiling(self, t, u):
        xl = lerp(self.x0, self.fl, t)
        xr = lerp(self.x1, self.fr, t)
        y = lerp(self.y0, self.ft, t)
        return (lerp(xl, xr, u), y)

    def wall_quad(self, side, t0, t1, v0, v1):
        return [self.wall(side, t0, v0), self.wall(side, t0, v1),
                self.wall(side, t1, v1), self.wall(side, t1, v0)]

    def span_quad(self, t0, t1, u0, u1, on_floor):
        f = self.floor if on_floor else self.ceiling
        return [f(t0, u0), f(t0, u1), f(t1, u1), f(t1, u0)]


def draw_corridor(draw, v, mood="normal", fire=True, smoke=False, t_far=0.86):
    w = v.x1 - v.x0
    # end wall
    rect(draw, (v.fl, v.ft, v.fr, v.fb), (146, 144, 138))

    # floor and ceiling
    draw.polygon([(v.x0, v.y1), (v.x1, v.y1), (v.fr, v.fb), (v.fl, v.fb)], fill=(126, 130, 132))
    draw.polygon([(v.x0, v.y0), (v.x1, v.y0), (v.fr, v.ft), (v.fl, v.ft)], fill=(178, 180, 182))

    # floor seam, so the corridor reads as a corridor
    mid_top = ((v.fl + v.fr) / 2, v.fb)
    draw.line([(v.cx, v.y1), mid_top], fill=(112, 116, 118), width=2)

    # walls
    draw.polygon([(v.x0, v.y0), (v.x0, v.y1), (v.fl, v.fb), (v.fl, v.ft)], fill=(206, 203, 197))
    draw.polygon([(v.x1, v.y0), (v.x1, v.y1), (v.fr, v.fb), (v.fr, v.ft)], fill=(188, 185, 179))

    for side in (-1, 1):
        shade = (86, 92, 98) if side < 0 else (78, 84, 90)
        draw.polygon(v.wall_quad(side, 0, 1, 0, 0.30), fill=shade)
        draw.polygon(v.wall_quad(side, 0, 1, 0.295, 0.315), fill=(52, 56, 60))

    # ceiling light panels
    for t in (0.05, 0.22, 0.39, 0.56, 0.73):
        draw.polygon(v.span_quad(t, t + 0.055, 0.38, 0.62, False), fill=(246, 244, 232))

    # doors on the left wall
    for t0, t1 in ((0.30, 0.40), (0.55, 0.63)):
        draw.polygon(v.wall_quad(-1, t0, t1, 0, 0.72), fill=(70, 74, 78))
        draw.polygon(v.wall_quad(-1, t0, t1, 0.69, 0.72), fill=(198, 198, 198))

    if fire:
        # bin + flames on the right, half way down
        base = v.floor(0.60, 0.66)
        size = max(6, int(w * 0.018))
        draw.ellipse((base[0] - size, base[1] - size * 1.5, base[0] + size, base[1] + size * 0.4),
                     fill=(38, 38, 40))
        glow = Image.new("RGBA", (size * 8, size * 8), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        for i in range(7, 0, -1):
            r = size * (0.6 + i * 0.5)
            a = int(26 * (7 - i) / 7 + 8)
            gd.ellipse((size * 4 - r, size * 4 - r, size * 4 + r, size * 4 + r),
                       fill=(255, 140, 40, a))
        draw.bitmap((base[0] - size * 4, base[1] - size * 5), glow, fill=None)
        for i, dx in enumerate((-2, 0, 1, 3)):
            h = size * (1.9 if i % 2 == 0 else 1.3)
            draw.polygon([(base[0] + dx * size * 0.4, base[1]),
                          (base[0] + dx * size * 0.4 - size * 0.5, base[1] - h * 0.55),
                          (base[0] + dx * size * 0.4, base[1] - h),
                          (base[0] + dx * size * 0.4 + size * 0.5, base[1] - h * 0.5)],
                         fill=(255, 170, 60) if i % 2 == 0 else (240, 110, 30))

    if smoke:
        haze = Image.new("RGBA", (v.x1 - v.x0, v.y1 - v.y0), (0, 0, 0, 0))
        hd = ImageDraw.Draw(haze)
        x0, y0 = v.x0, v.y0
        for i, (cx, cy, r, a) in enumerate([
                (v.fl + likely_w(v, 0.10), v.fb - (v.y1 - v.y0) * 0.05, w * 0.10, 120),
                (v.fl + likely_w(v, 0.02), v.fb + (v.y1 - v.y0) * 0.02, w * 0.13, 95),
                (v.fl + likely_w(v, 0.18), v.fb + (v.y1 - v.y0) * 0.09, w * 0.11, 70)]):
            hd.ellipse((cx - x0 - r, cy - y0 - r, cx - x0 + r, cy - y0 + r),
                       fill=(190, 190, 195, a))
        draw.bitmap((v.x0, v.y0), haze, fill=None)

    # far exit sign
    ex = (v.fl + v.fr) / 2
    ey = v.ft + (v.fb - v.ft) * 0.10
    sw, sh = max(10, int(w * 0.035)), max(5, int(w * 0.012))
    rect(draw, (ex - sw, ey - sh, ex + sw, ey + sh), GREEN)
    text(draw, (ex, ey), "EXIT", max(7, int(sh * 1.4)), (10, 40, 20), anchor="mm")


def likely_w(v, f):
    return (v.fr - v.fl) * f


def draw_signs(draw, v):
    # red alarm call point on the left wall
    pts = v.wall_quad(-1, 0.16, 0.20, 0.42, 0.60)
    draw.polygon(pts, fill=(196, 40, 34))
    # "in case of fire" board on the left, near the camera
    pts = v.wall_quad(-1, 0.02, 0.13, 0.34, 0.86)
    draw.polygon(pts, fill=(244, 243, 238))
    x = min(p[0] for p in pts) + 6
    y = min(p[1] for p in pts) + 8
    text(draw, (x, y), "IN CASE OF FIRE", 13, (170, 30, 26), bold=True)
    for i, line in enumerate(("1  RAISE THE ALARM", "2  CALL 112", "3  EVACUATE BY THE STAIRS",
                              "4  DO NOT USE THE LIFT", "5  GO TO THE ASSEMBLY POINT")):
        text(draw, (x, y + 22 + i * 15), line, 9, (40, 40, 44))


# --------------------------------------------------------------------- #
# Editor chrome
# --------------------------------------------------------------------- #

def editor_frame(title="FireSafetyTrainer - SampleScene - Unity 6.5 (6000.5.3f1)"):
    img = Image.new("RGB", (W, H), EDIT_BG)
    d = ImageDraw.Draw(img)
    rect(d, (0, 0, W, 30), EDIT_TOPBAR)
    text(d, (14, 8), "Unity 6.5", 12, TEXT_DIM)
    text(d, (W / 2, 15), title, 12, TEXT_DIM, anchor="mm")
    for offset, item in zip([16, 52, 92, 136, 210, 296, 344, 400],
                            ("File", "Edit", "Assets", "GameObject", "Component", "Tools",
                             "Window", "Help")):
        text(d, (offset, 36), item, 12, TEXT)
    # play buttons
    rect(d, (W / 2 - 62, 33, W / 2 + 62, 53), EDIT_BAR, EDIT_LINE)
    draw = d
    draw.polygon([(W / 2 - 40, 37), (W / 2 - 40, 49), (W / 2 - 30, 43)], fill=(150, 200, 150))
    draw.polygon([(W / 2 - 8, 37), (W / 2 - 8, 49), (W / 2 + 2, 43)], fill=(230, 180, 90))
    draw.rectangle((W / 2 + 14, 37, W / 2 + 26, 49), fill=(200, 100, 100))
    return img, d


def panel_box(d, box, title=None, bg=EDIT_PANEL, title_bg=EDIT_PANEL_2):
    rect(d, box, bg, EDIT_LINE)
    if title:
        rect(d, (box[0], box[1], box[2], box[1] + 24), title_bg, EDIT_LINE)
        text(d, (box[0] + 8, box[1] + 5), title, 12, TEXT)


def hierarchy(d, box, items, selected):
    panel_box(d, box, "Hierarchy")
    y = box[1] + 32
    for depth, name in items:
        row = (box[0] + 1, y - 2, box[2] - 1, y + 16)
        if name == selected:
            rect(d, row, SELECT)
        text(d, (box[0] + 10 + depth * 14, y), name, 12,
             TEXT_BRIGHT if name == selected else TEXT)
        y += 19


def inspector(d, box, title, rows):
    panel_box(d, box, "Inspector")
    y = box[1] + 32
    rect(d, (box[0] + 8, y, box[2] - 8, y + 26), (52, 52, 52))
    text(d, (box[0] + 16, y + 7), title, 13, TEXT_BRIGHT, bold=True)
    y += 36
    for row in rows:
        kind, label = row[0], row[1]
        value = row[2] if len(row) > 2 else None
        if kind == "head":
            rect(d, (box[0] + 8, y, box[2] - 8, y + 20), (52, 52, 52))
            text(d, (box[0] + 14, y + 4), label, 11, TEXT_BRIGHT, bold=True)
            y += 26
            continue
        if kind == "label":
            text(d, (box[0] + 14, y), label, 11, TEXT_DIM)
            y += 18
            continue
        text(d, (box[0] + 14, y), label, 11, TEXT)
        rect(d, (box[0] + 150, y - 2, box[2] - 14, y + 15), (62, 62, 62), (36, 36, 36))
        text(d, (box[0] + 158, y), value, 11, TEXT_BRIGHT)
        y += 21


def project_panel(d, box, entries):
    panel_box(d, box, "Project")
    text(d, (box[0] + 10, box[1] + 30), "Assets", 12, TEXT_BRIGHT)
    y = box[1] + 50
    for name, indent in entries:
        text(d, (box[0] + 22 + indent * 14, y), "\u25a0  " + name if indent == 0 else "\u25a1  " + name,
             11, TEXT if indent else TEXT_BRIGHT)
        y += 17


def game_toolbar(d, box, in_play=True, eye=None):
    rect(d, (box[0], box[1], box[2], box[1] + 26), (50, 50, 50), EDIT_LINE)
    text(d, (box[0] + 10, box[1] + 6), "Game", 12, TEXT_BRIGHT, bold=True)
    text(d, (box[0] + 70, box[1] + 6), "Display 1", 11, TEXT_DIM)
    text(d, (box[0] + 150, box[1] + 6), "Free Aspect", 11, TEXT_DIM)
    if eye:
        rect(d, (box[2] - 300, box[1] + 3, box[2] - 210, box[1] + 23), (70, 70, 70), (30, 30, 30))
        text(d, (box[2] - 255, box[1] + 7), eye, 11, TEXT_BRIGHT, anchor="ma")
    if in_play:
        rect(d, (box[2] - 150, box[1] + 3, box[2] - 12, box[1] + 23), (32, 76, 120))
        text(d, (box[2] - 81, box[1] + 7), "Play Focused", 11, (210, 230, 250), anchor="ma")


# --------------------------------------------------------------------- #
# In-game HUD (mirrors LessonUI)
# --------------------------------------------------------------------- #

def hud(d, box, section, objective, prompt=None, caption=None, menu=False, panel=None,
        crosshair=True):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    s = w / 1600.0  # scale factor from the 1600x900 design

    def S(v):
        return v * s

    # The HUD is hidden while the main menu is showing (LessonUI.SetHudVisible).
    if section:
        rect(d, (x0 + S(24), y0 + S(24), x0 + S(584), y0 + S(76)), HUD_BG)
        rect(d, (x0 + S(24), y0 + S(24), x0 + S(30), y0 + S(76)), AMBER)
        text(d, (x0 + S(44), y0 + S(50)), section, int(S(24)), AMBER, bold=True, anchor="lm")

    if objective:
        ox, oy = x1 - S(24) - S(470), y0 + S(24)
        rect(d, (ox, oy, ox + S(470), oy + S(176)), HUD_BG)
        rect(d, (ox, oy, ox + S(470), oy + S(6)), AMBER)
        text(d, (ox + S(20), oy + S(30)), "CURRENT OBJECTIVE", int(S(20)), AMBER, bold=True)
        words, line, lines = objective.split(), "", []
        for word in words:
            trial = (line + " " + word).strip()
            if d.textlength(trial, font=font(int(S(24)))) > S(430):
                lines.append(line)
                line = word
            else:
                line = trial
        lines.append(line)
        for i, ln in enumerate(lines[:4]):
            text(d, (ox + S(20), oy + S(62) + i * S(32)), ln, int(S(24)), WHITE)

    if crosshair:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        d.ellipse((cx - 13 * s, cy - 13 * s, cx + 13 * s, cy + 13 * s), outline=(255, 184, 64))
        d.ellipse((cx - 3 * s, cy - 3 * s, cx + 3 * s, cy + 3 * s), fill=(255, 255, 255))

    if caption:
        cbx = (x0 + x1) / 2
        top = y1 - S(168)
        rect(d, (cbx - S(620), top, cbx + S(620), top + S(76)), HUD_BG)
        rect(d, (cbx - S(620), top, cbx - S(612), top + S(76)), AMBER)
        text(d, (cbx - S(590), top + S(38)), caption, int(S(34)), WHITE, bold=True, anchor="lm")

    if prompt:
        pbx = (x0 + x1) / 2
        rect(d, (pbx - S(460), y1 - S(186), pbx + S(460), y1 - S(120)), (12, 16, 23))
        text(d, (pbx, y1 - S(153)), prompt, int(S(28)), WHITE, bold=True, anchor="mm")

    if not menu:
        text(d, (x0 + S(24), y1 - S(40)),
             "WASD move  |  Mouse look  |  E interact  |  Shift run  |  Esc pause",
             int(S(20)), (196, 200, 208))

    if menu:
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        top, bottom = my - S(268), my + S(268)
        rect(d, (mx - S(430), top, mx + S(430), bottom), (12, 17, 25))
        rect(d, (mx - S(430), top, mx + S(430), top + S(6)), AMBER)
        text(d, (mx, top + S(52)), "VR FIRE SAFETY TRAINER", int(S(44)), WHITE, bold=True,
             anchor="mm")
        text(d, (mx, top + S(112)), "Raise the alarm  \u00b7  call 112  \u00b7  leave by the stairs",
             int(S(21)), (150, 160, 175), anchor="mm")
        rect(d, (mx - S(160), top + S(140), mx + S(160), top + S(143)), (60, 72, 86))
        for i, label in enumerate(("START TRAINING", "CONTROLS", "REFERENCES", "EXIT")):
            by = top + S(170) + i * S(74)
            rect(d, (mx - S(330), by, mx + S(330), by + S(62)), (41, 61, 87))
            text(d, (mx, by + S(31)), label, int(S(26)), WHITE, bold=True, anchor="mm")
        text(d, (mx, bottom - S(26)),
             "Basic educational simulation  \u00b7  Unity 6.5  \u00b7  URP",
             int(S(17)), (110, 120, 132), anchor="mm")

    if panel:
        title_, body, footer, buttons = panel
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        rect(d, (mx - S(700), my - S(340), mx + S(700), my + S(390)), (14, 18, 26))
        rect(d, (mx - S(700), my - S(340), mx + S(700), my - S(332)), AMBER)
        text(d, (mx - S(660), my - S(300)), title_, int(S(34)), AMBER, bold=True)
        y = my - S(246)
        for line in body:
            bold = line.startswith("**")
            clean = line.replace("**", "")
            text(d, (mx - S(660), y), clean, int(S(21)), WHITE if bold else (206, 214, 224),
                 bold=bold)
            y += S(31)
        if footer:
            text(d, (mx - S(660), my + S(292)), footer, int(S(19)), (150, 160, 175))
        if buttons:
            bw = S(1344) / len(buttons) - S(16)
            for i, label in enumerate(buttons):
                bx = mx - S(672) + i * (bw + S(16))
                rect(d, (bx, my + S(312), bx + bw, my + S(312) + S(56)), (41, 61, 87))
                text(d, (bx + bw / 2, my + S(340)), label, int(S(24)), WHITE, bold=True,
                     anchor="mm")


# --------------------------------------------------------------------- #
# Screens
# --------------------------------------------------------------------- #

def shot_editor_scene():
    img, d = editor_frame()
    hierarchy(d, (0, 58, 300, 560), [
        (0, "FireSafetyTrainer"), (1, "Environment"), (1, "LessonManager"),
        (1, "TrainingUI"), (1, "EventSystem"), (1, "Player"), (2, "Main Camera"),
        (1, "AlarmCallPoint"), (1, "MaskDisplay"), (1, "ExtinguisherModel_Water"),
        (1, "ExtinguisherStation"), (1, "ContainedFireDemo"), (1, "CorridorSmokeHazard"),
        (1, "Checkpoints"), (1, "Directional Light"),
    ], "LessonManager")
    view = View(306, 84, 1180, 560)
    draw_corridor(d, view)
    draw_signs(d, view)
    inspector(d, (1186, 58, 1600, 560), "LessonManager (Script)", [
        ("label", "Script", None), ("field", "Player", "Player (PlayerController)"),
        ("field", "Alarm", "AlarmCallPoint (AlarmContr\u2026)"),
        ("field", "Evacuation", "Evacuation (EvacuationCo\u2026)"),
        ("field", "Extinguisher Station", "ExtinguisherStation (Exting\u2026)"),
        ("field", "Fire", "ContainedFireDemo (FireDemo)"),
        ("field", "Mask Display", "MaskDisplay (SimpleInteract\u2026)"),
        ("field", "Phone", "EmergencyPhone (SimpleInter\u2026)"),
        ("head", "Extinguisher Cards", None), ("field", "Size", "6"),
        ("label", "Element 0      Card_Water"),
        ("label", "Element 1      Card_Foam"),
        ("field", "Ui Audio", "None (Audio Source)"),
        ("field", "Click Clip", "ui_click"),
        ("field", "Panel Open Delay", "0.35"),
    ])
    project_panel(d, (0, 566, 1180, 900), [
        ("Assets", 0), ("Scenes", 1), ("Scripts", 1), ("Editor", 1), ("Materials", 1),
        ("Textures", 1), ("Prefabs", 1), ("Settings", 1), ("XR", 1), ("Documentation", 1),
    ])
    panel_box(d, (1186, 566, 1600, 900), "Console")
    logs = [("Fire Safety", "Opened Assets/Scenes/FireSafetyTrainer.unity. Press Play, then choose Start Training.", TEXT_DIM),
            ("Fire Safety", "Validation passed with 6 note(s).", TEXT),
            ("Fire Safety", "Unity 6000.5.3f1 | active input handling: Both | XR devices enabled: none", TEXT)]
    y = 598
    for tag, msg, colour in logs:
        text(d, (1196, y), "\u2139", 12, UNITY_BLUE)
        text(d, (1214, y), msg, 10, colour)
        y += 34
    img.save(os.path.join(OUT, "01-editor-scene.png"))


def shot_game_desktop():
    img, d = editor_frame()
    hierarchy(d, (0, 58, 300, 330), [
        (0, "FireSafetyTrainer"), (1, "Environment"), (1, "LessonManager"),
        (1, "TrainingUI"), (1, "Player"), (2, "Main Camera"),
    ], "Main Camera")
    box = (306, 84, 1180, 760)
    view = View(box[0] + 6, box[1] + 30, box[2] - 6, box[3] - 6)
    # the corridor fire is not part of this close-up: the only fire here is the practice bin
    draw_corridor(d, view, fire=False)
    draw_signs(d, view)
    game_toolbar(d, box, in_play=True)
    hud(d, (view.x0, view.y0, view.x1, view.y1),
        "Section A - Immediate response",
        "Raise the alarm at the red call point on the left wall.",
        prompt="[E]  Raise the fire alarm")
    inspector(d, (1186, 58, 1600, 760), "PlayerController (Script)", [
        ("field", "Player Camera", "Main Camera (Camera)"),
        ("head", "Desktop movement", None),
        ("field", "Walk Speed", "2.4"), ("field", "Run Speed", "4.2"),
        ("field", "Mouse Sensitivity", "2.2"), ("field", "Eye Height", "1.62"),
        ("head", "Interaction", None),
        ("field", "Interact Distance", "3.2"), ("field", "Interact Radius", "0.22"),
        ("head", "VR", None),
        ("field", "Vr Move Speed", "2"), ("field", "Snap Turn Degrees", "30"),
        ("field", "Request Floor Origin", "\u2713"),
    ])
    project_panel(d, (0, 766, 1600, 900), [("Assets", 0), ("Scenes", 1), ("Scripts", 1)])
    img.save(os.path.join(OUT, "02-game-desktop.png"))


def shot_menu():
    img, d = editor_frame()
    box = (306, 84, 1180, 760)
    view = View(box[0] + 6, box[1] + 30, box[2] - 6, box[3] - 6)
    draw_corridor(d, view)
    game_toolbar(d, box, in_play=True)
    hud(d, (view.x0, view.y0, view.x1, view.y1), "", "", menu=True, crosshair=False)
    text(d, (20, 880), "Main menu. Start Training begins the lesson; Exit quits the player.",
         12, TEXT_DIM)
    img.save(os.path.join(OUT, "03-main-menu.png"))


def shot_teaching_panel():
    img, d = editor_frame()
    box = (306, 84, 1180, 760)
    view = View(box[0] + 6, box[1] + 30, box[2] - 6, box[3] - 6)
    draw_corridor(d, view)
    game_toolbar(d, box, in_play=True)
    hud(d, (view.x0, view.y0, view.x1, view.y1),
        "Section B - Masks and extinguishers",
        "Learn the Indian fire classes.",
        panel=("B3  Indian fire classes",
               ["**Class A**  solids - wood, paper, cloth",
                "**Class B**  flammable liquids - petrol, solvents",
                "**Class C**  flammable gases - LPG, methane",
                "**Class D**  combustible metals - magnesium",
                "**Class F**  cooking oils and fats",
                "",
                "Energised electrical equipment is a hazard, not a class."],
               "Choose the extinguisher printed on the label.",
               ["Next: safety rules"]),
        crosshair=False)
    img.save(os.path.join(OUT, "04-teaching-panel.png"))


def shot_pass_demo():
    """The practice station close up: table, unit, powder jet and the bin fire."""
    img, d = editor_frame()
    box = (306, 84, 1180, 760)
    view = View(box[0] + 6, box[1] + 30, box[2] - 6, box[3] - 6)
    # the corridor fire is not part of this close-up: the only fire here is the practice bin
    draw_corridor(d, view, fire=False)
    draw_signs(d, view)
    game_toolbar(d, box, in_play=True)

    # ---- the practice table and the unit, foreground left -----------------
    table = (view.x0 + 60, 556, view.x0 + 300, 600)
    rect(d, table, (120, 96, 70))
    rect(d, (table[0] + 20, table[3], table[0] + 34, table[3] + 40), (60, 52, 40))
    rect(d, (table[2] - 34, table[3], table[2] - 20, table[3] + 40), (60, 52, 40))

    unit_x = table[0] + 110
    body_top, body_bottom = 412, 556
    rect(d, (unit_x - 34, body_top, unit_x + 34, body_bottom), (176, 36, 32), radius=6)
    rect(d, (unit_x - 30, body_top, unit_x + 30, body_top + 8), (120, 24, 22))
    # label
    rect(d, (unit_x - 26, body_top + 44, unit_x + 26, body_top + 100), (240, 238, 230))
    text(d, (unit_x, body_top + 60), "ABC", 12, (176, 36, 32), bold=True, anchor="ma")
    text(d, (unit_x, body_top + 78), "POWDER", 8, (60, 60, 64), anchor="ma")
    # valve, lever, horn and hose
    rect(d, (unit_x - 16, body_top - 26, unit_x + 16, body_top), (54, 54, 58))
    rect(d, (unit_x - 46, body_top - 40, unit_x + 10, body_top - 26), (40, 40, 44), radius=3)
    d.line((unit_x + 34, body_top + 30, unit_x + 96, body_top + 6), fill=(32, 32, 34), width=9)
    rect(d, (unit_x + 92, body_top - 6, unit_x + 136, body_top + 22), (32, 32, 34), radius=4)

    # ---- powder jet sweeping across the base of the fire ------------------
    horn = (unit_x + 136, body_top + 8)
    fire = (unit_x + 470, 526)
    for i in range(26):
        t = i / 25.0
        cx = lerp(horn[0], fire[0], t)
        cy = lerp(horn[1], fire[1], t) - (28 * t * (1 - t))
        r = 4 + 30 * t
        a = int(230 * (1 - t * 0.85))
        overlay = Image.new("RGBA", (int(r * 2 + 2), int(r * 2 + 2)), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.ellipse((1, 1, r * 2, r * 2), fill=(238, 240, 244, a))
        img.paste(Image.alpha_composite(img.crop((int(cx - r), int(cy - r),
                                                  int(cx - r) + overlay.width,
                                                  int(cy - r) + overlay.height)).convert("RGBA"),
                                        overlay).convert("RGB"), (int(cx - r), int(cy - r)))

    # ---- the bin fire at the end of the jet ------------------------------
    rect(d, (fire[0] - 30, fire[1] - 4, fire[0] + 30, fire[1] + 34), (40, 40, 44), radius=3)
    for i, dx in enumerate((-14, -4, 6, 16)):
        h = 60 if i % 2 == 0 else 40
        d.polygon([(fire[0] + dx, fire[1] - 4),
                   (fire[0] + dx - 9, fire[1] - 4 - h * 0.55),
                   (fire[0] + dx, fire[1] - 4 - h),
                   (fire[0] + dx + 9, fire[1] - 4 - h * 0.5)],
                  fill=(255, 176, 64) if i % 2 == 0 else (238, 110, 30))

    hud(d, (view.x0, view.y0, view.x1, view.y1),
        "Section B - Masks and extinguishers",
        "PASS: pull, aim at the base, squeeze, sweep.",
        caption="1 of 4   PULL the safety pin")
    note = ("The practice unit is animated, not a menu: the pin leaves the valve, the horn turns "
            "to the base, the lever moves and the jet sweeps until the fire is out.")
    line, ny = "", view.y1 + 6
    for word in note.split():
        trial = (line + " " + word).strip()
        if d.textlength(trial, font=font(11)) > (box[2] - box[0] - 20):
            text(d, (view.x0 + 10, ny), line, 11, TEXT_DIM)
            line, ny = word, ny + 15
        else:
            line = trial
    text(d, (view.x0 + 10, ny), line, 11, TEXT_DIM)
    img.save(os.path.join(OUT, "05-pass-demo.png"))


def shot_both_eyes():
    img, d = editor_frame()
    box = (306, 84, 1180, 760)
    game_toolbar(d, box, in_play=True, eye="Both Eyes")
    mid = (box[0] + box[2]) / 2
    for i, xoff in enumerate((-1, 1)):
        vx0 = box[0] + 6 if i == 0 else mid + 2
        vx1 = mid - 2 if i == 0 else box[2] - 6
        view = View(vx0, box[1] + 30, vx1, box[3] - 6)
        draw_corridor(d, view)
        draw_signs(d, view)
        # a little parallax so the two eyes differ
        shift = 8 if i else -8
        for t in (0.05, 0.22, 0.39):
            q = view.span_quad(t, t + 0.05, 0.38, 0.62, False)
            d.polygon([(p[0] + shift * 0.3, p[1] + shift * 0.1) for p in q], fill=(248, 246, 236))
        hud(d, (view.x0, view.y0, view.x1, view.y1),
            "Section C - Evacuation exercise", "Follow the EXIT signs.",
            crosshair=False)
    d.line((mid, box[1] + 26, mid, box[3] - 6), fill=(20, 20, 20), width=3)
    # F2 diagnostics panel
    px, py = box[0] + 10, box[1] + 40
    lines = ["VR READINESS  (F2 to hide)",
             "Unity 6000.5.3f1   build: Editor", "",
             "XR session ....... ACTIVE",
             "XR device ........ MockHMD",
             "Stereo mode ...... SinglePassInstanced",
             "Eye resolution ... scale 1.0   graphics D3D11", "",
             "Head pose ........ not reported",
             "Tracking origin .. Device / default", "",
             "Controllers:",
             "  left  not reported",
             "  right not reported",
             "  head  not reported", "",
             "Frame ............ 74 fps   1600 x 900",
             "Lesson: running   |   UI canvases: ready"]
    # docked at the bottom-left of the Game view so both eye views stay readable
    box_h = 18 + len(lines) * 13
    py = box[3] - 10 - box_h
    rect(d, (px, py, px + 300, py + box_h), (8, 12, 18), (26, 30, 38))
    for i, ln in enumerate(lines):
        text(d, (px + 8, py + 7 + i * 13), ln, 9, WHITE if i else AMBER)
    img.save(os.path.join(OUT, "06-both-eyes.png"))


def shot_xr_plugin():
    img = Image.new("RGB", (W, H), (44, 44, 44))
    d = ImageDraw.Draw(img)
    rect(d, (0, 0, W, 30), EDIT_TOPBAR)
    text(d, (14, 8), "Unity 6.5", 12, TEXT_DIM)
    text(d, (W / 2, 15), "Project Settings", 12, TEXT_DIM, anchor="mm")

    # left tree
    rect(d, (0, 30, 330, H), (38, 38, 38), EDIT_LINE)
    items = ["Adaptive Performance", "Audio", "Editor", "Graphics", "Input Manager",
             "Memory Settings", "Package Manager", "Physics", "Player", "Preset Manager",
             "Quality", "Scene Template", "Services", "Time", "UI Toolkit", "XR Plug-in Management",
             "     OpenXR", "     Project Validation", "     XR Interaction Toolkit"]
    y = 46
    for name in items:
        if "XR Plug-in" in name:
            rect(d, (0, y - 3, 330, y + 16), SELECT_DIM)
        if name.strip() == "OpenXR":
            rect(d, (0, y - 3, 330, y + 16), SELECT)
        text(d, (20, y), name, 12, TEXT_BRIGHT if "XR" in name else TEXT)
        y += 22

    # content
    x = 370
    text(d, (x, 56), "XR Plug-in Management", 24, TEXT_BRIGHT, bold=True)
    rect(d, (x, 100, x + 250, 126), (60, 60, 60))
    text(d, (x + 125, 113), "PC", 12, TEXT_BRIGHT, anchor="mm")
    rect(d, (x + 251, 100, x + 501, 126), (46, 46, 46))
    text(d, (x + 376, 113), "Android", 12, TEXT_DIM, anchor="mm")

    rows = [("OpenXR", True, "1.17.1"), ("Mock HMD", True, "1.4.0"),
            ("Unity OpenXR: Meta", False, "not installed"),
            ("XR Interaction Toolkit", False, "3.5.1 (runtime only)")]
    y = 150
    for name, ticked, version in rows:
        rect(d, (x, y, x + 900, y + 42), (48, 48, 48), (32, 32, 32))
        box = (x + 16, y + 13, x + 32, y + 29)
        rect(d, box, (70, 70, 70), (110, 110, 110))
        if ticked:
            d.line((box[0] + 2, box[1] + 8, box[0] + 6, box[1] + 13), fill=UNITY_BLUE, width=2)
            d.line((box[0] + 6, box[1] + 13, box[0] + 14, box[1] + 3), fill=UNITY_BLUE, width=2)
        text(d, (x + 46, y + 12), name, 14, TEXT_BRIGHT if ticked else TEXT)
        text(d, (x + 700, y + 12), version, 12, TEXT_DIM)
        y += 50

    text(d, (x, y + 20), "Plug-in providers", 15, TEXT_BRIGHT, bold=True)
    y += 52
    for name, ticked in (("Unity OpenXR Provider", True), ("Mock HMD Provider", True)):
        rect(d, (x, y, x + 900, y + 36), (44, 44, 44), (32, 32, 32))
        box = (x + 16, y + 10, x + 32, y + 26)
        rect(d, box, (70, 70, 70), (110, 110, 110))
        if ticked:
            d.line((box[0] + 2, box[1] + 8, box[0] + 6, box[1] + 13), fill=UNITY_BLUE, width=2)
            d.line((box[0] + 6, box[1] + 13, box[0] + 14, box[1] + 3), fill=UNITY_BLUE, width=2)
        text(d, (x + 46, y + 8), name, 13, TEXT)
        y += 44

    text(d, (x, y + 24), "Initialize XR on Startup  \u2713     Active Input Handling: Both",
         13, TEXT_DIM)
    text(d, (20, H - 28), "Reconstruction of the PC tab: OpenXR stays ticked, Mock HMD is added and ticked "
                            "for the stereo demo run.",
         12, TEXT_DIM)
    img.save(os.path.join(OUT, "07-xr-plug-in-management.png"))


def shot_openxr_page():
    img = Image.new("RGB", (W, H), (44, 44, 44))
    d = ImageDraw.Draw(img)
    rect(d, (0, 0, W, 30), EDIT_TOPBAR)
    text(d, (14, 8), "Unity 6.5", 12, TEXT_DIM)
    text(d, (W / 2, 15), "Project Settings", 12, TEXT_DIM, anchor="mm")

    rect(d, (0, 30, 330, H), (38, 38, 38), EDIT_LINE)
    items = ["Graphics", "Input Manager", "Memory Settings", "Package Manager", "Physics",
             "Player", "Preset Manager", "Quality", "Scene Template", "Services", "Time",
             "UI Toolkit", "XR Plug-in Management", "     OpenXR",
             "     Project Validation", "     XR Interaction Toolkit"]
    y = 46
    for name in items:
        if name.strip() == "OpenXR":
            rect(d, (0, y - 3, 330, y + 16), SELECT)
        text(d, (20, y), name, 12, TEXT_BRIGHT if "XR" in name else TEXT)
        y += 22

    x = 370
    text(d, (x, 52), "OpenXR", 24, TEXT_BRIGHT, bold=True)
    rect(d, (x, 92, x + 250, 118), (60, 60, 60))
    text(d, (x + 125, 105), "PC", 12, TEXT_BRIGHT, anchor="mm")
    rect(d, (x + 251, 92, x + 501, 118), (46, 46, 46))
    text(d, (x + 376, 105), "Android", 12, TEXT_DIM, anchor="mm")

    rows = [("Render Mode", "Single Pass Instanced"),
            ("Auto Color Submission Mode", "\u2713"),
            ("Latency Optimization", "Prioritize Rendering"),
            ("Depth Submission Mode", "None"),
            ("Use OpenXR Predicted Time", "\u2713"),
            ("Play Mode OpenXR Runtime", "Oculus  (System Default)")]
    y = 140
    for label, value in rows:
        text(d, (x + 20, y), label, 13, TEXT)
        rect(d, (x + 320, y - 3, x + 760, y + 21), (62, 62, 62), (34, 34, 34))
        text(d, (x + 332, y + 1), value, 12, TEXT_BRIGHT)
        y += 34

    text(d, (x + 20, y + 16), "Enabled Interaction Profiles", 14, TEXT_BRIGHT, bold=True)
    y += 46
    rect(d, (x + 20, y, x + 760, y + 30), (62, 62, 62), (34, 34, 34))
    text(d, (x + 32, y + 8), "Oculus Touch Controller Profile", 12, TEXT_BRIGHT)
    y += 44
    text(d, (x + 20, y), "OpenXR Feature Groups", 14, TEXT_BRIGHT, bold=True)
    y += 30
    for name in ("API Layers", "Debug Utils", "D-Pad Binding", "Foveated Rendering",
                 "Hand Interaction Poses", "Mock Runtime", "Palm Pose", "Runtime Debugger"):
        box = (x + 20, y, x + 36, y + 16)
        rect(d, box, (70, 70, 70), (110, 110, 110))
        text(d, (x + 48, y - 1), name, 12, TEXT_DIM)
        y += 26
    text(d, (20, H - 28), "Reconstruction: the profile that must not be empty, and a named "
                          "play-mode runtime.", 12, TEXT_DIM)
    img.save(os.path.join(OUT, "08-openxr-page.png"))


def shot_project_window():
    img, d = editor_frame()
    rect(d, (0, 58, 1600, 900), (42, 42, 42))
    rect(d, (0, 58, 1600, 82), (52, 52, 52))
    text(d, (14, 64), "Project", 12, TEXT_BRIGHT, bold=True)
    text(d, (100, 64), "Favorites", 12, TEXT_DIM)
    text(d, (200, 64), "Assets", 12, TEXT)
    text(d, (760, 64), "Search", 12, TEXT_DIM)
    text(d, (14, 92), "Assets  \u203a", 13, TEXT_BRIGHT)
    folders = [("Scenes", "FireSafetyTrainer"), ("Scripts", "18 files"), ("Editor", "2 files"),
               ("Materials", "53 materials"), ("Textures", "Signs"), ("Settings", "URP"),
               ("XR", "Settings"), ("Documentation", "README"), ("Resources", "Audio")]
    x, y = 20, 140
    for i, (name, sub) in enumerate(folders):
        cx = x + (i % 5) * 300
        cy = y + (i // 5) * 130
        rect(d, (cx, cy, cx + 44, cy + 34), (70, 84, 96), (30, 30, 30))
        rect(d, (cx, cy, cx + 44, cy + 8), (96, 110, 124))
        text(d, (cx + 52, cy + 4), name, 13, TEXT_BRIGHT)
        text(d, (cx + 52, cy + 20), sub, 11, TEXT_DIM)
    text(d, (20, 430), "Assets/Scripts", 14, TEXT_BRIGHT, bold=True)
    scripts = ["LessonManager.cs", "LessonContent.cs", "LessonUI.cs", "PlayerController.cs",
               "AlarmController.cs", "FireDemo.cs", "ExtinguisherStation.cs",
               "EvacuationController.cs", "CorridorSmoke.cs", "HazardZone.cs",
               "DoorController.cs", "CheckpointTrigger.cs", "SimpleInteractable.cs",
               "InteractableBase.cs", "IInteractable.cs", "HudFollower.cs",
               "VrReadinessPanel.cs", "VfxUtil.cs", "AudioHelper.cs"]
    for i, name in enumerate(scripts):
        cx = 20 + (i % 4) * 300
        cy = 470 + (i // 4) * 60
        rect(d, (cx, cy, cx + 30, cy + 34), (120, 140, 160), (30, 30, 30))
        text(d, (cx + 8, cy + 8), "C#", 10, (20, 30, 40), bold=True)
        text(d, (cx + 38, cy + 10), name, 12, TEXT)
    text(d, (20, 862), "Reconstruction of the Assets layout: no imported art, everything "
                       "generated by the tools/ scripts.", 12, TEXT_DIM)
    img.save(os.path.join(OUT, "09-project-window.png"))


def shot_console_tools():
    img, d = editor_frame()
    panel_box(d, (0, 300, 1600, 900), "Console")
    logs = [
        ("[Fire Safety] Opened Assets/Scenes/FireSafetyTrainer.unity. Press Play, then choose Start Training.", TEXT_DIM),
        ("[Fire Safety] Validation passed with 6 note(s).", TEXT),
        ("[Fire Safety] Note: Unity 6000.5.3f1", TEXT),
        ("[Fire Safety] Note: Active Input Handling is 'Both' - keyboard, mouse and XR input are all available.", TEXT),
        ("[Fire Safety] Note: No XR device is enabled yet. Desktop play works now; to test in a headset, enable OpenXR.", TEXT),
        ("[Fire Safety] Note: 14 interactable objects found.", TEXT),
        ("[Fire Safety] VR readiness report written to docs/VR-Readiness-Report.md", TEXT),
        ("[Fire Safety] OpenXR interaction profiles enabled: Oculus Touch Controller.", TEXT),
        ("[Fire Safety] XR session active (MockHMD). The Game view is set to both eyes; press F2 for the XR diagnostics panel.", TEXT),
    ]
    y = 336
    for msg, colour in logs:
        text(d, (16, y), "\u2139", 12, UNITY_BLUE)
        text(d, (36, y), msg, 12, colour)
        y += 28
    text(d, (20, 862), "Reconstruction of the Editor console after running the project's own "
                       "validation and readiness tools.", 12, TEXT_DIM)

    # Tools menu, drawn last so it sits on top
    rect(d, (296, 50, 540, 136), (70, 70, 70), (24, 24, 24))
    for i, name in enumerate(("Open Training Scene", "Validate Training Scene",
                              "VR Readiness Report", "Project Setup Report", "Open Project README")):
        if i == 2:
            rect(d, (298, 54 + i * 17, 538, 69 + i * 17), SELECT)
        text(d, (308, 55 + i * 17), name, 12, TEXT_BRIGHT if i == 2 else TEXT)
    img.save(os.path.join(OUT, "10-console-and-tools.png"))


SHOTS = [
    ("01-editor-scene.png", "Editor: Hierarchy, scene view and LessonManager"),
    ("02-game-desktop.png", "Play mode on a normal monitor"),
    ("03-main-menu.png", "Main menu"),
    ("04-teaching-panel.png", "A lesson panel"),
    ("05-pass-demo.png", "Animated PASS demonstration"),
    ("06-both-eyes.png", "Both Eyes plus the F2 panel"),
    ("07-xr-plug-in-management.png", "XR Plug-in Management, PC tab"),
    ("08-openxr-page.png", "OpenXR settings"),
    ("09-project-window.png", "Project window"),
    ("10-console-and-tools.png", "Tools menu and console"),
]


def contact_sheet():
    """One overview image: the ten screenshots side by side with their file names."""
    tw, th, label_h, pad = 460, 259, 40, 14
    cols, rows = 5, 2
    W = cols * tw + (cols + 1) * pad
    H = rows * (th + label_h) + (rows + 1) * pad + 40
    sheet = Image.new("RGB", (W, H), (24, 26, 30))
    d = ImageDraw.Draw(sheet)
    text(d, (pad, 12), "Documentation screenshots \u2014 reconstructions, not screen captures",
         14, (150, 158, 170))
    for i, (name, label) in enumerate(SHOTS):
        col, row = i % cols, i // cols
        x = pad + col * (tw + pad)
        y = 40 + pad + row * (th + label_h + pad)
        shot = Image.open(os.path.join(OUT, name)).convert("RGB").resize((tw, th), Image.LANCZOS)
        sheet.paste(shot, (x, y))
        d.rectangle((x, y, x + tw - 1, y + th - 1), outline=(70, 74, 82))
        text(d, (x + 2, y + th + 6), name, 11, (250, 250, 250))
        text(d, (x + 2, y + th + 21), label, 10, (150, 158, 170))
    sheet.save(os.path.join(OUT, "00-overview.png"))
    print("Wrote", os.path.join(OUT, "00-overview.png"))


def main():
    os.makedirs(OUT, exist_ok=True)
    shot_editor_scene()
    shot_game_desktop()
    shot_menu()
    shot_teaching_panel()
    shot_pass_demo()
    shot_both_eyes()
    shot_xr_plugin()
    shot_openxr_page()
    shot_project_window()
    shot_console_tools()
    contact_sheet()
    print("Wrote 10 images plus the overview to", OUT)


if __name__ == "__main__":
    main()
