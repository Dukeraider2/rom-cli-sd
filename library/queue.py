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
from .recovery import inspect_jobs

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
            if "attempt" not in {r[1] for r in db.execute("PRAGMA table_info(jobs)")}:
                db.execute("ALTER TABLE jobs ADD COLUMN attempt INTEGER")
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
            linked=target.is_symlink()
            exists=target.exists()
            duplicate="existing filename" if exists else "no known match"
            checksum=data["checksums"].get("sha256")
            if checksum:
                with closing(manifest.catalog_reader(self.folder/"manifest.sqlite3")) as db:
                    if db.execute("""SELECT 1 FROM contents JOIN locations ON content_id=contents.id
                                     WHERE sha256=? AND root=? LIMIT 1""",(checksum,str(folder.parent))).fetchone():
                        duplicate="checksum recorded; installer will verify"
            if linked:
                duplicate="Linked destination cannot be used"
            elif exists and not checksum:
                duplicate="File already exists. Inspect it in Installed library."
        return dict(destination=str(folder/data["name"]),duplicate=duplicate,
                    can_install=not linked and (not exists or bool(checksum)),
                    identity=[str(folder),str(stamp.st_dev),str(stamp.st_ino)])

    def enqueue(self,token,data,platform,system,identity):
        if self.closing:
            raise RequestError("busy","Session is closing")
        with closing(self.db()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            existing=db.execute("SELECT id FROM jobs WHERE token=?",(token,)).fetchone()
            if existing:
                return existing[0]
            existing=db.execute("""SELECT id FROM jobs WHERE platform=? AND system=? AND folder=?
                                 AND json_extract(data,'$.id')=? AND state IN (?,?,?,?,?)""",
                                (platform,system,json.dumps(identity),data["id"],*ACTIVE)).fetchone()
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
        if self.closing:
            raise RequestError("busy","Session is closing")
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
        else:
            self.network.abort(key)

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
                if self.closing and self.lease:
                    self.lease.close()
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
                with db:
                    if self.closing or not db.execute("""UPDATE jobs SET bytes=?,total=?
                            WHERE id=? AND cancel=0""",(count,total,key)).rowcount:
                        raise InterruptedError("Transfer cancelled before publication")
                last=now
        try:
            data=json.loads(job["data"])
            self.network.check(data["provider"],data["url"])
            row=discover(job["platform"],self.home)
            phase("downloading")
            options=dict(opener=lambda url:self.network.open(data["provider"],url,scope=key),progress=progress,
                         expected=data["size"],checksums=data["checksums"])
            with closing(manifest.connect(self.folder/"manifest.sqlite3")) as catalog:
                identity=tuple(json.loads(job["folder"]))
                checksum=data["checksums"].get("sha256")
                if job["attempt"]:
                    folder=destination(row,job["system"],write=True)
                    with pinned(folder) as handle:
                        stamp=handle.stat()
                        if (str(folder),str(stamp.st_dev),str(stamp.st_ino))!=identity:
                            raise ValueError("Confirmed storage changed; select the destination again")
                        inspect_jobs(catalog,row,folder,handle,True,job["attempt"])
                    previous=catalog.execute("""SELECT c.sha256 FROM downloads d JOIN files f ON d.file_id=f.id
                        JOIN contents c ON c.id=f.content_id WHERE d.id=?""",(job["attempt"],)).fetchone()
                    if previous:
                        checksum=previous[0]
                def remember(attempt):
                    with db:
                        db.execute("UPDATE jobs SET attempt=? WHERE id=?",(attempt,key))
                result=install(catalog,row,data["url"],job["system"],checksum=checksum,
                               phase=phase,transfer_options=options,expected_folder=identity,
                               on_attempt=remember,require_known_existing=True)
            with db:
                db.execute("UPDATE jobs SET state='completed',installation=? WHERE id=?",(result["id"],key))
        except Exception as exc:
            state="failed"
            cancelled=db.execute("SELECT cancel FROM jobs WHERE id=?",(key,)).fetchone()[0]
            if self.closing or cancelled or isinstance(exc,InterruptedError):
                state="needs_attention" if self.closing else "cancelled"
            elif isinstance(exc,(FileExistsError,PermissionError,FileNotFoundError,ValueError,OSError)):
                state="needs_attention"
            with db:
                db.execute("UPDATE jobs SET state=?,error=? WHERE id=?",(state,str(exc)[:300],key))

    def close(self):
        with self.guard:
            self.closing=True
            worker=self.worker
        self.network.stop()
        if worker:
            worker.join(timeout=4)
        if self.lease and (not worker or not worker.is_alive()):
            self.lease.close()

