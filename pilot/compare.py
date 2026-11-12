import json,re,difflib,glob,statistics as st
def words(d): return [re.sub(r"[^a-z0-9']","",w[2].lower()) for s in d['segments'] for w in s['words'] if re.sub(r"[^a-z0-9']","",w[2].lower())]
def lp(d): 
    ws=[w[3] for s in d['segments'] for w in s['words']]; return st.mean(ws), sum(p<0.5 for p in ws)/len(ws)
print("date        mins  small x  med x  agree%  small lowconf  med lowconf  words(s/m)")
tot=[0,0,0]
for f in sorted(glob.glob('results/*.small.en.json')):
    d=f[8:18]; s=json.load(open(f)); m=json.load(open(f'results/{d}.medium.en.json'))
    a,b=words(s),words(m); r=difflib.SequenceMatcher(None,a,b,autojunk=False).ratio()
    ls,lm=lp(s),lp(m)
    print(f"{d} {s['audio_seconds']/60:5.1f} {s['speed_x_realtime']:7.1f} {m['speed_x_realtime']:6.1f} {r*100:7.1f} {ls[1]*100:12.1f}% {lm[1]*100:11.1f}%  {len(a)}/{len(b)}")
    tot[0]+=s['audio_seconds']; tot[1]+=s['elapsed_seconds']; tot[2]+=m['elapsed_seconds']
print(f"total audio {tot[0]/3600:.1f}h  small {tot[1]/3600:.2f}h ({tot[0]/tot[1]:.1f}x)  medium {tot[2]/3600:.2f}h ({tot[0]/tot[2]:.1f}x)")
print("700 sermons @ avg length:", f"small {tot[1]/10*700/3600:.0f}h, medium {tot[2]/10*700/3600:.0f}h")
