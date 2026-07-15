"""
Jyotirmaya — Instagram carousel publisher via Graph API.
Requires env: IG_USER_ID, IG_ACCESS_TOKEN (long-lived), IMAGE_BASE_URL
Images must be publicly hosted (GitHub Pages) before publishing.
Instagram carousels allow max 10 items, so 13 slides (cover + 12 rashis)
are split into two posts, cover leading part 1. Each carousel container
is polled until Instagram finishes processing before publish is called.
"""
import json, os, sys, time, urllib.request, urllib.error, urllib.parse

GRAPH = "https://graph.instagram.com/v21.0"
MAX_CAROUSEL = 10


def _post(url, params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode(errors="replace")
        raise RuntimeError(f"Graph API error {e.code} calling {url.split('?')[0]}: {err_body}") from e


def _get(url, params):
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{url}?{qs}")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode(errors="replace")
        raise RuntimeError(f"Graph API error {e.code} calling {url.split('?')[0]}: {err_body}") from e


def _wait_until_ready(container_id, token, timeout=90, poll_interval=10):
    """Poll a media container until Instagram finishes processing it.
    Polling less frequently (10s, not 3s) meaningfully cuts API calls per
    run — likely the real driver of today's rate-limit hits, since two
    carousels' worth of tight polling can burn ~40 calls each on its own."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        res = _get(f"{GRAPH}/{container_id}", {
            "fields": "status_code", "access_token": token})
        status = res.get("status_code")
        print(f"[debug] container {container_id} status={status}")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"Container {container_id} failed processing: {res}")
        time.sleep(poll_interval)
    raise RuntimeError(f"Container {container_id} not ready after {timeout}s")


def publish_one_carousel(image_urls, caption, ig_user, token):
    """Publish a single carousel (must be 2-10 items). Returns published media id."""
    children = []
    for u in image_urls:
        res = _post(f"{GRAPH}/{ig_user}/media", {
            "image_url": u, "is_carousel_item": "true", "access_token": token})
        children.append(res["id"])
        time.sleep(1)

    carousel = _post(f"{GRAPH}/{ig_user}/media", {
        "media_type": "CAROUSEL", "children": ",".join(children),
        "caption": caption, "access_token": token})

    _wait_until_ready(carousel["id"], token)

    published = _post(f"{GRAPH}/{ig_user}/media_publish", {
        "creation_id": carousel["id"], "access_token": token})
    return published["id"]


def publish_in_batches(image_urls, base_caption):
    """Splits >10 images into sequential carousel posts, cover leading part 1."""
    ig_user = os.environ["IG_USER_ID"].strip()
    token = os.environ["IG_ACCESS_TOKEN"].strip()

    print(f"[debug] IG_USER_ID='{ig_user}' (len={len(ig_user)})")
    print(f"[debug] token length={len(token)}, starts='{token[:6]}...', "
          f"ends='...{token[-4:]}', contains_space={' ' in token}, "
          f"contains_newline={chr(10) in token or chr(13) in token}, "
          f"contains_quote={chr(34) in token or chr(39) in token}")

    if len(image_urls) <= MAX_CAROUSEL:
        batches = [image_urls]
    else:
        cover, rest = image_urls[0], image_urls[1:]
        mid = (len(rest) + 1) // 2
        batches = [[cover] + rest[:mid], rest[mid:]]

    ids = []
    for idx, batch in enumerate(batches, start=1):
        suffix = "" if len(batches) == 1 else f"\n\n({idx}/{len(batches)})"
        media_id = publish_one_carousel(batch, base_caption + suffix, ig_user, token)
        ids.append(media_id)
        print(f"[debug] published part {idx}/{len(batches)}: {media_id}")
        if idx < len(batches):
            time.sleep(5)
    return ids


def caption_for(date_str, weekday_odia):
    return (f"ଆଜିର ରାଶିଫଳ · {date_str} · {weekday_odia} 🌟\n"
            "ଆପଣଙ୍କ ରାଶି ଖୋଜନ୍ତୁ ଓ ପରିବାରକୁ ପଠାନ୍ତୁ 🙏\n\n"
            "#rashifala #odia #odisha #panjika #jyotish #ଓଡ଼ିଆ #jyotirmaya")


def _marker_path(outdir):
    return os.path.join(outdir, "published_parts.json")


def _load_published(outdir):
    path = _marker_path(outdir)
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    return {}


def _mark_published(outdir, part_num, media_id):
    path = _marker_path(outdir)
    data = _load_published(outdir)
    data[str(part_num)] = {"media_id": media_id, "published": True}
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    # Commit immediately so this survives even if a later part fails —
    # the NEXT run (manual or scheduled cron) will see this and skip it.
    os.system('git config user.name "jyotirmaya-bot" 2>/dev/null')
    os.system('git config user.email "bot@jyotirmaya" 2>/dev/null')
    os.system(f'git add "{path}" && git commit -m "mark part {part_num} published for {os.path.basename(outdir)}" '
              f'&& git push 2>&1 || echo "[warn] could not commit publish marker"')


if __name__ == "__main__":
    dstr = sys.argv[1]
    only_part = sys.argv[2] if len(sys.argv) > 2 else "both"  # "1", "2", or "both"
    base = os.environ["IMAGE_BASE_URL"].rstrip("/")
    outdir = os.path.join(os.path.dirname(__file__), "..", "output", dstr)

    # Explicit whitelist by known rashi slugs — immune to stray leftover
    # files (e.g. an old single-cover 01_cover.png from a prior design)
    # that a prefix-exclusion filter could misclassify as a rashi card.
    RASHI_SLUGS = ["mesha", "vrishabha", "mithuna", "karkata", "simha", "kanya",
                   "tula", "vrischika", "dhanu", "makara", "kumbha", "meena"]
    all_files = os.listdir(outdir)
    rashi_files = []
    for slug in RASHI_SLUGS:
        matches = [f for f in all_files if f.lower().endswith(f"_{slug}.png")]
        if len(matches) != 1:
            raise RuntimeError(f"expected exactly 1 file for rashi '{slug}', found {matches}")
        rashi_files.append(matches[0])

    stray = [f for f in all_files if f.endswith(".png")
             and f not in rashi_files
             and f not in ("cover_part1.png", "cover_part2.png", "festival_greeting.png")
             and not f.startswith("00_")]
    if stray:
        print(f"[warn] ignoring stray files not part of the expected set: {stray}")

    mid = (len(rashi_files) + 1) // 2
    part1 = ["cover_part1.png"] + rashi_files[:mid]
    part2 = ["cover_part2.png"] + rashi_files[mid:]

    if "festival_greeting.png" in all_files:
        part1 = ["festival_greeting.png"] + part1
        print("[info] festival greeting slide included at front of Part 1")

    ig_user = os.environ["IG_USER_ID"].strip()
    token = os.environ["IG_ACCESS_TOKEN"].strip()
    print(f"[debug] IG_USER_ID='{ig_user}' (len={len(ig_user)})")
    print(f"[debug] token length={len(token)}, starts='{token[:6]}...', "
          f"ends='...{token[-4:]}'")

    base_caption = caption_for(dstr, "")
    already = _load_published(outdir)
    ids = []
    for idx, batch in enumerate([part1, part2], start=1):
        if str(idx) in already and already[str(idx)].get("published"):
            print(f"[info] part {idx}/2 already published (media_id={already[str(idx)]['media_id']}) — skipping to avoid duplicate")
            continue
        if only_part not in ("both", str(idx)):
            print(f"[info] skipping part {idx}/2 (only_part={only_part})")
            continue
        urls = [f"{base}/{dstr}/{f}" for f in batch]
        cap = base_caption + f"\n\n({idx}/2)"
        media_id = publish_one_carousel(urls, cap, ig_user, token)
        ids.append(media_id)
        print(f"[debug] published part {idx}/2: {media_id}")
        _mark_published(outdir, idx, media_id)
        if idx == 1 and only_part == "both":
            time.sleep(5)
    print("published:", ids)
