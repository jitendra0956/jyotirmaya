"""
Jyotirmaya — Instagram carousel publisher via Graph API.
Images are uploaded to Cloudinary (not GitHub Pages/IMAGE_BASE_URL
anymore) — the same migration Songs & Quotes needed when its repo went
private, since GitHub Pages requires a public repo (or paid plan) to
serve files. If Jyotirmaya's repo is also private, IMAGE_BASE_URL would
never have actually served anything, which is a very plausible real cause
of "the workflow succeeds but nothing posts."
Requires env: IG_USER_ID, IG_ACCESS_TOKEN (long-lived), CLOUDINARY_CLOUD_NAME,
CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET.
Instagram carousels allow max 10 items, so 13 slides (cover + 12 rashis)
are split into two posts, cover leading part 1. Each carousel container
is polled until Instagram finishes processing before publish is called.
"""
import hashlib, json, os, sys, time, urllib.request, urllib.error, urllib.parse

GRAPH = "https://graph.instagram.com/v21.0"
MAX_CAROUSEL = 10


def _cloudinary_signature(params: dict, api_secret: str) -> str:
    """SHA-1 (Cloudinary's actual default, not SHA-256 — verified against
    Cloudinary's own documented worked example during the Songs & Quotes
    build)."""
    sorted_params = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return hashlib.sha1((sorted_params + api_secret).encode()).hexdigest()


def upload_to_cloudinary(local_image_path: str, public_id: str = None) -> str:
    """Upload a local image file to Cloudinary. Returns the secure_url.
    overwrite=true + invalidate=true so re-runs for the same date/part
    correctly replace the asset and bust CDN cache, rather than silently
    serving a stale previous attempt."""
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME", "").strip()
    api_key = os.environ.get("CLOUDINARY_API_KEY", "").strip()
    api_secret = os.environ.get("CLOUDINARY_API_SECRET", "").strip()
    if not all([cloud_name, api_key, api_secret]):
        missing = [k for k, v in {
            "CLOUDINARY_CLOUD_NAME": cloud_name, "CLOUDINARY_API_KEY": api_key,
            "CLOUDINARY_API_SECRET": api_secret}.items() if not v]
        raise RuntimeError(f"Missing Cloudinary credentials: {missing}")

    timestamp = str(int(time.time()))
    params_to_sign = {"timestamp": timestamp, "overwrite": "true", "invalidate": "true"}
    if public_id:
        params_to_sign["public_id"] = public_id
    signature = _cloudinary_signature(params_to_sign, api_secret)

    fields = {"api_key": api_key, "timestamp": timestamp, "signature": signature,
              "overwrite": "true", "invalidate": "true"}
    if public_id:
        fields["public_id"] = public_id

    boundary = "----jyotirmaya" + timestamp
    body = b""
    for key, value in fields.items():
        body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n").encode()
    with open(local_image_path, "rb") as f:
        file_data = f.read()
    filename = os.path.basename(local_image_path)
    body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
             f"Content-Type: image/png\r\n\r\n").encode() + file_data + b"\r\n"
    body += f"--{boundary}--\r\n".encode()

    url = f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload"
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            result = json.load(r)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode(errors="replace")
        raise RuntimeError(f"Cloudinary upload error {e.code}: {err_body[:500]}") from e

    secure_url = result.get("secure_url")
    if not secure_url:
        raise RuntimeError(f"Cloudinary response missing secure_url: {result}")
    print(f"[cloudinary] uploaded {local_image_path} -> {secure_url}")
    return secure_url


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


def already_posted_on_instagram(ig_user, token, dstr, part_num):
    """Ground-truth check: ask Instagram itself whether today's part has
    already been posted, rather than trusting our own script's memory of
    success/failure — tonight proved that memory can be wrong (Instagram
    completes the post server-side even when our own HTTP call reports
    an error). Looks at the last 10 posts' captions for this date+part."""
    try:
        res = _get(f"{GRAPH}/{ig_user}/media", {
            "fields": "caption,timestamp", "limit": "15", "access_token": token})
        marker = dstr
        part_marker = f"({part_num}/2)"
        for item in res.get("data", []):
            cap = item.get("caption") or ""
            if marker in cap and part_marker in cap:
                return True
        return False
    except Exception as e:
        print(f"[warn] could not check Instagram's existing posts ({e}) — proceeding normally")
        return False


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
            print(f"[info] part {idx}/2 already published per local marker — skipping")
            continue
        if already_posted_on_instagram(ig_user, token, dstr, idx):
            print(f"[info] part {idx}/2 already found live on Instagram (ground-truth check) — "
                  f"skipping and writing marker now so this stays remembered")
            _mark_published(outdir, idx, "found_via_ground_truth_check")
            continue
        if only_part not in ("both", str(idx)):
            print(f"[info] skipping part {idx}/2 (only_part={only_part})")
            continue
        print(f"[debug] uploading {len(batch)} files for part {idx}/2 to Cloudinary...")
        urls = [
            upload_to_cloudinary(os.path.join(outdir, f), public_id=f"jyotirmaya/{dstr}/{os.path.splitext(f)[0]}")
            for f in batch
        ]
        cap = base_caption + f"\n\n({idx}/2)"
        media_id = publish_one_carousel(urls, cap, ig_user, token)
        ids.append(media_id)
        print(f"[debug] published part {idx}/2: {media_id}")
        _mark_published(outdir, idx, media_id)
        if idx == 1 and only_part == "both":
            time.sleep(5)
    print("published:", ids)
