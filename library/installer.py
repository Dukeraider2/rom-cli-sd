"""A committed pending record spans publication and filesystem verification."""
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlsplit, unquote
from .naming import identify, names
from .platforms import destination
from .storage import checked_leaf, digest, pinned
from .transfer import transfer


def entity(db, table, keys, extra=None):
    # Identifiers are internal constants. All metadata are bound values.
    values = {**keys, **(extra or {})}
    columns = ",".join(values)
    placeholders = ",".join("?" for _ in values)
    db.execute(f"INSERT INTO {table}({columns}) VALUES({placeholders}) ON CONFLICT DO NOTHING",
               tuple(values.values()))
    where = " AND ".join(key+"=?" for key in keys)
    return db.execute(f"SELECT id FROM {table} WHERE {where}", tuple(keys.values())).fetchone()[0]


def reserve(db, platform, folder, filename, original, info, content, checksum, job):
    display, normalized, system, region, revision, disc = info
    sha, size = content
    cid = entity(db, "contents", dict(sha256=sha), dict(size=size))
    game = entity(db, "games", dict(system=system, normalized_title=normalized),
                  dict(display_title=display, metadata_source="user" if display != Path(original).stem else "filename"))
    release = entity(db, "releases", dict(game_id=game, region=region, revision=revision, language="", edition=""))
    fid = entity(db, "files", dict(release_id=release, content_id=cid, original_filename=original, disc=disc),
                 dict(normalized_filename=filename, format=Path(filename).suffix.lower(),
                      role="disc" if disc else "image", source_checksum=checksum,
                      integrity="checksum-matched" if checksum else "hashed"))
    loc = entity(db, "locations", dict(path=str(folder/filename)), dict(root=str(folder.parent), content_id=cid))
    if db.execute("SELECT content_id FROM locations WHERE id=?", (loc,)).fetchone()[0] != cid:
        raise ValueError("different content previously registered at this path")
    install = entity(db, "installations", dict(platform=platform, location_id=loc),
                     dict(file_id=fid, status="pending"))
    if db.execute("SELECT file_id FROM installations WHERE id=?", (install,)).fetchone()[0] != fid:
        raise ValueError("path already associated with different release metadata")
    db.execute("UPDATE downloads SET file_id=?, bytes=? WHERE id=?", (fid,size,job))
    return install


def install(db, row, source, system=None, title=None, region="", revision="", disc=0, checksum=None,
            probe=None):
    remote = "://" in source
    original = unquote(urlsplit(source).path.rsplit("/",1)[-1]) if remote else Path(source).name
    system = identify(original, system)
    display, normalized, filename = names(original, title, region, revision, disc)
    folder = destination(row, system, write=True, **({"probe":probe} if probe else {}))
    if checksum and not re.fullmatch("[a-fA-F0-9]{64}", checksum):
        raise ValueError("invalid SHA-256")
    checksum = checksum.lower() if checksum else None
    # Omit transient URL credentials/query strings from the persistent log.
    item = source.split("?",1)[0].split("#",1)[0] if remote else source
    if remote:
        from .transfer import origin
        origin(source)
    with db:
        job = db.execute("INSERT INTO downloads(source,item,status) VALUES(?,?,'started')",
                         ("http" if remote else "local",item)).lastrowid
    info = display, normalized, system, region, revision, disc
    try:
        with pinned(folder) as handle:
            target = handle/filename
            existing = None
            if target.is_symlink():
                raise ValueError("linked destination")
            if target.exists():
                existing = digest(target)
                if checksum and existing[0] != checksum:
                    raise FileExistsError(filename)
            stagepath = None
            try:
                if checksum and existing and existing[0] == checksum:
                    content = existing
                else:
                    with tempfile.NamedTemporaryFile(prefix=".rom-cli-",suffix=".part",dir=handle,delete=False) as stage:
                        stagepath = Path(stage.name)
                        content = transfer(source, stage, handle)
                    if checksum and content[0] != checksum:
                        raise ValueError("SHA-256 mismatch")
                    if existing and existing != content:
                        raise FileExistsError(filename)
                with db:
                    db.execute("BEGIN IMMEDIATE")
                    for other in db.execute("""SELECT path FROM locations JOIN contents ON contents.id=content_id
                                               WHERE sha256=? AND root=?""", (content[0], str(folder.parent))):
                        candidate = Path(other[0])
                        if candidate.parent == folder and candidate.name != filename:
                            leaf = handle/checked_leaf(folder,candidate)
                            if leaf.exists() and digest(leaf) == content:
                                raise ValueError(f"identical ROM already present: {candidate.name}")
                    iid = reserve(db,row["platform"],folder,filename,original,info,content,checksum,job)
                if existing is None:
                    os.link(stagepath,target)  # Atomic create-if-absent, same filesystem.
                    if os.name == "posix":
                        fd = os.open(handle, os.O_RDONLY | os.O_DIRECTORY)
                        try:
                            os.fsync(fd)
                        finally:
                            os.close(fd)
                if digest(target) != content or not os.path.samefile(handle, folder):
                    raise ValueError("destination changed; reconcile pending installation")
                with db:
                    db.execute("""UPDATE installations SET status='installed', installed_at=coalesce(installed_at,CURRENT_TIMESTAMP),
                                  verified_at=CURRENT_TIMESTAMP WHERE id=?""", (iid,))
                    db.execute("UPDATE downloads SET status='complete', completed_at=CURRENT_TIMESTAMP WHERE id=?", (job,))
                return dict(id=iid, path=str(folder/filename), sha256=content[0], reused=existing is not None)
            finally:
                if stagepath is not None:
                    stagepath.unlink(missing_ok=True)
    except Exception as exc:
        with db:
            db.execute("UPDATE downloads SET status='failed',error=? WHERE id=?", (str(exc),job))
        raise

