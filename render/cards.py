"""Ornate purple-gold card renderer. 1080x1080 output, 2x supersampled."""
import json, math, os, sys, datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import panchanga as pj

S = 2               # supersample factor
SIZE = 1080 * S
BG = (26, 15, 46)          # deep indigo
BG2 = (42, 26, 72)         # inner panel
GOLD = (217, 164, 65)
GOLD_LIGHT = (232, 200, 106)
PURPLE = (138, 95, 191)
CREAM = (244, 239, 228)
MUTED = (184, 168, 216)
TEXT = (232, 228, 216)

FDIR = os.path.join(os.path.dirname(__file__), "..", "fonts")
def F(name, size): return ImageFont.truetype(os.path.join(FDIR, name), size * S)

# Weekday planetary rulers (classical jyotish day-lords), keyed by date.weekday() (Mon=0..Sun=6)
WEEKDAY_THEME = {
    0: dict(name="ଚନ୍ଦ୍ର", symbol="\u263E", accent=(150, 178, 224), glow=(196, 214, 240)),   # Mon - Moon - cool silver-blue
    1: dict(name="ମଙ୍ଗଳ",  symbol="\u2642", accent=(206, 84, 68),  glow=(232, 128, 104)),   # Tue - Mars - red
    2: dict(name="ବୁଧ",    symbol="\u263F", accent=(96, 172, 128), glow=(150, 212, 168)),   # Wed - Mercury - green
    3: dict(name="ଗୁରୁ",   symbol="\u2643", accent=(217, 164, 65), glow=(240, 200, 110)),   # Thu - Jupiter - gold
    4: dict(name="ଶୁକ୍ର",  symbol="\u2640", accent=(212, 148, 188), glow=(238, 190, 218)),  # Fri - Venus - pink
    5: dict(name="ଶନି",    symbol="\u2644", accent=(102, 112, 150), glow=(140, 150, 188)),  # Sat - Saturn - slate-blue
    6: dict(name="ସୂର୍ଯ୍ୟ", symbol="\u2609", accent=(230, 142, 62), glow=(250, 180, 104)),  # Sun - Sun - orange
}
SYM_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def base_canvas(accent=None):
    accent = accent or GOLD
    img = Image.new("RGB", (SIZE, SIZE), BG)
    d = ImageDraw.Draw(img)
    # subtle vertical gradient
    for y in range(SIZE):
        t = y / SIZE
        r = int(26 + t * 8); g = int(15 + t * 6); b = int(46 + t * 18)
        d.line([(0, y), (SIZE, y)], fill=(r, g, b))
    # star field (a few tinted with the day's accent for subtle daily variation)
    import random
    random.seed(42)
    star_palette = [(139, 123, 184), (107, 91, 152), (155, 139, 200), accent]
    for _ in range(90):
        x, y = random.randint(0, SIZE), random.randint(0, SIZE)
        rr = random.choice([1, 1, 2]) * S
        c = random.choice(star_palette)
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=c)
    # double ornamental border
    m = 34 * S
    d.rounded_rectangle([m, m, SIZE - m, SIZE - m], radius=18 * S,
                        outline=accent, width=4 * S)
    m2 = 52 * S
    d.rounded_rectangle([m2, m2, SIZE - m2, SIZE - m2], radius=12 * S,
                        outline=PURPLE, width=2 * S)
    # corner arcs (temple-arch motif)
    for cx, cy, a in [(m, m, 0), (SIZE - m, m, 90), (SIZE - m, SIZE - m, 180), (m, SIZE - m, 270)]:
        for rad, w in [(56 * S, 3 * S), (38 * S, 2 * S)]:
            box = [cx - rad, cy - rad, cx + rad, cy + rad]
            d.arc(box, a, a + 90, fill=accent, width=w)
    # diamond accents mid-edges
    for x, y in [(SIZE // 2, m), (SIZE // 2, SIZE - m), (m, SIZE // 2), (SIZE - m, SIZE // 2)]:
        s = 14 * S
        d.polygon([(x, y - s), (x + s, y), (x, y + s), (x - s, y)], fill=accent)
    return img, d

def mandala(d, cx, cy, r):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=GOLD, width=3 * S)
    d.ellipse([cx - r + 12 * S, cy - r + 12 * S, cx + r - 12 * S, cy + r - 12 * S],
              outline=PURPLE, width=2 * S)
    for i in range(12):
        a = math.radians(i * 30)
        px, py = cx + (r + 12 * S) * math.cos(a), cy + (r + 12 * S) * math.sin(a)
        rr = 6 * S
        d.ellipse([px - rr, py - rr, px + rr, py + rr], fill=GOLD)
    d.ellipse([cx - r + 26 * S, cy - r + 26 * S, cx + r - 26 * S, cy + r - 26 * S], fill=BG2)

def wrap(d, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= max_w: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

BRAND = "ଜ୍ୟୋତିର୍ମୟ"
HANDLE = "@jyotirmaya.odia"
ODIA_MONTHS = {1:"ଜାନୁଆରୀ",2:"ଫେବୃଆରୀ",3:"ମାର୍ଚ୍ଚ",4:"ଏପ୍ରିଲ",5:"ମେ",6:"ଜୁନ",7:"ଜୁଲାଇ",8:"ଅଗଷ୍ଟ",9:"ସେପ୍ଟେମ୍ବର",10:"ଅକ୍ଟୋବର",11:"ନଭେମ୍ବର",12:"ଡିସେମ୍ବର"}

def date_odia(date):
    return pj.odia_digits(str(date.day)) + " " + ODIA_MONTHS[date.month] + " " + pj.odia_digits(str(date.year))

def draw_footer(d):
    f = F("NotoSansOriya-Bold.ttf", 20)
    txt = BRAND + "  ·  " + HANDLE
    w = d.textlength(txt, font=f)
    d.text(((SIZE - w) / 2, 1016 * S), txt, font=f, fill=(150, 130, 90))

def render_rashi_card(p, ctx, item, out, date):
    img, d = base_canvas()
    reg, bold, black = "NotoSansOriya-Regular.ttf", "NotoSansOriya-Bold.ttf", "NotoSansOriya-Black.ttf"
    # header
    hdr = "ଆଜିର ରାଶିଫଳ"
    f = F(bold, 30)
    w = d.textlength(hdr, font=f)
    d.text(((SIZE - w) / 2, 78 * S), hdr, font=f, fill=GOLD)
    dt = date_odia(date) + " · " + p["weekday_odia"]
    f2 = F(reg, 22)
    w = d.textlength(dt, font=f2)
    d.text(((SIZE - w) / 2, 124 * S), dt, font=f2, fill=MUTED)
    # mandala + symbol
    cx, cy, r = SIZE // 2, 320 * S, 105 * S
    mandala(d, cx, cy, r)
    sym_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 92 * S)
    sw = d.textlength(ctx["symbol"], font=sym_font)
    d.text((cx - sw / 2, cy - 62 * S), ctx["symbol"], font=sym_font, fill=GOLD_LIGHT)
    # rashi name
    f3 = F(black, 58)
    name = ctx["rashi_odia"] + " ରାଶି"
    w = d.textlength(name, font=f3)
    d.text(((SIZE - w) / 2, 462 * S), name, font=f3, fill=CREAM)
    # syllables
    f4 = F(reg, 22)
    syl = " · ".join(ctx["syllables_odia"].split())
    w = d.textlength(syl, font=f4)
    d.text(((SIZE - w) / 2, 552 * S), syl, font=f4, fill=MUTED)
    # divider
    d.line([(SIZE // 2 - 140 * S, 606 * S), (SIZE // 2 + 140 * S, 606 * S)], fill=GOLD, width=2 * S)
    dm = 10 * S
    d.polygon([(SIZE // 2, 606 * S - dm), (SIZE // 2 + dm, 606 * S), (SIZE // 2, 606 * S + dm), (SIZE // 2 - dm, 606 * S)], fill=GOLD)
    # prediction text
    f5 = F(reg, 30)
    lines = wrap(d, item["text"], f5, 800 * S)
    y = 648 * S
    for ln in lines:
        w = d.textlength(ln, font=f5)
        d.text(((SIZE - w) / 2, y), ln, font=f5, fill=TEXT)
        y += 52 * S
    # bottom pills
    pills = [("ଶୁଭ ରଙ୍ଗ", item["color"]), ("ଶୁଭ ସଂଖ୍ୟା", item["number"]), ("ରାହୁ କାଳ", p["rahu_kaal"]["start"].replace(":", ".") )]
    pw, ph, gap = 270 * S, 92 * S, 24 * S
    total = pw * 3 + gap * 2
    x0 = (SIZE - total) // 2
    yb = 906 * S
    fl = F(reg, 18); fv = F(bold, 26)
    for i, (lab, val) in enumerate(pills):
        x = x0 + i * (pw + gap)
        d.rounded_rectangle([x, yb, x + pw, yb + ph], radius=20 * S, fill=BG2, outline=GOLD, width=2 * S)
        w = d.textlength(lab, font=fl)
        d.text((x + (pw - w) / 2, yb + 14 * S), lab, font=fl, fill=MUTED)
        w = d.textlength(val, font=fv)
        d.text((x + (pw - w) / 2, yb + 44 * S), val, font=fv, fill=GOLD_LIGHT)
    draw_footer(d)
    img = img.resize((1080, 1080), Image.LANCZOS)
    img.save(out, quality=95)

def _planet_badge(d, cx, cy, r, theme):
    """Small badge showing today's weekday planetary ruler (day-lord)."""
    accent, glow = theme["accent"], theme["glow"]
    d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(38, 26, 58), outline=accent, width=2)
    d.ellipse([cx-r+6, cy-r+6, cx+r-6, cy+r-6], outline=glow, width=1)
    sym_font = ImageFont.truetype(SYM_FONT_PATH, int(r * 1.05))
    sw = d.textlength(theme["symbol"], font=sym_font)
    bbox = d.textbbox((0, 0), theme["symbol"], font=sym_font)
    sh = bbox[3] - bbox[1]
    d.text((cx - sw/2, cy - sh/2 - bbox[1]), theme["symbol"], font=sym_font, fill=glow)


def _radial_glow(img, cx, cy, radius, color, max_alpha=90):
    """Soft radial glow pasted behind content for depth/premium feel."""
    glow = Image.new("RGBA", (radius * 2, radius * 2), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    steps = 40
    for i in range(steps, 0, -1):
        t = i / steps
        rr = int(radius * t)
        alpha = int(max_alpha * (1 - t) ** 2)
        gd.ellipse([radius - rr, radius - rr, radius + rr, radius + rr],
                  fill=(color[0], color[1], color[2], alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(radius * 0.15))
    img.paste(Image.alpha_composite(
        img.convert("RGBA").crop((cx - radius, cy - radius, cx + radius, cy + radius)).convert("RGBA"),
        glow).convert("RGB"), (cx - radius, cy - radius))


def _grain_texture(img, strength=6):
    """Subtle noise overlay for a premium print/paper feel."""
    import random
    w, h = img.size
    noise = Image.new("L", (w // 2, h // 2))
    random.seed(7)
    npix = noise.load()
    for y in range(0, h // 2, 2):
        for x in range(0, w // 2, 2):
            v = 128 + random.randint(-strength, strength)
            npix[x, y] = max(0, min(255, v))
    noise = noise.resize((w, h))
    noise_rgb = Image.merge("RGB", (noise, noise, noise))
    return Image.blend(img, noise_rgb, 0.035)


def _lotus_flourish(d, cx, cy, scale, color):
    """Small stylized lotus motif — simple, elegant, non-denominational."""
    petal_w, petal_h = 9 * scale, 22 * scale
    for i, ang in enumerate([-50, -25, 0, 25, 50]):
        a = math.radians(ang)
        length = petal_h if ang != 0 else petal_h * 1.15
        tip_x = cx + length * math.sin(a)
        tip_y = cy - length * math.cos(a)
        base_l = (cx - petal_w * math.cos(a), cy - petal_w * math.sin(a))
        base_r = (cx + petal_w * math.cos(a), cy + petal_w * math.sin(a))
        d.polygon([base_l, (tip_x, tip_y), base_r], fill=None, outline=color, width=max(1, scale // 3))
    d.ellipse([cx - 4*scale, cy - 4*scale, cx + 4*scale, cy + 4*scale], fill=color)


def _moon_phase_disc(d, cx, cy, r, tithi_index):
    """Draws a crescent/gibbous/full moon matching today's actual tithi (0-29)."""
    # 0=new moon growing, 14=full, 15-29=waning back to new
    frac = tithi_index / 29.0  # 0..1 across the lunar month
    d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(58, 42, 92))
    # illuminated portion via an offset bright circle, clipped by outer disc
    if frac <= 0.5:
        # waxing: light grows from right
        offset = r * (1 - frac * 4) if frac < 0.25 else -r * ((frac-0.25) * 4)
    else:
        f2 = frac - 0.5
        offset = -r * (1 - f2 * 4) if f2 < 0.25 else r * ((f2-0.25) * 4)
    mask = Image.new("L", (int(r*2), int(r*2)), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([0, 0, r*2, r*2], fill=255)
    bright = Image.new("L", (int(r*2), int(r*2)), 0)
    bd = ImageDraw.Draw(bright)
    bd.ellipse([r - r + offset, 0, r + r + offset, r*2], fill=255)
    from PIL import ImageChops
    lit = ImageChops.multiply(mask, bright)
    glow_layer = Image.new("RGB", (int(r*2), int(r*2)), GOLD_LIGHT)
    base_img = d._image
    base_img.paste(glow_layer, (int(cx-r), int(cy-r)), lit)
    d.ellipse([cx-r, cy-r, cx+r, cy+r], outline=GOLD, width=2)


def render_cover(p, out, date, part_label=None, rashi_names=None):
    theme = WEEKDAY_THEME[date.weekday()]
    img, d = base_canvas(accent=theme["accent"])
    reg, bold, black = "NotoSansOriya-Regular.ttf", "NotoSansOriya-Bold.ttf", "NotoSansOriya-Black.ttf"

    # faint Konark-wheel watermark behind everything, upper area — tinted to day accent
    wheel_cx, wheel_cy, wheel_r = SIZE // 2, 230 * S, 175 * S
    wd = ImageDraw.Draw(img, "RGBA")
    ac = theme["accent"]
    wd.ellipse([wheel_cx-wheel_r, wheel_cy-wheel_r, wheel_cx+wheel_r, wheel_cy+wheel_r],
               outline=(ac[0], ac[1], ac[2], 45), width=2 * S)
    wd.ellipse([wheel_cx-wheel_r+16*S, wheel_cy-wheel_r+16*S, wheel_cx+wheel_r-16*S, wheel_cy+wheel_r-16*S],
               outline=(ac[0], ac[1], ac[2], 30), width=1 * S)
    for i in range(24):
        a = math.radians(i * 15)
        x1, y1 = wheel_cx + (wheel_r-16*S) * math.cos(a), wheel_cy + (wheel_r-16*S) * math.sin(a)
        x2, y2 = wheel_cx + (wheel_r-46*S) * math.cos(a), wheel_cy + (wheel_r-46*S) * math.sin(a)
        wd.line([(x1, y1), (x2, y2)], fill=(ac[0], ac[1], ac[2], 35), width=2 * S)

    # soft glow behind the title block for premium depth
    _radial_glow(img, SIZE // 2, 210 * S, 230 * S, theme["glow"], max_alpha=55)

    # planet badge (day-lord) top-left, with soft halo, small label beneath it
    _radial_glow(img, 150 * S, 210 * S, 90 * S, theme["glow"], max_alpha=70)
    _planet_badge(d, 150 * S, 210 * S, 44 * S, theme)
    lbl = theme["name"] + " ବାର"
    fl_badge = F(bold, 18)
    w = d.textlength(lbl, font=fl_badge)
    d.text((150 * S - w/2, 262 * S), lbl, font=fl_badge, fill=theme["glow"])

    hdr = "ଦୈନିକ ପଞ୍ଜିକା" + (f"  ·  {part_label}" if part_label else "")
    f = F(bold, 30 if part_label else 32)
    w = d.textlength(hdr, font=f)
    d.text(((SIZE - w) / 2, 90 * S), hdr, font=f, fill=GOLD)

    _radial_glow(img, SIZE - 150*S, 210*S, 90 * S, GOLD_LIGHT, max_alpha=70)
    _moon_phase_disc(d, SIZE - 150*S, 210*S, 44*S, p["tithi"]["index"])

    day = p["weekday_odia"]
    f2 = F(black, 76)
    w = d.textlength(day, font=f2)
    d.text(((SIZE - w) / 2, 158 * S), day, font=f2, fill=CREAM)
    dt = date_odia(date)
    f3 = F(reg, 30)
    w = d.textlength(dt, font=f3)
    d.text(((SIZE - w) / 2, 272 * S), dt, font=f3, fill=MUTED)

    cx_div, y_div = SIZE // 2, 344 * S
    d.line([(cx_div - 150 * S, y_div), (cx_div - 34*S, y_div)], fill=GOLD, width=2 * S)
    d.line([(cx_div + 34 * S, y_div), (cx_div + 150*S, y_div)], fill=GOLD, width=2 * S)
    _lotus_flourish(d, cx_div, y_div, S, GOLD)

    # fewer rows when a rashi list needs space below
    rows = [
        ("ତିଥି", p["tithi"]["odia"]),
        ("ନକ୍ଷତ୍ର", p["nakshatra"]["odia"]),
        ("ଚନ୍ଦ୍ର ରାଶି", p["moon_rashi"]["odia"]),
        ("ସୂର୍ଯ୍ୟୋଦୟ", pj.odia_digits(p["sunrise"])),
        ("ରାହୁ କାଳ", pj.odia_digits(p["rahu_kaal"]["start"] + " – " + p["rahu_kaal"]["end"])),
    ] if rashi_names else [
        ("ତିଥି", p["tithi"]["odia"]),
        ("ନକ୍ଷତ୍ର", p["nakshatra"]["odia"]),
        ("ଚନ୍ଦ୍ର ରାଶି", p["moon_rashi"]["odia"]),
        ("ସୂର୍ଯ୍ୟୋଦୟ", pj.odia_digits(p["sunrise"])),
        ("ସୂର୍ଯ୍ୟାସ୍ତ", pj.odia_digits(p["sunset"])),
        ("ରାହୁ କାଳ", pj.odia_digits(p["rahu_kaal"]["start"] + " – " + p["rahu_kaal"]["end"])),
    ]
    fl = F(reg, 26); fv = F(bold, 30)
    y = 388 * S
    for lab, val in rows:
        d.ellipse([170*S, y+8*S, 178*S, y+16*S], fill=GOLD)
        d.text((190 * S, y), lab, font=fl, fill=MUTED)
        w = d.textlength(val, font=fv)
        d.text((SIZE - 190 * S - w, y - 4 * S), val, font=fv, fill=CREAM)
        d.line([(190 * S, y + 58 * S), (SIZE - 190 * S, y + 58 * S)], fill=(58, 42, 92), width=1 * S)
        y += 76 * S

    if rashi_names:
        # "included in this post" block replacing the generic CTA
        y_block = y + 20 * S
        lbl = "ଏହି ପୋଷ୍ଟରେ ଅଛି"
        fl2 = F(bold, 26)
        w = d.textlength(lbl, font=fl2)
        d.text(((SIZE - w) / 2, y_block), lbl, font=fl2, fill=GOLD)
        names_line = "  ·  ".join(rashi_names)
        fn = F(reg, 27)
        lines = wrap(d, names_line, fn, 860 * S)
        yy = y_block + 46 * S
        for ln in lines:
            w = d.textlength(ln, font=fn)
            d.text(((SIZE - w) / 2, yy), ln, font=fn, fill=CREAM)
            yy += 40 * S
    else:
        cta = "ଆପଣଙ୍କ ରାଶିଫଳ ପାଇଁ ଆଗକୁ ଦେଖନ୍ତୁ →"
        fc = F(bold, 26)
        w = d.textlength(cta, font=fc)
        bx = (SIZE - w) / 2
        d.rounded_rectangle([bx - 36 * S, 928 * S, bx + w + 36 * S, 994 * S], radius=33 * S,
                            fill=BG2, outline=GOLD, width=2 * S)
        d.line([(bx - 30*S, 930*S), (bx + w + 30*S, 930*S)], fill=(160, 120, 60), width=1*S)
        d.text((bx, 942 * S), cta, font=fc, fill=GOLD_LIGHT)
    draw_footer(d)
    img = img.resize((1080, 1080), Image.LANCZOS)
    img = _grain_texture(img)
    img.save(out, quality=95)

def render_logo(out):
    sz = 1080
    img = Image.new("RGB", (sz, sz), BG)
    d = ImageDraw.Draw(img)
    for y in range(sz):
        t = y / sz
        d.line([(0, y), (sz, y)], fill=(int(26+t*10), int(15+t*8), int(46+t*22)))
    cx = cy = sz // 2
    for r, w, c in [(430, 10, GOLD), (395, 4, PURPLE)]:
        d.ellipse([cx-r, cy-r, cx+r, cy+r], outline=c, width=w)
    import math as _m
    for i in range(12):
        a = _m.radians(i * 30)
        px, py = cx + 460 * _m.cos(a), cy + 460 * _m.sin(a)
        d.ellipse([px-14, py-14, px+14, py+14], fill=GOLD)
    f = ImageFont.truetype(os.path.join(FDIR, "NotoSansOriya-Black.ttf"), 400)
    t = "ଜ୍ୟୋ"
    bb = d.textbbox((0, 0), t, font=f)
    d.text((cx - (bb[2]-bb[0])/2 - bb[0], cy - (bb[3]-bb[1])/2 - bb[1]), t, font=f, fill=GOLD_LIGHT)
    img.save(out, quality=95)

if __name__ == "__main__":
    dstr = sys.argv[1] if len(sys.argv) > 1 else "2026-07-12"
    date = datetime.date.fromisoformat(dstr)
    p = pj.compute_panchanga(date)
    ctxs = {c["rashi"]: c for c in pj.rashi_context(p)}
    here = os.path.dirname(__file__)
    content = json.load(open(os.path.join(here, "..", "output", f"content_{dstr}.json")))
    outdir = os.path.join(here, "..", "output", dstr)
    os.makedirs(outdir, exist_ok=True)
    render_logo(os.path.join(outdir, "00_logo.png"))

    rashi_order = [item["rashi"] for item in content["rashifala"]]
    mid = (len(rashi_order) + 1) // 2  # matches publish_in_batches split exactly
    part1_names = [ctxs[r]["rashi_odia"] for r in rashi_order[:mid]]
    part2_names = [ctxs[r]["rashi_odia"] for r in rashi_order[mid:]]

    render_cover(p, os.path.join(outdir, "cover_part1.png"), date,
                part_label="ଭାଗ ୧", rashi_names=part1_names)
    render_cover(p, os.path.join(outdir, "cover_part2.png"), date,
                part_label="ଭାଗ ୨", rashi_names=part2_names)
    print("covers: part1 ->", part1_names, "| part2 ->", part2_names)

    for i, item in enumerate(content["rashifala"], start=2):
        render_rashi_card(p, ctxs[item["rashi"]], item, os.path.join(outdir, f"{i:02d}_{item['rashi'].lower()}.png"), date)
    print("rendered:", sorted(os.listdir(outdir)))
