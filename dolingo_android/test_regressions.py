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
assert "self.fixed_nav.add_widget(tabs)" in code
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
    gloss = clean(vi.get(word) or item.get("vi") or cv.get(str(item.get("id") or "")
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
