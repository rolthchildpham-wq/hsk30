"""Dolingo diagnostic-safe Android entry point. Loads large dictionaries on demand."""
import json
import os
import random
import traceback
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner

HERE = os.path.dirname(os.path.abspath(__file__))
HSK_FILE = os.path.join(HERE, "data", "words_hsk30_real.json")
EN_FILE = os.path.join(HERE, "data", "english_learner_thesaurus.json")


class DolingoApp(App):
    def build(self):
        self.title = "Dolingo HSK English - diagnostic 1.0.2"
        self.deck = []
        self.position = 0
        self.groups = {}
        self.root_box = BoxLayout(orientation="vertical", padding=dp(12),
                                  spacing=dp(10))
        self.root_box.add_widget(Label(
            text="Dolingo 1.0.2 | KIEM TRA KHOI DONG",
            font_size="20sp", size_hint_y=None, height=dp(48)))
        self.status = Label(text="Ung dung da mo. Bam 'Tai du lieu' de bat dau.",
                            font_size="16sp", halign="center",
                            size_hint_y=None, height=dp(74))
        self.status.bind(size=self._wrap)
        self.root_box.add_widget(self.status)
        self.level = Spinner(text="HSK 1", values=["HSK 1"], 
                             size_hint_y=None, height=dp(54))
        self.root_box.add_widget(self.level)
        self.word = Label(text="DOLINGO", font_size="35sp", bold=True)
        self.word.bind(size=self._wrap)
        self.root_box.add_widget(self.word)
        self.meaning = Label(text="Du lieu chua duoc tai", font_size="17sp",
                             halign="center", valign="middle")
        self.meaning.bind(size=self._wrap)
        self.root_box.add_widget(self.meaning)
        actions = BoxLayout(size_hint_y=None, height=dp(58), spacing=dp(8))
        load = Button(text="Tai du lieu")
        load.bind(on_release=lambda *_: self.load_safe())
        next_item = Button(text="Tu tiep")
        next_item.bind(on_release=lambda *_: self.next_safe())
        actions.add_widget(load)
        actions.add_widget(next_item)
        self.root_box.add_widget(actions)
        self.level.bind(text=lambda *_: self.select_safe())
        return self.root_box

    @staticmethod
    def _wrap(widget, size):
        widget.text_size = (max(dp(30), size[0] - dp(16)), size[1])

    def on_start(self):
        # Give Android/Kivy a chance to draw the first frame before heavy JSON IO.
        Clock.schedule_once(lambda dt: self._set_ready(), 0.3)

    def _set_ready(self):
        self.status.text = "Khoi dong OK. Bam 'Tai du lieu'."

    def _report(self, stage, error):
        details = "%s: %s" % (stage, error)
        self.status.text = "CO LOI: " + details[:140]
        self.meaning.text = details[:800]
        traceback.print_exc()
        try:
            os.makedirs(self.user_data_dir, exist_ok=True)
            with open(os.path.join(self.user_data_dir, "dolingo_error.txt"), "a",
                      encoding="utf-8") as out:
                out.write(stage + "\n" + traceback.format_exc() + "\n")
        except Exception:
            pass

    def load_safe(self):
        try:
            self.status.text = "Dang tai du lieu..."
            groups = {}
            with open(HSK_FILE, "r", encoding="utf-8") as source:
                hsk = json.load(source)
            if not isinstance(hsk, list):
                raise ValueError("Invalid HSK JSON")
            for r in hsk:
                key = str(r.get("level") or "").strip()
                w = str(r.get("word") or "").strip()
                if key.startswith("HSK ") and w:
                    groups.setdefault(key, []).append({
                        "word": w,
                        "pronounce": str(r.get("pinyin") or ""),
                        "meaning": str(r.get("en") or "Nghia tieng Anh dang bo sung"),
                    })
            with open(EN_FILE, "r", encoding="utf-8") as source:
                eng = json.load(source)
            for r in eng.get("entries", []):
                w = str(r.get("word") or "").strip()
                definition = str(r.get("definition") or "").strip()
                level = str(r.get("level") or "").strip()
                if w and definition and level in ("1", "2", "3"):
                    groups.setdefault("English " + level, []).append({
                        "word": w,
                        "pronounce": str(r.get("pos") or ""),
                        "meaning": definition,
                    })
            if not groups:
                raise ValueError("No learning words loaded")
            self.groups = groups
            names = sorted(groups, key=lambda x: (not x.startswith("HSK "), x))
            self.level.values = names
            self.level.text = names[0]
            self.select_safe()
            self.status.text = "Da tai %d muc HSK + %d muc English" % (
                len(hsk), len(eng.get("entries", [])))
        except Exception as exc:
            self._report("LOAD", exc)

    def select_safe(self):
        try:
            self.deck = list(self.groups.get(self.level.text, []))
            random.shuffle(self.deck)
            self.position = 0
            self.show_safe()
        except Exception as exc:
            self._report("SELECT", exc)

    def show_safe(self):
        try:
            if not self.deck:
                self.word.text = "Chua co du lieu"
                self.meaning.text = "Bam 'Tai du lieu' de bat dau."
                return
            row = self.deck[self.position]
            self.word.text = row["word"]
            self.meaning.text = row["pronounce"] + "\n\n" + row["meaning"]
        except Exception as exc:
            self._report("DISPLAY", exc)

    def next_safe(self):
        if self.deck:
            self.position = (self.position + 1) % len(self.deck)
        self.show_safe()


if __name__ == "__main__":
    DolingoApp().run()
