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
from kivy.graphics import Color, RoundedRectangle, Ellipse, Rectangle, Line, Triangle
from kivy.uix.widget import Widget
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
VI_PATH = os.path.join(ROOT, "data", "vi_starter.json")
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



# Draw simple, offline, word-specific pictures using Kivy shapes.
# Only supported concepts receive artwork; never show unrelated stock imagery.
ICON_WORDS = {
    "sun": "日 太阳 sun sunshine 阳光",
    "home": "家 房子 房间 house home 家里 回家",
    "book": "书 读 读书 课本 书店 book read study learn school 学校",
    "tree": "树 木 tree forest 林",
    "flower": "花 flower",
    "cup": "茶 水 牛奶 杯子 杯 喝 drink water tea milk coffee",
    "phone": "电话 手机 打电话 phone telephone mobile",
    "car": "车 汽车 打车 开车 car bus taxi",
    "plane": "飞机 机场 机票 plane airplane airport travel",
    "food": "饭 吃 吃饭 米饭 面包 包子 菜 食物 food eat bread",
    "heart": "爱 喜欢 爱好 love heart",
    "cloud": "云 天气 雨 cloud rain weather",
    "clock": "时间 时 点 今天 明天 yesterday today time",
    "computer": "电脑 computer laptop"
}
ICON_BY_WORD = {}
for _kind, _words in ICON_WORDS.items():
    for _word in _words.split():
        ICON_BY_WORD[_word] = _kind


class Picture(Widget):
    def __init__(self, kind, **kwargs):
        super().__init__(**kwargs)
        self.kind = kind
        self.bind(pos=self._paint, size=self._paint)
        Clock.schedule_once(self._paint, 0)

    def _paint(self, *_):
        self.canvas.clear()
        x, y = self.pos
        w, h = self.size
        cx, cy = x+w/2, y+h/2
        unit = min(w, h)/100.0
        def circle(px, py, r, shade):
            Color(*shade)
            Ellipse(pos=(cx+(px-r)*unit,cy+(py-r)*unit),
                    size=(2*r*unit,2*r*unit))
        def rect(px,py,rw,rh,shade):
            Color(*shade)
            Rectangle(pos=(cx+px*unit,cy+py*unit),
                      size=(rw*unit,rh*unit))
        def poly(points,shade):
            Color(*shade)
            Triangle(points=[v*unit+(cx if i%2==0 else cy)
                             for i,v in enumerate(points)])
        dark=(0.11,0.31,0.24,1); gold=(0.99,0.73,0.31,1)
        pink=(0.94,0.42,0.43,1); sky=(0.40,0.75,0.92,1)
        white=(1,1,1,1)
        with self.canvas:
            if self.kind=="sun":
                circle(0,0,25,gold)
                Color(*gold)
                for i in range(12):
                    import math
                    ang=i*math.pi/6
                    ax,ay=math.cos(ang),math.sin(ang)
                    Line(points=[cx+ax*30*unit,cy+ay*30*unit,
                                 cx+ax*39*unit,cy+ay*39*unit],width=dp(3))
            elif self.kind=="home":
                rect(-29,-28,58,48,MINT)
                poly([-35,14, 0,43, 35,14],gold)
                rect(-7,-28,14,30,dark)
                rect(-24,-3,12,12,sky)
                rect(12,-3,12,12,sky)
            elif self.kind=="book":
                rect(-35,-26,32,53,white)
                rect(3,-26,32,53,white)
                rect(-2,-26,4,54,gold)
                Color(*dark)
                for yy in [-10,0,10]:
                    Line(points=[cx-29*unit,cy+yy*unit,cx-9*unit,cy+yy*unit],width=dp(2))
                    Line(points=[cx+9*unit,cy+yy*unit,cx+29*unit,cy+yy*unit],width=dp(2))
            elif self.kind=="tree":
                rect(-6,-34,12,40,(0.49,0.31,0.18,1))
                circle(-15,13,23,MINT);circle(17,12,22,(0.27,0.67,0.48,1))
                circle(0,28,24,(0.17,0.53,0.35,1))
            elif self.kind=="flower":
                rect(-3,-37,6,47,dark)
                for px,py in [(-20,10),(20,10),(0,-8),(0,28)]:
                    circle(px,py,15,pink)
                circle(0,10,12,gold)
                poly([-2,-10,-20,-23,-4,-21],MINT)
            elif self.kind=="cup":
                rect(-24,-23,46,36,white)
                rect(-27,13,51,5,gold)
                Color(*gold)
                Line(circle=(cx+22*unit,cy-4*unit,16*unit,270,90),width=dp(4))
                for px in [-10,0,10]:
                    Color(*white)
                    Line(points=[cx+px*unit,cy+23*unit,cx+(px-5)*unit,cy+37*unit],
                         width=dp(2))
            elif self.kind=="phone":
                rect(-20,-39,40,79,white)
                rect(-15,-26,30,55,sky)
                circle(0,-33,3,dark)
            elif self.kind=="car":
                rect(-33,-17,66,29,gold)
                poly([-20,12,-8,28,17,28],sky)
                poly([-20,12,17,28,26,12],sky)
                circle(-21,-20,11,dark);circle(21,-20,11,dark)
                circle(-21,-20,4,white);circle(21,-20,4,white)
            elif self.kind=="plane":
                poly([-39,-5,41,4,-39,13],white)
                poly([-5,3,-23,34,22,3],sky)
                poly([-5,1,-23,-28,22,1],sky)
            elif self.kind=="food":
                circle(0,-3,34,white)
                circle(0,-3,26,gold)
                circle(-10,4,10,pink)
                circle(11,-7,10,MINT)
            elif self.kind=="heart":
                circle(-14,12,20,pink);circle(14,12,20,pink)
                poly([-33,8,33,8,0,-39],pink)
            elif self.kind=="cloud":
                circle(-22,0,16,white);circle(-1,12,24,white)
                circle(22,0,18,white);rect(-27,-16,53,22,white)
            elif self.kind=="clock":
                circle(0,0,36,white)
                circle(0,0,31,MINT)
                Color(*dark)
                Line(points=[cx,cy,cx,cy+21*unit],width=dp(3))
                Line(points=[cx,cy,cx+16*unit,cy-8*unit],width=dp(3))
            elif self.kind=="computer":
                rect(-40,-22,80,55,dark)
                rect(-35,-17,70,45,sky)
                rect(-5,-34,10,12,white)
                rect(-24,-37,48,5,white)


