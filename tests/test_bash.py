"""Exercise the original interactive entry points with deterministic selections."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


@unittest.skipUnless(sys.platform=="linux" and shutil.which("jq"),"Linux shell and jq fixtures")
class BashTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base=Path(tmp.name)
        self.env=dict(os.environ,PATH=str(self.base)+":"+os.environ["PATH"],
                      ROM_CLI_DOWNLOAD_DIR=str(self.base/"out"),ROM_CLI_MIRROR="")
        self.cli=str(Path(__file__).resolve().parents[1]/"rom-cli")
        self.stub("fzf","cat")
        self.stub("aria2c",'''for arg do case "$arg" in --dir=*) dir=${arg#--dir=};; esac; done
printf demo > "$dir/payload"''')
        self.stub("curl",'''case "$*" in
*advancedsearch*) echo '{"response":{"numFound":1,"docs":[{"identifier":"demo","title":"Demo"}]}}';;
*metadata*) echo '{"files":[{"name":"folder/Demo.nes","size":"4"}]}';;
*) echo '<a href="Demo.nes">Demo.nes</a>';;
esac''')

    def stub(self,name,script):
        path=self.base/name
        path.write_text("#!/bin/sh\n"+script+"\n")
        path.chmod(0o755)

    def invoke(self,*args):
        return subprocess.run(["bash",self.cli,*args],env=self.env,text=True,capture_output=True)

    def test_archive_and_mirror(self):
        for args,sub in [(("demo",),"demo"),(("--mirror","http://fixture.invalid","Demo"),"mirror")]:
            with self.subTest(sub=sub):
                result=self.invoke(*args)
                self.assertEqual(result.returncode,0,result.stderr)
                target=self.base/"out"/sub/"Demo.nes"
                self.assertEqual(target.read_bytes(),b"demo")
                self.assertNotEqual(self.invoke(*args).returncode,0)
                self.assertEqual(target.read_bytes(),b"demo")

    def test_transfer_failure(self):
        self.stub("aria2c","exit 3")
        result=self.invoke("--mirror","http://fixture.invalid","Demo")
        self.assertNotEqual(result.returncode,0)
        self.assertFalse(list((self.base/"out/mirror").iterdir()))

