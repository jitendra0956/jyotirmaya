"""
Jyotirmaya — LLM interpretation layer.
Code computes all facts (panchanga.py); this module only turns facts into
traditional Odia prose via Gemini, then validates the output.
Requires: GEMINI_API_KEY env var. Falls back with clear error for approval gate.
"""
import json, os, re, sys, time, urllib.request, urllib.error, datetime

sys.path.insert(0, os.path.dirname(__file__))
import panchanga as pj

MODEL = "gemini-2.0-flash"
API = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

LUCKY = {  # deterministic per rashi lord — code decides, not the LLM
    "Mesha":   ("ଲାଲ", "୯"),    "Vrishabha": ("ଧଳା", "୬"),
    "Mithuna": ("ସବୁଜ", "୫"),   "Karkata":   ("ରୁପେଲି", "୨"),
    "Simha":   ("କମଳା", "୧"),   "Kanya":     ("ସବୁଜ", "୫"),
    "Tula":    ("ଧଳା", "୬"),    "Vrischika": ("ଲାଲ", "୯"),
    "Dhanu":   ("ହଳଦିଆ", "୩"),  "Makara":    ("ନୀଳ", "୮"),
    "Kumbha":  ("ନୀଳ", "୮"),    "Meena":     ("ହଳଦିଆ", "୩"),
}

FORBIDDEN_PATTERNS = [
    "ମୃତ୍ୟୁ", "ମରଣ", "ଡିଭୋର୍ସ", "ଛାଡପତ୍ର",          # death, divorce
    "ନିଶ୍ଚିତ ଭାବେ ମିଳିବ", "ଗ୍ୟାରେଣ୍ଟି",              # certainty/guarantee
    "ଭୟଙ୍କର", "ସର୍ବନାଶ", "ଅଘଟଣ ଘଟିବ",               # fear-mongering
]

SYSTEM_RULES = """ତୁମେ ଏକ ଅଭିଜ୍ଞ ଓଡ଼ିଆ ପଞ୍ଜିକା ଲେଖକ। ପାରମ୍ପରିକ ଖବରକାଗଜ ରାଶିଫଳ ଶୈଳୀରେ ଲେଖ।

କଠୋର ନିୟମ:
1. କେବଳ ମାର୍ଗଦର୍ଶନ ଭାଷା — "ମିଳିପାରେ", "ସମ୍ଭାବନା", "ସୂଚନା", "ହିତକର"। କଦାପି ନିଶ୍ଚିତ ଭବିଷ୍ୟବାଣୀ ନୁହେଁ।
2. ଭୟ ସୃଷ୍ଟିକାରୀ କଥା ନିଷେଧ — ମୃତ୍ୟୁ, ଗୁରୁତର ରୋଗ, ଦୁର୍ଘଟଣା, ବିବାହବିଚ୍ଛେଦ ଉଲ୍ଲେଖ କର ନାହିଁ।
3. ସ୍ୱାସ୍ଥ୍ୟ ବିଷୟରେ କେବଳ "ସ୍ୱାସ୍ଥ୍ୟ ପ୍ରତି ଧ୍ୟାନ ଦିଅନ୍ତୁ" ପରି ସାଧାରଣ କଥା।
4. ପ୍ରତି ରାଶି ପାଇଁ ଠିକ୍ 3ଟି ଛୋଟ ବାକ୍ୟ — କର୍ମ/ଅର୍ଥ, ପରିବାର/ସମ୍ପର୍କ, ଏବଂ ଗୋଟିଏ ପରାମର୍ଶ।
5. ଶୁଦ୍ଧ, ସ୍ୱାଭାବିକ ଓଡ଼ିଆ — ହିନ୍ଦୀ ମିଶ୍ରଣ ନାହିଁ।
6. transit_tone "favourable" ହେଲେ ସକାରାତ୍ମକ ସ୍ୱର, "mixed" ହେଲେ ସନ୍ତୁଳିତ ସାବଧାନ ସ୍ୱର।
7. ଉତ୍ତର କେବଳ JSON: {"rashifala":[{"rashi":"Mesha","text":"..."}, ... ସବୁ 12ଟି]}"""


