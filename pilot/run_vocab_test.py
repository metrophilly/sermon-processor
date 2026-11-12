import json,time,sys
from pathlib import Path
from faster_whisper import WhisperModel
import vocab, run_pilot
HERE=Path(__file__).parent; OUT=HERE/"results"
DATES=["2012-08-05","2014-07-27","2017-07-02"]
man={x["spokenDate"][:10]:x for x in json.loads((HERE/"manifest.json").read_text())}
model=WhisperModel("small.en",device="cpu",compute_type="int8")
for variant in ["hot","prompt"]:
    for d in DATES:
        out=OUT/f"{d}.small.en+{variant}.json"
        if out.exists(): continue
        hw,n=vocab.hotwords_for(man[d],model.hf_tokenizer)
        kw=dict(hotwords=hw) if variant=="hot" else dict(initial_prompt=hw)
        audio=run_pilot.decode(HERE/"audio"/f"{d}.mp3"); t0=time.time()
        segs,_=model.transcribe(audio,language="en",word_timestamps=True,vad_filter=False,**kw)
        rows=[{"start":float(s.start),"end":float(s.end),"text":s.text.strip(),"avg_logprob":float(s.avg_logprob),"no_speech_prob":float(s.no_speech_prob),
               "words":[[float(w.start),float(w.end),w.word,float(w.probability)] for w in (s.words or [])]} for s in segs]
        el=time.time()-t0
        out.write_text(json.dumps({"date":d,"model":f"small.en+{variant}","terms":n,"hotwords":hw,"audio_seconds":len(audio)/16000,"elapsed_seconds":el,"speed_x_realtime":len(audio)/16000/el,"segments":rows}))
        print(d,variant,f"{len(audio)/16000/el:.1f}x",flush=True)
