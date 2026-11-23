"""Combine measured shards, validate pairing, summarize with explicit denominators."""
import argparse
import gzip
import json
from collections import Counter
from pathlib import Path
from statistics import median

def pct(values, q):
    if not values:
        return None
    seq=sorted(values)
    pos=q*(len(seq)-1)
    i=int(pos)
    return round(seq[i]+(seq[min(i+1,len(seq)-1)]-seq[i])*(pos-i),3)

def summarize(rows):
    speech=[r for r in rows if r["expected"] is not None]
    noise=[r for r in rows if r["expected"] is None]
    proc=[r for r in rows if r["fresh_process"] is not None]
    times=[r["elapsed_ms"] for r in speech]
    return dict(rows=len(rows),errors=sum(not r["ok"] for r in rows),speech=len(speech),non_speech=len(noise),
        raw_exact=sum(r["ok"] and r["transcript"]==r["expected"] for r in speech),
        normalized_exact=sum(r["ok"] and r["normalized"]==r["expected_normalized"] for r in speech),
        gate_false_rejections=sum(r["gate_rejected"] for r in speech),
        nonempty_false_inputs=sum(bool(r["transcript"]) for r in noise),
        non_speech_sent_to_engine=sum(r["fresh_process"] is not None for r in noise),
        retrieval={size:dict(original=sum(r["retrieval"][size]["original"]==r["expected"] for r in speech),
                   title_aware=sum(r["retrieval"][size]["title_aware"]=={"status":"match","candidates":[r["expected"]]} for r in speech),
                   ambiguous=sum(r["retrieval"][size]["title_aware"]["status"]=="ambiguous" for r in speech))
                   for size in ("small","large")},title_p50_ms=pct(times,.5),title_p95_ms=pct(times,.95),
        first_process_ms=next((r["elapsed_ms"] for r in proc if r["fresh_process"]==1),None),
        subsequent_process_p50_ms=pct([r["elapsed_ms"] for r in proc if r["fresh_process"]>1],.5),
        child_cpu_s=round(sum(r["metrics"].get("cpu_seconds",0) for r in proc),3),
        sampled_peak_child_rss=max((r["metrics"].get("peak_rss_bytes_sampled") or 0 for r in proc),default=None),
        peak_final_temp_bytes=max((r["metrics"].get("temporary_disk_bytes",0) for r in proc),default=0),
        gate_cpu_s=round(sum(r["gate_cpu_s"] for r in rows),4),
        gate_p50_ms=pct([r["gate_ms"] for r in rows],.5),gate_p95_ms=pct([r["gate_ms"] for r in rows],.95))

def aggregate(paths):
    groups={}
    common=None
    hosts=[]
    for path in paths:
        shard=json.loads(path.read_text(encoding="utf8"))
        signature={k:shard[k] for k in ("revision","engine_sha256","manifest","catalogs","threshold","gate_training")}
        if common is None:
            common=signature
        if common!=signature or shard["measurement_class"]!="real_engine_synthetic_only":
            raise ValueError("Incompatible inputs or fixture provenance")
        host={k:v for k,v in shard.items() if k not in (*signature,"rows")}
        index=len(hosts)
        hosts.append(host)
        for r in shard["rows"]:
            r["host_index"]=index
            groups.setdefault(r["model"]+"/"+r["config"],[]).append(r)
    ids={f["id"] for f in common["manifest"]["clips"]}
    expected={(k,i) for k in ids for i in (1,2)}
    if set(groups)!={m+"/"+c for m in ("tiny.en","base.en") for c in ("beam4","greedy4","beam2","gate4")}:
        raise ValueError("Incomplete experiment grid")
    summaries={}
    for name,rows in groups.items():
        if Counter((r["fixture"],r["repeat"]) for r in rows)!=Counter(expected):
            raise ValueError("Unpaired or duplicate fixture rows")
        summaries[name]={split:summarize([r for r in rows if split=="all" or r["split"]==split])
                         for split in ("all","control","dev","test")}
    return dict(**common,hosts=hosts,summary=summaries,rows=[r for name in sorted(groups) for r in groups[name]])

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("inputs",nargs="+",type=Path)
    a=p.parse_args()
    result=aggregate(a.inputs)
    a.output.write_bytes(gzip.compress(json.dumps(result,separators=(",",":")).encode(),mtime=0))
    print(f"Verified {len(result['rows'])} rows across {len(result['summary'])} conditions")
