"""Durable single-consumer queue beside the M1 manifest."""
import json
import os
import secrets
import sqlite3
import threading
import time
from contextlib import closing
from pathlib import Path
from . import manifest
from .formats import installed_formats
from .installer import install
from .platforms import discover, destination
from .storage import pinned

ACTIVE=("queued","resolving","downloading","verifying","installing")
RETRY=("cancelled","failed","needs_attention")


class RequestError(ValueError):
    def __init__(self,code,message):
        super().__init__(message)
        self.code=code


def ident():
    return secrets.token_hex(16)


class Queue:
    def __init__(self,folder,network,home=None):
        self.folder=Path(folder)
        self.folder.mkdir(mode=0o700,parents=True,exist_ok=True)
        self.network=network
        self.home=home
        self.guard=threading.Lock()
        self.worker=None
        self.closing=False
        self.lease=None
        if os.name=="posix":
            import fcntl
            self.lease=(self.folder/"decky-worker.lock").open("a")
            try:
                fcntl.flock(self.lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except OSError:
                self.lease.close()
                raise RequestError("busy","Another plugin instance owns the queue")
        with closing(self.db()) as db, db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, token TEXT UNIQUE NOT NULL,
                  data TEXT NOT NULL, platform TEXT NOT NULL, system TEXT NOT NULL, folder TEXT NOT NULL,
                  state TEXT NOT NULL, bytes INTEGER DEFAULT 0,total INTEGER,cancel INTEGER DEFAULT 0,
                  error TEXT, installation INTEGER, created INTEGER NOT NULL);
                CREATE INDEX IF NOT EXISTS jobs_state ON jobs(state,created);
            """)
            db.execute("""UPDATE jobs SET state='needs_attention',error='Session interrupted. Inspect destination before retry.'
                          WHERE state IN ('resolving','downloading','verifying','installing')""")
        self.wake()

    def db(self):
        db=sqlite3.connect(self.folder/"decky-jobs.sqlite3",timeout=5)
        db.row_factory=sqlite3.Row
        return db

    def preview(self,data,platform,system):
        if system not in data["systems"]:
            raise RequestError("unsupported","Choose a supported console")
        row=discover(platform,self.home)
        folder=destination(row,system,write=True)
        with pinned(folder) as handle:
            if Path(data["name"]).suffix.lower() not in installed_formats(handle,system):
                raise RequestError("unsupported","Installed console excludes this format")
            stamp=handle.stat()
            target=handle/data["name"]
            duplicate="filename exists" if target.exists() or target.is_symlink() else "no known match"
            checksum=data["checksums"].get("sha256")
            if checksum:
                with closing(manifest.catalog_reader(self.folder/"manifest.sqlite3")) as db:
                    if db.execute("""SELECT 1 FROM contents JOIN locations ON content_id=contents.id
                                     WHERE sha256=? AND root=? LIMIT 1""",(checksum,str(folder.parent))).fetchone():
                        duplicate="checksum recorded; installer will verify"
        return dict(destination=str(folder/data["name"]),duplicate=duplicate,
                    identity=[str(folder),str(stamp.st_dev),str(stamp.st_ino)])

    def enqueue(self,token,data,platform,system,identity):
        with closing(self.db()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            existing=db.execute("SELECT id FROM jobs WHERE token=?",(token,)).fetchone()
            if existing:
                return existing[0]
            self.capacity(db)
            db.execute("""DELETE FROM jobs WHERE id IN (SELECT id FROM jobs WHERE state IN
                       ('completed','cancelled','failed','needs_attention') ORDER BY created DESC LIMIT -1 OFFSET 200)""")
            key=ident()
            db.execute("""INSERT INTO jobs(id,token,data,platform,system,folder,state,total,created)
                          VALUES(?,?,?,?,?,?,'queued',?,?)""",
                       (key,token,json.dumps(data),platform,system,json.dumps(identity),data["size"],time.time_ns()))
        self.wake()
        return key

    @staticmethod
    def capacity(db):
        if db.execute("SELECT count(*) FROM jobs WHERE state IN (?,?,?,?,?)",ACTIVE).fetchone()[0]>=16:
            raise RequestError("queue_full","Queue limit is 16 active and waiting jobs")

    def change(self,key,retry=False):
        with closing(self.db()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            if retry:
                self.capacity(db)
                changed=db.execute("""UPDATE jobs SET state='queued',cancel=0,error=NULL,bytes=0
                    WHERE id=? AND state IN ('cancelled','failed','needs_attention')""",(key,)).rowcount
            else:
                changed=db.execute("""UPDATE jobs SET cancel=1,state=CASE WHEN state='queued' THEN 'cancelled' ELSE state END
                    WHERE id=? AND state IN ('queued','resolving','downloading','verifying')""",(key,)).rowcount
            if not changed:
                raise RequestError("state","Action unavailable in the current job state")
        if retry:
            self.wake()

    def jobs(self,key=None,page=1):
        with closing(self.db()) as db:
            sql="""SELECT id,platform,system,state,bytes,total,error,installation,
                   json_extract(data,'$.name') AS name FROM jobs """
            if key:
                row=db.execute(sql+"WHERE id=?",(key,)).fetchone()
                if not row:
                    raise RequestError("not_found","Unknown job")
                return dict(row)
            return [dict(r) for r in db.execute(sql+"ORDER BY created DESC LIMIT 20 OFFSET ?",((page-1)*20,))]

    def wake(self):
        with self.guard:
            if self.closing or self.worker is not None:
                return
            with closing(self.db()) as db:
                if not db.execute("SELECT 1 FROM jobs WHERE state='queued' LIMIT 1").fetchone():
                    return
            self.worker=threading.Thread(target=self.drain,name="rom-cli-transfer",daemon=True)
            self.worker.start()

    def drain(self):
        try:
            with closing(self.db()) as db:
                while not self.closing:
                    with db:
                        db.execute("BEGIN IMMEDIATE")
                        job=db.execute("SELECT * FROM jobs WHERE state='queued' ORDER BY created LIMIT 1").fetchone()
                        if not job:
                            break
                        db.execute("UPDATE jobs SET state='resolving' WHERE id=?",(job["id"],))
                    self.execute(db,job)
        finally:
            with self.guard:
                self.worker=None
            self.wake()

    def execute(self,db,job):
        key=job["id"]
        last=0
        def phase(state):
            with db:
                changed=db.execute("UPDATE jobs SET state=? WHERE id=? AND cancel=0",(state,key)).rowcount
                if not changed or self.closing:
                    raise InterruptedError("Transfer cancelled before publication")
        def progress(count,total):
            nonlocal last
            now=time.monotonic()
            if now-last>=0.5 or count==total:
                phase("downloading")
                with db:
                    db.execute("UPDATE jobs SET bytes=?,total=? WHERE id=?",(count,total,key))
                last=now
        try:
            data=json.loads(job["data"])
            self.network.check(data["provider"],data["url"])
            row=discover(job["platform"],self.home)
            phase("downloading")
            options=dict(opener=lambda url:self.network.open(data["provider"],url),progress=progress,
                         expected=data["size"],checksums=data["checksums"])
            with closing(manifest.connect(self.folder/"manifest.sqlite3")) as catalog:
                result=install(catalog,row,data["url"],job["system"],checksum=data["checksums"].get("sha256"),
                               phase=phase,transfer_options=options,expected_folder=tuple(json.loads(job["folder"])))
            with db:
                db.execute("UPDATE jobs SET state='completed',installation=? WHERE id=?",(result["id"],key))
        except Exception as exc:
            state="failed"
            if isinstance(exc,InterruptedError):
                state="needs_attention" if self.closing else "cancelled"
            elif isinstance(exc,(FileExistsError,PermissionError,FileNotFoundError,ValueError,OSError)):
                state="needs_attention"
            with db:
                db.execute("UPDATE jobs SET state=?,error=? WHERE id=?",(state,str(exc)[:300],key))

    def close(self):
        with self.guard:
            self.closing=True
            worker=self.worker
        if worker:
            worker.join()
        if self.lease:
            self.lease.close()

