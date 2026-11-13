"""Dolingo 1.2.1: pastel study dashboard, flashcards and CVDICT offline."""
import json
import os
import random
import re
import unicodedata
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
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from cvdict_search import Dictionary

ROOT = os.path.dirname(os.path.abspath(__file__))
HSK_PATH = os.path.join(ROOT, "data", "words_hsk30_real.json")
EN_PATH = os.path.join(ROOT, "data", "english_learner_thesaurus.json")
VI_PATH = os.path.join(ROOT, "data", "vi_starter.json")
CVDICT_PATH = os.path.join(ROOT, "data", "vi_hsk_cvdict.json")
ILLUSTRATION_DIR = os.path.join(ROOT, "assets", "illustrations")
BG = (0.974, 0.980, 0.996, 1)
INK = (0.16, 0.20, 0.29, 1)
GREEN = (0.10, 0.36, 0.32, 1)  # Deep teal for legible labels
ACCENT = (0.27, 0.65, 0.53, 1)
MINT = (0.86, 0.96, 0.91, 1)
GOLD = (1.00, 0.84, 0.52, 1)
WHITE = (1, 1, 1, 1)
MUTED = (0.39, 0.44, 0.52, 1)
PINK = (1.00, 0.88, 0.92, 1)
LAVENDER = (0.92, 0.90, 0.99, 1)
SKY = (0.85, 0.93, 1.00, 1)
PEACH = (1.00, 0.92, 0.85, 1)
LEMON = (1.00, 0.96, 0.80, 1)
FONT = "Roboto"
CJK_FONT = FONT
CJK_BUNDLE = os.path.join(ROOT, "assets", "fonts", "NotoSansCJKsc-Regular.otf")


