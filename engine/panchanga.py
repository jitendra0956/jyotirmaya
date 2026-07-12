"""
Odia Rashifala — Calculation Engine (truth layer)
All astronomical/astrological FACTS come from here. The LLM never calculates.
Lahiri ayanamsa, Bhubaneswar as reference location, IST output.
"""
import swisseph as swe
import datetime
import json

LAT, LON, ALT = 20.2961, 85.8245, 30
IST = 5.5

swe.set_sid_mode(swe.SIDM_LAHIRI)
FLAGS = swe.FLG_SWIEPH | swe.FLG_SIDEREAL

TITHI_NAMES = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima",
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Amavasya",
]
TITHI_ODIA = [
    "ପ୍ରତିପଦା", "ଦ୍ୱିତୀୟା", "ତୃତୀୟା", "ଚତୁର୍ଥୀ", "ପଞ୍ଚମୀ",
    "ଷଷ୍ଠୀ", "ସପ୍ତମୀ", "ଅଷ୍ଟମୀ", "ନବମୀ", "ଦଶମୀ",
    "ଏକାଦଶୀ", "ଦ୍ୱାଦଶୀ", "ତ୍ରୟୋଦଶୀ", "ଚତୁର୍ଦ୍ଦଶୀ", "ପୂର୍ଣ୍ଣିମା",
    "ପ୍ରତିପଦା", "ଦ୍ୱିତୀୟା", "ତୃତୀୟା", "ଚତୁର୍ଥୀ", "ପଞ୍ଚମୀ",
    "ଷଷ୍ଠୀ", "ସପ୍ତମୀ", "ଅଷ୍ଟମୀ", "ନବମୀ", "ଦଶମୀ",
    "ଏକାଦଶୀ", "ଦ୍ୱାଦଶୀ", "ତ୍ରୟୋଦଶୀ", "ଚତୁର୍ଦ୍ଦଶୀ", "ଅମାବାସ୍ୟା",
]
NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]
NAKSHATRA_ODIA = [
    "ଅଶ୍ୱିନୀ", "ଭରଣୀ", "କୃତ୍ତିକା", "ରୋହିଣୀ", "ମୃଗଶିରା", "ଆର୍ଦ୍ରା",
    "ପୁନର୍ବସୁ", "ପୁଷ୍ୟା", "ଆଶ୍ଳେଷା", "ମଘା", "ପୂର୍ବ ଫାଲ୍ଗୁନୀ",
    "ଉତ୍ତର ଫାଲ୍ଗୁନୀ", "ହସ୍ତା", "ଚିତ୍ରା", "ସ୍ୱାତୀ", "ବିଶାଖା", "ଅନୁରାଧା",
    "ଜ୍ୟେଷ୍ଠା", "ମୂଳା", "ପୂର୍ବାଷାଢ଼ା", "ଉତ୍ତରାଷାଢ଼ା", "ଶ୍ରବଣା",
    "ଧନିଷ୍ଠା", "ଶତଭିଷା", "ପୂର୍ବ ଭାଦ୍ରପଦ", "ଉତ୍ତର ଭାଦ୍ରପଦ", "ରେବତୀ",
]
RASHI_NAMES = [
    "Mesha", "Vrishabha", "Mithuna", "Karkata", "Simha", "Kanya",
    "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena",
]
RASHI_ODIA = [
    "ମେଷ", "ବୃଷ", "ମିଥୁନ", "କର୍କଟ", "ସିଂହ", "କନ୍ୟା",
    "ତୁଳା", "ବିଛା", "ଧନୁ", "ମକର", "କୁମ୍ଭ", "ମୀନ",
]
RASHI_SYMBOLS = ["\u2648", "\u2649", "\u264A", "\u264B", "\u264C", "\u264D",
                 "\u264E", "\u264F", "\u2650", "\u2651", "\u2652", "\u2653"]
RASHI_SYLLABLES_ODIA = [
    "ଚୁ ଚେ ଚୋ ଲା ଲି ଲୁ ଲେ ଲୋ ଅ",
    "ଇ ଉ ଏ ଓ ବା ବି ବୁ ବେ ବୋ",
    "କା କି କୁ ଘ ଙ ଛ କେ କୋ ହ",
    "ହି ହୁ ହେ ହୋ ଡା ଡି ଡୁ ଡେ ଡୋ",
    "ମା ମି ମୁ ମେ ମୋ ଟା ଟି ଟୁ ଟେ",
    "ଟୋ ପା ପି ପୁ ଷ ଣ ଠ ପେ ପୋ",
    "ରା ରି ରୁ ରେ ରୋ ତା ତି ତୁ ତେ",
    "ତୋ ନା ନି ନୁ ନେ ନୋ ୟା ୟି ୟୁ",
    "ୟେ ୟୋ ଭା ଭି ଭୁ ଧା ଫା ଢା ଭେ",
    "ଭୋ ଜା ଜି ଖି ଖୁ ଖେ ଖୋ ଗା ଗି",
    "ଗୁ ଗେ ଗୋ ସା ସି ସୁ ସେ ସୋ ଦା",
    "ଦି ଦୁ ଥ ଝ ଞ ଦେ ଦୋ ଚା ଚି",
]
WEEKDAY_ODIA = ["ସୋମବାର", "ମଙ୍ଗଳବାର", "ବୁଧବାର", "ଗୁରୁବାର",
                "ଶୁକ୍ରବାର", "ଶନିବାର", "ରବିବାର"]  # Mon..Sun (Python weekday order)
