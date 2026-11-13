import json
import os
import random
import traceback

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner

ROOT = os.path.dirname(os.path.abspath(__file__))
HSK_PATH = os.path.join(ROOT, "data", "words_hsk30_real.json")
ENGLISH_PATH = os.path.join(ROOT, "data", "english_learner_thesaurus.json")


def read_json(path):
    with open(path, "r", encoding="utf-8") as stream:
        return json.load(stream)


class DolingoApp(App):
    def build(self):
        self.title = "Dolingo HSK & English"
        self.by_course = {}
        self.current = []
        self.index = 0
        self.failure = ""
        self.load_data()
        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(9))
        root.add_widget(Label(text="DOLINGO | HSK 3.0 + ENGLISH", font_size="21sp",
                              size_hint_y=None, height=dp(50), bold=True))
        self.level = Spinner(text="HSK 1", values=sorted(self.by_course),
                             size_hint_y=None, height=dp(52))
        root.add_widget(self.level)
        self.counter = Label(text="", font_size="16sp", size_hint_y=None, height=dp(35))
        root.add_widget(self.counter)
        self.headword = Label(text="", font_size="36sp", bold=True, halign="center",
                              size_hint_y=None, height=dp(110))
        root.add_widget(self.headword)
        self.pronunciation = Label(text="", font_size="20sp", size_hint_y=None,
                                   height=dp(52))
        root.add_widget(self.pronunciation)
        self.definition = Label(text="", font_size="17sp", halign="center",
                                valign="middle")
        self.definition.bind(size=lambda obj, size: setattr(obj, "text_size",
                             (max(10, size[0] - dp(16)), size[1])))
        root.add_widget(self.definition)
        control = BoxLayout(size_hint_y=None, height=dp(58), spacing=dp(8))
        shuffle = Button(text="Trộn")
        shuffle.bind(on_release=lambda *_: self.reset_deck())
        next_btn = Button(text="Tiếp theo")
        next_btn.bind(on_release=lambda *_: self.next_word())
        control.add_widget(shuffle)
        control.add_widget(next_btn)
        root.add_widget(control)
        self.level.bind(text=lambda *_: self.reset_deck())
        self.reset_deck()
        return root

    def load_data(self):
        try:
            records = read_json(HSK_PATH)
            if not isinstance(records, list):
                raise ValueError("HSK data must be a list")
            for row in records:
                level = str(row.get("level", "")).strip()
                word = str(row.get("word", "")).strip()
                if not level.startswith("HSK ") or not word:
                    continue
                self.by_course.setdefault(level, []).append({
                    "word": word,
                    "pronunciation": str(row.get("pinyin") or ""),
                    "definition": str(row.get("en") or "English meaning pending review"),
                    "secondary": "Phồn thể: " + str(row.get("traditional") or "-"),
                })
        except Exception as exc:
            self.failure += "HSK: " + str(exc) + "\n"
            traceback.print_exc()

        try:
            data = read_json(ENGLISH_PATH)
            for row in data.get("entries", []):
                word = str(row.get("word") or "").strip()
                definition = str(row.get("definition") or "").strip()
                level = str(row.get("level") or "").strip()
                if not word or not definition or level not in ("1", "2", "3"):
                    continue
                self.by_course.setdefault("English " + level, []).append({
                    "word": word,
                    "pronunciation": str(row.get("pos") or ""),
                    "definition": definition,
                    "secondary": "Synonyms: " + ", ".join(row.get("synonyms") or []),
                })
        except Exception as exc:
            self.failure += "English: " + str(exc) + "\n"
            traceback.print_exc()

    def reset_deck(self):
        self.current = list(self.by_course.get(self.level.text, []))
        random.shuffle(self.current)
        self.index = 0
        self.show_word()

    def show_word(self):
        if not self.current:
            self.headword.text = "Chưa tải được dữ liệu"
            self.pronunciation.text = ""
            self.definition.text = self.failure or "Không có mục từ trong cấp độ này."
            self.counter.text = ""
            return
        record = self.current[self.index]
        self.headword.text = record["word"]
        self.pronunciation.text = record["pronunciation"]
        self.definition.text = record["definition"] + "\n\n" + record["secondary"]
        self.counter.text = "%s: %d / %d" % (self.level.text, self.index + 1,
                                               len(self.current))

    def next_word(self):
        if self.current:
            self.index = (self.index + 1) % len(self.current)
            self.show_word()


if __name__ == "__main__":
    try:
        DolingoApp().run()
    except Exception:
        traceback.print_exc()
        raise
