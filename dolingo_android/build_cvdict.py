"""Build an offline SQLite index from Phong Phan's CVDICT (CC BY-SA 4.0).

Source: https://github.com/ph0ngp/CVDICT (CVDICT.u8).
The app keeps this adapted dictionary separately from the HSK course data.
"""
import re
import sqlite3
import sys
import unicodedata
import urllib.request
from pathlib import Path

SOURCE = "https://raw.githubusercontent.com/ph0ngp/CVDICT/main/CVDICT.u8"
ENTRY = re.compile(r"^(\S+)\s+(\S+)\s+\[([^\]]+)\]\s+/(.+)/\s*$")


def fold(value):
    value = unicodedata.normalize("NFD", value.lower().replace("u:", "ü"))
    return "".join(c for c in value if not unicodedata.combining(c)).replace("ü", "u")


def build(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    conn = sqlite3.connect(str(target))
    try:
        conn.executescript("""
        CREATE TABLE entries (
          id INTEGER PRIMARY KEY,
          traditional TEXT NOT NULL,
          simplified TEXT NOT NULL,
          pinyin TEXT NOT NULL,
          pinyin_search TEXT NOT NULL,
          meaning TEXT NOT NULL
        );
        CREATE INDEX entries_simplified ON entries(simplified);
        CREATE INDEX entries_traditional ON entries(traditional);
        CREATE INDEX entries_pinyin ON entries(pinyin_search);
        """)
        count = 0
        malformed = 0
        with source.open(encoding="utf-8-sig") as stream:
            for line in stream:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                match = ENTRY.match(line)
                if not match:
                    malformed += 1
                    if malformed <= 10:
                        print("Skipping unparseable CVDICT record:", repr(line[:180]))
                    continue
                trad, simp, pinyin, meaning = match.groups()
                conn.execute(
                    "INSERT INTO entries (traditional,simplified,pinyin,pinyin_search,meaning) VALUES (?,?,?,?,?)",
                    (trad, simp, pinyin, fold(pinyin), meaning.replace("/", "; ")),
                )
                count += 1
        if malformed > 100:
            raise ValueError("Too many malformed CVDICT records: %d" % malformed)
        if count < 100000:
            raise ValueError("Incomplete CVDICT: %d entries" % count)
        conn.commit()
        print("CVDICT offline entries:", count, "malformed:", malformed, "DB bytes:", target.stat().st_size)
    finally:
        conn.close()


if __name__ == "__main__":
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/dolingo-CVDICT.u8")
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent / "data" / "cvdict.sqlite3"
    if not src.is_file():
        urllib.request.urlretrieve(SOURCE, str(src))
    build(src, output)
