"""
Search demand for the draft theme list (DT-259, DT-273).

Demand decides which themes get a public landing page. It never decides which themes exist or
which sermons are tagged. Two inputs, both exported by hand:

- Google Keyword Planner: volume ranges for the phrases this module writes.
- Google Search Console (Queries.csv): what Metro already appears for.

`build_phrases` writes the phrases to paste into Keyword Planner. `join` combines the results.
Nothing here calls the network. Only generic phrases leave the machine, pasted by hand.
"""

import codecs
import csv
import io
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
THEMES_PATH = os.path.join(ROOT, "config", "theme_starter.json")
TEMPLATES = [
    "bible verses about {x}",
    "what does the bible say about {x}",
    "sermon on {x}",
    "{x} bible study",
]


def load_themes(path=THEMES_PATH):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)["themes"]


def build_phrases(themes):
    """One row per phrase: theme, group, phrase, template. Extra phrases are used as written."""
    rows, seen = [], set()
    for theme in themes:
        candidates = [(t.format(x=theme["search_term"]), t) for t in TEMPLATES]
        candidates += [(p, "extra") for p in theme.get("extra_phrases", [])]
        for phrase, template in candidates:
            if phrase not in seen:
                seen.add(phrase)
                rows.append({"theme": theme["slug"], "group": theme["group"], "phrase": phrase, "template": template})
    return rows


def write_phrase_files(rows, csv_path, txt_path):
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["theme", "group", "phrase", "template"])
        writer.writeheader()
        writer.writerows(rows)
    with open(txt_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(r["phrase"] for r in rows) + "\n")


_UNITS = {"": 1, "k": 1_000, "m": 1_000_000}


def _number(text):
    match = re.fullmatch(r"([\d.,]+)\s*([kKmM]?)", text.strip())
    if not match:
        return None
    return int(float(match.group(1).replace(",", "")) * _UNITS[match.group(2).lower()])


def parse_volume(text):
    """Keyword Planner volume -> (low, high). '10K - 100K' -> (10000, 100000); '1,200' -> (1200, 1200)."""
    text = (text or "").strip()
    if not text or text in {"-", "—", "–"}:
        return None
    parts = [p for p in re.split(r"\s*[-–—]\s*", text) if p]
    numbers = [_number(p) for p in parts]
    if not numbers or any(n is None for n in numbers) or len(numbers) > 2:
        return None
    return (numbers[0], numbers[-1])


def _read_text(path):
    raw = open(path, "rb").read()
    for bom, encoding in ((codecs.BOM_UTF16_LE, "utf-16"), (codecs.BOM_UTF16_BE, "utf-16"), (codecs.BOM_UTF8, "utf-8-sig")):
        if raw.startswith(bom):
            return raw.decode(encoding)
    return raw.decode("utf-8", errors="replace")


def read_planner(path):
    """Keyword Planner export (CSV or UTF-16 tab file) -> {phrase: (low, high)}."""
    lines = _read_text(path).splitlines()
    start = next((i for i, line in enumerate(lines) if line.lstrip("﻿").lower().startswith(("keyword\t", "keyword,", '"keyword"'))), None)
    if start is None:
        raise ValueError("No header row starting with 'Keyword' found in the Keyword Planner file")
    sample = lines[start]
    delimiter = "\t" if sample.count("\t") >= sample.count(",") else ","
    reader = csv.DictReader(io.StringIO("\n".join(lines[start:])), delimiter=delimiter)
    column = next((c for c in reader.fieldnames if c.lower().startswith("avg. monthly searches")), None)
    if column is None:
        raise ValueError("No 'Avg. monthly searches' column found")
    out = {}
    for row in reader:
        volume = parse_volume(row.get(column, ""))
        if volume and row.get("Keyword"):
            out[row["Keyword"].strip().lower()] = volume
    return out


def read_gsc(path):
    """Search Console Queries.csv -> {query: (clicks, impressions, position)}."""
    out = {}
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        next(reader)
        for row in reader:
            if len(row) >= 5:
                out[row[0].strip().lower()] = (int(row[1]), int(row[2]), float(row[4]))
    return out


def join(rows, planner, gsc, threshold=1000):
    """One summary per theme. A theme is a landing-page candidate when its best phrase's
    lower volume bound reaches the threshold. Missing planner data counts as unknown, not zero."""
    summary = {}
    for row in rows:
        s = summary.setdefault(row["theme"], {"theme": row["theme"], "group": row["group"], "best_phrase": "",
                                              "best_low": None, "best_high": None, "known": 0, "phrases": 0,
                                              "metro_impressions": 0, "metro_clicks": 0})
        s["phrases"] += 1
        volume = planner.get(row["phrase"].lower())
        if volume:
            s["known"] += 1
            if s["best_low"] is None or volume[0] > s["best_low"]:
                s["best_phrase"], s["best_low"], s["best_high"] = row["phrase"], volume[0], volume[1]
        seen = gsc.get(row["phrase"].lower())
        if seen:
            s["metro_clicks"] += seen[0]
            s["metro_impressions"] += seen[1]
    for s in summary.values():
        if s["known"] == 0:
            s["verdict"] = "no data"
        elif s["best_low"] >= threshold:
            s["verdict"] = "landing page candidate"
        else:
            s["verdict"] = "tag only"
    return sorted(summary.values(), key=lambda s: -(s["best_low"] or -1))


def format_summary(summary, threshold):
    lines = [f"Landing page threshold: best phrase at {threshold:,} or more searches a month (lower bound)", ""]
    for s in summary:
        volume = "unknown" if s["best_low"] is None else f"{s['best_low']:,} to {s['best_high']:,}"
        lines.append(f"{s['theme']:12} {s['verdict']:24} best: {s['best_phrase'] or '-'} ({volume}); "
                     f"Metro today: {s['metro_impressions']} impressions, {s['metro_clicks']} clicks; "
                     f"{s['known']}/{s['phrases']} phrases found")
    return lines


def write_summary(summary, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)
