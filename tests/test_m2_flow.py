"""Complete RPC search-to-install on both configured suites using local HTTP."""
import json
import tempfile
import threading
import time
import unittest
from contextlib import closing
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from library.decky_api import Service
from library.provider_http import Network
from library.queue import Queue
from library import platforms
from library.manifest import catalog_reader


class FlowTests(unittest.TestCase):
    def test_end_to_end_and_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)
            for suite in platforms.PLATFORMS:
                (home/suite/"gba").mkdir(parents=True)
            cfg=home/".config/EmuDeck/settings.sh"
            cfg.parent.mkdir(parents=True)
            cfg.write_text("romsPath=~/emudeck")
            cfg=home/".var/app"/platforms.APP/"config/retrodeck/retrodeck.json"
            cfg.parent.mkdir(parents=True)
            cfg.write_text(json.dumps({"paths":{"rd_home_path":str(home),"roms_path":str(home/"retrodeck")}}))
            class Handler(BaseHTTPRequestHandler):
                def do_GET(self):
                    data=b'<a href="Demo.gba">Demo</a>' if self.path=="/" else b"synthetic homebrew"
                    self.send_response(200)
                    self.send_header("Content-Length",str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                def log_message(self,*args):
                    pass
            server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
            threading.Thread(target=server.serve_forever,daemon=True).start()
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
            source=f"http://127.0.0.1:{server.server_port}/"
            def fake_info(*args):
                return "read-only" if args[0].startswith("--file-access") else "app/fixture"
            def discover(suite,home):
                return platforms.discover(suite,home,fake_info)
            def destination(row,system,write=False):
                return platforms.destination(row,system,write=write,probe=fake_info)
            with patch("library.queue.discover",discover),patch("library.queue.destination",destination),patch("library.installer.destination",destination):
                queue=Queue(home/"catalog",Network(source,True),home)
                try:
                    api=Service(queue)
                    def rpc(op,**args):
                        result=api.request(1,op,args)
                        self.assertTrue(result["ok"],result)
                        return result["data"]
                    rows=rpc("search",provider="mirror",query="Demo",system=None,page=1,file_page=1)
                    hit=rows["results"][0]
                    self.assertNotIn("url",hit)
                    for suite in platforms.PLATFORMS:
                        preview=rpc("get_result",result=hit["id"],platform=suite,system="gba")
                        job=rpc("enqueue",token=preview["token"],confirmed=True)["id"]
                        for _ in range(300):
                            status=rpc("get_progress",job=job)["state"]
                            if status in ("completed","needs_attention","failed"):
                                break
                            time.sleep(.01)
                        self.assertEqual(status,"completed")
                        self.assertEqual((home/suite/"gba/Demo.gba").read_bytes(),b"synthetic homebrew")
                    self.assertEqual(len(rpc("list_games",page=1)),2)
                    with closing(queue.db()) as db, db:
                        db.execute("UPDATE jobs SET state='verifying' WHERE id=?",(job,))
                finally:
                    queue.close()
                restarted=Queue(home/"catalog",Network(source,True),home)
                try:
                    self.assertEqual(restarted.jobs(job)["state"],"needs_attention")
                finally:
                    restarted.close()

    def test_source_policy(self):
        network=Network("http://127.0.0.1/private/")
        with self.assertRaisesRegex(ValueError,"authorized network"):
            with network.open("mirror",network.mirror):
                pass
        with self.assertRaises(ValueError):
            network.check("archive","https://example.invalid/a")

