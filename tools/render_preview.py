#!/usr/bin/env python3
"""Approximate PNG preview of the generated deck (no LibreOffice in this environment).

This is a layout sanity check, not a faithful renderer: it draws the same shapes at the same
positions with DejaVuSans, which is wider than Segoe UI, so text that fits here will fit in
PowerPoint.

Run: python3 tools/render_preview.py [outdir]   (default /tmp/deck-preview)
"""

from __future__ import annotations

import os
import sys

from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.util import Emu

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECK = os.path.join(ROOT, "docs", "VR-Fire-Safety-Implementation.pptx")
FONT_REG = os.path.join(ROOT, "Assets", "Fonts", "DejaVuSans.ttf")
FONT_BOLD = os.path.join(ROOT, "Assets", "Fonts", "DejaVuSans-Bold.ttf")

SCALE = 1600 / 13.333  # px per inch


def px(value):
    return int(round((value / 914400) * SCALE))


def rgb(colour):
    try:
        return tuple(colour.rgb)
    except Exception:
        return None


def font_for(size_pt, bold):
    path = FONT_BOLD if bold else FONT_REG
    return ImageFont.truetype(path, max(7, int(round(size_pt * SCALE / 72))))


def wrapped(draw, text, font, width):
    words = text.split(" ")
    lines, current = [], ""
    for word in words:
        trial = (current + " " + word).strip()
        if draw.textlength(trial, font=font) <= width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else "/tmp/deck-preview"
    os.makedirs(outdir, exist_ok=True)
    prs = Presentation(DECK)
    index = 0
    for slide in prs.slides:
        index += 1
        img = Image.new("RGB", (1600, 900), (14, 21, 30))
        draw = ImageDraw.Draw(img)
        for shape in slide.shapes:
            x, y = px(shape.left), px(shape.top)
            w, h = px(shape.width), px(shape.height)
            fill = None
            line = None
            try:
                if shape.fill.type is not None and shape.fill.type == 1:
                    fill = rgb(shape.fill.fore_color)
            except Exception:
                fill = None
            is_autoshape = "AUTO_SHAPE" in str(shape.shape_type) or "OVAL" in str(shape.shape_type) \
                or "CONNECTOR" in str(shape.shape_type)
            if is_autoshape:
                try:
                    if shape.line.fill.type == 1:
                        line = rgb(shape.line.color)
                except Exception:
                    line = None

            kind = str(shape.shape_type)
            has_border = line is not None
            if "OVAL" in kind:
                if fill or has_border:
                    draw.ellipse([x, y, x + w, y + h], fill=fill,
                                 outline=line if has_border else None,
                                 width=1 if has_border else 0)
            elif "CONNECTOR" in kind or "LINE" in str(shape.name):
                draw.line([x, y, x + w, y + h], fill=line or (110, 124, 139), width=2)
            elif fill or has_border:
                radius = 8 if "ROUNDED" in kind else 0
                # PIL draws a white outline when outline=None, so only draw when needed.
                draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=fill,
                                       outline=line if has_border else None,
                                       width=1 if has_border else 0)

            if not shape.has_text_frame:
                continue
            text = shape.text_frame.text
            if not text.strip():
                continue
            cursor = y + 4
            for para in shape.text_frame.paragraphs:
                runs = para.runs
                if not runs:
                    cursor += 8
                    continue
                size = max((r.font.size.pt if r.font.size else 18) for r in runs)
                bold = any(r.font.bold for r in runs)
                colour = rgb(runs[0].font.color) or (236, 241, 246)
                fnt = font_for(size, bold)
                line_text = "".join(r.text for r in runs)
                for piece in wrapped(draw, line_text, fnt, max(10, w - 10)):
                    draw.text((x + 5, cursor), piece, font=fnt, fill=colour)
                    cursor += int(size * SCALE / 72 * 1.25)
                cursor += int(size * 0.25)

        img.save(os.path.join(outdir, "slide-%02d.png" % index))

    # simple contact sheet, four per row
    files = sorted(os.listdir(outdir))
    cols, rows = 3, 3
    thumbs = [Image.open(os.path.join(outdir, f)).resize((520, 293)) for f in files[:9]]
    sheet = Image.new("RGB", (cols * 530, rows * 303), (8, 12, 18))
    for i, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((i % cols) * 530 + 5, (i // cols) * 303 + 5))
    sheet.save(os.path.join(outdir, "contact-sheet-1.png"))

    thumbs = [Image.open(os.path.join(outdir, f)).resize((520, 293)) for f in files[9:18]]
    sheet = Image.new("RGB", (cols * 530, rows * 303), (8, 12, 18))
    for i, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((i % cols) * 530 + 5, (i // cols) * 303 + 5))
    sheet.save(os.path.join(outdir, "contact-sheet-2.png"))
    print("Rendered %d slides to %s" % (len(files), outdir))


if __name__ == "__main__":
    main()
