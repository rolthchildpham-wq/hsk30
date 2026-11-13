"""Fast offline CVDICT lookups without loading the whole dictionary into memory."""
import sqlite3
import unicodedata
from pathlib import Path

DB = Path(__file__).resolve().parent / "data" / "cvdict.sqlite3"


def normalize(value):
    chars = unicodedata.normalize("NFD", value.casefold().replace("u:", "ü"))
    return "".join(ch for ch in chars if not unicodedata.combining(ch)).replace("ü", "u")


class Dictionary:
    def __init__(self):
        self.connection = None
        if DB.is_file():
            self.connection = sqlite3.connect(str(DB))

    @property
    def available(self):
        return self.connection is not None

    def lookup(self, query, limit=35):
        query = (query or "").strip()[:100]
        if not self.connection or not query:
            return []
        normalized = normalize(query)
        if any("\u3400" <= ch <= "\u9fff" for ch in query):
            sql = """SELECT traditional, simplified, pinyin, meaning
                     FROM entries WHERE simplified = ? OR traditional = ?
                     UNION ALL
                     SELECT traditional, simplified, pinyin, meaning
                     FROM entries WHERE (simplified LIKE ? OR traditional LIKE ?)
                     AND simplified <> ? AND traditional <> ?
                     LIMIT ?"""
            values = (query, query, query + "%", query + "%", query, query, limit)
        else:
            sql = """SELECT traditional, simplified, pinyin, meaning
                     FROM entries WHERE pinyin_search LIKE ?
                     ORDER BY length(pinyin_search) ASC LIMIT ?"""
            values = (normalized + "%", limit)
        return [dict(traditional=a, simplified=b, pinyin=c, meaning=d)
                for a,b,c,d in self.connection.execute(sql, values)]

    def exact_meaning(self, simplified, traditional=""):
        """Prefer exact CVDICT definitions, never prefix results for translations."""
        if not self.connection:
            return ""
        word = (simplified or "").strip()
        trad = (traditional or "").strip()
        if not word and not trad:
            return ""
        rows = self.connection.execute(
            """SELECT meaning FROM entries
               WHERE simplified = ? OR traditional = ?
                  OR (? <> '' AND simplified = ?)
                  OR (? <> '' AND traditional = ?)
               ORDER BY CASE WHEN simplified = ? THEN 0
                             WHEN traditional = ? THEN 1 ELSE 2 END,
                        length(meaning) ASC LIMIT 1""",
            (word, word, trad, trad, trad, trad, word, word)
        ).fetchone()
        return rows[0] if rows else ""

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None
