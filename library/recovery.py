"""Identify interrupted workers on Linux before touching their staged bytes."""
import os
import re
from pathlib import Path


def process_owner(pid=None):
    if os.name != "posix":
        return None
    pid = pid or os.getpid()
    boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    # Field 22 is starttime; the parenthesized process name can contain spaces.
    fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")",1)[1].split()
    return f"{boot}:{pid}:{fields[19]}"


def abandoned(owner):
    if not owner or os.name != "posix":
        return False
    try:
        boot, pid, start = owner.split(":")
        return owner != process_owner(int(pid))
    except FileNotFoundError:
        return True
    except (OSError,ValueError,IndexError):
        return False


def inspect_jobs(db, row, folder, handle, repair, attempt=None):
    reports = []
    jobs = db.execute("""SELECT * FROM downloads WHERE platform=? AND folder=?
                         AND (status='started' OR stage IS NOT NULL) AND (? IS NULL OR id=?)""",
                      (row["platform"],str(folder),attempt,attempt)).fetchall()
    for job in jobs:
        if not abandoned(job["owner"]):
            continue
        leaf = job["stage"]
        file = None
        if leaf and re.fullmatch(r"\.rom-cli-[a-zA-Z0-9_-]+\.part",leaf):
            candidate = handle/leaf
            try:
                st = candidate.lstat()
                if candidate.is_file() and not candidate.is_symlink() and (str(st.st_dev),str(st.st_ino)) == (job["stage_dev"],job["stage_ino"]):
                    file = candidate
            except FileNotFoundError:
                pass
        if job["status"] == "started" or file:
            reports.append(dict(status="interrupted-transfer",id=job["id"],stage=leaf))
        if repair:
            if file:
                file.unlink(missing_ok=True)
            with db:
                db.execute("""UPDATE downloads SET stage=NULL,status=CASE WHEN status='started'
                              THEN 'interrupted' ELSE status END WHERE id=?""",(job["id"],))
    return reports

