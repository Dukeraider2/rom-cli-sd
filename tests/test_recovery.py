import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from library.installer import install
from library.manifest import connect
from library.reconcile import scan
from library.storage import publish


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.folder = self.base/"roms/gba"
        self.folder.mkdir(parents=True)
        self.path = self.base/"catalog.db"
        self.src = self.base/"game.gba"
        self.src.write_bytes(b"local demo")
        self.row = dict(root=str(self.folder.parent),status="ready",platform="emudeck")
        self.db = connect(self.path)
        self.addCleanup(self.db.close)

    def test_pending_reservation_blocks_second_name(self):
        entered, release = threading.Event(),threading.Event()
        errors = []
        def pause(src,dest):
            entered.set()
            if not release.wait(5):
                raise RuntimeError("timed out waiting for other install")
            publish(src,dest)
        def worker():
            db = connect(self.path)
            try:
                install(db,self.row,str(self.src))
            except Exception as exc:
                errors.append(str(exc))
            finally:
                db.close()
        with patch("library.installer.publish",side_effect=pause):
            thread = threading.Thread(target=worker)
            thread.start()
            try:
                self.assertTrue(entered.wait(5))
                with self.assertRaisesRegex(ValueError,"reserved"):
                    install(self.db,self.row,str(self.src),title="Alias")
            finally:
                release.set()
                thread.join(5)
        self.assertEqual(errors,[])
        self.assertEqual(len(list(self.folder.iterdir())),1)

    def test_shared_detection_and_preflight(self):
        result=install(self.db,self.row,str(self.src))
        other=dict(self.row,platform="retrodeck")
        self.assertEqual(scan(self.db,other,"gba",probe=lambda *_:"read-only")[0]["status"],"shared")
        with patch("library.installer.transfer",side_effect=AssertionError):
            with self.assertRaisesRegex(ValueError,"identical"):
                install(self.db,self.row,str(self.src),title="Alias",checksum=result["sha256"])

    def test_publication_refuses_concurrent_collision(self):
        destination=self.folder/self.src.name
        destination.write_bytes(b"already here")
        with self.assertRaises(FileExistsError):
            publish(self.src,destination)
        self.assertEqual(destination.read_bytes(),b"already here")
        self.assertEqual(self.src.read_bytes(),b"local demo")

    @unittest.skipUnless(sys.platform=="linux","Linux worker identity and directory pinning")
    def test_killed_transfer_cleanup(self):
        code="""import os,sys
from unittest.mock import patch
from library.manifest import connect
from library.installer import install
with patch('library.installer.transfer', side_effect=lambda *a: os._exit(7)):
    install(connect(sys.argv[1]),dict(root=sys.argv[2],platform='emudeck',status='ready'),sys.argv[3])
"""
        result=subprocess.run([sys.executable,"-c",code,str(self.path),str(self.folder.parent),str(self.src)])
        self.assertEqual(result.returncode,7)
        self.assertEqual(scan(self.db,self.row,"gba")[0]["status"],"interrupted-transfer")
        self.assertEqual(len(list(self.folder.iterdir())),1)
        scan(self.db,self.row,"gba",True)
        self.assertEqual(list(self.folder.iterdir()),[])
        self.assertEqual(self.db.execute("SELECT status FROM downloads").fetchone()[0],"interrupted")

