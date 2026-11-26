"""User-owned SQLite catalog. Callers group mutations with 'with db:'."""
import os
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE games(id INTEGER PRIMARY KEY, display_title TEXT NOT NULL, normalized_title TEXT NOT NULL, system TEXT NOT NULL, metadata_source TEXT NOT NULL, UNIQUE(system,normalized_title));
CREATE TABLE aliases(game_id INTEGER NOT NULL REFERENCES games, title TEXT NOT NULL, PRIMARY KEY(game_id,title));
CREATE TABLE releases(id INTEGER PRIMARY KEY, game_id INTEGER NOT NULL REFERENCES games, region TEXT NOT NULL DEFAULT '', revision TEXT NOT NULL DEFAULT '', language TEXT NOT NULL DEFAULT '', edition TEXT NOT NULL DEFAULT '', metadata TEXT NOT NULL DEFAULT '{}', UNIQUE(game_id,region,revision,language,edition));
CREATE TABLE contents(id INTEGER PRIMARY KEY, sha256 TEXT NOT NULL UNIQUE CHECK(length(sha256)=64), size INTEGER NOT NULL CHECK(size>=0));
CREATE TABLE files(id INTEGER PRIMARY KEY, release_id INTEGER NOT NULL REFERENCES releases, content_id INTEGER NOT NULL REFERENCES contents, original_filename TEXT NOT NULL, normalized_filename TEXT NOT NULL, format TEXT NOT NULL, role TEXT NOT NULL, disc INTEGER NOT NULL DEFAULT 0, source_checksum TEXT, integrity TEXT NOT NULL, UNIQUE(release_id,content_id,original_filename,disc));
CREATE TABLE locations(id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE, root TEXT NOT NULL, content_id INTEGER NOT NULL REFERENCES contents);
CREATE TABLE installations(id INTEGER PRIMARY KEY, file_id INTEGER NOT NULL REFERENCES files, location_id INTEGER NOT NULL REFERENCES locations, platform TEXT NOT NULL CHECK(platform IN ('emudeck','retrodeck')), status TEXT NOT NULL CHECK(status IN ('pending','installed')), installed_at TEXT, verified_at TEXT, UNIQUE(platform,location_id));
CREATE TABLE downloads(id INTEGER PRIMARY KEY, source TEXT NOT NULL, item TEXT NOT NULL, file_id INTEGER REFERENCES files, status TEXT NOT NULL, bytes INTEGER NOT NULL DEFAULT 0, completed_at TEXT, error TEXT);
CREATE TABLE artwork(id INTEGER PRIMARY KEY, game_id INTEGER NOT NULL REFERENCES games, provider TEXT NOT NULL, external_id TEXT, type TEXT, location TEXT, confidence REAL CHECK(confidence BETWEEN 0 AND 1));
"""
INDEXES = """
CREATE INDEX locations_content ON locations(content_id);
CREATE INDEX locations_root ON locations(root);
CREATE INDEX files_content ON files(content_id);
CREATE INDEX installations_location ON installations(location_id);
"""
TABLES = "games aliases releases contents files locations installations downloads artwork".split()
JOBS = """
ALTER TABLE downloads ADD COLUMN folder TEXT;
ALTER TABLE downloads ADD COLUMN platform TEXT;
ALTER TABLE downloads ADD COLUMN stage TEXT;
ALTER TABLE downloads ADD COLUMN stage_dev TEXT;
ALTER TABLE downloads ADD COLUMN stage_ino TEXT;
ALTER TABLE downloads ADD COLUMN owner TEXT;
ALTER TABLE downloads ADD COLUMN installation_id INTEGER REFERENCES installations ON DELETE SET NULL;
CREATE INDEX downloads_recovery ON downloads(platform,folder,status);
"""
FINGERPRINT = "ALTER TABLE locations ADD COLUMN fingerprint TEXT"
VERSION = 4


def catalog_reader(path=None):
    path = Path(path or default_path())
    if not path.exists():
        db = sqlite3.connect(":memory:")
        db.executescript(SCHEMA + INDEXES + JOBS + FINGERPRINT)
    else:
        db = sqlite3.connect(path.resolve().as_uri()+"?mode=ro", uri=True, timeout=8)
        if db.execute("PRAGMA user_version").fetchone()[0] != VERSION:
            db.close()
            raise ValueError("manifest version differs; run --library init to migrate a supported catalog")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA trusted_schema=OFF")
    db.execute("PRAGMA query_only=ON")
    return db


def default_path():
    base = os.getenv("XDG_DATA_HOME")
    root = Path(base) if base and Path(base).is_absolute() else Path.home() / ".local/share"
    return root / "rom-cli-sd/manifest.sqlite3"


def connect(path=None):
    path = Path(path or default_path())
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=8)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA trusted_schema=OFF")
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version > VERSION:
            raise ValueError("newer manifest version")
        db.execute("PRAGMA journal_mode=WAL")
        if version < VERSION:
            with db:
                db.execute("BEGIN IMMEDIATE")
                version = db.execute("PRAGMA user_version").fetchone()[0]
                if version == 0 and db.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone():
                    raise ValueError("unrecognized database")
                for script in (SCHEMA, INDEXES, JOBS, FINGERPRINT)[version:]:
                    for statement in script.strip().split(";"):
                        if statement.strip():
                            db.execute(statement)
                db.execute(f"PRAGMA user_version={VERSION}")
        return db
    except BaseException:
        db.close()
        raise


def export(db):
    with db:
        db.execute("BEGIN")
        return {"version": VERSION, "tables": {
            table: [dict(row) for row in db.execute(f"SELECT * FROM {table} ORDER BY rowid")]
            for table in TABLES}}


def backup(db, target):
    from contextlib import closing
    target = Path(target)
    with target.open("xb"):
        pass
    try:
        with closing(sqlite3.connect(target)) as copy:
            db.backup(copy)
            if copy.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("backup failed integrity check")
    except BaseException:
        target.unlink()
        raise

