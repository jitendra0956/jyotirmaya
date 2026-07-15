#!/usr/bin/env python3
"""One-time helper: exchange short-lived IG token for long-lived (60-day).
Run via GitHub Actions so it happens server-side, reading straight from
already-correct secrets — avoids any browser/copy-paste corruption."""
import os, json, urllib.request, urllib.parse

token = os.environ["IG_ACCESS_TOKEN"].strip()
secret = os.environ["IG_APP_SECRET"].strip()

print(f"Token length: {len(token)}, starts: {token[:6]}...")
print(f"Secret length: {len(secret)}")

params = urllib.parse.urlencode({
    "grant_type": "ig_exchange_token",
    "client_secret": secret,
    "access_token": token,
})
url = f"https://graph.instagram.com/access_token?{params}"

try:
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.load(r)
except urllib.error.HTTPError as e:
    print("FAILED:", e.read().decode(errors="replace"))
    raise SystemExit(1)

if "access_token" in data:
    t = data["access_token"]
    days = data.get("expires_in", 0) // 86400
    print(f"SUCCESS. New token length: {len(t)}, expires in ~{days} days")
    print()
    print("COPY THIS FULL TOKEN INTO YOUR IG_ACCESS_TOKEN SECRET:")
    print(t)
else:
    print("FAILED:", data)
    raise SystemExit(1)
