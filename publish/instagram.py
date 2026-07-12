"""
Jyotirmaya — Instagram carousel publisher via Graph API.
Requires env: IG_USER_ID, IG_ACCESS_TOKEN (long-lived), IMAGE_BASE_URL
Images must be publicly hosted (GitHub Pages) before publishing.
Flow: item containers -> carousel container -> publish. Fails loudly for the
fallback/alert layer in the Actions workflow.
"""
import json, os, sys, time, urllib.request, urllib.parse

GRAPH = "https://graph.facebook.com/v21.0"


def _post(url, params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def publish_carousel(image_urls, caption):
    ig_user = os.environ["IG_USER_ID"]
    token = os.environ["IG_ACCESS_TOKEN"]

    children = []
    for u in image_urls:
        res = _post(f"{GRAPH}/{ig_user}/media", {
            "image_url": u, "is_carousel_item": "true", "access_token": token})
        children.append(res["id"])
        time.sleep(1)

    carousel = _post(f"{GRAPH}/{ig_user}/media", {
        "media_type": "CAROUSEL", "children": ",".join(children),
        "caption": caption, "access_token": token})

    published = _post(f"{GRAPH}/{ig_user}/media_publish", {
        "creation_id": carousel["id"], "access_token": token})
    return published["id"]


def caption_for(date_str, weekday_odia):
    return (f"ଆଜିର ରାଶିଫଳ · {date_str} · {weekday_odia} 🌟\n"
            "ଆପଣଙ୍କ ରାଶି ଖୋଜନ୍ତୁ ଓ ପରିବାରକୁ ପଠାନ୍ତୁ 🙏\n\n"
            "#rashifala #odia #odisha #panjika #jyotish #ଓଡ଼ିଆ #jyotirmaya")


if __name__ == "__main__":
    dstr = sys.argv[1]
    base = os.environ["IMAGE_BASE_URL"].rstrip("/")
    outdir = os.path.join(os.path.dirname(__file__), "..", "output", dstr)
    files = sorted(f for f in os.listdir(outdir)
                   if f.endswith(".png") and not f.startswith("00_"))
    urls = [f"{base}/{dstr}/{f}" for f in files]
    media_id = publish_carousel(urls, caption_for(dstr, ""))
    print("published:", media_id)
