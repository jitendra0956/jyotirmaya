"""
Jyotirmaya — LLM interpretation layer.
Code computes all facts (panchanga.py); this module only turns facts into
traditional Odia prose via Gemini, then validates the output.
Requires: GEMINI_API_KEY env var. Falls back with clear error for approval gate.
"""
import json, os, re, sys, time, urllib.request, urllib.error, datetime

sys.path.insert(0, os.path.dirname(__file__))
import panchanga as pj
import odia_lexicon as lex

MODEL = "gemini-3.5-flash"  # was gemini-2.5-flash — deprecated, "no longer
                             # available to new users" (same issue found
                             # and fixed for Songs & Quotes earlier)
FALLBACK_MODEL = "gemini-3.5-flash-lite"
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

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

SYSTEM_RULES = """ତୁମେ ଏକ ଅଭିଜ୍ଞ ଓଡ଼ିଆ ପଞ୍ଜିକା ଲେଖକ ଓ ଟିଭି ଜ୍ୟୋତିଷ ଉପସ୍ଥାପକ। ପାରମ୍ପରିକ ଖବରକାଗଜ ରାଶିଫଳ ଶୈଳୀରେ ଲେଖ।

ଭାଷା ଶୈଳୀ (ଅତି ଗୁରୁତ୍ୱପୂର୍ଣ୍ଣ):
- ସ୍ୱାଭାବିକ, ଆଧୁନିକ, ଖବରକାଗଜ-ମାନର ଓଡ଼ିଆରେ ଲେଖ — ଇଂରାଜୀରୁ ଆକ୍ଷରିକ ଅନୁବାଦ ପରି ନୁହେଁ।
- ଓଡ଼ିଆ ଖବରକାଗଜ, ପତ୍ରିକା, ଜ୍ୟୋତିଷ କଲମ ଓ ଟିଭି ରାଶିଫଳ କାର୍ଯ୍ୟକ୍ରମରେ ସାଧାରଣତଃ ବ୍ୟବହୃତ ହେଉଥିବା ଶବ୍ଦ ବ୍ୟବହାର କର।
- ଉଦାହରଣ: "କାର୍ଯ୍ୟ" ପରିବର୍ତ୍ତେ "କାର୍ଯ୍ୟକ୍ଷେତ୍ର"; "ପ୍ରେମ" ପରିବର୍ତ୍ତେ "ପ୍ରେମଜୀବନ"; "ଫଳପ୍ରାପ୍ତିର ସମ୍ଭାବନା" ପରିବର୍ତ୍ତେ "ଫଳ ମିଳିବାର ସମ୍ଭାବନା"।
- ଏକ ଅଭିଜ୍ଞ ଟିଭି ଜ୍ୟୋତିଷୀ କଥା କହୁଥିବା ପରି ସହଜ, ପ୍ରବାହମୟ ଓଡ଼ିଆ ଲେଖ — ଅନୁବାଦିତ AI ଭାଷା ପରି ନୁହେଁ।
- ଅତ୍ୟଧିକ ସଂସ୍କୃତ-ମିଶ୍ରିତ, ପୁସ୍ତକୀୟ କିମ୍ବା ଯାନ୍ତ୍ରିକ ଶବ୍ଦ ଏଡ଼ାଅ। ସରଳତା ଓ ସ୍ୱାଭାବିକ ପ୍ରବାହକୁ ପ୍ରାଥମିକତା ଦିଅ।

କଠୋର ନିୟମ:
1. କେବଳ ମାର୍ଗଦର୍ଶନ ଭାଷା — "ମିଳିପାରେ", "ସମ୍ଭାବନା", "ସୂଚନା", "ହିତକର"। କଦାପି ନିଶ୍ଚିତ ଭବିଷ୍ୟବାଣୀ ନୁହେଁ।
2. ଭୟ ସୃଷ୍ଟିକାରୀ କଥା ନିଷେଧ — ମୃତ୍ୟୁ, ଗୁରୁତର ରୋଗ, ଦୁର୍ଘଟଣା, ବିବାହବିଚ୍ଛେଦ ଉଲ୍ଲେଖ କର ନାହିଁ।
3. ସ୍ୱାସ୍ଥ୍ୟ ବିଷୟରେ କେବଳ "ସ୍ୱାସ୍ଥ୍ୟ ପ୍ରତି ଧ୍ୟାନ ଦିଅନ୍ତୁ" ପରି ସାଧାରଣ କଥା।
4. ପ୍ରତି ରାଶି ପାଇଁ ଦୁଇଟି ପୂର୍ଣ୍ଣ, ସମ୍ପୂର୍ଣ୍ଣ ବାକ୍ୟ ଲେଖ (ଖଣ୍ଡ ବାକ୍ୟାଂଶ ନୁହେଁ):
   - "do": ଆଜି କଣ କରିବା ଉଚିତ୍ (କାର୍ଯ୍ୟ/ଅର୍ଥ/ପରିବାର ମଧ୍ୟରୁ ଗୋଟିଏ ପ୍ରସଙ୍ଗ ଚୟନ କରି)
   - "dont": ଆଜି କଣ ଏଡ଼ାଇବା ଉଚିତ୍
   ଉଭୟ ପୂର୍ଣ୍ଣ ମନେ ହେବା ଉଚିତ୍ — ଉଦାହରଣ ଶୈଳୀ: "ନୂଆ କାର୍ଯ୍ୟ ଆରମ୍ଭ କରିବା ପାଇଁ ଆଜି ଉତ୍ତମ ଦିନ, ସାହସର ସହ ଆଗକୁ ବଢ଼ନ୍ତୁ" — ଏକ ଛୋଟ ଖଣ୍ଡବାକ୍ୟ ନୁହେଁ, ଏକ ସମ୍ପୂର୍ଣ୍ଣ, ପ୍ରବାହମୟ ବାକ୍ୟ।
5. ଶୁଦ୍ଧ, ସ୍ୱାଭାବିକ ଓଡ଼ିଆ — ହିନ୍ଦୀ ମିଶ୍ରଣ ନାହିଁ।
6. transit_tone "favourable" ହେଲେ ସକାରାତ୍ମକ ସ୍ୱର, "mixed" ହେଲେ ସନ୍ତୁଳିତ ସାବଧାନ ସ୍ୱର।
7. ଉତ୍ତର କେବଳ JSON: {"rashifala":[{"rashi":"Mesha","do":"...","dont":"..."}, ... ସବୁ 12ଟି]}"""


