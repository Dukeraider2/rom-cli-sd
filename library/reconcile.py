"""Report one configured console, never recurse or trust catalog path components."""
from collections import defaultdict
from pathlib import Path
from .platforms import destination, FORMATS
from .storage import checked_leaf, digest, fingerprint, pinned
import stat
import sys
from .recovery import inspect_jobs


def scan(db, row, system, repair=False, probe=None, force_hash=False, checkpoint=None, limit=None):
    findings = []
    def report(status, **fields):
        findings.append({"status":status, **fields})
    try:
        folder = destination(row, system, **({"probe":probe} if probe else {}))
    except (OSError, ValueError) as exc:
        return [{"status":"unavailable","reason":str(exc)}]
    tracked = db.execute("""SELECT i.id, i.status, l.path, l.fingerprint, l.content_id, f.content_id AS expected_id,
                            c.sha256 FROM installations i JOIN locations l ON l.id=i.location_id
                            JOIN files f ON f.id=i.file_id JOIN releases r ON r.id=f.release_id
                            JOIN games g ON g.id=r.game_id JOIN contents c ON c.id=f.content_id
                            WHERE i.platform=? AND l.root=? AND g.system=? LIMIT ?""",
                         (row["platform"],str(folder.parent),system,limit+1 if limit else -1)).fetchall()
    if limit and len(tracked)>limit:
        raise ValueError("Console exceeds preview limit; use the library CLI")
    seen = defaultdict(list)
    missing = []
    with pinned(folder) as handle:
        findings.extend(inspect_jobs(db,row,folder,handle,repair))
        expected = set()
        for record in tracked:
            if checkpoint:
                checkpoint()
            path = record["path"]
            try:
                name = checked_leaf(folder,path)
                if record["content_id"] != record["expected_id"]:
                    raise ValueError("manifest content mismatch")
                expected.add(name)
                metadata = (handle/name).lstat()
                cached = (sys.platform == "linux" and not force_hash and record["status"] == "installed" and stat.S_ISREG(metadata.st_mode)
                          and fingerprint(metadata) == record["fingerprint"] and metadata.st_ino != 0)
                sha = record["sha256"] if cached else digest(handle/name,checkpoint=checkpoint)[0]
                seen[sha].append(name)
                if sha != record["sha256"]:
                    report("modified",path=path)
                elif record["status"] == "pending":
                    if repair:
                        with db:
                            db.execute("""UPDATE installations SET status='installed',installed_at=CURRENT_TIMESTAMP,
                                       verified_at=CURRENT_TIMESTAMP WHERE id=? AND status='pending'""",(record["id"],))
                            db.execute("""UPDATE downloads SET status='recovered',completed_at=CURRENT_TIMESTAMP
                                       WHERE id=(SELECT max(id) FROM downloads WHERE installation_id=?)
                                       AND status IN ('interrupted','failed')""",(record["id"],))
                    report("recovered" if repair else "pending",path=path)
                else:
                    report("verified",path=path,method="stat-cache" if cached else "sha256")
            except FileNotFoundError:
                missing.append(record)
            except (ValueError,OSError) as exc:
                report("invalid-or-inaccessible",path=path,reason=str(exc))
        for index,item in enumerate(handle.iterdir()):
            if checkpoint:
                checkpoint()
            if limit and index>=limit:
                raise ValueError("Console exceeds preview limit; use the library CLI")
            if item.name in expected or item.suffix.lower() not in FORMATS[system]:
                continue
            try:
                sha, _ = digest(item,checkpoint=checkpoint)
                seen[sha].append(item.name)
                shared = db.execute("""SELECT i.platform FROM installations i JOIN locations l ON l.id=i.location_id
                                       JOIN contents c ON c.id=l.content_id WHERE l.path=? AND c.sha256=?
                                       AND i.platform<>?""",(str(folder/item.name),sha,row["platform"])).fetchone()
                report("shared" if shared else "untracked",path=str(folder/item.name),sha256=sha)
            except (OSError,ValueError) as exc:
                report("inaccessible",path=str(folder/item.name),reason=str(exc))
        for record in missing:
            candidates = seen.get(record["sha256"],[])
            report("moved-or-renamed" if candidates else "missing",path=record["path"],candidates=candidates,
                   sha256=record["sha256"])
        for sha,names in seen.items():
            if len(names)>1:
                report("duplicate",sha256=sha,files=names)
    return findings


def scan_root(db, row, *, repair=False, force_hash=False):
    if row["status"] != "ready":
        return [{"status":"unavailable","reason":row["status"],"root":row["root"]}]
    results = []
    candidates = defaultdict(list)
    for system in FORMATS:
        for item in scan(db,row,system,repair,force_hash=force_hash):
            item["system"] = system
            results.append(item)
            if item["status"] in ("untracked","shared"):
                candidates[item["sha256"]].append(item["path"])
    for item in results:
        if item["status"] == "missing" and item["sha256"] in candidates:
            item.update(status="moved-or-renamed",candidates=candidates[item["sha256"]])
    return results