# Rahu kaal daily segment (of 8 day-parts), 0-indexed: Mon..Sun
RAHU_SEGMENT = {0: 1, 1: 6, 2: 4, 3: 5, 4: 3, 5: 2, 6: 7}
ODIA_DIGITS = str.maketrans("0123456789", "୦୧୨୩୪୫୬୭୮୯")

PLANETS = {
    "sun": swe.SUN, "moon": swe.MOON, "mars": swe.MARS,
    "mercury": swe.MERCURY, "jupiter": swe.JUPITER,
    "venus": swe.VENUS, "saturn": swe.SATURN,
}


def _to_ist_hm(jd_ut):
    y, m, d, h = swe.revjul(jd_ut)
    h = (h + IST) % 24
    return f"{int(h):02d}:{int((h - int(h)) * 60):02d}"


def sidereal_lon(jd_ut, planet):
    return swe.calc_ut(jd_ut, planet, FLAGS)[0][0]


def compute_panchanga(date: datetime.date) -> dict:
    """Full panchanga for the given civil date at Bhubaneswar, at sunrise."""
    # find sunrise: search from local midnight (IST) expressed in UT
    jd_search = swe.julday(date.year, date.month, date.day, 0.0) - IST / 24.0
    jd_rise = swe.rise_trans(jd_search, swe.SUN, swe.CALC_RISE,
                             (LON, LAT, ALT))[1][0]
    jd_set = swe.rise_trans(jd_rise, swe.SUN, swe.CALC_SET,
                            (LON, LAT, ALT))[1][0]

    sun = sidereal_lon(jd_rise, swe.SUN)
    moon = sidereal_lon(jd_rise, swe.MOON)

    elong = (moon - sun) % 360
    tithi_idx = int(elong / 12)
    paksha = "Shukla" if tithi_idx < 15 else "Krishna"
    paksha_odia = "ଶୁକ୍ଳ" if tithi_idx < 15 else "କୃଷ୍ଣ"

    nak_idx = int(moon / (360 / 27))

    weekday = date.weekday()  # Mon=0
    seg = RAHU_SEGMENT[weekday]
    day_len = jd_set - jd_rise
    rahu_start = jd_rise + day_len * seg / 8
    rahu_end = jd_rise + day_len * (seg + 1) / 8

    planet_positions = {}
    for name, pid in PLANETS.items():
        lon_p = sidereal_lon(jd_rise, pid)
        planet_positions[name] = {
            "longitude": round(lon_p, 2),
            "rashi": RASHI_NAMES[int(lon_p / 30)],
            "rashi_odia": RASHI_ODIA[int(lon_p / 30)],
        }

    return {
        "date": date.isoformat(),
        "weekday_odia": WEEKDAY_ODIA[weekday],
        "location": "Bhubaneswar",
        "sunrise": _to_ist_hm(jd_rise),
        "sunset": _to_ist_hm(jd_set),
        "tithi": {
            "name": TITHI_NAMES[tithi_idx],
            "odia": f"{paksha_odia} {TITHI_ODIA[tithi_idx]}",
            "paksha": paksha,
            "index": tithi_idx,
        },
        "nakshatra": {
            "name": NAKSHATRA_NAMES[nak_idx],
            "odia": NAKSHATRA_ODIA[nak_idx],
            "index": nak_idx,
        },
        "moon_rashi": {
            "name": RASHI_NAMES[int(moon / 30)],
            "odia": RASHI_ODIA[int(moon / 30)],
        },
        "rahu_kaal": {"start": _to_ist_hm(rahu_start),
                      "end": _to_ist_hm(rahu_end)},
        "planets": planet_positions,
    }


def rashi_context(panchanga: dict) -> list:
    """Per-rashi astrological context for the LLM: moon transit house from
    each rashi (chandra gochara), the classical driver of daily rashifala."""
    moon_rashi_idx = RASHI_NAMES.index(panchanga["moon_rashi"]["name"])
    out = []
    for i in range(12):
        # house the transiting moon occupies counted from this rashi (1-12)
        moon_house = ((moon_rashi_idx - i) % 12) + 1
        # classical chandra gochara favourability
        good = moon_house in (1, 3, 6, 7, 10, 11)
        out.append({
            "rashi": RASHI_NAMES[i],
            "rashi_odia": RASHI_ODIA[i],
            "symbol": RASHI_SYMBOLS[i],
            "syllables_odia": RASHI_SYLLABLES_ODIA[i],
            "moon_transit_house": moon_house,
            "transit_tone": "favourable" if good else "mixed",
        })
    return out


def odia_digits(s: str) -> str:
    return s.translate(ODIA_DIGITS)


if __name__ == "__main__":
    today = datetime.date(2026, 7, 12)
    p = compute_panchanga(today)
    print(json.dumps(p, ensure_ascii=False, indent=2))
    print("\n--- rashi contexts ---")
    for r in rashi_context(p):
        print(f'{r["rashi_odia"]:>6}  moon in house {r["moon_transit_house"]:>2}  {r["transit_tone"]}')
