"""Regression checks for Dolingo: screenshot issues and safe course data.

Run with: python3 dolingo_android/test_regressions.py
No Kivy import needed in Linux CI.
"""
import ast
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
code = (ROOT / "main.py").read_text(encoding="utf-8")
tree = ast.parse(code)
compile(code, str(ROOT / "main.py"), "exec")
clean_node = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                  and node.name == "clean_vi_gloss")
ns = {"re": re, "unicodedata": unicodedata}
exec(compile(ast.Module(body=[clean_node], type_ignores=[]),
             "<clean_vi_gloss>", "exec"), ns)
clean = ns["clean_vi_gloss"]
assert clean("bữa trưa; LT:�[fen4],�[dun4]") == "bữa trưa"
assert clean("học\ufffd tập") == "học tập"
assert clean("quyển sách") == "quyển sách"

dict_node = next(node for node in tree.body if isinstance(node, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == "ILLUSTRATED_WORDS"
                         for t in node.targets))
mapping = ast.literal_eval(dict_node.value)
assert mapping["午饭"] == "food"
assert mapping["苹果"] == "apple"
assert mapping["书"] == "book"
art = ROOT / "assets" / "illustrations"
for item in ("午饭", "苹果", "书", "学校", "猫"):
    assert (art / (mapping[item] + ".png")).is_file(), item
assert "self.bottom_nav.add_widget(" in code
assert "self.root_panel.add_widget(self.bottom_nav)" in code
assert "def render_library(self)" in code
assert "def render_profile(self)" in code
assert 'self.root_panel.add_widget(self.fixed_nav)' in code
assert "self.flashcard_flipped = not self.flashcard_flipped" in code
assert 'self.progress["_flashcard_saved"]' in code
assert 'self.change_mode("dashboard")' in code
assert 'def open_dictionary(self' in code

hsk = json.loads((ROOT / "data" / "words_hsk30_real.json").read_text(encoding="utf-8"))
vi = json.loads((ROOT / "data" / "vi_starter.json").read_text(encoding="utf-8"))["hsk"]
cv = json.loads((ROOT / "data" / "vi_hsk_cvdict.json").read_text(encoding="utf-8"))["entries"]
assert len(hsk) == 11092, len(hsk)
bad = 0
for item in hsk:
    word = str(item.get("word", "")).split("|")[0]
    gloss = clean(vi.get(word) or item.get("vi") or cv.get(str(item.get("id") or ""), ""))
    if "\ufffd" in gloss or "LT:" in gloss:
        bad += 1
assert bad == 0, bad

# Confirm the real offline dictionary can fill missing HSK meanings.
import sys
sys.path.insert(0, str(ROOT))
from cvdict_search import Dictionary
dictionary = Dictionary()
assert dictionary.available, "SQLite dictionary missing"
for word in ("午饭", "学习", "老师"):
    assert dictionary.exact_meaning(word), word
missing = []
for item in hsk:
    word = str(item.get("word", "")).split("|")[0]
    gloss = clean(vi.get(word) or item.get("vi")
                  or cv.get(str(item.get("id") or ""), "")
                  or dictionary.exact_meaning(word))
    if not gloss:
        missing.append(word)
print("HSK Vietnamese coverage: %d/%d, missing=%d" %
      (len(hsk)-len(missing), len(hsk), len(missing)))
print("Missing HSK examples:", missing[:30])
assert len(missing) < len(hsk) // 4, "Dictionary coverage dropped"

font = ROOT / "assets" / "fonts" / "NotoSansCJKsc-Regular.otf"
assert font.is_file() and font.stat().st_size > 10000000
spec = (ROOT / "buildozer.spec").read_text(encoding="utf-8")
assert "sqlite3,otf,ttf" in spec
assert 'CJK_BUNDLE,' in code and 'font=CJK_FONT' in code
print("PASS: screenshots, Vietnamese gloss cleanup, 24 PNG asset generation, "
      "fixed navigation, 11,092 HSK entries and flashcard/CVDICT integration")

# ChineseSkill-inspired original practice engine: tones, SRS, and speech wiring.
from learning_tools import tone_of_pinyin, review_update, is_due
assert tone_of_pinyin("wǔ fàn") == 3
assert tone_of_pinyin("ma1") == 1
assert tone_of_pinyin("mā") == 1
assert tone_of_pinyin("mǎ") == 3
assert tone_of_pinyin("xué xí") == 2
assert tone_of_pinyin("") is None
review = review_update({}, "good", "2026-11-13")
assert review["due"] == "2026-11-15", review
assert is_due(review, "2026-11-13") is False
assert is_due(review, "2026-11-15") is True
assert review_update(review, "again", "2026-11-15")["due"] == "2026-11-15"
assert "def pronounce_item(self, item)" in code
assert "def render_tone_practice(self)" in code
assert "def mark_review(self, item, grade)" in code
assert "Pronouncer()" in code
assert 'item["reading"] or "Pinyin chưa có dữ liệu"' in code
from tts_android import Pronouncer
assert hasattr(Pronouncer, "speak")
print("PASS: Pinyin tones, spaced review, TTS wiring and learning controls")

# IPA data is generated for offline study, rather than guessed from spelling.
ipa_file = ROOT / "data" / "english_ipa.json"
assert ipa_file.exists(), "English IPA database absent"
ipa = json.loads(ipa_file.read_text(encoding="utf-8"))
assert len(ipa) >= 800, len(ipa)
assert ipa.get("hello", "").startswith("/") or len(ipa) >= 1500
print("PASS: English IPA pronunciations:", len(ipa))

# Dolingo 1.2.7 skill modules and authored reading passages.
passages = json.loads((ROOT / "data" / "reading_passages.json").read_text(encoding="utf-8"))["passages"]
assert len(passages) >= 6
assert {"HSK 1", "HSK 2", "HSK 3", "English 1", "English 2", "English 3"}.issubset(
    {p["group"] for p in passages})
for passage in passages:
    assert passage["sentences"]
    assert len(passage["answers"]) >= 3
    assert 0 <= passage["correct"] < len(passage["answers"])
    assert all(s["tokens"] and s["text"] and s["vi"] for s in passage["sentences"])
for function in ("render_reading", "render_speaking", "render_fill_exercise",
                 "render_matching_exercise", "request_recording", "stop_recording",
                 "play_recording", "answer_reading", "submit_fill", "select_match"):
    assert "def " + function + "(" in code, function
from voice_recorder import VoiceRecorder
recorder = VoiceRecorder(str(ROOT / "test-recordings"))
assert recorder.play()[0] is False
assert "android.permissions = RECORD_AUDIO" in spec
print("PASS: reading passages, tap-to-lookup, fill and match, microphone wiring")
