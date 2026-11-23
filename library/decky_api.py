"""Version 1 RPC boundary. The client sends enums, bounded text and opaque IDs."""
import re
import sqlite3
import time
from contextlib import closing
from threading import BoundedSemaphore,Lock
from pathlib import Path
from . import manifest
from .cli import LIST
from .formats import installed_formats
from .platforms import discover,destination,PLATFORMS,FORMATS
from .providers import search
from .queue import RequestError,ident
from .reconcile import scan
from .storage import pinned

FIELDS={
    "list_platforms":(), "list_consoles":("platform",),
    "search":("provider","query","system","page","file_page"),"get_result":("result","platform","system"),
    "enqueue":("token","confirmed"),"list_jobs":("page",),"get_progress":("job",),
    "cancel":("job",),"retry":("job","confirmed"),"list_games":("page",),
    "inspect_game":("game",),"reconcile_preview":("platform","system"),
}


def validate(op,args):
    if type(op)!=str or op not in FIELDS or type(args)!=dict or set(args)!=set(FIELDS[op]):
        raise RequestError("invalid_request","Unknown operation or fields")
    for key,value in args.items():
        ok=False
        if key=="platform":
            ok=value in PLATFORMS
        elif key=="system":
            ok=(type(value)==str and value in FORMATS) or (op=="search" and value is None)
        elif key=="provider":
            ok=value in ("archive","mirror")
        elif key=="query":
            ok=type(value)==str and 1<=len(value.strip())<=80 and value.isprintable()
        elif key in ("page","file_page","game"):
            ok=type(value)==int and 1<=value<=(2147483647 if key=="game" else 1000)
        elif key=="confirmed":
            ok=value is True
        else:
            length=64 if key=="result" else 32
            ok=type(value)==str and bool(re.fullmatch(f"[0-9a-f]{{{length}}}",value))
        if not ok:
            raise RequestError("invalid_request","Invalid "+key)


class Service:
    def __init__(self,queue):
        self.queue=queue
        self.cache={}
        self.tokens={}
        self.lock=Lock()
        self.expensive=BoundedSemaphore(1)

    def remember(self,table,key,value):
        with self.lock:
            if len(table)>=256:
                table.pop(next(iter(table)))
            table[key]=(time.monotonic()+600,value)

    def recall(self,table,key):
        with self.lock:
            entry=table.get(key)
            if entry and entry[0]>time.monotonic():
                return entry[1]
        raise RequestError("expired","Selection expired. Search again.")

    def request(self,version,op,args):
        try:
            if type(version)!=int or version!=1:
                raise RequestError("version","Unsupported API version")
            validate(op,args)
            if op in ("search","reconcile_preview","list_consoles"):
                if not self.expensive.acquire(blocking=False):
                    raise RequestError("busy","Another library operation is running")
                try:
                    result=self.dispatch(op,args)
                finally:
                    self.expensive.release()
            else:
                result=self.dispatch(op,args)
            return {"version":1,"ok":True,"data":result}
        except RequestError as exc:
            code,message=exc.code,str(exc)
        except (OSError,ValueError,sqlite3.Error) as exc:
            code,message="unavailable",str(exc)[:300]
        except (KeyError,TypeError,AttributeError,RecursionError):
            code,message="invalid_source","Source metadata could not be read"
        return {"version":1,"ok":False,"error":{"code":code,"message":message}}

    def dispatch(self,op,a):
        queue=self.queue
        if op=="list_platforms":
            return [discover(s,queue.home) for s in PLATFORMS]
        if op=="list_consoles":
            row=discover(a["platform"],queue.home)
            consoles=[]
            for system in FORMATS:
                try:
                    path=destination(row,system,write=True)
                    with pinned(path) as handle:
                        formats=installed_formats(handle,system)
                    consoles.append(dict(system=system,path=str(path),formats=formats,available=True))
                except (OSError,ValueError) as exc:
                    consoles.append(dict(system=system,available=False,error=str(exc)))
            return consoles
        if op=="search":
            rows,more=search(queue.network,a["provider"],a["query"],a["system"],a["page"])
            start=(a["file_page"]-1)*20
            result=[]
            for row in rows[start:start+20]:
                self.remember(self.cache,row["id"],row)
                result.append({k:v for k,v in row.items() if k!="url"})
            return dict(results=result,more=more,more_files=len(rows)>start+20)
        if op=="get_result":
            data=self.recall(self.cache,a["result"])
            preview=queue.preview(data,a["platform"],a["system"])
            identity=preview.pop("identity")
            token=ident()
            self.remember(self.tokens,token,(data,a["platform"],a["system"],identity))
            return dict(**preview,token=token)
        if op=="enqueue":
            values=self.recall(self.tokens,a["token"])
            return {"id":queue.enqueue(a["token"],*values)}
        if op=="list_jobs":
            return queue.jobs(page=a["page"])
        if op=="get_progress":
            return queue.jobs(a["job"])
        if op in ("cancel","retry"):
            queue.change(a["job"],retry=op=="retry")
            return queue.jobs(a["job"])
        with closing(manifest.catalog_reader(queue.folder/"manifest.sqlite3")) as db:
            if op=="list_games":
                return [dict(row) for row in db.execute(LIST+" ORDER BY g.normalized_title,i.id LIMIT 20 OFFSET ?",((a["page"]-1)*20,))]
            if op=="inspect_game":
                return [dict(row) for row in db.execute(LIST+" WHERE g.id=? ORDER BY i.id LIMIT 100",(a["game"],))]
            findings=scan(db,discover(a["platform"],queue.home),a["system"])
            return dict(count=len(findings),findings=findings[:100])

