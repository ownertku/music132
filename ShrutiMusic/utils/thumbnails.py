# Copyright (c) 2025 Nand Yaduwanshi <NoxxOP>
# Enhanced UI by Aalyan | ShrutiBots
# Premium Glassmorphism Thumbnail Generator v3.0

import os
import random
import math
import aiohttp
import aiofiles
import traceback
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance, ImageChops
from py_yt import VideosSearch
from ShrutiMusic import app

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

CANVAS_W, CANVAS_H = 1280, 720

FONT_REGULAR_PATH = "ShrutiMusic/assets/font2.ttf"
FONT_BOLD_PATH    = "ShrutiMusic/assets/font3.ttf"
DEFAULT_THUMB     = "ShrutiMusic/assets/ShrutiBots.jpg"


# ─────────────────────────────────────────────
# Color Palettes — rich dark gradients
# ─────────────────────────────────────────────
PALETTES = [
    {   # Deep Violet Blue
        "bg":      [(10, 8, 35), (22, 18, 65), (14, 12, 50)],
        "accent":  (110, 160, 255),
        "glow":    (80, 120, 255),
        "bar":     (120, 170, 255),
    },
    {   # Midnight Rose
        "bg":      [(35, 8, 22), (65, 14, 40), (50, 10, 30)],
        "accent":  (255, 120, 180),
        "glow":    (220, 80, 140),
        "bar":     (255, 140, 190),
    },
    {   # Forest Teal
        "bg":      [(8, 28, 30), (12, 50, 52), (10, 38, 40)],
        "accent":  (80, 220, 200),
        "glow":    (50, 190, 170),
        "bar":     (100, 230, 210),
    },
    {   # Amber Dark
        "bg":      [(30, 18, 5), (60, 35, 8), (45, 25, 5)],
        "accent":  (255, 185, 60),
        "glow":    (220, 150, 30),
        "bar":     (255, 200, 80),
    },
    {   # Electric Purple
        "bg":      [(20, 5, 40), (45, 10, 80), (30, 7, 58)],
        "accent":  (190, 100, 255),
        "glow":    (160, 70, 230),
        "bar":     (200, 120, 255),
    },
    {   # Deep Ocean
        "bg":      [(5, 15, 40), (8, 30, 70), (6, 22, 55)],
        "accent":  (60, 180, 255),
        "glow":    (30, 150, 230),
        "bar":     (80, 200, 255),
    },
]


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3))


def apply_gradient(canvas, bg_colors):
    c1, c2, c3 = bg_colors
    draw = ImageDraw.Draw(canvas)
    for y in range(CANVAS_H):
        t = y / CANVAS_H
        if t < 0.5:
            col = lerp_color(c1, c2, t / 0.5)
        else:
            col = lerp_color(c2, c3, (t - 0.5) / 0.5)
        draw.line([(0, y), (CANVAS_W, y)], fill=(*col, 255))
    return canvas


def add_noise_texture(canvas, intensity=8):
    """Subtle film-grain noise for premium feel."""
    noise = Image.new("RGBA", (CANVAS_W, CANVAS_H))
    pixels = noise.load()
    for y in range(CANVAS_H):
        for x in range(CANVAS_W):
            v = random.randint(-intensity, intensity)
            pixels[x, y] = (128 + v, 128 + v, 128 + v, 18)
    return Image.alpha_composite(canvas, noise)


def draw_glow_circle(canvas, cx, cy, radius, color, layers=8):
    """Multi-layer soft glow behind album art."""
    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(glow)
    for i in range(layers, 0, -1):
        r = radius + i * 18
        alpha = int(60 * (i / layers))
        g_draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=(*color, alpha)
        )
    glow = glow.filter(ImageFilter.GaussianBlur(20))
    return Image.alpha_composite(canvas, glow)


