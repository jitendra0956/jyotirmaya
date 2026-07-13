"""
Run this after your occasional native Odia reviewer has actually read a
day's content and confirmed it's correct. It adds that day's vocabulary
to the permanent approved list, making the automated lexicon_gate() less
noisy (fewer false "unknown word" flags) for all future days.

Usage:
    python engine/audit_approve.py 2026-07-13
"""
import sys, os, json, re

sys.path.insert(0, os.path.dirname(__file__))
import odia_lexicon as lex

ODIA_RE = re.compile(r"[\u0B00-\u0B7F]+")

if __name__ == "__main__":
    dstr = sys.argv[1]
    path = os.path.join(os.path.dirname(__file__), "..", "output", f"content_{dstr}.json")
    content = json.load(open(path, encoding="utf-8"))
    words = set()
    for item in content["rashifala"]:
        words |= set(ODIA_RE.findall(item["text"]))
    lex.add_to_approved(words)
    print(f"Approved {len(words)} words from {dstr} — future lexicon checks will be quieter for these.")
