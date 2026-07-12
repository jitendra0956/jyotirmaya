"""
Jyotirmaya — premium cover from curated AI-art pool.
Pool: assets/covers/{mon..sun}.png (1080x1080, textless, clean center).
Selection is deterministic by weekday -> consistent brand rhythm.
Fallback: if pool image missing/corrupt, cards.py renders the classic PIL cover.
All text is PIL-overlaid with real Odia fonts — never AI-generated text.
"""
import os, datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(__file__)
POOL = os.path.join(HERE, "..", "assets", "covers")
FDIR = os.path.join(HERE, "..", "fonts")

GOLD = (217, 164, 65)
GOLD_LIGHT = (232, 200, 106)
CREAM = (244, 239, 228)
MUTED = (200, 188, 225)

WEEKDAY_FILES = ["mon.png", "tue.png", "wed.png", "thu.png",
                 "fri.png", "sat.png", "sun.png"]


def pool_image_for(date: datetime.date):
    """Return opened pool image for this weekday, or None (triggers fallback)."""
    path = os.path.join(POOL, WEEKDAY_FILES[date.weekday()])
    if not os.path.exists(path):
        # secondary: any image in pool, still deterministic
        try:
            imgs = sorted(f for f in os.listdir(POOL)
                          if f.lower().endswith((".png", ".jpg", ".jpeg")))
        except FileNotFoundError:
            return None
        if not imgs:
            return None
        path = os.path.join(POOL, imgs[date.toordinal() % len(imgs)])
    try:
        img = Image.open(path).convert("RGB")
        return img.resize((1080, 1080), Image.LANCZOS)
    except Exception:
        return None


def _text_with_glow(img, xy, text, font, fill, glow=(0, 0, 0)):
    """Soft dark glow behind text for readability on any artwork."""
    x, y = xy
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.text((x, y), text, font=font, fill=glow + (200,))
    layer = layer.filter(ImageFilter.GaussianBlur(6))
    img.paste(Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB"), (0, 0))
    d = ImageDraw.Draw(img)
    d.text((x, y), text, font=font, fill=fill)


def render_premium_cover(date: datetime.date, date_odia: str,
                         weekday_odia: str, out: str) -> bool:
    """Compose pool art + branding overlay. Returns False if pool unavailable
    (caller then uses the classic PIL cover as fallback)."""
    art = pool_image_for(date)
    if art is None:
        return False
    d = ImageDraw.Draw(art)
    W = 1080

    def F(name, size):
        return ImageFont.truetype(os.path.join(FDIR, name), size)

    # top: small brand line
    f_top = F("NotoSansOriya-Bold.ttf", 30)
    t = "ଦୈନିକ ପଞ୍ଜିକା"
    w = d.textlength(t, font=f_top)
    _text_with_glow(art, ((W - w) / 2, 56), t, f_top, GOLD)

    # title block (bottom third — pool art keeps center clean, subject upper-mid)
    f_title = F("NotoSansOriya-Black.ttf", 88)
    t = "ଆଜିର ରାଶିଫଳ"
    w = d.textlength(t, font=f_title)
    _text_with_glow(art, ((W - w) / 2, 800), t, f_title, CREAM)

    f_date = F("NotoSansOriya-Bold.ttf", 40)
    t = f"{date_odia} · {weekday_odia}"
    w = d.textlength(t, font=f_date)
    _text_with_glow(art, ((W - w) / 2, 916), t, f_date, GOLD_LIGHT)

    # footer brand
    f_foot = F("NotoSansOriya-Bold.ttf", 26)
    t = "ଜ୍ୟୋତିର୍ମୟ  ·  @jyotirmaya.odia"
    w = d.textlength(t, font=f_foot)
    _text_with_glow(art, ((W - w) / 2, 1006), t, f_foot, MUTED)

    art.save(out, quality=95)
    return True
