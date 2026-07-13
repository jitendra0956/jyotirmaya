"""
Jyotirmaya — Odia vocabulary checker.
Since neither the developer nor Claude is a fluent native Odia reader,
this is the automated substitute for daily human review. Three layers:
1. A real 45k-word Odia frequency list (Tesseract OCR training data)
2. A suffix stripper, since Odia is agglutinative (ଙ୍କ/କୁ/ରେ/ମାନେ etc.
   attach to correct words and would otherwise look "unknown")
3. A growing approved-vocabulary file, seeded from human-reviewed days,
   extendable whenever the occasional native reviewer checks in
"""
import os, re, json

HERE = os.path.dirname(__file__)
WORDLIST_PATH = os.path.join(HERE, "..", "assets", "lexicon", "odia_wordlist.txt")
APPROVED_PATH = os.path.join(HERE, "..", "assets", "lexicon", "approved_vocab.json")

ODIA_RE = re.compile(r"[\u0B00-\u0B7F]+")

# Longest-suffix-first so we strip "ଙ୍କରେ" before the shorter "ରେ" inside it, etc.
SUFFIXES = sorted([
    "ମାନଙ୍କଠାରୁ", "ମାନଙ୍କଠାରେ", "ମାନଙ୍କର", "ମାନଙ୍କୁ", "ମାନଙ୍କ", "ମାନେ",
    "ଙ୍କଠାରୁ", "ଙ୍କଠାରେ", "ଙ୍କଦ୍ୱାରା", "ଙ୍କରେ", "ଙ୍କୁ", "ଙ୍କର", "ଙ୍କ",
    "ଠାରୁ", "ଠାରେ", "ଦ୍ୱାରା",
    "ରୁ", "ରେ", "କୁ", "ର", "ଟି", "ଟା", "ଗୁଡ଼ିକ",
], key=len, reverse=True)


def _load_wordlist():
    words = set()
    with open(WORDLIST_PATH, encoding="utf-8") as f:
        for line in f:
            w = line.strip()
            if w and ODIA_RE.fullmatch(w):
                words.add(w)
    return words


def _load_approved():
    if os.path.exists(APPROVED_PATH):
        return set(json.load(open(APPROVED_PATH, encoding="utf-8")))
    return set()


_WORDLIST = _load_wordlist()
_APPROVED = _load_approved()


def add_to_approved(words):
    """Call this after a native reviewer confirms a batch of text is correct —
    grows the vocabulary memory so future checks get less noisy over time."""
    global _APPROVED
    _APPROVED |= set(words)
    json.dump(sorted(_APPROVED), open(APPROVED_PATH, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


def _strip_suffix(word):
    for suf in SUFFIXES:
        if word.endswith(suf) and len(word) > len(suf) + 1:
            return word[: -len(suf)]
    return word


def known(word):
    if word in _WORDLIST or word in _APPROVED:
        return True
    stemmed = _strip_suffix(word)
    return stemmed in _WORDLIST or stemmed in _APPROVED


def unknown_words(text):
    """Returns the list of Odia words in text not found in wordlist/approved,
    even after stripping common suffixes."""
    words = ODIA_RE.findall(text)
    return [w for w in words if not known(w)]


def unknown_rate(text):
    words = ODIA_RE.findall(text)
    if not words:
        return 0.0
    unk = unknown_words(text)
    return len(unk) / len(words)
