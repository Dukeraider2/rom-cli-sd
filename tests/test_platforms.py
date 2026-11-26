import json
import tempfile
import unittest
from pathlib import Path
from library.platforms import APP, discover, destination
from library.naming import identify, names


class PlatformTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        self.root = self.home / "external storage"
        (self.root/"gba").mkdir(parents=True)
        self.cfg = self.home/".var/app"/APP/"config/retrodeck"
        self.cfg.mkdir(parents=True)

    def test_emudeck(self):
        self.assertFalse(discover("emudeck", self.home)["installed"])
        cfg = self.home/".config/EmuDeck/settings.sh"
        cfg.parent.mkdir(parents=True)
        cfg.write_text('romsPath="~/external storage"')
        result = discover("emudeck", self.home)
        self.assertEqual(destination(result, "gba"), self.root/"gba")
        cfg.write_text('romsPath=$(unknown)')
        self.assertEqual(discover("emudeck", self.home)["status"], "configuration-error")

    def test_retrodeck(self):
        self.assertFalse(discover("retrodeck", self.home, lambda *_:"")["installed"])
        cfg = self.cfg/"retrodeck.cfg"
        cfg.write_text('rdhome=~/data\nroms_folder="~/external storage"')
        result = discover("retrodeck", self.home, lambda *_:"installed")
        with self.assertRaises(PermissionError):
            destination(result, "gba", probe=lambda *_:"hidden")
        self.assertEqual(destination(result, "gba", probe=lambda *_:"read-only"), self.root/"gba")
        current = self.cfg/"retrodeck.json"
        current.write_text(json.dumps({"paths":{"rd_home_path":str(self.home),"roms_path":str(self.home/"missing")}}))
        self.assertEqual(discover("retrodeck", self.home, lambda *_:"installed")["status"], "storage-unavailable")
        current.write_text("{}")
        self.assertEqual(discover("retrodeck", self.home, lambda *_:"installed")["status"], "configuration-error")

    def test_names(self):
        self.assertEqual(identify("Demo.GBA"), "gba")
        for name in ("a.chd", "../a.gba", "a.zip", "a.bios", "a.m3u"):
            with self.assertRaises(ValueError):
                identify(name)
        self.assertEqual(names("disc.chd","Demo","USA","1",2)[2], "Demo (USA) (Rev 1) (Disc 2).chd")

    def test_both_and_neither(self):
        self.assertFalse(discover("emudeck", self.home)["installed"])
        self.assertFalse(discover("retrodeck", self.home, lambda *_:"")["installed"])
        cfg=self.home/".config/EmuDeck/settings.sh"
        cfg.parent.mkdir(parents=True)
        cfg.write_text('romsPath="~/external storage"')
        (self.cfg/"retrodeck.json").write_text(json.dumps({"paths":{
            "rd_home_path":str(self.home),"roms_path":str(self.root)}}))
        for suite in ("emudeck","retrodeck"):
            self.assertEqual(discover(suite,self.home,lambda *_:"installed")["root"],str(self.root))

