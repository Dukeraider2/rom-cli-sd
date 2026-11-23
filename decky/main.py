"""Decky API v1 plugin entry point."""
import asyncio
import json
import os
import pwd
import sys
from pathlib import Path
import decky

sys.path.insert(0,decky.DECKY_PLUGIN_DIR)
from library.decky_api import Service
from library.manifest import default_path
from library.provider_http import Network
from library.queue import Queue


def user_paths():
    uid=os.geteuid()
    account=pwd.getpwuid(uid)
    home=Path(account.pw_dir)
    if (uid==0 or os.getuid()!=uid or account.pw_name!=decky.DECKY_USER
            or home!=Path(decky.DECKY_USER_HOME) or home!=Path.home() or home.stat().st_uid!=uid):
        raise PermissionError("Decky must run as the active unprivileged account")
    folder=default_path().parent
    for path in (folder,Path(decky.DECKY_PLUGIN_SETTINGS_DIR)):
        if not path.is_relative_to(home) or path!=path.resolve():
            raise PermissionError("Expected a user-owned path beneath the account home")
    for path in (folder,folder/"manifest.sqlite3",folder/"decky-jobs.sqlite3",folder/"decky-worker.lock"):
        if path.is_symlink() or path.exists() and (path.stat().st_uid!=uid or path.stat().st_mode & 0o022):
            raise PermissionError("Catalog storage requires private write access")
    return home,folder


class Plugin:
    async def _main(self):
        self.service=None
        self.error="Starting library"
        self.inflight=0
        try:
            os.umask(0o077)
            home,folder=user_paths()
            config=Path(decky.DECKY_PLUGIN_SETTINGS_DIR)/"mirror.json"
            settings={}
            if config.exists():
                if config.is_symlink() or config.stat().st_uid!=os.getuid() or config.stat().st_mode & 0o022 or config.stat().st_size>4096:
                    raise PermissionError("Mirror configuration must be user-owned")
                settings=json.loads(config.read_text())
            self.service=Service(Queue(folder,Network(settings.get("base"),settings.get("allow_private",False)),home))
        except Exception as exc:
            self.error=str(exc)[:300]
            decky.logger.error("Library startup failed: %s",self.error)

    async def rpc(self,version:int,operation:str,request:dict):
        service=getattr(self,"service",None)
        if not service or self.inflight>=4:
            return {"ok":False,"version":1,"error":{"code":"busy","message":getattr(self,"error","Starting") if not service else "Too many requests"}}
        self.inflight+=1
        try:
            return await asyncio.to_thread(service.request,version,operation,request)
        finally:
            self.inflight-=1

    async def _unload(self):
        service=getattr(self,"service",None)
        self.service=None
        if service:
            await asyncio.to_thread(service.queue.close)

