"""
Shared fix list for transcripts (DT-249).

Applies find-and-replace rules from `config/transcript_fixes.json` to a raw
transcript and returns an EDITED layer: a list of edits that point at word IDs,
plus the edited paragraph text. The raw transcript is never changed and never
rewritten. Rules match whole words, in order, ignoring case.

A rule never matches across punctuation: "first, John said" is left alone, but
"first John" is matched. Punctuation after the last matched word is kept.
"""

import json
import os

FIXES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config", "transcript_fixes.json"
)
TRAILING = ".,;:!?\"')”’"
LEADING = "\"'(“‘"


def load_rules(path=FIXES_PATH):
    with open(path) as handle:
        rules = json.load(handle)["rules"]
    seen = set()
    for rule in rules:
        if not rule.get("id") or not rule.get("find") or "replace" not in rule:
            raise ValueError(f"Fix rule needs id, find and replace: {rule}")
        if rule["id"] in seen:
            raise ValueError(f"Duplicate fix rule id: {rule['id']}")
        seen.add(rule["id"])
    return rules


def _split(text):
    """('"first', ...) -> (leading quotes, core, trailing punctuation)."""
    core = text.lstrip(LEADING)
    lead = text[: len(text) - len(core)]
    stripped = core.rstrip(TRAILING)
    return lead, stripped, core[len(stripped):]


def _join_run(words, parsed, i):
    """Built-in spacing fixes the engine leaves behind. Returns (rule id, word count) or None.

    join-hyphen: "self -centered" -> "self-centered" (a word, then a word that starts with a hyphen and a letter).
    join-thousands: "10 ,000" -> "10,000" (digits, then a comma and exactly three digits).
    """
    if i + 1 >= len(words):
        return None
    lead, core, trail = parsed[i]
    if trail or not core:
        return None
    nxt = words[i + 1]["text"]
    if core.isdigit() and not lead and len(nxt) >= 4 and nxt[0] == "," and nxt[1:4].isdigit():
        tail = nxt[4:]
        if not tail or not tail[0].isdigit():
            return "join-thousands", 2
    if core[-1].isalpha() and len(nxt) >= 2 and nxt[0] == "-" and nxt[1].isalpha():
        n = 2
        while True:
            _, _, t = parsed[i + n - 1]
            if t or i + n >= len(words):
                break
            more = words[i + n]["text"]
            if len(more) >= 2 and more[0] == "-" and more[1].isalpha():
                n += 1
            else:
                break
        return "join-hyphen", n
    return None


def find_edits(words, rules):
    """List of edits over a word list. Earlier rules and earlier positions win; edits never overlap."""
    parsed = [_split(w["text"]) for w in words]
    edits, i = [], 0
    while i < len(words):
        hit = None
        for rule in rules:
            find = rule["find"]
            n = len(find)
            if i + n > len(words):
                continue
            ok = True
            for k, want in enumerate(find):
                lead, core, trail = parsed[i + k]
                if core.lower() != want.lower() or (k < n - 1 and trail):
                    ok = False
                    break
            if ok:
                hit = (rule, n)
                break
        if not hit:
            run = _join_run(words, parsed, i)
            if run:
                rule_id, n = run
                group = words[i : i + n]
                edits.append(
                    {
                        "rule": rule_id,
                        "word_ids": [w["id"] for w in group],
                        "old": " ".join(w["text"] for w in group),
                        "new": "".join(w["text"] for w in group),
                    }
                )
                i += n
                continue
            i += 1
            continue
        rule, n = hit
        group = words[i : i + n]
        new_text = parsed[i][0] + rule["replace"] + parsed[i + n - 1][2]
        old_text = " ".join(w["text"] for w in group)
        if new_text != old_text:
            edits.append(
                {"rule": rule["id"], "word_ids": [w["id"] for w in group], "old": old_text, "new": new_text}
            )
        i += n
    return edits


def apply_fixes(transcript, rules):
    """Edited layer for a raw transcript. The transcript argument is not modified."""
    all_edits, paragraphs = [], []
    for paragraph in transcript["paragraphs"]:
        words = paragraph["words"]
        edits = find_edits(words, rules)
        if not edits:
            continue
        all_edits += edits
        replaced = {e["word_ids"][0]: e["new"] for e in edits}
        dropped = {wid for e in edits for wid in e["word_ids"][1:]}
        text = " ".join(replaced.get(w["id"], w["text"]) for w in words if w["id"] not in dropped)
        paragraphs.append({"id": paragraph["id"], "text": text})
    return {
        "schema_version": 1,
        "layer": "edited",
        "based_on": "raw",
        "sermon_id": transcript["sermon_id"],
        "date": transcript["date"],
        "audio_sha256": transcript["audio"]["sha256"],
        "edit_count": len(all_edits),
        "edits": all_edits,
        "paragraphs": paragraphs,
    }


def write_edited(edited, path):
    tmp = path + ".part"
    with open(tmp, "w") as handle:
        json.dump(edited, handle, indent=1, ensure_ascii=False)
    os.replace(tmp, path)
