import json,re,difflib,collections
import vocab
n=lambda w: re.sub(r"[^a-z0-9']","",w.lower())
terms={n(w) for k in ("characters","places","groups","theology") for w in vocab.CATALOG[k] if " " not in w}|{n(b) for b in vocab.BOOKS if " " not in b}
def load(d,m): return json.load(open(f'results/{d}.{m}.json'))
def toks(r): return [(n(w[2]),w[0],w[2].strip()) for s in r['segments'] for w in s['words'] if n(w[2])]
for d in ["2012-08-05","2014-07-27","2017-07-02"]:
    try: base=toks(load(d,'small.en')); med=toks(load(d,'medium.en'))
    except Exception as e: print(d,e); continue
    print(f"\n== {d}  baseline words {len(base)}")
    c=lambda t: collections.Counter(x[0] for x in t if x[0] in terms)
    cb,cm=c(base),c(med)
    for v in ("hot","prompt"):
        try: r=load(d,f'small.en+{v}')
        except Exception: continue
        t=toks(r); cv=c(t)
        sm=difflib.SequenceMatcher(None,[x[0] for x in base],[x[0] for x in t],autojunk=False)
        ops=[o for o in sm.get_opcodes() if o[0]!='equal']
        print(f" {v}: {r['speed_x_realtime']:.1f}x, words {len(t)}, agree w/ baseline {sm.ratio()*100:.1f}%, agree w/ medium {difflib.SequenceMatcher(None,[x[0] for x in med],[x[0] for x in t],autojunk=False).ratio()*100:.1f}% (baseline~medium {difflib.SequenceMatcher(None,[x[0] for x in med],[x[0] for x in base],autojunk=False).ratio()*100:.1f}%), vocab-term hits {sum(cv.values())} vs baseline {sum(cb.values())} vs medium {sum(cm.values())}")
        shown=0
        for tag,i1,i2,j1,j2 in ops:
            A=' '.join(x[2] for x in base[i1:i2]); B=' '.join(x[2] for x in t[j1:j2])
            if any(x[0] in terms or x[2][:1].isupper() for x in base[i1:i2]+t[j1:j2]) and shown<10 and max(i2-i1,j2-j1)<=4:
                print(f"    {int(base[i1][1]//60)}:{int(base[i1][1]%60):02d}  baseline [{A}] -> {v} [{B}]"); shown+=1
