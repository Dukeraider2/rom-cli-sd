"""Generate the control recordings unchanged, then paired synthetic variations."""
import argparse
import json
import math
import random
import subprocess
from pathlib import Path
from .fixtures import generate, read_wav, save_wav, synthesize, SAMPLE_RATE
from .transcribe import digest

# id, target, spoken rendering, split, synthesis voice/rate, gain, SNR, saturate
SPEECH = [
    ("dev-fzero","F-Zero","F zero","dev","en",165,.01,None,None),
    ("dev-tetris","Tetris","Tetris","dev","en-us",210,.003,None,None),
    ("dev-fzero-clean","F-Zero","F zero","dev","en",165,1,None,None),
    ("dev-tetris-clean","Tetris","Tetris","dev","en-us",210,1,None,None),
    ("mario-three","Super Mario Bros. 3","Super Mario brothers three","test","en-us",155,1,None,None),
    ("mario-voice","Super Mario Bros. 3","Super Mario Bros. 3","test","en-sc",155,1,None,None),
    ("mario-rate","Super Mario Bros. 3","Super Mario Bros. 3","test","en-us",195,1,None,None),
    ("echoes-words","Metroid Prime 2: Echoes","Metroid Prime two, echoes","test","en-us",155,1,None,None),
    ("echoes-slow","Metroid Prime 2: Echoes","Metroid Prime 2: Echoes","test","en-us",125,1,None,None),
    ("street-words","Street Fighter II","Street Fighter two","test","en-us",155,1,None,None),
    ("street-three","Street Fighter III","Street Fighter three","test","en",170,1,None,None),
    ("sonic-voice","Sonic the Hedgehog","Sonic the Hedgehog","test","en-sc",155,1,None,None),
    ("sonic-quiet","Sonic the Hedgehog","Sonic the Hedgehog","test","en-us",155,.004,None,None),
    ("zelda-voice","The Legend of Zelda","The Legend of Zelda","test","en",155,1,None,None),
    ("zelda-clip","The Legend of Zelda","The Legend of Zelda","test","en-us",155,1,None,1100),
    ("chrono-snr15","Chrono Trigger","Chrono Trigger","test","en-us",155,1,15,None),
    ("chrono-snr3","Chrono Trigger","Chrono Trigger","test","en-us",155,1,3,None),
    ("chrono-cross","Chrono Cross","Chrono Cross","test","en",145,1,None,None),
    ("nba","NBA Jam","N B A Jam","test","en",175,1,None,None),
    ("metroid-fusion","Metroid Fusion","Metroid Fusion","test","en-sc",160,1,None,None),
    ("megaman","Mega Man X","Mega man ex","test","en-us",155,1,None,None),
    ("doom","Doom","Doom","test","en-us",230,.002,None,None),
]

def rms(values):
    return math.sqrt(sum(x*x for x in values)/len(values))

def build(folder):
    manifest=generate(folder,False)
    clips=manifest["clips"]
    for c in clips:
        c["split"]="control"
    def record(key,title,split,kind,params,samples):
        path=folder/(key+".wav")
        save_wav(path,samples)
        clips.append(dict(id=key,expected_title=title,split=split,kind=kind,
                          provenance=params,sha256=digest(path)))
    for key,title,words,split,voice,rate,gain,snr,clip in SPEECH:
        path=folder/(key+".wav")
        synthesize(words,path,voice,rate)
        samples=[round(x*gain) for x in read_wav(path)]
        params=dict(spoken=words,voice=voice,rate=rate,gain=gain,peak_clip=clip)
        if snr is not None:
            rng=random.Random(481)
            noise=[rng.uniform(-1,1) for _ in samples]
            scale=rms(samples)/rms(noise)*10**(-snr/20)
            mixed=[max(-32768,min(32767,round(x+n*scale))) for x,n in zip(samples,noise)]
            params.update(seed=481,target_snr_db=snr,actual_snr_db=20*math.log10(rms(samples)/rms([x-y for x,y in zip(mixed,samples)])))
            samples=mixed
        if clip:
            samples=[max(-clip,min(clip,x)) for x in samples]
        record(key,title,split,"synthetic",params,samples)
    for split,seed in (("dev",31),("test",79)):
        for kind in ("silence","room","game","clicks"):
            rng=random.Random(seed)
            values=[]
            duration=1.5 if split=="dev" else 2.25
            for i in range(int(SAMPLE_RATE*duration)):
                t=i/SAMPLE_RATE
                if kind=="room":
                    x=9*math.sin(2*math.pi*60*t)+rng.uniform(-3,3)
                elif kind=="game":
                    notes=(220,275,330) if split=="dev" else (294,392,330,262)
                    x=500*math.sin(2*math.pi*notes[int(t*4)%len(notes)]*t)
                elif kind=="clicks":
                    x=1200 if i%(607+seed)==0 else 0
                else:
                    x=0
                values.append(round(x))
            record(split+"-"+kind,None,split,"silence" if kind=="silence" else "noise",
                   dict(generator=kind,seed=seed,duration=duration),values)
    dev={c["sha256"] for c in clips if c["split"]=="dev"}
    if any(c["sha256"] in dev for c in clips if c["split"]=="test"):
        raise ValueError("Development and held-out files overlap")
    manifest["versions"]={k:subprocess.check_output([k,flag],text=True).splitlines()[0]
                          for k,flag in (("espeak","--version"),("ffmpeg","-version"))}
    (folder/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    return manifest

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    build(parser.parse_args().output)