def few_shot_examples():
    here = os.path.join(os.path.dirname(__file__), "data")
    ex = json.load(open(os.path.join(here, "style_examples.json"), encoding="utf-8"))
    return json.dumps({"rashifala": ex["rashifala"]}, ensure_ascii=False)


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
    """Same proven retry/backoff/fallback logic as Songs & Quotes/
    Kurukshetra's gemini_client.py — this function predated that pattern
    and only handled 429, not 503 or connection timeouts, which is what
    caused a real production failure (503 'high demand' propagating
    immediately with zero retry)."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set")
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.8, "responseMimeType": "application/json"},
    }).encode()

    def _attempt(model, max_retries):
        url = API_BASE.format(model=model) + f"?key={key}"
        req = urllib.request.Request(url, data=body,
                                     headers={"Content-Type": "application/json"})
        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    out = json.load(r)
                return out["candidates"][0]["content"]["parts"][0]["text"]
            except urllib.error.HTTPError as e:
                err_body = e.read().decode(errors="replace")

                if e.code in (401, 403):
                    raise RuntimeError(f"Gemini auth error {e.code} — check GEMINI_API_KEY: {err_body[:300]}") from e

                if e.code == 429 and attempt < max_retries - 1:
                    wait = 15 * (attempt + 1)
                    print(f"[gemini] 429 rate limit on {model}, retry {attempt+1}/{max_retries-1} in {wait}s")
                    time.sleep(wait)
                    continue

                if e.code == 503 and attempt < max_retries - 1:
                    wait = 5 * (2 ** attempt)  # 5s, 10s, 20s
                    print(f"[gemini] 503 high demand on {model}, retry {attempt+1}/{max_retries-1} in {wait}s")
                    time.sleep(wait)
                    continue

                raise RuntimeError(f"Gemini API error {e.code} on {model}: {err_body[:500]}") from e

            except (TimeoutError, urllib.error.URLError, ConnectionError) as e:
                if attempt < max_retries - 1:
                    wait = 5 * (2 ** attempt)
                    print(f"[gemini] connection timeout on {model} ({type(e).__name__}), "
                          f"retry {attempt+1}/{max_retries-1} in {wait}s")
                    time.sleep(wait)
                    continue
                raise RuntimeError(f"Gemini timeout on {model} after {max_retries} attempts: {e}") from e

        raise RuntimeError(f"Gemini exhausted {max_retries} retries on {model}")

    try:
        return _attempt(MODEL, retries)
    except RuntimeError as primary_err:
        err_lower = str(primary_err).lower()
        if any(s in err_lower for s in ("503", "exhausted", "timeout", "429", "quota", "resource_exhausted")):
            print(f"[gemini] primary model {MODEL!r} unavailable — trying fallback {FALLBACK_MODEL!r}")
            return _attempt(FALLBACK_MODEL, 3)
        raise


ODIA_RANGE = re.compile(r"[\u0B00-\u0B7F]")

def validate(items):
    """Second pass: structural + content safety checks. Returns list of problems."""
    problems = []
    if len(items) != 12:
        problems.append(f"expected 12 rashis, got {len(items)}")
    seen = set()
    for it in items:
        r = it.get("rashi", "?")
        seen.add(r)
        for field in ("do", "dont"):
            t = it.get(field, "")
            if not t:
                problems.append(f"{r}: missing '{field}'")
                continue
            odia_chars = len(ODIA_RANGE.findall(t))
            if odia_chars < len(t) * 0.5:
                problems.append(f"{r}: '{field}' not enough Odia script")
            if not (30 <= len(t) <= 140):
                problems.append(f"{r}: '{field}' length {len(t)} outside 30-140")
            for pat in FORBIDDEN_PATTERNS:
                if pat in t:
                    problems.append(f"{r}: '{field}' forbidden phrase '{pat}'")
    missing = set(LUCKY) - seen
    if missing:
        problems.append(f"missing rashis: {missing}")
    return problems


PROOFREAD_PROMPT = """ତୁମେ ଜଣେ ଅତି ଯତ୍ନବାନ ଓଡ଼ିଆ ପ୍ରୁଫ୍‌ରିଡର୍, ପାରମ୍ପରିକ ଜ୍ୟୋତିଷ/ପଞ୍ଜିକା ଲେଖାରେ ବିଶେଷଜ୍ଞ।
ନିମ୍ନଲିଖିତ ୧୨ଟି ରାଶିର "do" ଓ "dont" ବାକ୍ୟ ଯାଞ୍ଚ କର:
- ବନାନ ଭୁଲ, ଅଣ-ଓଡ଼ିଆ/ହିନ୍ଦୀ ମିଶ୍ରଣ, କିମ୍ବା ଅସ୍ୱାଭାବିକ ବାକ୍ୟ ଥିଲେ ସୁଧାର।
- ଅତ୍ୟଧିକ ସଂସ୍କୃତ-ମିଶ୍ରିତ, ପୁସ୍ତକୀୟ, ଯାନ୍ତ୍ରିକ କିମ୍ବା ଆକ୍ଷରିକ-ଅନୁବାଦ ପରି ଲାଗୁଥିବା ଶବ୍ଦ/ବାକ୍ୟକୁ ଆଧୁନିକ ଖବରକାଗଜ-ମାନର ସହଜ ଓଡ଼ିଆରେ ବଦଳାଅ (ଉଦାହରଣ: "କାର୍ଯ୍ୟ"→"କାର୍ଯ୍ୟକ୍ଷେତ୍ର", "ପ୍ରେମ"→"ପ୍ରେମଜୀବନ", "ଫଳପ୍ରାପ୍ତିର ସମ୍ଭାବନା"→"ଫଳ ମିଳିବାର ସମ୍ଭାବନା")।
- ଉଭୟ ବାକ୍ୟ ପୂର୍ଣ୍ଣ, ସମ୍ପୂର୍ଣ୍ଣ ମନେ ହେବା ଉଚିତ୍ — ଛୋଟ ଖଣ୍ଡବାକ୍ୟାଂଶ ନୁହେଁ।
- ଏକ ଅଭିଜ୍ଞ ଟିଭି ଜ୍ୟୋତିଷୀ କହୁଥିବା ପରି ସ୍ୱାଭାବିକ, ପ୍ରବାହମୟ ଶୁଣାଯିବା ଉଚିତ୍ — AI-ଅନୁବାଦିତ ପରି ନୁହେଁ।
- ଅର୍ଥ ଓ ଶୈଳୀ ଅପରିବର୍ତ୍ତିତ ରଖ, କେବଳ ଭାଷାଗତ ତ୍ରୁଟି ସୁଧାର।
- କୌଣସି ତ୍ରୁଟି ନ ଥିଲେ ସେହିପରି ଫେରାଅ।
- କେବଳ JSON ଫେରାଅ: {"rashifala":[{"rashi":"...","do":"...","dont":"..."}, ...ସବୁ ୧୨ଟି], "had_corrections": true/false}

