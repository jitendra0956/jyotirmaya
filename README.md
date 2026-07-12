# ଜ୍ୟୋତିର୍ମୟ (Jyotirmaya)
Daily Odia panjika + rashifala pipeline.

## Structure
- engine/panchanga.py — Swiss Ephemeris calculations (truth layer)
- engine/interpret.py — Gemini Odia interpretation + validator (needs GEMINI_API_KEY)
- render/cards.py — PIL carousel renderer (branded, per-date output)
- publish/instagram.py — Instagram Graph API publisher
- .github/workflows/daily.yml — 9PM IST generate + approval, 5:30AM IST publish
- fonts/ — Noto Sans Oriya
- output/ — generated content JSON + rendered cards per date

## Manual run
python engine/interpret.py 2026-07-14   # needs GEMINI_API_KEY
python render/cards.py 2026-07-14

## Required GitHub secrets
GEMINI_API_KEY, TG_BOT_TOKEN, TG_CHAT_ID, IG_USER_ID, IG_ACCESS_TOKEN, IMAGE_BASE_URL
