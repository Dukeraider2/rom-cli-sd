"""Pin directory handles on SteamOS. Operations accept only validated leaf names."""
import hashlib
import os
import stat
from contextlib import contextmanager
from pathlib import Path
from .naming import basename


@contextmanager
def pinned(folder):
    folder = Path(folder)
    if folder.resolve(strict=True) != folder:
        raise ValueError("linked directory")
    if os.name != "posix":
        # Host fixture path for Windows development; SteamOS uses pinned handles.
        yield folder
        return
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open("/", flags)
    try:
        for part in folder.parts[1:]:
            child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        yield Path("/proc/self/fd") / str(fd)
    finally:
        os.close(fd)


def regular(path):
    if path.is_symlink():
        raise ValueError("linked file")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                 | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0))
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise ValueError("expected regular file")
    return os.fdopen(fd, "rb")


def fingerprint(stat_result):
    return ":".join(str(value) for value in (stat_result.st_dev,stat_result.st_ino,
                    stat_result.st_size,stat_result.st_ctime_ns,stat_result.st_mtime_ns))


def digest(path, *, with_stamp=False):
    with regular(path) as stream:
        before = os.fstat(stream.fileno())
        sha = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            sha.update(chunk)
        after = os.fstat(stream.fileno())
        now = path.lstat()
        if (not os.path.samestat(after, now) or before.st_size != after.st_size
                or before.st_mtime_ns != after.st_mtime_ns or before.st_ctime_ns != after.st_ctime_ns):
            raise ValueError("file changed during verification")
        result = sha.hexdigest(), after.st_size
        return (*result, fingerprint(after)) if with_stamp else result


def checked_leaf(folder, path):
    path = Path(path)
    if path.parent != folder:
        raise ValueError("manifest path outside selected console")
    return basename(path.name)

