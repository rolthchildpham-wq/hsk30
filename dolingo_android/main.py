"""Dolingo 1.1: offline HSK and English mobile lessons."""
import json
import os
import random
import traceback
from collections import defaultdict
from functools import partial

from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

ROOT = os.path.dirname(os.path.abspath(__file__))
HSK_PATH = os.path.join(ROOT, "data", "words_hsk30_real.json")
EN_PATH = os.path.join(ROOT, "data", "english_learner_thesaurus.json")
BG = (0.975, 0.966, 0.943, 1)
INK = (0.11, 0.19, 0.17, 1)
GREEN = (0.064, 0.24, 0.19, 1)
MINT = (0.83, 0.92, 0.85, 1)
GOLD = (0.96, 0.73, 0.36, 1)
WHITE = (1, 1, 1, 1)
MUTED = (0.44, 0.50, 0.46, 1)
FONT = "Roboto"
CJK_FONT = FONT


def select_fonts():
    global FONT, CJK_FONT
    # Android has native Vietnamese and CJK fonts. Register explicitly so Kivy
    # does not replace Chinese characters with missing-glyph boxes.
    common = [
        "/system/fonts/NotoSans-Regular.ttf",
        "/system/fonts/Roboto-Regular.ttf",
    ]
    cjk = [
        "/system/fonts/NotoSansCJK-Regular.ttc",
        "/system/fonts/NotoSansSC-Regular.otf",
        "/system/fonts/NotoSansCJKsc-Regular.otf",
        "/system/fonts/DroidSansFallback.ttf",
    ]
    for path in common:
        if os.path.isfile(path):
            try:
                LabelBase.register("DolingoText", path)
                FONT = "DolingoText"
                break
            except Exception:
                continue
    for path in cjk:
        if os.path.isfile(path):
            try:
                LabelBase.register("DolingoCJK", path)
                CJK_FONT = "DolingoCJK"
                break
            except Exception:
                continue


class Panel(BoxLayout):
    def __init__(self, color=WHITE, radius=18, **kwargs):
        super().__init__(**kwargs)
        self._shade = color
        self._radius = dp(radius)
        with self.canvas.before:
            Color(*self._shade)
            self._shape = RoundedRectangle(pos=self.pos, size=self.size,
                                            radius=[self._radius])
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_):
        self._shape.pos = self.pos
        self._shape.size = self.size


def label(text="", size=16, color=INK, bold=False, height=None,
          font=None, align="left"):
    kw = dict(text=str(text), color=color, font_size=dp(size), bold=bold,
              font_name=font or FONT, halign=align, valign="middle")
    if height is not None:
        kw.update(size_hint_y=None, height=dp(height))
    widget = Label(**kw)
    widget.bind(size=lambda inst, value: setattr(inst, "text_size",
                 (max(dp(20), value[0] - dp(4)), value[1])))
    return widget


def button(text, callback, bg=GREEN, fg=WHITE, height=50, size=15):
    widget = Button(text=text, font_name=FONT, font_size=dp(size), bold=True,
                    color=fg, background_normal="", background_down="",
                    background_color=bg, size_hint_y=None, height=dp(height))
    widget.bind(on_release=lambda *_: callback())
    return widget


def load_courses():
    groups = defaultdict(list)
    with open(HSK_PATH, "r", encoding="utf-8") as stream:
        hsk = json.load(stream)
    for item in hsk:
        group = str(item.get("level") or "").strip()
        word = str(item.get("word") or "").strip()
        if not group.startswith("HSK ") or not word:
            continue
        groups[group].append({
            "word": word,
            "reading": str(item.get("pinyin") or ""),
            "meaning": str(item.get("en") or "").strip(),
            "other": str(item.get("traditional") or "").strip(),
            "source": "HSK 3.0 - ivankra/hsk30",
            "course": "HSK"
        })
    with open(EN_PATH, "r", encoding="utf-8") as stream:
        english = json.load(stream)
    for item in english.get("entries", []):
        level = str(item.get("level") or "")
        word = str(item.get("word") or "").strip()
        meaning = str(item.get("definition") or "").strip()
        if level in ("1", "2", "3") and word and meaning:
            groups["English " + level].append({
                "word": word,
                "reading": str(item.get("pos") or ""),
                "meaning": meaning,
                "other": ", ".join(item.get("synonyms") or []),
                "source": "carryword/english-vocabulary (MIT)",
                "course": "English"
            })
    return dict(groups), len(hsk), len(english.get("entries", []))


