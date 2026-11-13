"""Offline-friendly learning helpers inspired by common language-learning patterns.

Original implementation; no ChineseSkill assets or lesson content.
"""
import re
import unicodedata
from datetime import date, timedelta

TONE_MARKS = {
    "ā":1,"á":2,"ǎ":3,"à":4,"ē":1,"é":2,"ě":3,"è":4,
    "ī":1,"í":2,"ǐ":3,"ì":4,"ō":1,"ó":2,"ǒ":3,"ò":4,
    "ū":1,"ú":2,"ǔ":3,"ù":4,"ǖ":1,"ǘ":2,"ǚ":3,"ǜ":4,
}
def tone_of_pinyin(reading):
    """First marked/numeric pinyin syllable's tone, or None if ambiguous."""
    text = str(reading or "").strip().lower()
    syllables = re.split(r"[^a-züāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ0-9]+", text)
    for syllable in syllables:
        if not syllable:
            continue
        marked = next((TONE_MARKS[c] for c in syllable if c in TONE_MARKS), None)
        if marked:
            return marked
        digit = re.search(r"[1-5]$", syllable)
        if digit:
            return int(digit.group()) if digit.group() != "5" else 5
    return None

def review_update(old, grade, today=None):
    """Simple transparent spaced-review scheduling, not proprietary SRS."""
    today = date.fromisoformat(today) if isinstance(today, str) else (today or date.today())
    old = old or {}
    interval = max(0, int(old.get("interval", 0)))
    if grade == "again":
        interval = 0
        due = today
    elif grade == "hard":
        interval = max(1, interval + 1)
        due = today + timedelta(days=interval)
    elif grade == "good":
        interval = max(1, 2 if interval == 0 else round(interval * 2.2))
        due = today + timedelta(days=interval)
    else:
        raise ValueError("Unknown review grade")
    return {"interval":interval, "due":due.isoformat(), "last":today.isoformat()}

def is_due(item, today=None):
    due = (item or {}).get("due", "")
    if not due:
        return True
    return due <= (today or date.today()).isoformat()
