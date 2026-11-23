"""Offline Phase 2 comparison. One configuration, or every paired configuration."""
import argparse
import difflib
import json
import math
import os
import platform
import random
import threading
import time
import tracemalloc
from pathlib import Path
from .benchmark import normalize,catalog_match,MARGIN,MATCH_THRESHOLD
from .fixtures import read_wav
from .reliability_fixtures import rms
from .transcribe import WhisperAdapter,MODELS,ENGINE_REVISION,digest,validate_audio,TranscriptionError

CONFIGS={"beam4":("beam",4,False),"greedy4":("greedy",4,False),"beam2":("beam",2,False),
         "gate4":("beam",4,True)}
DISTRACTORS=["Super Mario Bros.","Super Mario World","New Super Mario Bros.","Super Mario Land",
    "Metroid Prime 3: Corruption","Metroid Prime Hunters","Metroid Prime Remastered","Super Metroid",
    "Sonic Adventure","Sonic Adventure 2","Sonic the Hedgehog 3","Sonic CD","Sonic Spinball",
    "Street Fighter","Street Fighter Alpha 2","Street Fighter IV","Super Street Fighter II",
    "Mega Man","Mega Man 4","Mega Man X2","Mega Man X3","Mega Man Zero","Mega Man Zero 2",
    "The Legend of Zelda: The Minish Cap","Zelda II: The Adventure of Link","Chrono Trigger DS",
    "Tetris DX","Tetris Plus","NBA Jam Tournament Edition","F-Zero X","F-Zero GX","Final Doom","Doom II"]

def energy(path,cancel=None,deadline=None):
    def check():
        if cancel and cancel.is_set():
            raise TranscriptionError("cancelled","Gate cancelled")
        if deadline is not None and time.monotonic()>=deadline:
            raise TranscriptionError("timeout","Gate timed out")
    check()
    validate_audio(path)
    values=read_wav(path)
    peak=0.
    for i in range(0,len(values),320):
        check()
        peak=max(peak,rms(values[i:i+320]))
    return peak

def calibrate(fixtures,folder):
    dev=[(energy(folder/(f["id"]+".wav")),bool(f["expected_title"])) for f in fixtures if f["split"]=="dev"]
    scores=[]
    for threshold in (1,4,12,24,48,96,192):
        scores.append(dict(threshold=threshold,reject_speech=sum(v<t and s for v,s in dev for t in [threshold]),
                           accept_noise=sum(v>=threshold and not s for v,s in dev)))
    best=min(scores,key=lambda s:(s["reject_speech"],s["accept_noise"],s["threshold"]))
    return best["threshold"],scores

def title_key(title):
    mapping={"ii":"2","iii":"3","iv":"4","brothers":"bros"}
    return " ".join(mapping.get(w,w) for w in normalize(title).split())

def ranked(text,catalog):
    key=title_key(text)
    if not key:
        return {"status":"empty","candidates":[]}
    scores=sorted(((difflib.SequenceMatcher(None,key,title_key(t)).ratio(),t) for t in catalog),reverse=True)
    exact=[t for score,t in scores if score==1]
    if len(exact)==1:
        return {"status":"match","candidates":exact}
    if scores[0][0]<MATCH_THRESHOLD:
        return {"status":"no_match","candidates":[]}
    choices=[t for score,t in scores if scores[0][0]-score<MARGIN]
    return {"status":"match" if len(choices)==1 else "ambiguous","candidates":choices}

def compare(args):
    manifest=json.loads((args.fixtures/"manifest.json").read_text())
    clips=manifest["clips"]
    if manifest["fixture_mode"]!="synthetic_speech" or any(f["kind"] not in ("synthetic","silence","noise") for f in clips):
        raise ValueError("Expected generated synthetic Phase 2 fixtures")
    for f in clips:
        path=args.fixtures/(f["id"]+".wav")
        if path.resolve().parent!=args.fixtures.resolve() or path.is_symlink() or digest(path)!=f["sha256"]:
            raise ValueError("Invalid fixture path or digest")
    original=json.loads((Path(__file__).parent/"catalog.json").read_text())
    small=list(dict.fromkeys(original+[f["expected_title"] for f in clips if f["expected_title"]]))
    catalogs={"small":small,"large":small+DISTRACTORS}
    threshold,training=calibrate(clips,args.fixtures)
    tracemalloc.start()
    for f in clips:
        energy(args.fixtures/(f["id"]+".wav"))
    heap=tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    report=dict(schema=1,measurement_class="real_engine_synthetic_only",revision=ENGINE_REVISION,
                engine_sha256=digest(args.engine),system=platform.platform(),python=platform.python_version(),
                cpu=next((s for s in Path("/proc/cpuinfo").read_text().splitlines() if s.startswith("model name")),"unknown"),
                allocated_cpus=len(os.sched_getaffinity(0)),manifest=manifest,catalogs=catalogs,threshold=threshold,
                gate_training=training,gate_peak_python_heap_bytes=heap,gate_temp_bytes=0,models={},rows=[])
    for model in ([args.model] if args.model else MODELS):
        for config in ([args.config] if args.config else CONFIGS):
            decoder,threads,gated=CONFIGS[config]
            adapter=WhisperAdapter(args.engine,args.models_dir,threads=threads,decoder=decoder,timeout_seconds=60)
            report["models"][model]=adapter._model(model)[1]
            order=[(f,rep) for rep in (1,2) for f in clips]
            random.Random(719).shuffle(order)
            ordinal=0
            for fixture,rep in order:
                key=fixture["id"]
                path=args.fixtures/(key+".wav")
                start=time.perf_counter()
                gate_ms=gate_cpu=0.
                score=None
                if gated:
                    cpu=time.process_time()
                    score=energy(path,deadline=time.monotonic()+1)
                    gate_cpu=time.process_time()-cpu
                    gate_ms=(time.perf_counter()-start)*1000
                rejected=gated and score<threshold
                if rejected:
                    result={"ok":True,"text":"","metrics":{}}
                else:
                    ordinal+=1
                    result=adapter.transcribe(path,model)
                elapsed=(time.perf_counter()-start)*1000
                text=result.get("text","")
                row=dict(fixture=key,split=fixture["split"],expected=fixture["expected_title"],model=model,
                         config=config,decoder=decoder,threads=threads,repeat=rep,ok=result["ok"],error=result.get("error"),
                         transcript=text,normalized=normalize(text),title_normalized=title_key(text),
                         fresh_process=ordinal if not rejected else None,metrics=result.get("metrics",{}),
                         elapsed_ms=elapsed,gate_score=score,gate_rejected=rejected,gate_ms=gate_ms,gate_cpu_s=gate_cpu,
                         retrieval={k:{"original":catalog_match(text,c),"title_aware":ranked(text,c)} for k,c in catalogs.items()})
                report["rows"].append(row)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,separators=(",",":"))+"\n")
    if any(not row["ok"] for row in report["rows"]):
        raise RuntimeError("Engine failure; inspect per-row errors")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for name in ("engine","models-dir","fixtures","output"):
        p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--model",choices=MODELS)
    p.add_argument("--config",choices=CONFIGS)
    compare(p.parse_args())
