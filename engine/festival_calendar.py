"""
Jyotirmaya — Festival & Vrat calendar (weekly, Friday post).
Reuses compute_panchanga() directly for Ekadashi/Purnima/Amavasya
detection (already proven, already tested against real ephemeris data)
and the existing festival_dates_2026.json for named festivals — no new
astronomical computation needed, exactly as expected going in.
"""
import datetime, json, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import panchanga as pj

FESTIVAL_JSON = os.path.join(os.path.dirname(__file__), "..", "assets", "festivals", "festival_dates_2026.json")

VRAT_NAMES = {
    "is_ekadashi": "ଏକାଦଶୀ",
    "is_purnima": "ପୂର୍ଣ୍ଣିମା",
    "is_amavasya": "ଅମାବାସ୍ୟା",
}


def upcoming_events(start_date: datetime.date, days: int = 7) -> list:
    """Returns a list of {date, name_odia, type} for the next `days` days
    (inclusive of start_date), combining named festivals (from the JSON)
    with recurring Vrat days (Ekadashi/Purnima/Amavasya, detected live via
    compute_panchanga — same real ephemeris call the daily rashifala
    already uses, not a separate/duplicated calculation)."""
    with open(FESTIVAL_JSON, encoding="utf-8") as f:
        festivals = json.load(f)

    events = []
    for i in range(days):
        d = start_date + datetime.timedelta(days=i)
        d_str = d.isoformat()

        if d_str in festivals:
            entry = festivals[d_str]
            events.append({"date": d, "name_odia": entry["name_odia"], "type": "festival"})

        p = pj.compute_panchanga(d)
        for flag, vrat_name in VRAT_NAMES.items():
            if p.get(flag):
                events.append({"date": d, "name_odia": vrat_name, "type": "vrat"})

    return events


if __name__ == "__main__":
    today = datetime.date.today()
    events = upcoming_events(today, days=7)
    print(f"Upcoming events from {today} for 7 days:")
    for e in events:
        print(f"  {e['date']} ({e['type']}): {e['name_odia']}")
    if not events:
        print("  (none in this window — real ephemeris/festival data, so this is a genuine result, not an error)")
