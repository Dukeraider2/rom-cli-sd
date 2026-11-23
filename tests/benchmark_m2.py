"""Measure one session with an 8 MiB local HTTP fixture, including its server."""
import json
import os
import platform
import statistics
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from library.decky_api import Service
from library.provider_http import Network
from library.queue import Queue


def counters():
    if sys.platform=="linux":
        fields=dict(line.split(":",1) for line in Path("/proc/self/status").read_text().splitlines())
        io=dict(line.split(":") for line in Path("/proc/self/io").read_text().splitlines())
        return int(fields["VmRSS"].split()[0])*1024,int(io["write_bytes"])
    import ctypes as c
    from ctypes import wintypes as w
    class Memory(c.Structure):
        _fields_=[("cb",w.DWORD),("faults",w.DWORD),("peak",c.c_size_t),("working",c.c_size_t),
                  ("others",c.c_size_t*6)]
    c.windll.kernel32.GetCurrentProcess.restype=w.HANDLE
    handle=w.HANDLE(c.windll.kernel32.GetCurrentProcess())
    memory=Memory()
    memory.cb=c.sizeof(memory)
    io=(c.c_ulonglong*6)()
    if not c.windll.psapi.GetProcessMemoryInfo(handle,c.byref(memory),memory.cb) or not c.windll.kernel32.GetProcessIoCounters(handle,c.byref(io)):
        raise OSError("Cannot read process counters")
    return memory.working,io[4]


def main():
    size=8*1024**2
    block=b"X"*65536
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            index=self.path=="/"
            data=b'<a href="Demo.gba">Demo</a>'
            self.send_response(200)
            self.send_header("Content-Length",str(len(data) if index else size))
            self.end_headers()
            if index:
                self.wfile.write(data)
            else:
                for _ in range(size//len(block)):
                    self.wfile.write(block)
        def log_message(self,*args):
            pass
    class MeasuredQueue(Queue):
        writes=0
        def db(self):
            db=super().db()
            def trace(sql):
                if sql.lstrip().split(" ",1)[0].upper() in ("UPDATE","DELETE","INSERT"):
                    self.writes+=1
            db.set_trace_callback(trace)
            return db
    with tempfile.TemporaryDirectory() as tmp, ThreadingHTTPServer(("127.0.0.1",0),Handler) as server:
        threading.Thread(target=server.serve_forever,daemon=True).start()
        home=Path(tmp)
        (home/"roms/gba").mkdir(parents=True)
        cfg=home/".config/EmuDeck/settings.sh"
        cfg.parent.mkdir(parents=True)
        cfg.write_text("romsPath=~/roms")
        q=MeasuredQueue(home/"catalog",Network(f"http://127.0.0.1:{server.server_port}/",True),home)
        try:
            api=Service(q)
            def rpc(op,**args):
                r=api.request(1,op,args)
                if not r["ok"]:
                    raise ValueError(r)
                return r["data"]
            started=time.perf_counter()
            result=rpc("search",provider="mirror",query="demo",page=1,file_page=1,system="gba")["results"][0]
            search_ms=(time.perf_counter()-started)*1000
            preview=rpc("get_result",result=result["id"],platform="emudeck",system="gba")
            before=counters()
            peak=before[0]
            cpu=time.process_time()
            start=time.perf_counter()
            job=rpc("enqueue",token=preview["token"],confirmed=True)["id"]
            while True:
                row=rpc("get_progress",job=job)
                peak=max(peak,counters()[0])
                if row["state"]=="completed":
                    break
                if row["state"] in ("failed","needs_attention","cancelled") or time.perf_counter()-start>30:
                    raise ValueError(row)
                time.sleep(.005)
            elapsed=time.perf_counter()-start
            used=time.process_time()-cpu
            after=counters()
            timings=[]
            for _ in range(50):
                start=time.perf_counter_ns()
                rpc("get_progress",job=job)
                timings.append((time.perf_counter_ns()-start)/1e6)
            start_cpu=time.process_time()
            time.sleep(1)
            idle_cpu=time.process_time()-start_cpu
            print(json.dumps(dict(host=platform.platform(),python=platform.python_version(),size=size,
                seconds=round(elapsed,3),mib_per_s=round(size/1048576/elapsed,2),
                cpu_s=round(used,3),cpu_one_core_pct=round(used/elapsed*100,1),
                rss_baseline=before[0],rss_sampled_peak=peak,process_write_bytes=after[1]-before[1],
                queue_write_statements=q.writes,search_rpc_ms=round(search_ms,2),
                progress_rpc_median_ms=round(statistics.median(timings),3),
                idle_worker=q.worker is not None,idle_1s_cpu_ms=round(idle_cpu*1000,2))))
        finally:
            q.close()
            server.shutdown()

if __name__=="__main__":
    main()