ଯାଞ୍ଚ କରିବାକୁ ଥିବା ବିଷୟବସ୍ତୁ:
"""


def proofread_pass(items):
    """Second, independent Gemini call acting as a native-style proofreader —
    this substitutes for daily human review, which isn't available here."""
    payload = json.dumps({"rashifala": [
        {"rashi": it["rashi"], "do": it["do"], "dont": it["dont"]} for it in items
    ]}, ensure_ascii=False)
    raw = call_gemini(PROOFREAD_PROMPT + payload)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return items, False
    corrected = data.get("rashifala", items)
    if len(corrected) != 12:
        return items, False
    return corrected, data.get("had_corrections", False)


def lexicon_gate(items, max_unknown_rate=0.06):
    """Flags text with an unusually high rate of words outside the verified
    Odia vocabulary — automated substitute for a native reviewer's eye."""
    problems = []
    for it in items:
        for field in ("do", "dont"):
            text = it.get(field, "")
            rate = lex.unknown_rate(text)
            if rate > max_unknown_rate:
                unk = lex.unknown_words(text)
                problems.append(f"{it['rashi']} ({field}): unknown-word rate {rate:.0%} ({unk})")
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
        if problems:
            last_problems = problems
            continue

        # Second pass: independent proofreading (substitute for daily human review).
        # Soft — if this call itself fails (network, exhausted rate-limit retries)
        # or corrupts structure, fall back to the already-valid first-pass content
        # (items, already validated above) rather than crashing generation.
        had_corrections = False
        try:
            proofed_items, corrections_flag = proofread_pass(items)
            if not validate(proofed_items):  # empty list = no problems = safe to use
                items, had_corrections = proofed_items, corrections_flag
            else:
                print("[warn] proofread pass broke structure, keeping original first-pass content")
        except Exception as e:
            print(f"[warn] proofread pass failed ({e}), using unproofed first-pass content")

        # Third pass: vocabulary check against verified Odia wordlist — SOFT.
        # This heuristic has a real false-positive rate (agglutinative grammar,
        # and legitimate but less-common words like "ପ୍ରେମଜୀବନରେ" get flagged).
        # It must never block or crash the daily post — only log for the
        # occasional human reviewer's attention.
        try:
            lex_problems = lexicon_gate(items)
            if lex_problems:
                log_path = os.path.join(os.path.dirname(__file__), "..", "output",
                                        "review_log.jsonl")
                os.makedirs(os.path.dirname(log_path), exist_ok=True)
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"date": date.isoformat(), "flagged": lex_problems},
                                       ensure_ascii=False) + "\n")
                print(f"[info] lexicon check flagged (not blocking): {lex_problems}")
        except Exception as e:
            print(f"[warn] lexicon check skipped due to error: {e}")

        for it in items:  # attach deterministic lucky color/number
            c, n = LUCKY[it["rashi"]]
            it["color"], it["number"] = c, n
        return {
            "date": date.isoformat(),
            "header_odia": "ଆଜିର ରାଶିଫଳ",
            "rashifala": items,
            "proofread_corrected": had_corrections,
        }
    raise RuntimeError(f"validation failed after {max_attempts} attempts: {last_problems}")


if __name__ == "__main__":
    dstr = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    date = datetime.date.fromisoformat(dstr)
    content = generate_content(date)
    out = os.path.join(os.path.dirname(__file__), "..", "output", f"content_{dstr}.json")
    json.dump(content, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("content written:", out)