def few_shot_examples():
    here = os.path.join(os.path.dirname(__file__), "..", "output")
    ex = json.load(open(os.path.join(here, "content_2026-07-12.json")))
    return json.dumps({"rashifala": [
        {"rashi": r["rashi"], "text": r["text"]} for r in ex["rashifala"][:4]
    ]}, ensure_ascii=False)


def build_prompt(p, contexts):
    facts = {
        "date": p["date"], "weekday": p["weekday_odia"],
        "tithi": p["tithi"]["odia"], "nakshatra": p["nakshatra"]["odia"],
        "moon_rashi": p["moon_rashi"]["odia"],
        "rashis": [{"rashi": c["rashi"], "moon_transit_house": c["moon_transit_house"],
                    "transit_tone": c["transit_tone"]} for c in contexts],
    }
    return (SYSTEM_RULES
            + "\n\nଉଦାହରଣ ଶୈଳୀ (ଗତ ଦିନର):\n" + few_shot_examples()
            + "\n\nଆଜିର ଜ୍ୟୋତିଷ ତଥ୍ୟ:\n" + json.dumps(facts, ensure_ascii=False)
            + "\n\nଏହି ତଥ୍ୟ ଅନୁସାରେ ଆଜିର 12 ରାଶିର ରାଶିଫଳ JSON ରେ ଲେଖ।")


def call_gemini(prompt, retries=4):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set")
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.8, "responseMimeType": "application/json"},
    }).encode()
    req = urllib.request.Request(f"{API}?key={key}", data=body,
                                 headers={"Content-Type": "application/json"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                out = json.load(r)
            return out["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            err_body = e.read().decode(errors="replace")
            if e.code == 429 and attempt < retries - 1:
                wait = 15 * (attempt + 1)  # 15s, 30s, 45s...
                print(f"429 rate limited, retrying in {wait}s... ({err_body[:300]})")
                time.sleep(wait)
                continue
            raise RuntimeError(f"Gemini API error {e.code}: {err_body[:500]}") from e
    raise RuntimeError("Gemini API: exhausted retries on 429")


ODIA_RANGE = re.compile(r"[\u0B00-\u0B7F]")

def validate(items):
    """Second pass: structural + content safety checks. Returns list of problems."""
    problems = []
    if len(items) != 12:
        problems.append(f"expected 12 rashis, got {len(items)}")
    seen = set()
    for it in items:
        r, t = it.get("rashi", "?"), it.get("text", "")
        seen.add(r)
        odia_chars = len(ODIA_RANGE.findall(t))
        if odia_chars < len(t) * 0.5:
            problems.append(f"{r}: not enough Odia script")
        if not (60 <= len(t) <= 260):
            problems.append(f"{r}: length {len(t)} outside 60-260")
        for pat in FORBIDDEN_PATTERNS:
            if pat in t:
                problems.append(f"{r}: forbidden phrase '{pat}'")
    missing = set(LUCKY) - seen
    if missing:
        problems.append(f"missing rashis: {missing}")
    return problems


def generate_content(date: datetime.date, max_attempts=3):
    p = pj.compute_panchanga(date)
    ctxs = pj.rashi_context(p)
    prompt = build_prompt(p, ctxs)
    last_problems = None
    for attempt in range(max_attempts):
        raw = call_gemini(prompt)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            last_problems = ["invalid JSON from model"]
            continue
        items = data.get("rashifala", [])
        problems = validate(items)
        if not problems:
            for it in items:  # attach deterministic lucky color/number
                c, n = LUCKY[it["rashi"]]
                it["color"], it["number"] = c, n
            return {
                "date": date.isoformat(),
                "header_odia": "ଆଜିର ରାଶିଫଳ",
                "rashifala": items,
            }
        last_problems = problems
    raise RuntimeError(f"validation failed after {max_attempts} attempts: {last_problems}")


if __name__ == "__main__":
    dstr = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    date = datetime.date.fromisoformat(dstr)
    content = generate_content(date)
    out = os.path.join(os.path.dirname(__file__), "..", "output", f"content_{dstr}.json")
    json.dump(content, open(out, "w"), ensure_ascii=False, indent=2)
    print("content written:", out)
