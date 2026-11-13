import csv
import os
import random
from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "hsk30.csv")

class DolingoApp(App):
    def build(self):
        self.title = "Dolingo HSK 3.0"
        self.by_level = {}
        with open(DATA_FILE, "r", encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                level = row.get("Level", "").strip()
                if level in ("7", "8", "9"):
                    level = "7-9"
                if not level:
                    continue
                word = row.get("Simplified", "").strip()
                if word:
                    self.by_level.setdefault(level, []).append(row)
        self.current = []
        self.index = 0
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        title = Label(text="Dolingo | HSK 3.0", font_size="24sp",
                      size_hint_y=None, height=dp(54), bold=True)
        root.add_widget(title)
        self.level = Spinner(text="HSK 1", values=["HSK " + x for x in sorted(self.by_level)],
                             size_hint_y=None, height=dp(52))
        self.level.bind(text=self.start)
        root.add_widget(self.level)
        self.counter = Label(text="", size_hint_y=None, height=dp(34))
        root.add_widget(self.counter)
        self.hanzi = Label(text="", font_size="42sp", bold=True, halign="center",
                           size_hint_y=None, height=dp(100))
        root.add_widget(self.hanzi)
        self.pinyin = Label(text="", font_size="22sp", halign="center",
                            size_hint_y=None, height=dp(60))
        root.add_widget(self.pinyin)
        self.extra = Label(text="", font_size="16sp", halign="center",
                          valign="top", size_hint_y=1)
        self.extra.bind(size=lambda inst, size: setattr(inst, "text_size", (size[0], None)))
        root.add_widget(self.extra)
        controls = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(10))
        next_button = Button(text="Từ tiếp theo")
        next_button.bind(on_press=self.next_word)
        shuffle_button = Button(text="Trộn lại")
        shuffle_button.bind(on_press=self.start)
        controls.add_widget(shuffle_button)
        controls.add_widget(next_button)
        root.add_widget(controls)
        self.start()
        return root

    def start(self, *_):
        level = self.level.text.replace("HSK ", "")
        self.current = list(self.by_level.get(level, []))
        random.shuffle(self.current)
        self.index = 0
        self.show_word()

    def show_word(self):
        if not self.current:
            self.hanzi.text = "Không có từ vựng"
            self.pinyin.text = ""
            self.extra.text = ""
            self.counter.text = ""
            return
        row = self.current[self.index]
        self.hanzi.text = row.get("Simplified", "")
        self.pinyin.text = row.get("Pinyin", "")
        self.extra.text = "Loại từ: " + (row.get("POS") or "—") + "\n\n" + "Từ phồn thể: " + (row.get("Traditional") or "—")
        self.counter.text = "Từ %d / %d" % (self.index + 1, len(self.current))

    def next_word(self, *_):
        if self.current:
            self.index = (self.index + 1) % len(self.current)
            self.show_word()

if __name__ == "__main__":
    DolingoApp().run()