def load_courses():
    groups = defaultdict(list)
    with open(VI_PATH, "r", encoding="utf-8") as stream:
        vi = json.load(stream)
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
            "vi": str(item.get("vi") or vi["hsk"].get(word.split("|")[0], "")).strip(),
            "picture": ICON_BY_WORD.get(word.split("|")[0], ""),
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
                "vi": str(vi["english"].get(word.lower(), "")).strip(),
                "picture": ICON_BY_WORD.get(word.lower(), ""),
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
        self.xp = int(self.progress.get("_xp", 0))
        self.streak = int(self.progress.get("_streak", 0))
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
        self.body.add_widget(label("XP: %d     •     Chuỗi đúng: %d" % (self.xp, self.streak), 14, GREEN, True, 32))
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
        card = self._card(630 if item["picture"] else 485)
        card.add_widget(label("FLASHCARD  •  " + self.group, 12, GOLD, True, 29))
        if item["picture"]:
            picture_bg = Panel(color=(0.15, 0.37, 0.29, 1), radius=16,
                               size_hint_y=None, height=dp(125), padding=dp(5))
            picture_bg.add_widget(Picture(item["picture"]))
            card.add_widget(picture_bg)
        card.add_widget(label(item["word"], 36 if len(item["word"]) < 14 else 26,
                              WHITE, True, 65,
                              font=CJK_FONT if item["course"]=="HSK" else FONT,
                              align="center"))
        card.add_widget(label(item["reading"], 17, GOLD, False, 32, align="center"))
        card.add_widget(label("NGHĨA TIẾNG VIỆT", 12, MINT, True, 24))
        card.add_widget(label(item["vi"] or "Chưa có bản dịch tiếng Việt",
                              18, WHITE, True, 54, align="center"))
        card.add_widget(label("ENGLISH DEFINITION", 11, MINT, True, 22))
        desc = item["meaning"] or "English meaning pending review"
        card.add_widget(label(desc[:330], 13, WHITE, height=105, align="center"))
        card.add_widget(label("Nguồn: " + item["source"], 10, MINT, height=21,
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
        if not self.deck[self.index]["meaning"]:
            valid = [r for r in self.deck if r["meaning"]]
            if len(valid) < 4:
                self.body.add_widget(label("Chưa đủ nghĩa để luyện tập.", height=80))
                return
            self.deck = valid
            self.index = 0
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
            self.body.add_widget(button((opt["vi"] or opt["meaning"])[:110] or "Chưa có nghĩa",
                                        partial(self.answer, opt is item),
                                        bg=WHITE, fg=INK, height=70, size=14))

    def answer(self, is_correct):
        self.attempts += 1
        if is_correct:
            self.correct += 1
            self.xp += 10
            self.streak += 1
            self.status.text = "Chính xác! +1 điểm  •  " + self.group
        else:
            self.streak = 0
            self.status.text = "Cố gắng nhé! Câu tiếp theo  •  " + self.group
        self.progress["_xp"] = self.xp
        self.progress["_streak"] = self.streak
        self._save_progress()
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
                panel.add_widget(label((item["vi"] or item["meaning"] or "Chưa có nghĩa")[:100],
                                       13, MUTED, height=48))
                results.add_widget(panel)
        search.bind(on_text_validate=search_now)
        self.body.add_widget(button("TÌM KIẾM", search_now, bg=GREEN))


if __name__ == "__main__":
    DolingoApp().run()
