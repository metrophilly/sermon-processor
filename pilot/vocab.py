"""Build vocab.json and per-sermon hotword strings for Whisper (DT-249 seed)."""
import json,re
from pathlib import Path
HERE=Path(__file__).parent
BOOKS="Genesis Exodus Leviticus Numbers Deuteronomy Joshua Judges Ruth 1_Samuel 2_Samuel 1_Kings 2_Kings 1_Chronicles 2_Chronicles Ezra Nehemiah Esther Job Psalms Proverbs Ecclesiastes Song_of_Solomon Isaiah Jeremiah Lamentations Ezekiel Daniel Hosea Joel Amos Obadiah Jonah Micah Nahum Habakkuk Zephaniah Haggai Zechariah Malachi Matthew Mark Luke John Acts Romans 1_Corinthians 2_Corinthians Galatians Ephesians Philippians Colossians 1_Thessalonians 2_Thessalonians 1_Timothy 2_Timothy Titus Philemon Hebrews James 1_Peter 2_Peter 1_John 2_John 3_John Jude Revelation".split()
BOOKS=[b.replace('_',' ') for b in BOOKS]
CHARACTERS="Melchizedek Nebuchadnezzar Mephibosheth Bathsheba Uriah Absalom Jehoshaphat Hezekiah Zerubbabel Barnabas Onesimus Nicodemus Lazarus Zacchaeus Caiaphas Pilate Gamaliel Apollos Rahab Gideon Delilah Naomi Boaz Elijah Elisha Pharaoh Abraham Isaac Jacob Joseph Moses Aaron David Solomon Samuel Saul Jonathan Peter Paul Timothy".split()
PLACES="Rephidim Capernaum Gethsemane Golgotha Bethlehem Nazareth Jerusalem Canaan Sinai Horeb Moriah Gilgal Jericho Babylon Nineveh Antioch Ephesus Philippi Corinth Galatia Colossae Thessalonica Damascus Samaria Galilee Bethany Emmaus".split()
GROUPS="Pharisees Sadducees Sanhedrin Levites Philistines Amalekites Israelites Gentiles".split()
THEOLOGY="propitiation justification sanctification imputation atonement redemption reconciliation regeneration incarnation covenant eschatology Trinity gospel-centered repentance Messiah".split()
METRO=["Metro Church","MetroPres","East Falls","Cherry Hill","Center City"]
raw=json.loads((HERE/"metro_names_raw.json").read_text())["result"]
PEOPLE=sorted({f"{p['firstName']} {p['lastName']}".strip() for p in raw["people"] if p.get("isMetroLeadership")})
SERIES=sorted({s["title"] for s in raw["series"]})
CATALOG=dict(books=BOOKS,characters=CHARACTERS,places=PLACES,groups=GROUPS,theology=THEOLOGY,metro=METRO,people=PEOPLE,series=SERIES)
(HERE/"vocab.json").write_text(json.dumps(CATALOG,indent=1))

def passage_books(passage):
    found=[]
    for b in sorted(BOOKS,key=len,reverse=True):
        if re.search(r"\b"+re.escape(b.rstrip("s") if b=="Psalms" else b)+r"s?\b",passage or "") and b not in found: found.append(b)
    return found

def hotwords_for(entry, tokenizer, budget=200):
    """Priority order; stop when the token budget is reached."""
    order=passage_books(entry.get("passage"))+METRO+CHARACTERS+PLACES+GROUPS+THEOLOGY+PEOPLE+BOOKS
    out,seen=[],set()
    for w in order:
        if w in seen: continue
        trial=", ".join(out+[w])
        if len(tokenizer.encode(" "+trial))>budget: break
        out.append(w); seen.add(w)
    return ", ".join(out), len(out)

if __name__=="__main__":
    from faster_whisper import WhisperModel
    tk=WhisperModel("small.en",device="cpu",compute_type="int8").hf_tokenizer
    m=json.loads((HERE/"manifest.json").read_text())[0]
    s,n=hotwords_for(m,tk); print(n,"terms,",len(tk.encode(' '+s)),"tokens"); print(s[:400])
    print({k:len(v) for k,v in CATALOG.items()})
