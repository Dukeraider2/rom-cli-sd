import sqlite3
import tempfile
import unittest
from pathlib import Path
from contextlib import closing
from library import manifest


class ManifestTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name)/"db"

    def test_init_and_backup(self):
        with closing(manifest.connect(self.path)) as db:
            db.execute("INSERT INTO games VALUES(1,'Demo','demo','nes','user')")
            db.commit()
            manifest.backup(db, self.path.with_suffix(".bak"))
            self.assertEqual(manifest.export(db)["tables"]["games"][0]["id"], 1)
        with closing(manifest.connect(self.path.with_suffix(".bak"))) as restored:
            self.assertEqual(restored.execute("SELECT count(*) FROM games").fetchone()[0], 1)

    def test_upgrade(self):
        with closing(sqlite3.connect(self.path)) as old:
            old.executescript(manifest.SCHEMA+"PRAGMA user_version=1;")
        with closing(manifest.connect(self.path)) as db:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 2)
            self.assertTrue(db.execute("PRAGMA index_list(locations)").fetchall())

    def test_transaction_and_foreign_keys(self):
        with closing(manifest.connect(self.path)) as db:
            with self.assertRaises(sqlite3.IntegrityError), db:
                db.execute("INSERT INTO games VALUES(1,'Demo','demo','nes','user')")
                db.execute("INSERT INTO aliases VALUES(2,'Alternate')")
            self.assertFalse(db.execute("SELECT * FROM games").fetchall())

    def test_unknown_version_and_corruption(self):
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("PRAGMA user_version=99")
        with self.assertRaises(ValueError):
            manifest.connect(self.path)
        self.path.write_bytes(b"broken database"*128)
        with self.assertRaises(sqlite3.DatabaseError):
            manifest.connect(self.path)