def select_fonts():
    global FONT, CJK_FONT
    # Use bundled CJK OTF first; Android .ttc often fails with SDL2/Kivy.
    # Keep Vietnamese text separate, rendered with a Latin font.
    common = [
        "/system/fonts/NotoSans-Regular.ttf",
        "/system/fonts/Roboto-Regular.ttf",
    ]
    cjk = [
        CJK_BUNDLE,
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
# Explicit word-to-image mapping avoids unrelated illustrations.
# PNG assets are generated during the APK build and included offline.
ILLUSTRATED_WORDS = {
    "午饭": "food", "午餐": "food", "吃饭": "food", "饭": "food",
    "早饭": "breakfast", "早餐": "breakfast", "晚饭": "dinner", "晚餐": "dinner",
    "米饭": "rice", "苹果": "apple", "apple": "apple",
    "书": "book", "书本": "book", "读书": "book", "book": "book",
    "家": "home", "房子": "home", "home": "home", "house": "home",
    "学校": "school", "school": "school",
    "老师": "teacher", "teacher": "teacher",
    "太阳": "sun", "sun": "sun", "月亮": "moon", "moon": "moon",
    "花": "flower", "flower": "flower", "树": "tree", "tree": "tree",
    "水": "water", "water": "water", "茶": "cup", "杯子": "cup", "tea": "cup",
    "汽车": "car", "车": "car", "car": "car", "飞机": "plane", "plane": "plane",
    "手机": "phone", "电话": "phone", "phone": "phone",
    "时间": "clock", "钟": "clock", "clock": "clock",
    "爱": "heart", "love": "heart",
    "云": "cloud", "cloud": "cloud", "电脑": "computer", "computer": "computer",
    "猫": "cat", "cat": "cat", "狗": "dog", "dog": "dog",
    "人": "person", "朋友": "person", "person": "person",
}

def clean_vi_gloss(value):
    """Remove CVDICT classifier metadata and broken legacy glyphs from UI."""
    text = unicodedata.normalize("NFC", str(value or "")).strip()
    # HSK flashcards need a readable Vietnamese gloss, not technical metadata.
    text = re.split(r"(?i)LT\s*:", text, maxsplit=1)[0]
    text = text.replace("\ufffd", "").replace("\u200b", "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Cc" or ch in "\n\t")
    text = text.strip(" ;,/\t\n")
    return text[:220]

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


def load_courses(dictionary=None):
    groups = defaultdict(list)
    missing_hsk = 0
    missing_english = 0
    with open(VI_PATH, "r", encoding="utf-8") as stream:
        vi = json.load(stream)
    with open(CVDICT_PATH, "r", encoding="utf-8") as stream:
        cvdict = json.load(stream).get("entries", {})
    with open(HSK_PATH, "r", encoding="utf-8") as stream:
        hsk = json.load(stream)
    for item in hsk:
        group = str(item.get("level") or "").strip()
        word = str(item.get("word") or "").strip()
        if not group.startswith("HSK ") or not word:
            continue
        headword = word.split("|")[0]
        definition = clean_vi_gloss(vi["hsk"].get(headword, "")
                                    or item.get("vi")
                                    or cvdict.get(str(item.get("id") or ""), ""))
        if not definition and dictionary is not None and dictionary.available:
            definition = clean_vi_gloss(dictionary.exact_meaning(
                headword, str(item.get("traditional") or "").split("|")[0]))
        if not definition:
            missing_hsk += 1
        groups[group].append({
            "word": word,
            "reading": str(item.get("pinyin") or ""),
            "meaning": str(item.get("en") or "").strip(),
            "vi": definition,
            "picture": ILLUSTRATED_WORDS.get(word.split("|")[0], "") or ICON_BY_WORD.get(word.split("|")[0], ""),
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
            english_vi = clean_vi_gloss(vi["english"].get(word.lower(), ""))
            if not english_vi:
                missing_english += 1
            groups["English " + level].append({
                "word": word,
                "reading": str(item.get("pos") or ""),
                "meaning": meaning,
                "vi": english_vi,
                "picture": ILLUSTRATED_WORDS.get(word.lower(), "") or ICON_BY_WORD.get(word.lower(), ""),
                "other": ", ".join(item.get("synonyms") or []),
                "source": "carryword/english-vocabulary (MIT)",
                "course": "English"
            })
    return (dict(groups), len(hsk), len(english.get("entries", [])),
            missing_hsk, missing_english)


class DolingoApp(App):
    def build(self):
        select_fonts()
        self.title = "Dolingo | Study Studio"
        self.data = {}
        self.dictionary = Dictionary()
        self.saved_words = []
        self.hsk_count = 0
        self.en_count = 0
        self.missing_hsk = 0
        self.missing_english = 0
        self.mode = "dashboard"
        self.group = "HSK 1"
        self.deck = []
        self.index = 0
        self.correct = 0
        self.attempts = 0
        self.reveal = False
        self.flashcard_flipped = False
        self.progress = {}
        self._load_progress()
        self.saved_words = list(self.progress.get("_cvdict_saved", []))
        self.xp = int(self.progress.get("_xp", 0))
        self.streak = int(self.progress.get("_streak", 0))
        self.root_panel = Panel(color=BG, radius=0, orientation="vertical")

        self.status = label("Đang chuẩn bị bài học...", 14, MUTED, height=40,
                            align="center")
        self.root_panel.add_widget(self.status)
        self.fixed_nav = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(55))
        self.root_panel.add_widget(self.fixed_nav)
        self.main_scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        self.root_panel.add_widget(self.main_scroll)
        self.bottom_nav = Panel(color=WHITE, radius=0, size_hint_y=None,
                                height=dp(67), padding=[dp(8), dp(6), dp(8), dp(7)],
                                spacing=dp(4))
        self.root_panel.add_widget(self.bottom_nav)
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
            (self.data, self.hsk_count, self.en_count,
             self.missing_hsk, self.missing_english) = load_courses(self.dictionary)
            self.status.text = ("%s từ HSK 3.0  •  %s mục English  •  Offline" %
                                (self.hsk_count, self.en_count))
            self.change_group("HSK 1")
            self.change_mode("dashboard")
        except Exception as exc:
            traceback.print_exc()
            self.status.text = "Không tải được dữ liệu học"
            self.body.clear_widgets()
            self.body.add_widget(label(str(exc), 15, height=150))
            self.body.add_widget(button("Thử lại", lambda: self._initialize()))

    def _top_navigation(self):
        """Keep top branding quiet; the actual primary navigation is bottom-fixed."""
        header = Panel(color=WHITE, radius=0, size_hint_y=None, height=dp(55),
                       padding=[dp(15), 0, dp(15), 0], spacing=dp(6))
        header.add_widget(label("DOLINGO", 23, GREEN, True, 50))
        header.add_widget(label("HSK  •  ENGLISH  •  OFFLINE", 10,
                                MUTED, height=50, align="right"))
        self.fixed_nav.add_widget(header)
        self._bottom_navigation()

        if self.mode in ("learn", "quiz", "saved"):
            selector_row = Panel(color=WHITE, radius=16, size_hint_y=None,
                                 height=dp(60), padding=dp(6), spacing=dp(8))
            selector_row.add_widget(button("HSK", lambda: self.change_group("HSK 1"),
                                           bg=MINT if self.group.startswith("HSK") else BG,
                                           fg=GREEN, height=47, size=13))
            selector_row.add_widget(button("ENGLISH",
                                           lambda: self.change_group("English 1"),
                                           bg=SKY if self.group.startswith("English") else BG,
                                           fg=GREEN, height=47, size=13))
            selector_row.add_widget(button("CVDICT", self.open_dictionary,
                                           bg=LEMON, fg=GREEN, height=47, size=13))
            self.body.add_widget(selector_row)
            levels = (["HSK " + str(i) for i in range(1, 10)]
                      if self.group.startswith("HSK")
                      else ["English 1", "English 2", "English 3"])
            levels = [name for name in levels if name in self.data]
            select = Spinner(text=self.group, values=levels, font_name=FONT,
                             font_size=dp(15), color=INK, background_normal="",
                             background_color=LAVENDER, size_hint_y=None,
                             height=dp(50))
            select.bind(text=lambda _inst, name: self.change_group(name)
                        if name != self.group else None)
            self.body.add_widget(select)

    def _bottom_navigation(self):
        self.bottom_nav.clear_widgets()
        # Five large hit targets reflect the library-first layout in the reference video.
        items = [
            ("TRANG CHỦ", "dashboard"),
            ("HỌC TỪ", "learn"),
            ("THƯ VIỆN", "library"),
            ("ĐÃ LƯU", "saved"),
            ("CÁ NHÂN", "profile")
        ]
        for title, mode in items:
            active = (self.mode == mode or
                      (self.mode == "quiz" and mode == "learn"))
            self.bottom_nav.add_widget(
                button(title, partial(self.change_mode, mode),
                       bg=GREEN if active else WHITE,
                       fg=WHITE if active else MUTED,
                       height=52, size=10)
            )

    def render_library(self):
        """Browse actual bundled vocabulary by level, without fake video records."""
        self.body.add_widget(label("THƯ VIỆN HỌC TẬP", 21, GREEN, True, 48))
        self.body.add_widget(label("Khám phá từng cấp độ từ dữ liệu có sẵn.",
                                   13, MUTED, height=35))
        for title, prefix, shade in (("TIẾNG TRUNG  •  HSK 3.0", "HSK ", LAVENDER),
                                     ("TIẾNG ANH  •  ENGLISH", "English ", SKY)):
            self.body.add_widget(label(title, 15, GREEN, True, 37))
            for group in sorted((x for x in self.data if x.startswith(prefix)),
                                key=lambda x: int(re.search(r"\d+", x).group())):
                count = len(self.data[group])
                card = Panel(color=shade, radius=16, orientation="vertical",
                             padding=[dp(14), dp(10), dp(14), dp(10)],
                             size_hint_y=None, height=dp(104), spacing=dp(4))
                card.add_widget(label(group + "  •  " + str(count) + " từ",
                                      16, INK, True, 36))
                card.add_widget(button("HỌC CẤP ĐỘ NÀY",
                                       partial(self.change_group, group),
                                       bg=GREEN, fg=WHITE, height=44, size=12))
                self.body.add_widget(card)

    def render_profile(self):
        """Local profile: no unsupported account sync promises."""
        self.body.add_widget(label("KHÔNG GIAN CỦA BẠN", 21, GREEN, True, 47))
        profile = Panel(color=LAVENDER, radius=20, orientation="vertical",
                        padding=[dp(15), dp(12), dp(15), dp(12)],
                        size_hint_y=None, height=dp(184), spacing=dp(8))
        profile.add_widget(label("Tiến độ học trên thiết bị", 17, GREEN, True, 36))
        profile.add_widget(label("XP: %d   •   Chuỗi đúng: %d" %
                                  (self.xp, self.streak), 15, INK, height=40))
        profile.add_widget(label("Từ HSK: %d   •   English: %d" %
                                  (self.hsk_count, self.en_count), 13, MUTED,
                                  height=34))
        profile.add_widget(label("Dữ liệu cá nhân được giữ trên máy.",
                                  12, MUTED, height=30))
        self.body.add_widget(profile)
        self.body.add_widget(button("ÔN FLASHCARD ĐÃ LƯU",
                                    lambda: self.change_mode("saved"),
                                    bg=MINT, fg=GREEN))
        self.body.add_widget(button("LUYỆN TẬP TRẮC NGHIỆM",
                                    lambda: self.change_mode("quiz"),
                                    bg=SKY, fg=GREEN))
        if self.dictionary.available:
            self.body.add_widget(button("TRA CVDICT NGOẠI TUYẾN",
                                        self.open_dictionary,
                                        bg=LEMON, fg=GREEN))
        self.body.add_widget(label("Chưa bật đăng nhập hoặc đồng bộ cloud.",
                                   12, MUTED, height=40))

    def _stat_card(self, heading, value, note, shade):
        card = Panel(color=shade, radius=19, orientation="vertical",
                     size_hint_y=None, height=dp(125),
                     padding=[dp(14), dp(13), dp(10), dp(12)],
                     spacing=dp(2))
        card.add_widget(label(heading, 12, GREEN, True, 25))
        card.add_widget(label(str(value), 27, INK, True, 47))
        card.add_widget(label(note, 11, MUTED, height=25))
        return card

    def _action_card(self, heading, note, shade, callback):
        card = Panel(color=shade, radius=18, orientation="vertical",
                     size_hint_y=None, height=dp(153),
                     padding=[dp(11), dp(12), dp(11), dp(11)], spacing=dp(4))
        card.add_widget(label(heading, 15, GREEN, True, 33))
        card.add_widget(label(note, 12, INK, height=37))
        card.add_widget(button("MỞ NGAY", callback, bg=GREEN, fg=WHITE,
                               height=45, size=12))
        return card

    def render_dashboard(self):
        hero = Panel(color=LAVENDER, radius=23, orientation="vertical",
                     size_hint_y=None, height=dp(192), spacing=dp(7),
                     padding=[dp(17), dp(16), dp(17), dp(15)])
        hero.add_widget(label("CHÀO MỪNG TRỞ LẠI!", 12, GREEN, True, 28))
        hero.add_widget(label("Hôm nay học gì?", 25, INK, True, 42))
        hero.add_widget(label("Mỗi ngày một chút, tiến bộ thật nhiều.",
                              13, MUTED, height=30))
        hero.add_widget(button("TIẾP TỤC  •  " + self.group,
                               lambda: self.change_mode("learn"),
                               bg=GREEN, fg=WHITE, height=50, size=14))
        self.body.add_widget(hero)

        self.body.add_widget(label("THÀNH TÍCH CỦA BẠN", 15, GREEN, True, 36))
        row = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(125))
        row.add_widget(self._stat_card("KINH NGHIỆM", self.xp, "Điểm XP", PEACH))
        row.add_widget(self._stat_card("CHUỖI ĐÚNG", self.streak, "Câu liên tiếp", SKY))
        self.body.add_widget(row)
        row = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(125))
        saved_count = len(self.progress.get("_flashcard_saved", []))
        row.add_widget(self._stat_card("THẺ ĐÃ LƯU", saved_count,
                                       "Để ôn tập", PINK))
        row.add_widget(self._stat_card("ĐÃ HỌC", self.progress.get(self.group, 0),
                                       "Lượt xem " + self.group, MINT))
        self.body.add_widget(row)

        self.body.add_widget(label("KHÁM PHÁ NGAY", 15, GREEN, True, 36))
        row = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(153))
        row.add_widget(self._action_card("Học HSK 3.0", "Từ vựng tiếng Trung",
                                          LAVENDER, lambda: self.change_group("HSK 1")))
        row.add_widget(self._action_card("Học English", "Từ vựng tiếng Anh",
                                          SKY, lambda: self.change_group("English 1")))
        self.body.add_widget(row)
        row = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(153))
        row.add_widget(self._action_card("Flashcard", "Xem thẻ đã lưu",
                                          PINK, lambda: self.change_mode("saved")))
        row.add_widget(self._action_card("Từ điển", "Tra cứu CVDICT",
                                          LEMON, self.open_dictionary))
        self.body.add_widget(row)

        self.body.add_widget(button("XEM TOÀN BỘ THƯ VIỆN HỌC TẬP",
                                    lambda: self.change_mode("library"),
                                    bg=MINT, fg=GREEN, height=52))
        tip = Panel(color=WHITE, radius=19, orientation="vertical",
                    padding=[dp(15), dp(10), dp(15), dp(10)],
                    size_hint_y=None, height=dp(96), spacing=dp(5))
        tip.add_widget(label("MẸO HỌC TẬP", 14, GREEN, True, 28))
        tip.add_widget(label("Học 5 từ mới, lật thẻ và lưu những từ khó.",
                             13, INK, height=45))
        self.body.add_widget(tip)

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
        self.flashcard_flipped = False
        self.render()
        Clock.schedule_once(lambda *_: setattr(self.main_scroll, "scroll_y", 1), 0)

    def change_mode(self, mode):
        self.mode = mode
        self.reveal = False
        self.flashcard_flipped = False
        self.render()
        Clock.schedule_once(lambda *_: setattr(self.main_scroll, "scroll_y", 1), 0)

    def render(self):
        self.body.clear_widgets()
        self.fixed_nav.clear_widgets()
        self._top_navigation()
        if self.mode != "dashboard":
            self.body.add_widget(label("XP: %d     •     Chuỗi đúng: %d" % (self.xp, self.streak), 14, GREEN, True, 32))
        if self.mode == "dashboard":
            self.render_dashboard()
        elif self.mode == "library":
            self.render_library()
        elif self.mode == "profile":
            self.render_profile()
        elif self.mode == "saved":
            self.render_saved()
        elif self.mode == "search":
            self.render_search()
        elif self.mode == "quiz":
            self.render_quiz()
        else:
            self.render_learn()

    def _card(self, min_height=350):
        return Panel(color=WHITE, radius=23, orientation="vertical",
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
        card = self._card(370 if self.flashcard_flipped else (455 if item["picture"] else 265))
        card.add_widget(label(("MẶT SAU  •  " if self.flashcard_flipped else "MẶT TRƯỚC  •  ") + self.group,
                              12, GREEN, True, 29))
        if self.flashcard_flipped:
            card.add_widget(label("NGHĨA TIẾNG VIỆT", 12, GREEN, True, 30))
            card.add_widget(label(item["vi"] or "Chưa có bản dịch tiếng Việt", 21,
                                  INK, True, 98, align="center"))
            card.add_widget(label(item["reading"], 18, GREEN, height=42, align="center"))
            card.add_widget(label((item["meaning"] or "")[:240], 13, MUTED,
                                  height=105, align="center"))
        else:
            if item["picture"]:
                picture_bg = Panel(color=SKY, radius=16,
                                   size_hint_y=None, height=dp(170), padding=dp(5))
                image_path = os.path.join(ILLUSTRATION_DIR, item["picture"] + ".png")
                if os.path.isfile(image_path):
                    picture_bg.add_widget(Image(source=image_path, fit_mode="contain"))
                else:
                    picture_bg.add_widget(Picture(item["picture"]))
                card.add_widget(picture_bg)
            card.add_widget(label(item["word"], 36 if len(item["word"]) < 14 else 26,
                                  INK, True, 104, font=CJK_FONT if item["course"]=="HSK" else FONT,
                                  align="center"))
            card.add_widget(label("Hãy đoán nghĩa trước khi lật thẻ", 13, MUTED,
                                  height=40, align="center"))
        self.body.add_widget(card)
        self.body.add_widget(button("LẬT THẺ  •  XEM NGHĨA" if not self.flashcard_flipped
                                    else "LẬT LẠI  •  XEM TỪ", self.flip_flashcard,
                                    bg=GOLD, fg=INK))
        key = self.group + "|" + item["word"]
        saved = self.progress.get("_flashcard_saved", [])
        self.body.add_widget(button("BỎ LƯU THẺ" if key in saved else "LƯU FLASHCARD",
                                    self.toggle_flashcard_saved, bg=MINT, fg=GREEN))
        if item["other"]:
            if item["course"] == "HSK":
                # Never mix Vietnamese labels with CJK-only font glyph runs.
                self.body.add_widget(label("CHỮ PHỒN THỂ", 12, GREEN, True, 24))
                self.body.add_widget(label(item["other"][:100], 17, MUTED,
                                           height=43, font=CJK_FONT))
            else:
                self.body.add_widget(label("Đồng nghĩa: " + item["other"][:120],
                                           14, MUTED, height=52))
        controls = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(9))
        controls.add_widget(button("TRỘN LẠI", self.shuffle, bg=MINT, fg=GREEN))
        controls.add_widget(button("TỪ TIẾP  →", self.next_word, bg=GREEN))
        if item["course"] == "HSK":
            self.body.add_widget(button("TRA CVDICT  •  " + item["word"][:12],
                                        lambda: self.open_dictionary(item["word"].split("|")[0]),
                                        bg=MINT, fg=GREEN))
        self.body.add_widget(controls)
        self.body.add_widget(label("Luyện tập để kiểm tra mức độ ghi nhớ.", 13,
                                   MUTED, height=34, align="center"))

    def flip_flashcard(self):
        self.flashcard_flipped = not self.flashcard_flipped
        self.render()

    def toggle_flashcard_saved(self):
        item = self.deck[self.index]
        key = self.group + "|" + item["word"]
        saved = list(self.progress.get("_flashcard_saved", []))
        if key in saved:
            saved.remove(key)
        else:
            saved.append(key)
        self.progress["_flashcard_saved"] = saved
        self._save_progress()
        self.render()

    def render_saved(self):
        keys = self.progress.get("_flashcard_saved", [])
        self.body.add_widget(label("FLASHCARD ĐÃ LƯU  •  %d TỪ" % len(keys),
                                   17, GREEN, True, 52))
        if not keys:
            self.body.add_widget(label("Chưa có thẻ nào. Vào HỌC TỪ để lưu.",
                                       14, MUTED, height=85))
            return
        for key in keys[-100:]:
            if "|" not in key:
                continue
            group, word = key.split("|", 1)
            matches = [r for r in self.data.get(group, []) if r["word"] == word]
            if not matches:
                continue
            item = matches[0]
            card = Panel(color=WHITE, radius=14, orientation="vertical",
                         padding=dp(10), spacing=dp(5), size_hint_y=None, height=dp(122))
            card.add_widget(label(word + "  " + item["reading"], 18, GREEN, True,
                                  48, font=CJK_FONT))
            card.add_widget(label((item["vi"] or item["meaning"])[:160], 14,
                                  MUTED, height=55))
            self.body.add_widget(card)

    def shuffle(self):
        self.flashcard_flipped = False
        random.shuffle(self.deck)
        self.index = 0
        self.render()

    def next_word(self):
        self.flashcard_flipped = False
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
        card.add_widget(label("CHỌN NGHĨA ĐÚNG CHO TỪ", 12, GREEN, True, 32,
                              align="center"))
        card.add_widget(label(item["word"], 34, INK, True, 95,
                              font=CJK_FONT if item["course"]=="HSK" else FONT,
                              align="center"))
        card.add_widget(label(item["reading"], 17, GREEN, height=40, align="center"))
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


    def open_dictionary(self, initial=""):
        """Search all CVDICT entries in a separate popup; preserve lesson position."""
        if not self.dictionary.available:
            self.status.text = "Thiếu dữ liệu CVDICT offline trong bản APK này"
            return
        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        title = label("CVDICT  •  TRUNG - VIỆT", 18, GREEN, True, 44)
        root.add_widget(title)
        search = TextInput(text=initial, hint_text="Chữ Hán hoặc Pinyin (ni hao)",
                           multiline=False, font_name=CJK_FONT, font_size=dp(18),
                           size_hint_y=None, height=dp(52))
        root.add_widget(search)
        scroller = ScrollView(do_scroll_x=False)
        results = BoxLayout(orientation="vertical", spacing=dp(9), size_hint_y=None)
        results.bind(minimum_height=results.setter("height"))
        scroller.add_widget(results)
        root.add_widget(scroller)
        footer = button("ĐÓNG TỪ ĐIỂN", lambda: popup.dismiss(), height=48)
        root.add_widget(footer)
        popup = Popup(title="Tra cứu ngoại tuyến", content=root,
                      size_hint=(0.96, 0.88), auto_dismiss=True)

        def save_word(entry):
            key = entry["simplified"]
            if key not in self.saved_words:
                self.saved_words.append(key)
                self.progress["_cvdict_saved"] = self.saved_words
                self._save_progress()
                self.status.text = "Đã lưu từ: " + key

        def draw(*_):
            results.clear_widgets()
            query = search.text.strip()
            if not query:
                results.add_widget(label("Nhập chữ Hán hoặc Pinyin để tra cứu", 14,
                                         MUTED, height=70))
                return
            matches = self.dictionary.lookup(query)
            if not matches:
                results.add_widget(label("Không tìm thấy từ phù hợp.", 14,
                                         MUTED, height=65))
            for entry in matches:
                card = Panel(color=WHITE, radius=14, orientation="vertical",
                             padding=dp(10), spacing=dp(4), size_hint_y=None,
                             height=dp(202))
                card.add_widget(label(entry["simplified"][:60], 19, GREEN, True, 30,
                                      font=CJK_FONT))
                card.add_widget(label(entry["pinyin"][:95], 13, MUTED, height=25))
                card.add_widget(label(clean_vi_gloss(entry["meaning"])[:250], 14, INK, height=67))
                card.add_widget(button("LƯU VÀO SỔ TAY", partial(save_word, entry),
                                       bg=MINT, fg=GREEN, height=42, size=13))
                results.add_widget(card)

        search.bind(on_text_validate=draw)
        root.add_widget(button("TRA TỪ", draw, bg=GREEN, height=48))
        popup.open()
        draw()

    def on_stop(self):
        if getattr(self, "dictionary", None):
            self.dictionary.close()

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