def draw_album_art_circle(canvas, art_img, cx, cy, size):
    """Circular album art with glass border + inner shadow."""
    # Glow behind
    canvas = draw_glow_circle(canvas, cx, cy, size // 2, (150, 150, 255), layers=6)

    # Resize art square
    art = art_img.resize((size, size), Image.LANCZOS).convert("RGBA")

    # Circular mask
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size, size], fill=255)
    art.putalpha(mask)

    # Paste art
    ax, ay = cx - size // 2, cy - size // 2
    canvas.paste(art, (ax, ay), art)

    # Glass border ring
    ring = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    bw = 5
    rd.ellipse(
        [ax - bw, ay - bw, ax + size + bw, ay + size + bw],
        outline=(255, 255, 255, 60), width=bw
    )
    rd.ellipse(
        [ax - bw*2, ay - bw*2, ax + size + bw*2, ay + size + bw*2],
        outline=(255, 255, 255, 25), width=bw
    )
    canvas = Image.alpha_composite(canvas, ring)

    # Specular highlight (top-left shine)
    shine = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shine)
    sd.ellipse(
        [size // 6, size // 6, size // 2, size // 2],
        fill=(255, 255, 255, 18)
    )
    shine = shine.filter(ImageFilter.GaussianBlur(12))
    shine.putalpha(mask)
    canvas.paste(shine, (ax, ay), shine)

    return canvas


def draw_music_bars(draw, x, y, accent_color, bar_count=20, bar_w=7, gap=4, max_h=55):
    """Animated-look music equalizer bars."""
    heights = [
        int(max_h * abs(math.sin(i * 0.8 + random.uniform(0, 1)))) + 8
        for i in range(bar_count)
    ]
    for i, h in enumerate(heights):
        bx = x + i * (bar_w + gap)
        # Ensure coordinates are always valid (y0 <= y1)
        bar_top    = y - h
        bar_bottom = y
        mid        = (bar_top + bar_bottom) // 2

        top_col = tuple(min(255, c + 60) for c in accent_color)

        # Shadow
        draw.rectangle(
            [bx + 1, bar_top + 1, bx + bar_w + 1, bar_bottom + 1],
            fill=(0, 0, 0, 80)
        )
        # Top half bar (brighter)
        draw.rectangle(
            [bx, bar_top, bx + bar_w, mid],
            fill=(*top_col, 210)
        )
        # Bottom half bar
        draw.rectangle(
            [bx, mid, bx + bar_w, bar_bottom],
            fill=(*accent_color, 150)
        )
        # Rounded top cap
        cap_y1 = bar_top + bar_w
        if cap_y1 > bar_top:
            draw.ellipse(
                [bx, bar_top, bx + bar_w, cap_y1],
                fill=(*top_col, 230)
            )



def draw_text_with_shadow(draw, pos, text, font, color, shadow_color=(0, 0, 0), shadow_offset=3, shadow_blur=None):
    x, y = pos
    draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=(*shadow_color, 160))
    draw.text((x, y), text, font=font, fill=color)


def truncate_title(title, max_chars=32):
    return title[:max_chars].rstrip() + "…" if len(title) > max_chars else title


def wrap_title(draw, title, font, max_width):
    words = title.split()
    lines, line = [], ""
    for w in words:
        test = (line + " " + w).strip()
        if draw.textlength(test, font=font) <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
        if len(lines) == 2:
            break
    if line and len(lines) < 2:
        lines.append(line)
    # Add ellipsis if needed
    if len(lines) == 2 and len(words) > len(" ".join(lines).split()):
        lines[1] = lines[1].rstrip() + "…"
    return lines


def draw_glass_panel(canvas, x, y, w, h, radius=24):
    """Frosted-glass dark panel behind text area."""
    panel = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    pd = ImageDraw.Draw(panel)
    pd.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=(255, 255, 255, 12))
    pd.rounded_rectangle([x, y, x + w, y + h], radius=radius, outline=(255, 255, 255, 28), width=1)
    blurred = panel.filter(ImageFilter.GaussianBlur(2))
    return Image.alpha_composite(canvas, blurred)


def draw_corner_brackets(draw, color, margin=22, size=38, width=3):
    """Elegant corner brackets."""
    c = (*color, 140)
    m, s, w = margin, size, width
    R, B = CANVAS_W - m, CANVAS_H - m
    # Top-left
    draw.line([(m, m), (m + s, m)], fill=c, width=w)
    draw.line([(m, m), (m, m + s)], fill=c, width=w)
    # Top-right
    draw.line([(R, m), (R - s, m)], fill=c, width=w)
    draw.line([(R, m), (R, m + s)], fill=c, width=w)
    # Bottom-left
    draw.line([(m, B), (m + s, B)], fill=c, width=w)
    draw.line([(m, B), (m, B - s)], fill=c, width=w)
    # Bottom-right
    draw.line([(R, B), (R - s, B)], fill=c, width=w)
    draw.line([(R, B), (R, B - s)], fill=c, width=w)


def draw_divider(draw, x, y, length, color, alpha=120):
    draw.line([(x, y), (x + length, y)], fill=(*color, alpha), width=2)


def draw_dot_row(draw, x, y, count, color):
    for i in range(count):
        r = 3
        cx = x + i * 14
        draw.ellipse([cx - r, y - r, cx + r, y + r], fill=(*color, 80))


