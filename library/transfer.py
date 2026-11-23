import hashlib
import os
import shutil
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit
from .storage import regular

LIMIT = 16 * 1024**3


def origin(url):
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("expected HTTP(S) source without embedded credentials")
    return parsed.scheme, parsed.hostname, parsed.port


class Redirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        old, new = origin(req.full_url), origin(newurl)
        archive = (old[0] == new[0] == "https" and old[2] in (None,443) and new[2] in (None,443)
                   and all(h == "archive.org" or h.endswith(".archive.org") for h in (old[1], new[1])))
        if old != new and not archive:
            raise ValueError("redirect outside selected origin")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


@contextmanager
def source_stream(source):
    if "://" not in source:
        with regular(Path(source)) as stream:
            yield stream, os.fstat(stream.fileno()).st_size
        return
    origin(source)
    with urllib.request.build_opener(Redirects()).open(source, timeout=30) as stream:
        if stream.status != 200:
            raise ValueError("incomplete HTTP response")
        length = stream.headers.get("Content-Length")
        yield stream, int(length) if length is not None else None


def transfer(source, stage, folder, *, opener=source_stream, progress=None, expected=None, checksums=None):
    sha = hashlib.sha256()
    hashes = {key:hashlib.new(key) for key in (checksums or {})}
    total = 0
    with opener(source) as (stream, length):
        if expected is not None and length is not None and length != expected:
            raise ValueError("source size changed since selection")
        length = length if length is not None else expected
        if progress:
            progress(0,length)
        if length is not None and (length <= 0 or length > LIMIT or length > shutil.disk_usage(folder).free):
            raise ValueError("invalid source size or insufficient space")
        for block in iter(lambda: stream.read(1024*1024), b""):
            total += len(block)
            if total > LIMIT:
                raise ValueError("size limit exceeded")
            stage.write(block)
            sha.update(block)
            for value in hashes.values():
                value.update(block)
            if progress:
                progress(total,length)
        if not total or length is not None and total != length:
            raise ValueError("incomplete transfer")
    if any(value.hexdigest()!=checksums[key] for key,value in hashes.items()):
        raise ValueError("source checksum mismatch")
    stage.flush()
    os.fsync(stage.fileno())
    return sha.hexdigest(), total

