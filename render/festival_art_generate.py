"""
Jyotirmaya — Festival art candidate generator.
Uses Pollinations.ai (free, zero-API-key, Flux model) to generate several
candidate illustrations per festival. This is a CURATION tool — run once
per festival, review the outputs, pick the best one into assets/festivals/.
Never called live in the daily pipeline; festival art is fixed once chosen.

Usage:
    python festival_art_generate.py nuakhai
    python festival_art_generate.py --all
"""
import os, sys, time, urllib.request, urllib.parse

OUTDIR = os.path.join(os.path.dirname(__file__), "..", "output", "festival_candidates")
BASE = "https://image.pollinations.ai/prompt/"

STYLE_SUFFIX = (
    ", premium editorial illustration, deep purple and gold color palette, "
    "Odisha Pattachitra-inspired folk art style, ornate border, night sky, "
    "no text, no letters, no words, square composition, high detail"
)

# Symbolic / representational prompts — deliberately avoid asking the model
# to depict deities directly (distortion risk); use objects, motifs, scenes.
FESTIVAL_PROMPTS = {
    "makar_sankranti": "sesame sweets and til laddu on a brass plate, sun rising over paddy fields, harvest symbols",
    "raja_sankranti": "a decorated wooden swing under a mango tree, monsoon clouds, Odisha village, floral rangoli",
    "nuakhai": "a plate of fresh new rice and paddy stalks, harvest festival offering, golden fields at sunset",
    "ratha_yatra": "a giant ornate temple chariot wheel, colorful fabric canopy, festive crowd silhouette, Puri seaside",
    "chandana_yatra": "sandalwood paste and flowers floating on a temple tank, boats with canopies, evening lights",
    "snana_purnima": "a decorated temple bathing platform, pots of water, flowers, full moon, ceremonial umbrellas",
    "kartika_purnima": "small paper boats with diyas floating on a river at dusk, boita bandana, full moon reflection",
    "rakhi_purnima": "colorful rakhi threads on a brass plate with diya and rice, festive red and gold",
    "ganesh_chaturthi": "a decorated modak sweet, banana leaf, hibiscus flowers, festive lights, elephant motif silhouette",
    "durga_puja": "an ornate pandal silhouette, dhak drums, marigold garlands, festive lights, autumn sky",
    "diwali": "rows of diyas on a doorstep, rangoli patterns, fireworks in night sky, marigold flowers",
    "vasanta_panchami": "yellow mustard fields, a veena resting on a cloth, spring flowers, soft morning light",
}


def generate_candidates(festival_key, n=4):
    if festival_key not in FESTIVAL_PROMPTS:
        print(f"Unknown festival key '{festival_key}'. Options: {list(FESTIVAL_PROMPTS)}")
        return
    prompt = FESTIVAL_PROMPTS[festival_key] + STYLE_SUFFIX
    outdir = os.path.join(OUTDIR, festival_key)
    os.makedirs(outdir, exist_ok=True)
    encoded = urllib.parse.quote(prompt)
    for seed in range(n):
        url = f"{BASE}{encoded}?width=1080&height=1080&seed={seed}&nologo=true"
        out_path = os.path.join(outdir, f"candidate_{seed}.jpg")
        try:
            urllib.request.urlretrieve(url, out_path)
            print(f"  saved {out_path}")
        except Exception as e:
            print(f"  [warn] seed {seed} failed: {e}")
        time.sleep(16)  # anonymous tier is rate-limited to ~1 request/15s


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python festival_art_generate.py <festival_key|--all>")
        print("Available:", list(FESTIVAL_PROMPTS))
        sys.exit(1)
    if sys.argv[1] == "--all":
        for key in FESTIVAL_PROMPTS:
            print(f"Generating candidates for {key}...")
            generate_candidates(key)
    else:
        generate_candidates(sys.argv[1])
