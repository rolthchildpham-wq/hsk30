"""Generate small original offline illustrations for common vocabulary.

Requires Pillow in the CI build environment only; the Android app needs no Pillow.
All graphics are drawn from shapes, not downloaded stock photos.
"""
from pathlib import Path
from PIL import Image, ImageDraw
OUT = Path(__file__).resolve().parent / "assets" / "illustrations"
OUT.mkdir(parents=True, exist_ok=True)
S = 320
PALETTES = {
 "food": ("#FFF2DD","#F79A4C","#4EAC7E"),
 "breakfast": ("#FFF1D8","#F5B85F","#D36D57"),
 "dinner": ("#FFE8E5","#F28A71","#638EBC"),
 "apple": ("#FFEAE8","#E75860","#61AD73"),
 "book": ("#E8E9FF","#7764C8","#F1AE61"),
 "home": ("#E6F5FF","#5E9ECE","#EDAB78"),
 "school": ("#E6F6EF","#419D92","#F2C76D"),
 "sun": ("#FFF4D6","#F9B940","#F68E56"),
 "moon": ("#EAE9FF","#8C86D8","#FBDA85"),
 "flower": ("#FFE9F3","#F283A6","#64B789"),
 "tree": ("#E8F5E4","#4CA47A","#9C6B49"),
 "cup": ("#E5F5FF","#4F9EC8","#F5BF69"),
 "water": ("#DDF4FF","#5AB8E0","#BDE6F9"),
 "car": ("#EBF2FF","#5D88D8","#F6BD68"),
 "plane": ("#E4F4FF","#649ECC","#D6EDF9"),
 "phone": ("#ECE9FF","#8677C9","#6BBEC8"),
 "clock": ("#FFF2D9","#E6A85A","#60A7A4"),
 "heart": ("#FFE6EC","#EC7393","#F8A6BD"),
 "cloud": ("#E5F3FF","#8BB6D5","#FFFFFF"),
 "computer": ("#E8F4FF","#6C88C0","#A3E2DB"),
 "cat": ("#FFF2E3","#D99561","#E6BDA0"),
 "dog": ("#F7EADD","#BD936B","#E4C59B"),
 "person": ("#EAEFFF","#6E93C9","#F5C3A4"),
 "teacher": ("#E8F6EF","#5CA78D","#F8C9A9"),
 "rice": ("#FFF1D9","#F6C979","#FFFFFF"),
}
def make(kind, palette):
    bg, main, extra = palette
    image = Image.new("RGB", (S,S),bg)
    d=ImageDraw.Draw(image)
    d.ellipse((15,230,305,290),fill="#FFFFFF")
    if kind in ("food","breakfast","dinner","rice"):
        d.ellipse((45,102,275,278),fill="#D5AA84")
        d.ellipse((48,97,272,260),fill="#FFFFFF")
        d.ellipse((75,116,245,235),fill="#FCF1CD")
        for x,y in [(104,148),(146,166),(181,137),(198,186),(125,191)]:
            d.ellipse((x,y,x+33,y+23),fill=extra if kind!="rice" else "#FFFDF5")
        if kind!="rice":
            d.ellipse((139,138,184,176),fill=main)
            d.arc((40,95,278,265),15,175,fill="#D5D9DC",width=7)
    elif kind in ("apple","sun","moon","flower","tree","cloud","heart"):
        if kind=="apple":
            d.ellipse((74,75,246,253),fill=main);d.line((155,95,165,55),fill="#76543F",width=10);d.ellipse((165,55,218,86),fill=extra)
        elif kind=="sun":
            d.ellipse((95,89,225,220),fill=main)
            for x,y in [(160,50),(160,260),(53,160),(265,160),(83,82),(239,239),(84,237),(236,80)]:
                d.ellipse((x-9,y-9,x+9,y+9),fill=main)
        elif kind=="moon":
            d.ellipse((100,74,227,237),fill=extra);d.ellipse((135,50,265,206),fill=bg)
        elif kind=="flower":
            d.line((162,164,162,275),fill=extra,width=13)
            for x,y in [(110,117),(175,117),(141,81),(142,159)]:
                d.ellipse((x,y,x+65,y+65),fill=main)
            d.ellipse((145,135,183,173),fill="#F4D566")
        elif kind=="tree":
            d.rounded_rectangle((146,160,176,285),radius=8,fill=extra)
            for x,y in [(70,115),(150,80),(185,125),(120,125)]:
                d.ellipse((x,y,x+88,y+105),fill=main)
        elif kind=="cloud":
            for x,y,sz in [(55,142,110),(112,99,140),(181,143,100)]:
                d.ellipse((x,y,x+sz,y+sz),fill="#FFFFFF")
        else:
            d.ellipse((76,93,175,196),fill=main);d.ellipse((145,93,244,196),fill=main)
            d.polygon([(75,150),(245,150),(160,260)],fill=main)
    elif kind in ("home","school","book","phone","computer","clock","cup","water"):
        if kind in ("home","school"):
            d.rectangle((86,128,234,260),fill=main);d.polygon([(66,135),(160,59),(254,135)],fill=extra)
            d.rectangle((145,191,182,260),fill="#FFFFFF")
            d.rectangle((104,154,132,185),fill=bg);d.rectangle((196,154,225,185),fill=bg)
        elif kind=="book":
            d.rounded_rectangle((56,78,155,254),radius=12,fill=main)
            d.rounded_rectangle((163,78,264,254),radius=12,fill=extra)
            d.line((160,84,160,255),fill="#FFFFFF",width=8)
            for y in (118,146,174):d.line((77,y,136,y),fill="#FFFFFF",width=5)
        elif kind in ("phone","computer"):
            rect=(99,59,222,262) if kind=="phone" else (53,83,267,229)
            d.rounded_rectangle(rect,radius=18,fill="#344D68")
            d.rounded_rectangle((rect[0]+12,rect[1]+14,rect[2]-12,rect[3]-22),radius=9,fill=main)
            if kind=="computer":d.rectangle((151,226,169,261),fill="#344D68")
        elif kind=="clock":
            d.ellipse((65,64,255,257),fill=main);d.ellipse((85,85,235,237),fill="#FFFFFF")
            d.line((160,160,160,112),fill="#344D68",width=10);d.line((160,160,197,178),fill="#344D68",width=10)
        elif kind in ("cup","water"):
            d.rounded_rectangle((90,95,217,245),radius=24,fill=main)
            d.arc((177,120,270,222),270,100,fill=extra,width=14)
            d.ellipse((100,90,207,110),fill="#FFFFFF")
    elif kind in ("car","plane"):
        if kind=="car":
            d.rounded_rectangle((43,155,279,232),radius=23,fill=main)
            d.polygon([(88,160),(120,107),(213,107),(245,160)],fill=extra)
            for x in (91,226):d.ellipse((x-26,209,x+26,259),fill="#344D68")
        else:
            d.polygon([(34,143),(274,104),(287,136),(168,178),(119,258),(101,246),(121,170),(38,167)],fill=main)
    elif kind in ("cat","dog","person","teacher"):
        d.ellipse((89,97,233,250),fill=main)
        if kind in ("cat","dog"):
            d.polygon([(96,133),(102,67),(146,115)],fill=main)
            d.polygon([(180,112),(218,67),(226,135)],fill=main)
            d.ellipse((125,164,137,176),fill="#263E4D")
            d.ellipse((185,164,197,176),fill="#263E4D")
            d.ellipse((157,190,175,202),fill="#F4D7C6")
        else:
            d.ellipse((122,78,202,169),fill=extra)
            d.polygon([(105,207),(219,207),(252,291),(70,291)],fill=main)
    image.save(OUT/(kind+".png"),optimize=True)

for kind,palette in PALETTES.items():
    make(kind,palette)
print("Created original offline illustration PNGs:", len(PALETTES))
