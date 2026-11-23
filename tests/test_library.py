import hashlib
import shutil
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from library.manifest import connect
from library.installer import install
from library.reconcile import scan


class LibraryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.root = self.base/"roms"
        self.folder = self.root/"psx"
        self.folder.mkdir(parents=True)
        self.src = self.base/"Demo.chd"
        self.src.write_bytes(b"MComprHD"+"synthetic fixture".encode())
        self.db = connect(self.base/"manifest")
        self.addCleanup(self.db.close)
        self.row = dict(root=str(self.root),status="ready",platform="emudeck")

    def put(self, **kwargs):
        return install(self.db,self.row,str(self.src),"psx",**kwargs)

    def report(self, repair=False):
        return scan(self.db,self.row,"psx",repair,probe=lambda *_:"read-only")

    def test_discs_releases_and_shared_library(self):
        first = self.put(region="USA",disc=1)
        self.assertTrue(self.put(region="USA",disc=1)["reused"])
        self.row["platform"]="retrodeck"
        self.put(region="USA",disc=1,probe=lambda *_:"read-write")
        self.assertEqual(self.db.execute("SELECT count(*) FROM locations").fetchone()[0],1)
        self.row["platform"]="emudeck"
        self.src.write_bytes(b"MComprHDdisc 2")
        self.put(region="USA",disc=2)
        self.src.write_bytes(b"MComprHDEU")
        self.put(region="EU",disc=1)
        self.assertEqual(self.db.execute("SELECT count(*) FROM releases").fetchone()[0],2)
        self.assertTrue(Path(first["path"]).is_file())

    def test_collision_and_duplicate(self):
        target = Path(self.put()["path"])
        with self.assertRaises(ValueError):
            self.put(title="Another title")
        self.src.write_bytes(b"MComprHDnew content")
        with self.assertRaises(FileExistsError):
            self.put()
        self.assertNotEqual(target.read_bytes(), self.src.read_bytes())

    def test_verify_scan(self):
        path = Path(self.put()["path"])
        path.rename(self.folder/"new.chd")
        shutil.copy(self.folder/"new.chd",self.folder/"another.chd")
        self.assertEqual({r["status"] for r in self.report()}, {"untracked","moved-or-renamed","duplicate"})
        path.write_bytes(b"changed")
        self.assertIn("modified",[r["status"] for r in self.report()])
        for file in self.folder.iterdir():
            file.unlink()
        self.assertEqual(self.report()[0]["status"],"missing")
        self.folder.rmdir()
        self.assertEqual(self.report()[0]["status"],"unavailable")

    def test_recovery(self):
        with patch("library.installer.digest",side_effect=OSError("unmounted")):
            with self.assertRaises(OSError):
                self.put()
        self.assertEqual(self.report()[0]["status"],"pending")
        self.assertEqual(self.report(True)[0]["status"],"recovered")
        self.assertEqual(self.report()[0]["status"],"verified")

    def test_failures_clean_up(self):
        definition = self.folder/"systeminfo.txt"
        definition.write_text("Supported file extensions:\n.iso .ISO\n")
        with self.assertRaisesRegex(ValueError,"disabled"):
            self.put()
        definition.unlink()
        for failure in (OSError("full disk"),ConnectionError("interrupted")):
            with patch("library.installer.transfer",side_effect=failure), self.assertRaises(OSError):
                self.put()
        with self.assertRaises(ValueError):
            self.put(checksum="0"*64)
        self.assertFalse(list(self.folder.iterdir()))
        self.assertEqual(self.db.execute("SELECT count(*) FROM downloads WHERE status='failed'").fetchone()[0],4)

    def test_link_and_format_rejection(self):
        with self.assertRaises(ValueError):
            self.put(title="../unsafe")
        with self.assertRaises(ValueError):
            install(self.db,self.row,str(self.base/"bad.zip"),"psx")
        try:
            (self.folder/self.src.name).symlink_to(self.src)
        except OSError:
            self.skipTest("host cannot create symbolic links")
        with self.assertRaises(ValueError):
            self.put()

