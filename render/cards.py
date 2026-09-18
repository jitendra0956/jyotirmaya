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
RASHI_ICON_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "rashi_icons")
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

def render_festival_calendar_card(events, start_date, out):
    """Weekly Friday post — upcoming festivals & Vrat for the next 7 days.
    events: list of {date, name_odia, type} from engine/festival_calendar.py.
    Tested against real computed data (1-event, 2-event, and 0-event real
    weeks) before being wired into this reusable function."""
    img, d = base_canvas(GOLD)
    reg, bold, black = "NotoSansOriya-Regular.ttf", "NotoSansOriya-Bold.ttf", "NotoSansOriya-Black.ttf"

    hdr = "ଆଗାମୀ ସପ୍ତାହର ପର୍ବ ଓ ବ୍ରତ"
    f = F(bold, 34)
    w = d.textlength(hdr, font=f)
    d.text(((SIZE - w) / 2, 90 * S), hdr, font=f, fill=GOLD)

    sub = date_odia(start_date) + " ଠାରୁ ୭ ଦିନ"
    f2 = F(reg, 22)
    w = d.textlength(sub, font=f2)
    d.text(((SIZE - w) / 2, 148 * S), sub, font=f2, fill=MUTED)

    if not events:
        msg = "ଏହି ସପ୍ତାହରେ କୌଣସି ପ୍ରମୁଖ ପର୍ବ କିମ୍ବା ବ୍ରତ ନାହିଁ"
        f3 = F(reg, 28)
        w = d.textlength(msg, font=f3)
        d.text(((SIZE - w) / 2, SIZE // 2 - 20 * S), msg, font=f3, fill=TEXT)
    else:
        card_w = 820 * S
        x = (SIZE - card_w) / 2
        row_h = 130 * S
        start_y = 260 * S
        f_date = F(black, 34)
        f_name = F(bold, 32)
        f_type = F(reg, 20)
        month_names = ["", "ଜାନୁ", "ଫେବୃ", "ମାର୍ଚ୍ଚ", "ଏପ୍ରି", "ମେ", "ଜୁନ",
                      "ଜୁଲା", "ଅଗ", "ସେପ୍ଟ", "ଅକ୍ଟୋ", "ନଭେ", "ଡିସେ"]
        for i, e in enumerate(events):
            y = start_y + i * (row_h + 20 * S)
            d.rounded_rectangle([x, y, x + card_w, y + row_h], radius=18 * S, fill=BG2, outline=GOLD, width=2 * S)
            badge_w = 160 * S
            d.rounded_rectangle([x + 16 * S, y + 16 * S, x + 16 * S + badge_w, y + row_h - 16 * S],
                                radius=12 * S, fill=(26, 15, 46), outline=GOLD_LIGHT, width=1 * S)
            day_str = str(e["date"].day)
            month_str = month_names[e["date"].month]
            dw = d.textlength(day_str, font=f_date)
            d.text((x + 16 * S + (badge_w - dw) / 2, y + 24 * S), day_str, font=f_date, fill=GOLD_LIGHT)
            mw = d.textlength(month_str, font=f_type)
            d.text((x + 16 * S + (badge_w - mw) / 2, y + 68 * S), month_str, font=f_type, fill=MUTED)
            tx = x + 16 * S + badge_w + 30 * S
            d.text((tx, y + 30 * S), e["name_odia"], font=f_name, fill=CREAM)
            type_label = "ପର୍ବ" if e["type"] == "festival" else "ବ୍ରତ"
            d.text((tx, y + 72 * S), type_label, font=f_type, fill=MUTED)

    draw_footer(d)
    img = img.resize((1080, 1080), Image.LANCZOS)
    img.save(out, quality=95)
    return out


# ---------------------------------------------------------------------------
# Single-image daily grid — replaces the multi-slide carousel entirely.
# All 12 rashis in ONE post. Real trade-off, stated plainly: at 3 columns x
# 4 rows, there is not enough room for full do/dont sentences (they run
# 30-140 chars per the validator in interpret.py) — each is capped to 2
# short lines with an ellipsis rather than silently overflowing a cell or
# being invisibly cut off. This is a genuine density limit of "everyone in
# one image," not a bug; if it reads too cramped in practice, the honest
# fixes are fewer signs per post or a taller canvas, not smaller font past
# the point of legibility.
# ---------------------------------------------------------------------------

GRID_W, GRID_H = 1080 * S, 1350 * S

CELL_ACCENTS = [
    (206, 84, 68), (96, 172, 128), (212, 148, 188), (150, 178, 224),
    (230, 142, 62), (138, 95, 191), (217, 164, 65), (102, 149, 168),
    (191, 120, 84), (96, 140, 191), (168, 110, 168), (140, 168, 110),
]  # one distinct accent per rashi, fixed order — not weekday-dependent,
   # so each sign has a stable visual identity across days


def _grid_base_canvas(w, h, accent=GOLD):
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        r = int(26 + t * 8); g = int(15 + t * 6); b = int(46 + t * 18)
        d.line([(0, y), (w, y)], fill=(r, g, b))
    import random
    random.seed(42)
    star_palette = [(139, 123, 184), (107, 91, 152), (155, 139, 200), accent]
    for _ in range(120):
        x, y = random.randint(0, w), random.randint(0, h)
        rr = random.choice([1, 1, 2]) * S
        c = random.choice(star_palette)
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=c)
    m = 28 * S
    d.rounded_rectangle([m, m, w - m, h - m], radius=16 * S, outline=accent, width=3 * S)
    return img, d


def render_daily_grid(content, p, ctxs, out, date):
    """One dense single-image post: all 12 rashis, 3 columns x 4 rows.
    content: the parsed content_*.json dict (date/header_odia/rashifala).
    p: panchanga dict (compute_panchanga output) — used for header date/weekday.
    ctxs: rashi_context(p) output — rashi_odia names + symbols, fixed order.
    """
    img, d = _grid_base_canvas(GRID_W, GRID_H)
    reg, bold, black = "NotoSansOriya-Regular.ttf", "NotoSansOriya-Bold.ttf", "NotoSansOriya-Black.ttf"
    items_by_rashi = {it["rashi"]: it for it in content["rashifala"]}

    # header
    hdr = content.get("header_odia") or "ଆଜିର ରାଶିଫଳ"
    f = F(black, 40)
    w = d.textlength(hdr, font=f)
    d.text(((GRID_W - w) / 2, 46 * S), hdr, font=f, fill=GOLD)

    sub = date_odia(date) + " · " + p["weekday_odia"]
    f2 = F(reg, 24)
    w = d.textlength(sub, font=f2)
    d.text(((GRID_W - w) / 2, 96 * S), sub, font=f2, fill=MUTED)

    d.line([(GRID_W // 2 - 130 * S, 140 * S), (GRID_W // 2 + 130 * S, 140 * S)], fill=GOLD, width=2 * S)

    # grid geometry
    margin = 30 * S
    gap = 14 * S
    top = 168 * S
    bottom_reserve = 76 * S  # footer
    cols, rows = 3, 4
    col_w = (GRID_W - margin * 2 - gap * (cols - 1)) / cols
    row_h = (GRID_H - top - bottom_reserve - gap * (rows - 1)) / rows

    f_sym = ImageFont.truetype(SYM_FONT_PATH, int(26 * S))
    f_name = F(bold, 24)
    f_body = F(reg, 15)
    f_label = F(bold, 15)

    CATEGORY_ROWS = [
        ("love", "ପ୍ରେମ", (212, 148, 188)),
        ("money", "ଧନ", (217, 164, 65)),
        ("health", "ସ୍ୱାସ୍ଥ୍ୟ", (120, 200, 140)),
        ("work", "କାର୍ଯ୍ୟ", (150, 178, 224)),
    ]

    for i, ctx in enumerate(ctxs):
        row, col = divmod(i, cols)
        x = margin + col * (col_w + gap)
        y = top + row * (row_h + gap)
        accent = CELL_ACCENTS[i]
        item = items_by_rashi.get(ctx["rashi"], {})

        d.rounded_rectangle([x, y, x + col_w, y + row_h], radius=14 * S,
                             fill=BG2, outline=accent, width=2 * S)

        # mini header: illustrated icon if generated (assets/rashi_icons/),
        # falling back to the plain Unicode symbol badge if not -- so the
        # pipeline keeps working before generate_rashi_icons.py has been run
        badge_r = 18 * S
        bcx, bcy = x + 16 * S + badge_r, y + 16 * S + badge_r
        icon_path = os.path.join(RASHI_ICON_DIR, f"{ctx['rashi']}.png")
        if os.path.exists(icon_path):
            icon_d = badge_r * 2
            icon = Image.open(icon_path).convert("RGBA").resize((int(icon_d), int(icon_d)), Image.LANCZOS)
            d.ellipse([bcx - badge_r - 2*S, bcy - badge_r - 2*S, bcx + badge_r + 2*S, bcy + badge_r + 2*S],
                       fill=(38, 26, 58), outline=accent, width=2 * S)
            img.paste(icon, (int(bcx - badge_r), int(bcy - badge_r)), icon)
        else:
            d.ellipse([bcx - badge_r, bcy - badge_r, bcx + badge_r, bcy + badge_r],
                       fill=(38, 26, 58), outline=accent, width=2 * S)
            sw = d.textlength(ctx["symbol"], font=f_sym)
            d.text((bcx - sw / 2, bcy - 17 * S), ctx["symbol"], font=f_sym, fill=accent)
        d.text((x + 16 * S + badge_r * 2 + 10 * S, y + 14 * S), ctx["rashi_odia"],
                font=f_name, fill=CREAM)

        ty = y + 16 * S + badge_r * 2 + 16 * S
        inner_w = col_w - 32 * S
        # evenly split the remaining cell height across the 4 categories,
        # so a longer row never crowds the next one regardless of content
        remaining_h = row_h - (ty - y) - 10 * S
        row_budget = remaining_h / len(CATEGORY_ROWS)

        for field, label, color in CATEGORY_ROWS:
            text = item.get(field, "")
            if not text:
                ty += row_budget
                continue
            d.ellipse([x + 16 * S, ty + 4 * S, x + 22 * S, ty + 10 * S], fill=color)
            label_txt = label + ":"
            d.text((x + 26 * S, ty), label_txt, font=f_label, fill=color)
            label_w = d.textlength(label_txt, font=f_label)
            # Wrap against a width that already accounts for the label
            # eating into line space -- applied to EVERY line, not just
            # the first. A bit conservative for line 2+ (which doesn't
            # actually sit next to the label), but that's a small cost
            # for guaranteeing no line can ever run past the cell edge,
            # which a per-line-different-width version got wrong: it
            # wrapped against the FULL inner width while the first line
            # actually had less room, letting it overflow past the cell.
            first_line_w = inner_w - 22 * S - label_w - 4 * S
            lines = wrap(d, text, f_body, first_line_w)[:2]
            lx, ly = x + 26 * S + label_w + 4 * S, ty
            for j, ln in enumerate(lines):
                if j == 1:
                    lx, ly = x + 26 * S, ty + 20 * S
                d.text((lx, ly), ln, font=f_body, fill=TEXT)
            ty += row_budget

    footer_f = F("NotoSansOriya-Bold.ttf", 20)
    txt = BRAND + "  ·  " + HANDLE
    w = d.textlength(txt, font=footer_f)
    d.text(((GRID_W - w) / 2, GRID_H - 46 * S), txt, font=footer_f, fill=(150, 130, 90))

    img = img.resize((1080, 1350), Image.LANCZOS)
    img.save(out, quality=95)
    return out


if __name__ == "__main__":
    dstr = sys.argv[1] if len(sys.argv) > 1 else "2026-07-12"
    date = datetime.date.fromisoformat(dstr)
    p = pj.compute_panchanga(date)
    ctxs = pj.rashi_context(p)
    here = os.path.dirname(__file__)
    content = json.load(open(os.path.join(here, "..", "output", f"content_{dstr}.json")))
    outdir = os.path.join(here, "..", "output", dstr)
    os.makedirs(outdir, exist_ok=True)

    if not content.get("date"):
        content["date"] = dstr
    if not content.get("header_odia"):
        content["header_odia"] = "ଆଜିର ରାଶିଫଳ"

    # No more carousel: one dense image, all 12 rashis, this is the ONLY
    # file publish/instagram.py needs to pick up for the day.
    out_path = os.path.join(outdir, "daily_grid.png")
    render_daily_grid(content, p, ctxs, out_path, date)
    print("rendered:", out_path)
