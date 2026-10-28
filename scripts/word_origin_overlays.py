#!/usr/bin/env python3
"""2D Typography, Karaoke Subtitles & Black Note End Card Overlays for HaRiENG Word Origin (`word_origin_overlays.py`).
Supports both Linux (`vpsg16gb`) and macOS font paths.
Rule: File length <= 150 lines (AGENTS.md).
"""
import os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MASCOT_DIR = os.path.join(os.path.dirname(BASE_DIR), "01_LOCKED_MASCOTS_AND_LOGO")
ASSETS_DIR = os.path.join(BASE_DIR, "assets_quarantine_v2")
LOGO_PNG = os.path.join(MASCOT_DIR, "harieng_2d_logo.png")
COVER_PAINTED = os.path.join(ASSETS_DIR, "quarantine_tov_cover_painted.jpg")


def _pick_font(candidates: list) -> str:
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[-1]


FONT_HEAVY = _pick_font([
    "/System/Library/Fonts/Supplemental/Impact.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Impact.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
])
FONT_BOLD = _pick_font([
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
])
FONT_THIN = _pick_font([
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
])
SERIF_REG = _pick_font([
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Georgia.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
])
SERIF_BOLD = _pick_font([
    "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Georgia_Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
])

PAINTED_MAIN_RGBA = None


def fnt(path: str, size: int):
    return ImageFont.truetype(path, size)


def extract_painted_main_word() -> Image.Image:
    im = Image.open(COVER_PAINTED).convert("RGBA").resize((1080, 1920), Image.Resampling.LANCZOS)
    crop = im.crop((0, 122, 1080, 760))
    arr = np.array(crop, dtype=np.float32)
    dist = np.sqrt((arr[..., 0] - 10) ** 2 + (arr[..., 1] - 32) ** 2 + (arr[..., 2] - 62) ** 2)
    arr[..., 3] = np.clip((dist - 28.0) * 4.2, 0, 255)
    return Image.fromarray(arr.astype(np.uint8))


def draw_top_header_and_logo(canvas: Image.Image):
    cx, cy, r = 890, 1745, 48
    bg = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(bg)
    bd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(7, 15, 32, 245))
    canvas.alpha_composite(bg)
    logo = Image.open(LOGO_PNG).convert("RGBA")
    lw = 210
    lh = int(logo.height * (lw / float(logo.width)))
    logo = logo.resize((lw, lh), Image.Resampling.LANCZOS)
    canvas.alpha_composite(logo, (cx - lw // 2, cy - lh // 2))
    d = ImageDraw.Draw(canvas)
    d.text((540, 146), "WORD ORIGIN", font=fnt(FONT_BOLD, 24),
           fill=(255, 232, 165, 245), anchor="mm", stroke_width=3, stroke_fill=(6, 12, 24, 240))


def make_static_top_overlay(sc: dict) -> Image.Image:
    global PAINTED_MAIN_RGBA
    if PAINTED_MAIN_RGBA is None:
        PAINTED_MAIN_RGBA = extract_painted_main_word()
    ov = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    top_grad_h = 590 if sc["use_painted_main"] else 460
    for y in range(top_grad_h):
        a = int(215 * (1.0 - y / float(top_grad_h)) ** 1.35)
        d.line([(0, y), (1080, y)], fill=(7, 15, 32, a))
    for y in range(1320, 1920):
        a = int(235 * ((y - 1320) / 600.0) ** 1.25)
        d.line([(0, y), (1080, y)], fill=(6, 12, 26, a))
    if sc["use_painted_main"]:
        pm = PAINTED_MAIN_RGBA.resize((950, 526), Image.Resampling.LANCZOS)
        ov.alpha_composite(pm, (65, 148))
    else:
        d = ImageDraw.Draw(ov)
        mw = sc["main_word"]
        fsz = 92 if len(mw) <= 13 else (78 if len(mw) <= 17 else 68)
        d.text((546, 266), mw, font=fnt(FONT_HEAVY, fsz), fill=(0, 0, 0, 225), anchor="mm")
        d.text((540, 258), mw, font=fnt(FONT_HEAVY, fsz), fill=(255, 182, 42, 255),
               anchor="mm", stroke_width=5, stroke_fill=(10, 18, 36, 255))
        d.text((540, 356), sc["main_sub"], font=fnt(FONT_HEAVY, 38), fill=(255, 252, 242, 255),
               anchor="mm", stroke_width=4, stroke_fill=(10, 18, 36, 245))
    d = ImageDraw.Draw(ov)
    f_vi = fnt(FONT_THIN, 26)
    for idx, vline in enumerate(sc["vi_lines"]):
        d.text((540, 1596 + idx * 36), vline, font=f_vi, fill=(220, 235, 252, 245),
               anchor="mm", stroke_width=2, stroke_fill=(5, 10, 22, 230))
    draw_top_header_and_logo(ov)
    return ov


def draw_karaoke_eng_sub(base_ov: Image.Image, en_lines: list, active_idx: int) -> Image.Image:
    ov = base_ov.copy()
    d = ImageDraw.Draw(ov)
    f_en = fnt(FONT_BOLD, 34)
    w_counter = 0
    start_y = 1432 if len(en_lines) == 3 else 1456
    for l_idx, line in enumerate(en_lines):
        words = line.split()
        space_w = d.textlength(" ", font=f_en)
        word_widths = [d.textlength(w, font=f_en) for w in words]
        total_w = sum(word_widths) + space_w * max(0, len(words) - 1)
        x = 540.0 - total_w / 2.0
        y = start_y + l_idx * 48
        for w, ww in zip(words, word_widths):
            if w_counter == active_idx:
                d.rounded_rectangle([x - 9, y - 23, x + ww + 9, y + 21], radius=10,
                                    fill=(22, 163, 74, 250), outline=(134, 239, 172, 220), width=2)
            d.text((x, y), w, font=fnt(FONT_BOLD, 34), fill=(255, 255, 255, 255), anchor="lm",
                   stroke_width=3, stroke_fill=(6, 12, 24, 240))
            x += ww + space_w
            w_counter += 1
    return ov
