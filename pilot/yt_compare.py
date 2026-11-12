import json,re,difflib
norm=lambda w: re.sub(r"[^a-z0-9']","",w.lower())
def yt(id):
    d=json.load(open(f'yt/{id}.en.json3')); out=[]
    for e in d['events']:
        for s in e.get('segs',[]):
            w=norm(s.get('utf8','')); 
            if w: out.append((w,(e['tStartMs']+s.get('tOffsetMs',0))/1000))
    return out
def wh(date,m):
    d=json.load(open(f'results/{date}.{m}.json')); return [(norm(w[2]),w[0]) for s in d['segments'] for w in s['words'] if norm(w[2])]
for date,id in [('2025-07-06','-9ydVt79MmA'),('2026-06-07','7M9MQdD8OvA')]:
    y,s,m=yt(id),wh(date,'small.en'),wh(date,'medium.en')
    print(date,"words yt/small/medium:",len(y),len(s),len(m), "yt last t=%.0fs"%y[-1][1], "whisper last t=%.0fs"%m[-1][1], "yt first t=%.0fs"%y[0][1], "whisper first t=%.0fs"%m[0][1])
    f=lambda a,b: difflib.SequenceMatcher(None,[x[0] for x in a],[x[0] for x in b],autojunk=False).ratio()*100
    print("  agree yt~small %.1f  yt~medium %.1f  small~medium %.1f"%(f(y,s),f(y,m),f(s,m)))
    # sample spots where medium & small agree but yt differs (yt likely wrong) and names
    A=[x[0] for x in y];B=[x[0] for x in m]
    ops=[o for o in difflib.SequenceMatcher(None,A,B,autojunk=False).get_opcodes() if o[0]!='equal']
    print("  yt vs medium disagreement spots:",len(ops))
    import random;random.seed(1)
    for t,i1,i2,j1,j2 in random.sample(ops,8): print("   yt:[%s] medium:[%s]"%(' '.join(A[i1:i2]),' '.join(B[j1:j2])))
