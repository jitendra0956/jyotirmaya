"""
Jyotirmaya — one-time rashi icon generator (Pollinations.ai).

Run this ONCE (locally, or as a manual GitHub Actions job) to produce 12
illustrated zodiac icons -- NOT part of the daily pipeline. A zodiac
sign's icon doesn't change day to day, so regenerating it every single
run would be pointless waste; generate once, commit the 12 files as
static assets, and the renderer uses them from then on.

Uses the SAME proven Pollinations.ai setup already fixed and confirmed
working for Kurukshetra: the current gen.pollinations.ai endpoint (not
the legacy image.pollinations.ai/prompt/ host), the correct `key=` query
parameter (their real parameter name, not the `token=` guess that
turned out to be wrong), sent alongside a Bearer header for good
measure, and a random seed per request. Needs the SAME kind of
POLLINATIONS_TOKEN as Kurukshetra -- reuse that account/key, or
register a separate free one at https://enter.pollinations.ai if you'd
rather keep usage separate.

Usage:
    export POLLINATIONS_TOKEN=sk_...
    python engine/generate_rashi_icons.py

Produces: assets/rashi_icons/<Rashi>.png  (12 files, 512x512, transparent
background where possible)
"""
import os, sys, time, random, urllib.request, urllib.parse

sys.path.insert(0, os.path.dirname(__file__))
import panchanga as pj

BASE = "https://gen.pollinations.ai/image/"
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "rashi_icons")

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/124.0.0.0 Safari/537.36")

# One clear physical subject per rashi (the classical symbol), described
# for a consistent icon SET rather than 12 independently-styled images.
RASHI_SUBJECTS = {
    "Mesha": "a ram's head in profile",
    "Vrishabha": "a bull's head in profile",
    "Mithuna": "a pair of celestial twins standing together",
    "Karkata": "a crab viewed from above",
    "Simha": "a lion's head facing forward",
    "Kanya": "a maiden holding a sheaf of wheat",
    "Tula": "a balance scale",
    "Vrischika": "a scorpion viewed from above",
    "Dhanu": "a centaur archer drawing a bow",
    "Makara": "a mythical sea-goat (crocodile head, fish tail)",
    "Kumbha": "a water-bearer pouring water from a pot",
    "Meena": "two fish swimming in opposite directions, tied together",
}

STYLE_SUFFIX = (
    ", elegant thin gold line-art icon, single continuous line style, "
    "minimalist, symmetrical, centered composition, on a transparent "
    "or plain deep indigo background, no text, no letters, no shading, "
    "no gradient, flat single-color gold outline only, temple-art "
    "inspired, icon design, vector-style, clean edges"
)


def generate_one(rashi_key: str, subject: str, out_path: str, retries: int = 3):
    prompt = f"{subject}{STYLE_SUFFIX}"
    encoded = urllib.parse.quote(prompt)
    seed = random.randint(1, 2_000_000_000)
    url = f"{BASE}{encoded}?width=512&height=512&nologo=true&seed={seed}"

    token = os.environ.get("POLLINATIONS_TOKEN", "").strip()
    headers = {"User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        url += f"&key={urllib.parse.quote(token)}"
    else:
        print(f"  [warn] POLLINATIONS_TOKEN not set -- {rashi_key} icon will carry a watermark")

    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            if len(data) < 1000:
                raise RuntimeError(f"suspiciously small response ({len(data)} bytes)")
            with open(out_path, "wb") as f:
                f.write(data)
            print(f"  saved: {out_path} ({len(data)} bytes)")
            return
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                wait = 16
                print(f"  attempt {attempt+1}/{retries} failed ({e}), retry in {wait}s")
                time.sleep(wait)
    raise RuntimeError(f"failed to generate {rashi_key} icon after {retries} attempts: {last_err}")


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"Generating 12 rashi icons into {OUT_DIR} ...")
    print("This makes 12 real requests -- if on the free anonymous tier "
          "(no POLLINATIONS_TOKEN), expect ~15s between requests due to "
          "rate limiting, so this will take a few minutes total.\n")
    for rashi in pj.RASHI_NAMES:
        out_path = os.path.join(OUT_DIR, f"{rashi}.png")
        if os.path.exists(out_path):
            print(f"  {rashi}: already exists, skipping (delete the file to regenerate)")
            continue
        print(f"{rashi} ({RASHI_SUBJECTS[rashi]})...")
        generate_one(rashi, RASHI_SUBJECTS[rashi], out_path)
    print("\nDone. Review the 12 files in assets/rashi_icons/ before committing --")
    print("AI generation is inconsistent run to run; regenerate any that don't")
    print("look right by deleting that one file and running this script again.")
