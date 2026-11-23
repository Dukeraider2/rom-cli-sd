import tempfile
import threading
import time
import unittest
from contextlib import closing
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from library.provider_http import Network
from library.providers import candidate
from library.queue import Queue


class QueueTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home=Path(tmp.name)
        self.root=self.home/"roms/gba"
        self.root.mkdir(parents=True)
        settings=self.home/".config/EmuDeck/settings.sh"
        settings.parent.mkdir(parents=True)
        settings.write_text("romsPath=~/roms")
        self.body=b"Game"*65536
        body=self.body
        self.arrived=threading.Event()
        self.release=threading.Event()
        arrived,release=self.arrived,self.release
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Length",str(len(body)))
                self.end_headers()
                arrived.set()
                release.wait(5)
                self.wfile.write(body)
            def log_message(self,*args):
                pass
        server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base=f"http://127.0.0.1:{server.server_port}/"
        self.network=Network(base,True)
        self.data=candidate("mirror","fixture","Game",base+"Game.gba","Game.gba",len(body))
        self.queue=Queue(self.home/"catalog",self.network,self.home)
        self.addCleanup(self.queue.close)
        self.addCleanup(self.release.set)
        self.identity=self.queue.preview(self.data,"emudeck","gba")["identity"]

    def enqueue(self,token="a"):
        return self.queue.enqueue(token,self.data,"emudeck","gba",self.identity)

    def wait_state(self,key,states):
        for _ in range(300):
            row=self.queue.jobs(key)
            if row["state"] in states:
                return row
            time.sleep(0.02)
        self.fail(str(row))

    def test_cancel_retry_and_idempotency(self):
        key=self.enqueue()
        self.assertEqual(self.enqueue(),key)
        self.assertTrue(self.arrived.wait(3))
        self.queue.change(key)
        self.release.set()
        self.wait_state(key,["cancelled"])
        self.assertEqual(list(self.root.iterdir()),[])
        self.queue.change(key,retry=True)
        row=self.wait_state(key,["completed"])
        self.assertEqual(row["bytes"],len(self.body))
        self.assertEqual((self.root/"Game.gba").read_bytes(),self.body)

    def test_changed_storage_and_checksum(self):
        self.identity[2]="other"
        self.wait_state(self.enqueue(),["needs_attention"])
        self.identity=self.queue.preview(self.data,"emudeck","gba")["identity"]
        self.data["checksums"]={"sha1":"0"*40}
        self.release.set()
        self.wait_state(self.enqueue("b"),["needs_attention"])
        self.assertEqual(list(self.root.iterdir()),[])