class DolingoApp(App):
    def build(self):
        select_fonts()
        self.title = "Dolingo | Study Studio"
        self.data = {}
        self.hsk_count = 0
        self.en_count = 0
        self.mode = "learn"
        self.group = "HSK 1"
        self.deck = []
        self.index = 0
        self.correct = 0
        self.attempts = 0
        self.reveal = False
        self.progress = {}
        self._load_progress()
        self.root_panel = Panel(color=BG, radius=0, orientation="vertical")
        self.root_panel.add_widget(label("DOLINGO", 25, GREEN, True, 58, align="center"))
        self.root_panel.add_widget(label("HỌC NGOẠI NGỮ MỖI NGÀY", 12, MUTED,
                                         False, 26, align="center"))
        self.status = label("Đang chuẩn bị bài học...", 14, MUTED, height=40,
                            align="center")
        self.root_panel.add_widget(self.status)
        self.main_scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        self.root_panel.add_widget(self.main_scroll)
        self.body = BoxLayout(orientation="vertical", size_hint_y=None,
                              padding=[dp(15), dp(10), dp(15), dp(20)],
                              spacing=dp(12))
        self.body.bind(minimum_height=self.body.setter("height"))
        self.main_scroll.add_widget(self.body)
        Clock.schedule_once(self._initialize, 0.3)
        return self.root_panel

    def _load_progress(self):
        try:
            with open(os.path.join(self.user_data_dir, "progress.json"),
                      "r", encoding="utf-8") as stream:
                self.progress = json.load(stream)
        except Exception:
            self.progress = {}

    def _save_progress(self):
        try:
            os.makedirs(self.user_data_dir, exist_ok=True)
            path = os.path.join(self.user_data_dir, "progress.json")
            with open(path, "w", encoding="utf-8") as stream:
                json.dump(self.progress, stream, ensure_ascii=False)
        except Exception:
            traceback.print_exc()

    def _initialize(self, *_):
        try:
            self.data, self.hsk_count, self.en_count = load_courses()
            self.status.text = ("%s từ HSK 3.0  •  %s mục English  •  Offline" %
                                (self.hsk_count, self.en_count))
            self.change_group("HSK 1")
        except Exception as exc:
            traceback.print_exc()
            self.status.text = "Không tải được dữ liệu học"
            self.body.clear_widgets()
            self.body.add_widget(label(str(exc), 15, height=150))
            self.body.add_widget(button("Thử lại", lambda: self._initialize()))

    def _top_navigation(self):
        course = Panel(color=WHITE, radius=16, size_hint_y=None, height=dp(60),
                       padding=dp(7), spacing=dp(8))
        a = button("HSK 3.0", lambda: self.change_group("HSK 1"),
                   bg=GREEN if self.group.startswith("HSK") else MINT,
                   fg=WHITE if self.group.startswith("HSK") else GREEN, height=45)
        b = button("ENGLISH", lambda: self.change_group("English 1"),
                   bg=GREEN if self.group.startswith("English") else MINT,
                   fg=WHITE if self.group.startswith("English") else GREEN, height=45)
        course.add_widget(a)
        course.add_widget(b)
        self.body.add_widget(course)

        levels = ["HSK " + str(n) for n in range(1, 10)] if self.group.startswith("HSK") else [
            "English 1", "English 2", "English 3"]
        levels = [name for name in levels if name in self.data]
        picker = Spinner(text=self.group, values=levels, font_name=FONT,
                         font_size=dp(16), color=INK, background_normal="",
                         background_color=MINT, size_hint_y=None, height=dp(50))
        picker.bind(text=lambda _inst, name: self.change_group(name)
                    if name != self.group else None)
        self.body.add_widget(picker)

        tools = Panel(color=WHITE, radius=16, size_hint_y=None, height=dp(58),
                      padding=dp(6), spacing=dp(6))
        tools.add_widget(button("HỌC TỪ", lambda: self.change_mode("learn"),
                                bg=GREEN if self.mode=="learn" else MINT,
                                fg=WHITE if self.mode=="learn" else GREEN, height=46))
        tools.add_widget(button("LUYỆN TẬP", lambda: self.change_mode("quiz"),
                                bg=GREEN if self.mode=="quiz" else MINT,
                                fg=WHITE if self.mode=="quiz" else GREEN, height=46))
        tools.add_widget(button("TÌM TỪ", lambda: self.change_mode("search"),
                                bg=GREEN if self.mode=="search" else MINT,
                                fg=WHITE if self.mode=="search" else GREEN, height=46))
        self.body.add_widget(tools)

    def change_group(self, group):
        if group not in self.data:
            return
        self.group = group
        self.deck = list(self.data[group])
        random.shuffle(self.deck)
        self.index = 0
        self.reveal = False
        self.correct = 0
        self.attempts = 0
        self.mode = "learn"
        self.render()

    def change_mode(self, mode):
        self.mode = mode
        self.reveal = False
        self.render()

    def render(self):
        self.body.clear_widgets()
        self._top_navigation()
        if self.mode == "search":
            self.render_search()
        elif self.mode == "quiz":
            self.render_quiz()
        else:
            self.render_learn()

    def _card(self, min_height=350):
        return Panel(color=GREEN, radius=23, orientation="vertical",
                     padding=[dp(16), dp(18), dp(16), dp(18)],
                     spacing=dp(10), size_hint_y=None, height=dp(min_height))

    def render_learn(self):
        if not self.deck:
            self.body.add_widget(label("Không có dữ liệu", height=80))
            return
        item = self.deck[self.index]
        viewed = self.progress.get(self.group, 0)
        self.body.add_widget(label("BÀI HỌC CỦA BẠN", 13, MUTED, True, 28))
        self.body.add_widget(label("Đã xem %d từ  •  Từ %d / %d" %
                                   (viewed, self.index+1, len(self.deck)),
                                   14, GREEN, True, 32))
        card = self._card(385)
        card.add_widget(label("FLASHCARD  •  " + self.group, 12, GOLD, True, 32))
        card.add_widget(label(item["word"], 38 if len(item["word"]) < 14 else 27,
                              WHITE, True, 85,
                              font=CJK_FONT if item["course"]=="HSK" else FONT,
                              align="center"))
        card.add_widget(label(item["reading"], 18, GOLD, False, 45, align="center"))
        card.add_widget(label("NGHĨA / DEFINITION", 12, MINT, True, 26))
        desc = item["meaning"] or "Chưa có nghĩa được xác minh"
        card.add_widget(label(desc[:450], 15, WHITE, height=140, align="center"))
        card.add_widget(label("Nguồn: " + item["source"], 11, MINT, height=25,
                              align="center"))
        self.body.add_widget(card)
        if item["other"]:
            self.body.add_widget(label(
                ("Phồn thể: " if item["course"]=="HSK" else "Đồng nghĩa: ") +
                item["other"][:120], 14, MUTED, height=52,
                font=CJK_FONT if item["course"]=="HSK" else FONT))
        controls = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(9))
        controls.add_widget(button("TRỘN LẠI", self.shuffle, bg=MINT, fg=GREEN))
        controls.add_widget(button("TỪ TIẾP  →", self.next_word, bg=GREEN))
        self.body.add_widget(controls)
        self.body.add_widget(label("Luyện tập để kiểm tra mức độ ghi nhớ.", 13,
                                   MUTED, height=34, align="center"))

    def shuffle(self):
        random.shuffle(self.deck)
        self.index = 0
        self.render()

    def next_word(self):
        self.index = (self.index + 1) % len(self.deck)
        self.progress[self.group] = self.progress.get(self.group, 0) + 1
        self._save_progress()
        self.render()

    def render_quiz(self):
        if len(self.deck) < 4:
            self.body.add_widget(label("Chưa đủ dữ liệu luyện tập", height=80))
            return
        item = self.deck[self.index]
        self.body.add_widget(label("THỬ THÁCH KIẾN THỨC", 13, MUTED, True, 30))
        self.body.add_widget(label("Đúng: %d / %d" % (self.correct, self.attempts),
                                   15, GREEN, True, 34))
        card = self._card(220)
        card.add_widget(label("CHỌN NGHĨA ĐÚNG CHO TỪ", 12, GOLD, True, 32,
                              align="center"))
        card.add_widget(label(item["word"], 34, WHITE, True, 95,
                              font=CJK_FONT if item["course"]=="HSK" else FONT,
                              align="center"))
        card.add_widget(label(item["reading"], 17, MINT, height=40, align="center"))
        self.body.add_widget(card)
        options = [item]
        others = [r for r in self.deck if r["word"]!=item["word"] and r["meaning"]]
        random.shuffle(others)
        options.extend(others[:3])
        random.shuffle(options)
        for opt in options:
            self.body.add_widget(button(opt["meaning"][:110] or "Chưa có nghĩa",
                                        partial(self.answer, opt is item),
                                        bg=WHITE, fg=INK, height=70, size=14))

    def answer(self, is_correct):
        self.attempts += 1
        if is_correct:
            self.correct += 1
            self.status.text = "Chính xác! +1 điểm  •  " + self.group
        else:
            self.status.text = "Cố gắng nhé! Câu tiếp theo  •  " + self.group
        self.index = (self.index + 1) % len(self.deck)
        self.render()

    def render_search(self):
        self.body.add_widget(label("TRA CỨU TỪ VỰNG", 16, GREEN, True, 45))
        search = TextInput(hint_text="Nhập từ hoặc phiên âm...", multiline=False,
                           font_name=CJK_FONT, font_size=dp(18),
                           size_hint_y=None, height=dp(54))
        self.body.add_widget(search)
        results = BoxLayout(orientation="vertical", spacing=dp(8),
                            size_hint_y=None)
        results.bind(minimum_height=results.setter("height"))
        self.body.add_widget(results)

        def search_now(*_):
            results.clear_widgets()
            query = search.text.strip().lower()
            if not query:
                results.add_widget(label("Nhập từ để tìm trong " + self.group,
                                         height=60))
                return
            matches = [r for r in self.data.get(self.group, [])
                       if query in r["word"].lower() or
                       query in r["reading"].lower()]
            if not matches:
                results.add_widget(label("Không tìm thấy từ phù hợp.", height=60))
            for item in matches[:30]:
                panel = Panel(color=WHITE, radius=12, orientation="vertical",
                              size_hint_y=None, height=dp(100),
                              padding=dp(8), spacing=dp(4))
                panel.add_widget(label(item["word"]+"  "+item["reading"], 19, GREEN,
                                       True, 35, font=CJK_FONT))
                panel.add_widget(label((item["meaning"] or "Chưa có nghĩa")[:100],
                                       13, MUTED, height=48))
                results.add_widget(panel)
        search.bind(on_text_validate=search_now)
        self.body.add_widget(button("TÌM KIẾM", search_now, bg=GREEN))


if __name__ == "__main__":
    DolingoApp().run()
