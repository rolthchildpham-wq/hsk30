"""Create an offline IPA lookup for Dolingo English vocabulary.

Build-time only: cmudict (Carnegie Mellon Pronouncing Dictionary).
Source: https://github.com/cmusphinx/cmudict ; BSD-style license.
IPA is an American-English approximation from CMU phoneme transcriptions.
"""
import json
import re
from pathlib import Path
import cmudict

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
ARPABET = {
    "AA":"ɑ", "AE":"æ", "AH":"ʌ", "AO":"ɔ", "AW":"aʊ", "AY":"aɪ",
    "B":"b", "CH":"tʃ", "D":"d", "DH":"ð", "EH":"ɛ", "ER":"ɝ",
    "EY":"eɪ", "F":"f", "G":"ɡ", "HH":"h", "IH":"ɪ", "IY":"i",
    "JH":"dʒ", "K":"k", "L":"l", "M":"m", "N":"n", "NG":"ŋ",
    "OW":"oʊ", "OY":"ɔɪ", "P":"p", "R":"ɹ", "S":"s", "SH":"ʃ",
    "T":"t", "TH":"θ", "UH":"ʊ", "UW":"u", "V":"v", "W":"w",
    "Y":"j", "Z":"z", "ZH":"ʒ",
}

def convert(phones):
    result = []
    for phoneme in phones:
        phoneme = str(phoneme)
        base = re.sub(r"[0-2]$", "", phoneme)
        if base not in ARPABET:
            return ""
        stress = phoneme[-1] if phoneme[-1].isdigit() else ""
        if stress == "1":
            result.append("ˈ")
        elif stress == "2":
            result.append("ˌ")
        # Reduced schwa and weak rhotic vowel.
        if base == "AH" and stress == "0":
            result.append("ə")
        elif base == "ER" and stress == "0":
            result.append("ɚ")
        else:
            result.append(ARPABET[base])
    return "/" + "".join(result) + "/" if result else ""

def main():
    entries = json.loads((DATA/"english_learner_thesaurus.json").read_text(encoding="utf-8"))["entries"]
    pron = cmudict.dict()
    out = {}
    for row in entries:
        word = str(row.get("word", "")).strip().lower()
        if word in pron:
            value = convert(pron[word][0])
            if value:
                out[word] = value
    (DATA/"english_ipa.json").write_text(json.dumps(out,ensure_ascii=False,
                                                        separators=(",",":")),encoding="utf-8")
    print("IPA coverage:",len(out),"of",len(entries))
    assert len(out) >= 800, "Unexpectedly low IPA coverage"

if __name__ == "__main__":
    main()
