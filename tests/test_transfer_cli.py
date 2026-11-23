import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import patch
from library.formats import validate
from library.transfer import transfer
from library.manifest import catalog_reader


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"NES\x1a"+bytes(64)
        self.send_response(200)
        self.send_header("Content-Length",str(len(body)))
        self.end_headers()
        self.wfile.write(body if self.path=="/good.nes" else body[:4])

    def log_message(self,*args):
        pass


class TransferTests(unittest.TestCase):
    def test_http_cli_round_trip(self):
        server=HTTPServer(("127.0.0.1",0),Handler)
        self.addCleanup(server.server_close)
        worker=threading.Thread(target=server.serve_forever,daemon=True)
        worker.start()
        self.addCleanup(server.shutdown)
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)
            config=home/".config/EmuDeck/settings.sh"
            config.parent.mkdir(parents=True)
            config.write_text('romsPath=~/roms')
            folder=home/"roms/nes"
            folder.mkdir(parents=True)
            env=dict(os.environ,HOME=tmp,USERPROFILE=tmp,XDG_DATA_HOME=str(home/"data"))
            def cli(*args):
                return subprocess.run([sys.executable,"-I",str(Path(__file__).resolve().parents[1]/"library-entry.py"),*args],
                                      capture_output=True,text=True,env=env,cwd=tmp)
            base=f"http://127.0.0.1:{server.server_port}/"
            self.assertEqual(cli("scan","--platform","emudeck","--system","nes").returncode,0)
            self.assertFalse((home/"data").exists())
            self.assertNotEqual(cli("install","--platform","emudeck",base+"short.nes").returncode,0)
            self.assertEqual(list(folder.iterdir()),[])
            result=cli("install","--platform","emudeck",base+"good.nes")
            self.assertEqual(result.returncode,0,result.stderr)
            sha=json.loads(result.stdout)["sha256"]
            self.assertEqual(sha,hashlib.sha256((folder/"good.nes").read_bytes()).hexdigest())
            self.assertEqual(len(json.loads(cli("games").stdout)),1)
            self.assertEqual(json.loads(cli("verify","--platform","emudeck","--system","nes").stdout)[0]["status"],"verified")
            self.assertEqual(json.loads(cli("history").stdout)[1]["status"],"failed")

    def test_capacity_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"source"
            path.write_bytes(bytes(16))
            with patch("library.transfer.shutil.disk_usage") as usage:
                usage.return_value.free=1
                with self.assertRaises(ValueError):
                    transfer(str(path),io.BytesIO(),Path(tmp))

    def test_mismatched_payload(self):
        for data,ext in [(b"<html>missing", ".gba"),(b"wrong", ".nes"),(b"PK\x03\x04", ".sfc")]:
            with self.assertRaises(ValueError):
                validate(io.BytesIO(data),ext)

