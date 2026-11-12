import json,re,difflib,glob,random
def toks(d): return [(re.sub(r"[^a-z0-9']","",w[2].lower()),w[0],w[2]) for s in d['segments'] for w in s['words'] if re.sub(r"[^a-z0-9']","",w[2].lower())]
out=[];allc=0
for f in sorted(glob.glob('results/*.small.en.json')):
    d=f[8:18]; a=toks(json.load(open(f))); b=toks(json.load(open(f'results/{d}.medium.en.json')))
    sm=difflib.SequenceMatcher(None,[x[0] for x in a],[x[0] for x in b],autojunk=False)
    for tag,i1,i2,j1,j2 in sm.get_opcodes():
        if tag=='equal': continue
        allc+=1
        ctx=' '.join(x[2] for x in a[max(0,i1-4):i1]).strip()
        out.append((d,a[i1][1] if i1<len(a) else 0,ctx,' '.join(x[2] for x in a[i1:i2]),' '.join(x[2] for x in b[j1:j2])))
json.dump(out,open('diffs.json','w'))
print("total disagreement spots:",allc)
random.seed(3)
for d,t,ctx,x,y in random.sample(out,16):
    print(f"{d} {int(t//60)}:{int(t%60):02d} ...{ctx} | small: [{x}] medium: [{y}]")