async def gen_thumb(videoid: str):
    url = f"https://www.youtube.com/watch?v={videoid}"
    thumb_path = None

    # Direct YouTube thumbnail URLs (high quality first, then fallbacks)
    thumb_urls = [
        f"https://i.ytimg.com/vi/{videoid}/maxresdefault.jpg",
        f"https://i.ytimg.com/vi/{videoid}/sddefault.jpg",
        f"https://i.ytimg.com/vi/{videoid}/hqdefault.jpg",
        f"https://i.ytimg.com/vi/{videoid}/mqdefault.jpg",
    ]

    title, duration, views, channel = "Unknown Title", "0:00", "—", "Unknown"

    try:
        results = VideosSearch(url, limit=1)
        result = (await results.next())["result"][0]
        title    = result.get("title", "Unknown Title")
        duration = result.get("duration", "0:00")
        views    = result.get("viewCount", {}).get("short", "—")
        channel  = result.get("channel", {}).get("name", "Unknown")
    except Exception as e:
        print(f"[gen_thumb Search Error] {e}")

    # Download thumbnail — try each URL until one works
    thumb_path = CACHE_DIR / f"thumb{videoid}.jpg"
    downloaded = False
    try:
        async with aiohttp.ClientSession() as session:
            for turl in thumb_urls:
                try:
                    async with session.get(
                        turl,
                        timeout=aiohttp.ClientTimeout(total=10),
                        headers={"User-Agent": "Mozilla/5.0"}
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            if len(data) > 5000:   # valid image must be > 5KB
                                async with aiofiles.open(thumb_path, "wb") as f:
                                    await f.write(data)
                                downloaded = True
                                break
                except Exception:
                    continue
    except Exception as e:
        print(f"[gen_thumb Download Error] {e}")

    # Load image
    try:
        if downloaded and thumb_path.exists() and thumb_path.stat().st_size > 5000:
            base_img = Image.open(thumb_path).convert("RGBA")
        else:
            # Absolute path fallback
            fallback = Path(__file__).parent.parent / "assets" / "ShrutiBots.jpg"
            base_img = Image.open(str(fallback)).convert("RGBA")
    except Exception as e:
        print(f"[gen_thumb Image Load Error] {e}")
        try:
            fallback = Path(__file__).parent.parent / "assets" / "ShrutiBots.jpg"
            base_img = Image.open(str(fallback)).convert("RGBA")
        except Exception:
            traceback.print_exc()
            return None


    try:
        palette = random.choice(PALETTES)
        bg_colors  = palette["bg"]
        accent     = palette["accent"]
        glow_col   = palette["glow"]
        bar_color  = palette["bar"]

        # ── Canvas ──────────────────────────────────────
        canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 255))
        canvas = apply_gradient(canvas, bg_colors)

        # Subtle vignette
        vignette = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
        vd = ImageDraw.Draw(vignette)
        for i in range(200):
            alpha = int(160 * (1 - (i / 200) ** 0.4))
            vd.rectangle([i, i, CANVAS_W - i, CANVAS_H - i], outline=(0, 0, 0, alpha // 6))
        canvas = Image.alpha_composite(canvas, vignette)

        # Subtle noise
        canvas = add_noise_texture(canvas, intensity=6)

        # ── Left side: Album Art ────────────────────────
        art_size = 380
        art_cx   = 110 + art_size // 2          # center-x
        art_cy   = CANVAS_H // 2                 # center-y

        canvas = draw_album_art_circle(canvas, base_img, art_cx, art_cy, art_size)

        # ── Right side: Text Panel ──────────────────────
        panel_x = 380
        panel_y = 80
        panel_w = CANVAS_W - panel_x - 40
        panel_h = CANVAS_H - 160

        canvas = draw_glass_panel(canvas, panel_x, panel_y, panel_w, panel_h)

        draw = ImageDraw.Draw(canvas)

        # Corner brackets
        draw_corner_brackets(draw, accent)

        # ── Bot username (top-left badge) ────────────────
        bot_font = ImageFont.truetype(FONT_BOLD_PATH, 30)
        badge_x, badge_y = 28, 26
        # Safe username fetch
        try:
            bot_name = f"@{app.username}" if getattr(app, 'username', None) else "@ShrutiMusicBot"
        except Exception:
            bot_name = "@ShrutiMusicBot"
        bw = int(draw.textlength(bot_name, font=bot_font)) + 28
        draw.rounded_rectangle(
            [badge_x - 10, badge_y - 6, badge_x + bw, badge_y + 36],
            radius=20, fill=(0, 0, 0, 120)
        )
        draw.rounded_rectangle(
            [badge_x - 10, badge_y - 6, badge_x + bw, badge_y + 36],
            radius=20, outline=(*accent, 80), width=1
        )
        draw.text((badge_x, badge_y), bot_name, font=bot_font, fill=(255, 255, 255, 230))

        # ── "NOW PLAYING" label ──────────────────────────
        tx = panel_x + 35
        np_font = ImageFont.truetype(FONT_BOLD_PATH, 34)
        np_y = panel_y + 36

        # Glowing pill behind "NOW PLAYING"
        np_w = int(draw.textlength("NOW PLAYING", font=np_font)) + 32
        draw.rounded_rectangle(
            [tx - 10, np_y - 6, tx + np_w, np_y + 40],
            radius=18, fill=(*accent, 28)
        )
        draw.rounded_rectangle(
            [tx - 10, np_y - 6, tx + np_w, np_y + 40],
            radius=18, outline=(*accent, 100), width=1
        )
        shadow_off = 2
        draw.text((tx + shadow_off, np_y + shadow_off), "NOW PLAYING",
                  font=np_font, fill=(0, 0, 0, 120))
        draw.text((tx, np_y), "NOW PLAYING", font=np_font, fill=(*accent, 255))

        # Small dot accent row
        draw_dot_row(draw, tx, np_y + 55, 5, accent)

        # ── Title ────────────────────────────────────────
        title_font = ImageFont.truetype(FONT_BOLD_PATH, 48)
        title_lines = wrap_title(draw, title, title_font, panel_w - 60)
        title_y = np_y + 72

        for i, line in enumerate(title_lines):
            ly = title_y + i * 62
            # Shadow
            draw.text((tx + 3, ly + 3), line, font=title_font, fill=(0, 0, 0, 150))
            draw.text((tx, ly), line, font=title_font, fill=(255, 255, 255, 255))

        # ── Divider ──────────────────────────────────────
        div_y = title_y + len(title_lines) * 62 + 18
        draw_divider(draw, tx, div_y, panel_w - 60, accent, alpha=90)

        # ── Meta info ────────────────────────────────────
        meta_font = ImageFont.truetype(FONT_REGULAR_PATH, 30)
        icon_font = ImageFont.truetype(FONT_BOLD_PATH, 30)
        meta_y = div_y + 22

        def meta_row(y, icon, label, value):
            # Icon dot accent
            draw.ellipse([tx, y + 10, tx + 10, y + 20], fill=(*accent, 200))
            draw.text((tx + 20, y), f"{label}  {value}", font=meta_font, fill=(210, 215, 230, 230))

        meta_row(meta_y,      "●", "Views   :", f"{views}")
        meta_row(meta_y + 46, "●", "Duration:", f"{duration}")
        meta_row(meta_y + 92, "●", "Channel :", f"{channel[:28]}{'…' if len(channel) > 28 else ''}")

        # ── Divider 2 ────────────────────────────────────
        div2_y = meta_y + 138
        draw_divider(draw, tx, div2_y, panel_w - 60, accent, alpha=55)

        # ── Music Equalizer Bars ─────────────────────────
        bars_y  = div2_y + 58
        bars_x  = tx
        draw_music_bars(
            draw, bars_x, bars_y,
            bar_color, bar_count=22, bar_w=8, gap=5, max_h=52
        )

        # "STREAMING" label beside bars
        stream_font = ImageFont.truetype(FONT_REGULAR_PATH, 24)
        bars_total_w = 22 * (8 + 5)
        draw.text(
            (bars_x + bars_total_w + 18, bars_y - 22),
            "STREAMING", font=stream_font, fill=(*accent, 160)
        )

        # ── Bottom watermark ─────────────────────────────
        wm_font = ImageFont.truetype(FONT_REGULAR_PATH, 22)
        wm_text = "Powered by ShrutiMusic • @NoxxOP"
        wm_w = int(draw.textlength(wm_text, font=wm_font))
        draw.text(
            (CANVAS_W - wm_w - 28, CANVAS_H - 36),
            wm_text, font=wm_font, fill=(*accent, 70)
        )

        # ── Save ─────────────────────────────────────────
        out = CACHE_DIR / f"{videoid}_final.png"
        canvas = canvas.convert("RGB")
        canvas.save(str(out), format="PNG", optimize=True)

        if thumb_path and thumb_path.exists():
            try:
                os.remove(thumb_path)
            except Exception:
                pass

        return str(out)

    except Exception as e:
        print(f"[gen_thumb Processing Error] {e}")
        traceback.print_exc()
        return None
