"""Score any model's transcripts against Paul's 80 review marks, and count dropped speech.

Usage: .venv/bin/python pilot/score_models.py small.en medium.en mlx-turbo [mlx-large]

For each marked spot, the review sheet gave a context before, a small.en reading,
a medium.en reading and a context after. A model "matches" a reading when its
words around that time overlap that reading's full phrase (context + reading)
more than the other reading's. Paul's mark says which reading was right.
Only decisive marks (small or medium) count toward accuracy.
Scoring small.en and medium.en is a self-check: small.en should match the small
reading at every spot, and medium.en the medium reading.
"""
import html
import json
import re
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

HERE = Path(__file__).parent
norm = lambda w: re.sub(r"[^a-z0-9']", "", w.lower())


def toks(s):
    return [x for x in (norm(w) for w in html.unescape(s).replace("(nothing)", "").split()) if x]


def load_cards():
    h = (HERE / "review.html").read_text()
    out = {}
    for key, ctx, small, medium in re.findall(
        r'data-id="([^"]+)"><div class=h>.*?<p class=ctx>(.*?)</p>.*?small: <b>(.*?)</b>.*?medium: <b>(.*?)</b>', h, re.S
    ):
        ctx = re.sub(r"<[^>]+>", "|", html.unescape(ctx)).split("|")
        out[key] = dict(before=toks(ctx[0].strip("… ")), after=toks(ctx[-1].strip("… ")), small=toks(small), medium=toks(medium))
    return out


def words(model, date):
    d = json.loads((HERE / "results" / f"{date}.{model}.json").read_text())
    return [(norm(w[2]), w[0]) for s in d["segments"] for w in s["words"] if norm(w[2])], d


def overlap(cand, window):
    sm = SequenceMatcher(None, cand, window, autojunk=False)
    return sum(b.size for b in sm.get_matching_blocks()) / max(1, len(cand))


def score(model, cards, marks):
    res = defaultdict(int)
    by_era = defaultdict(lambda: defaultdict(int))
    cache = {}
    for key, v in marks.items():
        if v["a"] not in ("small", "medium"):
            continue
        date, ts = key.split("@")
        m, s = ts.split(":")
        t = int(m) * 60 + int(s)
        if date not in cache:
            try:
                cache[date] = words(model, date)[0]
            except FileNotFoundError:
                cache[date] = None
        W = cache[date]
        if W is None:
            res["no_result"] += 1
            continue
        c = cards[key]
        win = [w for w, st in W if t - 5 <= st <= t + 9]
        a = overlap(c["before"] + c["small"] + c["after"], win)
        b = overlap(c["before"] + c["medium"] + c["after"], win)
        pick = "small" if a > b + 1e-9 else "medium" if b > a + 1e-9 else "tie"
        res["spots"] += 1
        res["matched_" + pick] += 1
        era = "2012-2017" if int(date[:4]) <= 2017 else "2019-2026"
        by_era[era]["spots"] += 1
        if pick == v["a"]:
            res["correct"] += 1
            by_era[era]["correct"] += 1
    return res, by_era


def dropped(model, others, dates, win=10, min_others=12):
    """Windows where this model has far fewer words than the best other model."""
    n = 0
    words_missing = 0
    for d in dates:
        try:
            W = words(model, d)[0]
        except FileNotFoundError:
            continue
        refs = [words(o, d)[0] for o in others]
        end = int(max(t for _, t in W)) + win
        for s in range(0, end, win):
            c = lambda X: sum(1 for _, t in X if s <= t < s + win)
            mine, best = c(W), max(c(r) for r in refs)
            if best >= min_others and mine <= 0.3 * best:
                n += 1
                words_missing += best - mine
    return n, words_missing


def main():
    models = sys.argv[1:] or ["small.en", "medium.en", "mlx-turbo"]
    cards = load_cards()
    marks = json.loads((HERE / "review_results.json").read_text())
    dates = sorted({k.split("@")[0] for k in marks})
    print(f"{len(cards)} cards, {len(marks)} marks\n")
    print(f"{'model':12} {'spots':>5} {'correct':>7} {'acc%':>6}   old (2012-17)   new (2019-26)   tie  dropped windows (words)")
    for mod in models:
        r, e = score(mod, cards, marks)
        if not r["spots"]:
            print(f"{mod:12} no results yet")
            continue
        ds = lambda era: f"{e[era]['correct']}/{e[era]['spots']}"
        others = [o for o in ("small.en", "medium.en", "mlx-turbo", "mlx-large") if o != mod and (HERE / "results" / f"{dates[0]}.{o}.json").exists()]
        n, wm = dropped(mod, others, dates)
        print(f"{mod:12} {r['spots']:5} {r['correct']:7} {100*r['correct']/r['spots']:6.1f}   {ds('2012-2017'):>13}   {ds('2019-2026'):>13}   {r['matched_tie']:3}  {n} ({wm})")
    print("\nNotes: 'dropped windows' = 10 second windows where the model has 30% or fewer of the words the best other model has.")


if __name__ == "__main__":
    main()
