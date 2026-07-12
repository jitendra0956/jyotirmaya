"""Ornate purple-gold card renderer. 1080x1080 output, 2x supersampled."""
import json, math, os, sys, datetime
from PIL import Image, ImageDraw, ImageFont

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

def base_canvas():
    img = Image.new("RGB", (SIZE, SIZE), BG)
    d = ImageDraw.Draw(img)
    # subtle vertical gradient
    for y in range(SIZE):
        t = y / SIZE
        r = int(26 + t * 8); g = int(15 + t * 6); b = int(46 + t * 18)
        d.line([(0, y), (SIZE, y)], fill=(r, g, b))
    # star field
    import random
    random.seed(42)
    for _ in range(90):
        x, y = random.randint(0, SIZE), random.randint(0, SIZE)
        rr = random.choice([1, 1, 2]) * S
        c = random.choice([(139, 123, 184), (107, 91, 152), (155, 139, 200)])
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=c)
    # double ornamental border
    m = 34 * S
    d.rounded_rectangle([m, m, SIZE - m, SIZE - m], radius=18 * S,
                        outline=GOLD, width=4 * S)
    m2 = 52 * S
    d.rounded_rectangle([m2, m2, SIZE - m2, SIZE - m2], radius=12 * S,
                        outline=PURPLE, width=2 * S)
    # corner arcs (temple-arch motif)
    for cx, cy, a in [(m, m, 0), (SIZE - m, m, 90), (SIZE - m, SIZE - m, 180), (m, SIZE - m, 270)]:
        for rad, w in [(56 * S, 3 * S), (38 * S, 2 * S)]:
            box = [cx - rad, cy - rad, cx + rad, cy + rad]
            d.arc(box, a, a + 90, fill=GOLD, width=w)
    # diamond accents mid-edges
    for x, y in [(SIZE // 2, m), (SIZE // 2, SIZE - m), (m, SIZE // 2), (SIZE - m, SIZE // 2)]:
        s = 14 * S
        d.polygon([(x, y - s), (x + s, y), (x, y + s), (x - s, y)], fill=GOLD)
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

def render_cover(p, out, date):
    img, d = base_canvas()
    reg, bold, black = "NotoSansOriya-Regular.ttf", "NotoSansOriya-Bold.ttf", "NotoSansOriya-Black.ttf"
    hdr = "ଦୈନିକ ପଞ୍ଜିକା"
    f = F(bold, 34)
    w = d.textlength(hdr, font=f)
    d.text(((SIZE - w) / 2, 96 * S), hdr, font=f, fill=GOLD)
    day = p["weekday_odia"]
    f2 = F(black, 72)
    w = d.textlength(day, font=f2)
    d.text(((SIZE - w) / 2, 168 * S), day, font=f2, fill=CREAM)
    dt = date_odia(date)
    f3 = F(reg, 30)
    w = d.textlength(dt, font=f3)
    d.text(((SIZE - w) / 2, 280 * S), dt, font=f3, fill=MUTED)
    d.line([(SIZE // 2 - 160 * S, 352 * S), (SIZE // 2 + 160 * S, 352 * S)], fill=GOLD, width=2 * S)
    rows = [
        ("ତିଥି", p["tithi"]["odia"]),
        ("ନକ୍ଷତ୍ର", p["nakshatra"]["odia"]),
        ("ଚନ୍ଦ୍ର ରାଶି", p["moon_rashi"]["odia"]),
        ("ସୂର୍ଯ୍ୟୋଦୟ", pj.odia_digits(p["sunrise"])),
        ("ସୂର୍ଯ୍ୟାସ୍ତ", pj.odia_digits(p["sunset"])),
        ("ରାହୁ କାଳ", pj.odia_digits(p["rahu_kaal"]["start"] + " – " + p["rahu_kaal"]["end"])),
    ]
    fl = F(reg, 26); fv = F(bold, 30)
    y = 400 * S
    for lab, val in rows:
        d.text((190 * S, y), lab, font=fl, fill=MUTED)
        w = d.textlength(val, font=fv)
        d.text((SIZE - 190 * S - w, y - 4 * S), val, font=fv, fill=CREAM)
        d.line([(190 * S, y + 58 * S), (SIZE - 190 * S, y + 58 * S)], fill=(58, 42, 92), width=1 * S)
        y += 78 * S
    cta = "ଆପଣଙ୍କ ରାଶିଫଳ ପାଇଁ ଆଗକୁ ଦେଖନ୍ତୁ →"
    fc = F(bold, 26)
    w = d.textlength(cta, font=fc)
    bx = (SIZE - w) / 2
    d.rounded_rectangle([bx - 36 * S, 928 * S, bx + w + 36 * S, 994 * S], radius=33 * S, fill=BG2, outline=GOLD, width=2 * S)
    d.text((bx, 942 * S), cta, font=fc, fill=GOLD_LIGHT)
    draw_footer(d)
    img = img.resize((1080, 1080), Image.LANCZOS)
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
    render_cover(p, os.path.join(outdir, "01_cover.png"), date)
    for i, item in enumerate(content["rashifala"], start=2):
        render_rashi_card(p, ctxs[item["rashi"]], item, os.path.join(outdir, f"{i:02d}_{item['rashi'].lower()}.png"), date)
    print("rendered:", sorted(os.listdir(outdir)))
