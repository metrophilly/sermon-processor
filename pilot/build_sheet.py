import json,re,difflib,glob,random,html
NORM={'gonna':'going to','kinda':'kind of','wanna':'want to','gotta':'got to','sorta':'sort of'}
DIG={'0':'zero','1':'one','2':'two','3':'three','4':'four','5':'five','6':'six','7':'seven','8':'eight','9':'nine','10':'ten'}
FILL={'um','uh','you','know','like','so','and','but','well','just','the','a','i','mean','yeah','okay','right'}
def n(w):
    w=re.sub(r"[^a-z0-9']","",w.lower()); w=NORM.get(w,w); return DIG.get(w,w)
def flat(d): return [(n(w[2]),w[0],w[2]) for s in d['segments'] for w in s['words'] if n(w[2])]
def key(ws): return ' '.join(x for w in ws for x in n(w[2]).split() if x)
cands=[]
for f in sorted(glob.glob('results/*.small.en.json')):
    d=f[8:18]; a=flat(json.load(open(f))); b=flat(json.load(open(f'results/{d}.medium.en.json')))
    sm=difflib.SequenceMatcher(None,[x[0] for x in a],[x[0] for x in b],autojunk=False)
    for tag,i1,i2,j1,j2 in sm.get_opcodes():
        if tag=='equal': continue
        A=[x[0] for x in a[i1:i2]]; B=[x[0] for x in b[j1:j2]]
        if ' '.join(A).replace("'","").replace(' ','')==' '.join(B).replace("'","").replace(' ',''): continue  # spacing/contraction only
        if set(A+B)<=FILL: continue   # filler-only
        if tag=='delete' or tag=='insert':
            if max(len(A),len(B))<3: continue
        t=(a[i1][1] if i1<len(a) else b[j1][1])
        cands.append(dict(date=d,t=t,before=' '.join(x[2] for x in a[max(0,i1-8):i1]),small=' '.join(x[2] for x in a[i1:i2]).strip(),medium=' '.join(x[2] for x in b[j1:j2]).strip(),after=' '.join(x[2] for x in a[i2:i2+8]),
            score=(3 if any(x[2][:1].isupper() for x in a[i1:i2]+b[j1:j2]) else 0)+(2 if tag=='replace' else 0)+(2 if max(len(A),len(B))>=3 else 0)))
random.seed(7)
by={}
for c in cands: by.setdefault(c['date'],[]).append(c)
pick=[]
for d,l in by.items():
    l.sort(key=lambda c:-c['score']); top=l[:30]; random.shuffle(top); pick+=sorted(top[:8],key=lambda c:c['t'])
print(len(cands),"substantive candidates;",len(pick),"in sheet")
rows=[]
for i,c in enumerate(pick):
    m,s=int(c['t']//60),int(c['t']%60)
    rows.append(f'''<div class=r data-i={i} data-id="{c['date']}@{m}:{s:02d}"><div class=h><b>{c['date']}</b> at {m}:{s:02d} <button onclick="play('{c['date']}',{max(0,c['t']-4):.1f})">Play 12s</button></div>
<p class=ctx>…{html.escape(c['before'])} <span class=x>[?]</span> {html.escape(c['after'])}…</p>
<label><input type=radio name=q{i} value=small> small: <b>{html.escape(c['small']) or '(nothing)'}</b></label>
<label><input type=radio name=q{i} value=medium> medium: <b>{html.escape(c['medium']) or '(nothing)'}</b></label>
<label><input type=radio name=q{i} value=both> both fine</label>
<label><input type=radio name=q{i} value=neither> neither</label>
<input class=fix placeholder="what was actually said (optional)" data-f={i}></div>''')
open('review.html','w').write('''<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Pilot Review Sheet</title>
<style>body{font:16px system-ui;max-width:760px;margin:0 auto;padding:16px;background:#fff;color:#111}@media(prefers-color-scheme:dark){body{background:#111;color:#eee}}
.r{border:1px solid #8884;border-radius:8px;padding:12px;margin:12px 0}.ctx{margin:8px 0}.x{background:#fc03;padding:0 4px;border-radius:3px}label{display:block;padding:4px 0}
.fix{width:100%;margin-top:6px;padding:6px;box-sizing:border-box}button{padding:6px 12px}#bar{position:sticky;top:0;background:inherit;padding:8px 0;border-bottom:1px solid #8884}</style>
<div id=bar><b id=n>0</b> of '''+str(len(pick))+''' marked <button onclick="exp()">Copy results as JSON</button> <audio id=a></audio></div>
<p>Listen to each spot, mark which model wrote what was actually said. Answers save in this browser as you go.</p>'''+'\n'.join(rows)+'''
<script>
let stop;function play(d,t){const a=document.getElementById('a');a.src='audio/'+d+'.mp3';a.currentTime=t;a.play();clearTimeout(stop);stop=setTimeout(()=>a.pause(),12000)}
const S=JSON.parse(localStorage.getItem('pilot')||'{}');
document.querySelectorAll('.r').forEach(r=>{const id=r.dataset.id;const v=S[id];if(v){const i=r.querySelector('input[value='+v.a+']');if(i)i.checked=true;r.querySelector('.fix').value=v.f||''}
r.addEventListener('input',()=>{const c=r.querySelector('input[type=radio]:checked');S[id]={a:c&&c.value,f:r.querySelector('.fix').value};localStorage.setItem('pilot',JSON.stringify(S));cnt()})});
function cnt(){document.getElementById('n').textContent=Object.values(S).filter(x=>x.a).length}cnt();
function exp(){navigator.clipboard.writeText(JSON.stringify(S,null,1));alert('Copied')}
</script>''')
