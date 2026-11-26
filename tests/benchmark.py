"""Repeatable manifest and console benchmarks using synthetic files only."""
import hashlib
import json
import platform
import statistics
import subprocess
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from library import manifest
from library.reconcile import scan
from library.cli import LIST


def elapsed(fn, repeats):
    times = []
    for _ in range(repeats):
        start = time.perf_counter_ns()
        fn()
        times.append((time.perf_counter_ns()-start)/1e6)
    return round(statistics.median(times),3)


def benchmark(n):
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        folder = base/"roms/nes"
        folder.mkdir(parents=True)
        start = time.perf_counter()
        db = manifest.connect(base/"manifest")
        init = 1000*(time.perf_counter()-start)
        try:
            with db:
                for i in range(1,n+1):
                    data = i.to_bytes(8,"big")
                    system = "nes" if i<=100 else "gba"
                    file = folder.parent/system/f"{i}.{system}"
                    if i<=100:
                        file.write_bytes(data)
                    sha = hashlib.sha256(data).hexdigest()
                    db.execute("INSERT INTO games VALUES(?,?,?,?,?)",(i,str(i),str(i),system,"fixture"))
                    db.execute("INSERT INTO releases(id,game_id) VALUES(?,?)",(i,i))
                    db.execute("INSERT INTO contents VALUES(?,?,?)",(i,sha,8))
                    db.execute("INSERT INTO files VALUES(?,?,?,?,?,?,?,?,?,?)",
                               (i,i,i,file.name,file.name,file.suffix,"image",0,None,"hashed"))
                    db.execute("INSERT INTO locations(id,path,root,content_id) VALUES(?,?,?,?)",(i,str(file),str(folder.parent),i))
                    db.execute("INSERT INTO installations VALUES(?,?,?,?,?,?,?)",(i,i,i,"emudeck","installed",None,None))
            db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            row = dict(root=str(folder.parent),status="ready",platform="emudeck")
            cpu = time.process_time()
            results = dict(games=n,init_ms=round(init,3),db_bytes=(base/"manifest").stat().st_size,
                           list_ms=elapsed(lambda:db.execute(LIST).fetchall(),5),
                           indexed_title_ms=elapsed(lambda:db.execute("SELECT id FROM games WHERE system=? AND normalized_title=?",("gba",str(n))).fetchone(),101),
                           duplicate_ms=elapsed(lambda:db.execute("SELECT id FROM contents WHERE sha256=?",(sha,)).fetchone(),101),
                           scan_100_ms=elapsed(lambda:scan(db,row,"nes"),5))
            results["query_scan_cpu_ms"]=round(1000*(time.process_time()-cpu),3)
            tracemalloc.start()
            scan(db,row,"nes")
            results["scan_python_peak_bytes"]=tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            return results
        finally:
            db.close()


if __name__=="__main__":
    print(json.dumps(dict(os=platform.platform(),python=platform.python_version(),
                          sqlite=manifest.sqlite3.sqlite_version,rows=[benchmark(1000),benchmark(10000)]),indent=2))

