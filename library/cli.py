"""One operation per process. stdout is JSON, errors use stderr and exit 1."""
import argparse
import json
import os
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from . import manifest
from .installer import install
from .platforms import discover, destination, FORMATS, PLATFORMS
from .reconcile import scan, scan_root
from .storage import pinned
from .formats import installed_formats

LIST = """SELECT i.id, g.id AS game_id,g.display_title,g.system,r.region,r.revision,f.disc,i.platform,
          l.path,i.status AS recorded_status,i.verified_at FROM installations i
          JOIN files f ON f.id=i.file_id JOIN releases r ON r.id=f.release_id
          JOIN games g ON g.id=r.game_id JOIN locations l ON l.id=i.location_id"""


def parser():
    p = argparse.ArgumentParser(prog="rom-cli --library")
    subs = p.add_subparsers(dest="command",required=True)
    for name in ("init","platforms","paths","consoles","install","verify","scan","reconcile","games",
                 "inspect","history","export","backup"):
        command = subs.add_parser(name)
        if name in ("install","verify","scan","reconcile","consoles"):
            command.add_argument("--platform",choices=PLATFORMS,required=True)
        if name in ("install","verify","scan","reconcile"):
            command.add_argument("--system",choices=FORMATS)
            command.add_argument("--root",type=Path,help="require this configured ROM root")
        if name=="inspect":
            command.add_argument("game_id",type=int)
        if name=="install":
            command.add_argument("source",help="authorized local file or direct HTTP(S) URL")
            for field in ("title","region","revision","language","edition","sha256"):
                command.add_argument("--"+field)
            command.add_argument("--disc",type=int,default=0)
        if name=="reconcile":
            command.add_argument("--confirm-pending",action="store_true")
        if name=="backup":
            command.add_argument("new_path",type=Path)
    return p


def run(args):
    op = args.command
    if op in ("paths","platforms"):
        return [discover(suite) for suite in PLATFORMS]
    if hasattr(args,"platform"):
        row = discover(args.platform)
        if getattr(args,"root",None) and str(args.root) != row["root"]:
            raise ValueError("configured root differs from requested root")
        if op=="consoles":
            results = []
            for system,formats in FORMATS.items():
                try:
                    path = destination(row,system)
                    with pinned(path) as handle:
                        formats = installed_formats(handle,system)
                    results.append(dict(system=system,path=str(path),formats=formats,writable=os.access(path,os.W_OK)))
                except (ValueError,OSError) as exc:
                    results.append(dict(system=system,error=str(exc)))
            return results
    writable = op in ("install","init") or getattr(args,"confirm_pending",False)
    with closing(manifest.connect() if writable else manifest.catalog_reader()) as db:
        if op=="init":
            return {"version":manifest.VERSION,"path":str(manifest.default_path())}
        if op=="install":
            return install(db,row,args.source,args.system,args.title,args.region or "",args.revision or "",
                           args.disc,args.sha256,language=args.language or "",edition=args.edition or "")
        if op in ("verify","scan","reconcile"):
            options = dict(repair=getattr(args,"confirm_pending",False),force_hash=op=="verify")
            records = scan(db,row,args.system,**options) if args.system else scan_root(db,row,**options)
            if op=="scan":
                return [r for r in records if r["status"]!="verified"]
            return records
        if op=="backup":
            manifest.backup(db,args.new_path)
            return {"backup":str(args.new_path)}
        if op=="export":
            return manifest.export(db)
        if op=="inspect":
            game = db.execute("SELECT * FROM games WHERE id=?", (args.game_id,)).fetchone()
            if not game:
                raise ValueError("unknown game identifier")
            return dict(game=dict(game),installations=[dict(r) for r in db.execute(
                        LIST+" WHERE g.id=?",(args.game_id,))], releases=[dict(r) for r in db.execute(
                        "SELECT * FROM releases WHERE game_id=?",(args.game_id,))])
        query = LIST+" ORDER BY g.normalized_title" if op=="games" else "SELECT * FROM downloads ORDER BY id DESC"
        return [dict(r) for r in db.execute(query)]


def main():
    from http.client import HTTPException
    os.umask(0o077)
    try:
        print(json.dumps(run(parser().parse_args()), ensure_ascii=True))
    except (ValueError,OSError,sqlite3.Error,HTTPException) as exc:
        print(json.dumps({"error":str(exc)}),file=sys.stderr)
        return 1
    return 0


if __name__=="__main__":
    sys.exit(main())

