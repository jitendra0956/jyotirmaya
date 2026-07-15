"""
Jyotirmaya — Festival greeting slide.
Checks whether today matches a known festival, and if the corresponding
artwork exists in assets/festivals/<key>.png, renders a greeting slide
(art + PIL text overlay). If either the date isn't a festival or the art
hasn't been added yet, this returns None and the daily pipeline proceeds
exactly as normal — this feature can never break a post.
"""
import json, os, datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(__file__)
FESTIVALS_DIR = os.path.join(HERE, "..", "assets", "festivals")
FDIR = os.path.join(HERE, "..", "fonts")
GOLD = (217, 164, 65)
CREAM = (244, 239, 228)


def check_today(date: datetime.date):
    """Returns festival info dict for this date, or None."""
    table_path = os.path.join(FESTIVALS_DIR, f"festival_dates_{date.year}.json")
    if not os.path.exists(table_path):
        return None
    table = json.load(open(table_path, encoding="utf-8"))
    return table.get(date.isoformat())


def art_available(festival_key):
    path = os.path.join(FESTIVALS_DIR, f"{festival_key}.png")
    return path if os.path.exists(path) else None


def _text_with_glow(img, xy, text, font, fill, glow=(0, 0, 0)):
    x, y = xy
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.text((x, y), text, font=font, fill=glow + (210,))
    layer = layer.filter(ImageFilter.GaussianBlur(6))
    img.paste(Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB"), (0, 0))
    ImageDraw.Draw(img).text((x, y), text, font=font, fill=fill)


def render_greeting_slide(date: datetime.date, date_odia_str: str, out_path: str) -> bool:
    """Attempts to render today's festival greeting slide.
    Returns True if rendered, False if skipped (no festival / no art yet)."""
    info = check_today(date)
    if not info:
        return False
    art_path = art_available(info["key"])
    if not art_path:
        print(f"[info] festival '{info['key']}' today but no art yet at "
              f"assets/festivals/{info['key']}.png — skipping greeting slide")
        return False

    img = Image.open(art_path).convert("RGB").resize((1080, 1080), Image.LANCZOS)
    d = ImageDraw.Draw(img)

    f_greeting = ImageFont.truetype(os.path.join(FDIR, "NotoSansOriya-Black.ttf"), 56)
    text = info["greeting_odia"]
    # wrap if too wide
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f_greeting) <= 900:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)

    total_h = len(lines) * 68
    y = 860 - total_h
    for ln in lines:
        w = d.textlength(ln, font=f_greeting)
        _text_with_glow(img, ((1080 - w) / 2, y), ln, f_greeting, CREAM)
        y += 68

    f_date = ImageFont.truetype(os.path.join(FDIR, "NotoSansOriya-Bold.ttf"), 30)
    w = d.textlength(date_odia_str, font=f_date)
    _text_with_glow(img, ((1080 - w) / 2, y + 10), date_odia_str, f_date, GOLD)

    f_brand = ImageFont.truetype(os.path.join(FDIR, "NotoSansOriya-Bold.ttf"), 24)
    brand = "ଜ୍ୟୋତିର୍ମୟ  ·  @jyotirmaya.odia"
    w = d.textlength(brand, font=f_brand)
    _text_with_glow(img, ((1080 - w) / 2, 1020), brand, f_brand, (200, 180, 140))

    img.save(out_path, quality=95)
    print(f"[info] rendered festival greeting: {info['key']}")
    return True
