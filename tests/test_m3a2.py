"""Deterministic checks only. The fixture engine never performs recognition."""
import os
import signal
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from experiments.m3a.fixtures import save_wav
from experiments.m3a.transcribe import WhisperAdapter,TranscriptionError,validate_audio
from experiments.m3a.reliability import calibrate,energy,ranked


class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base=Path(tmp.name)
        self.path=self.base/"quiet.wav"
        save_wav(self.path,[5,-5]*1600)
        (self.base/"ggml-tiny.en.bin").write_bytes(b"fixture")
        self.engine=self.base/"engine"
        self.temp=self.base/"scratch"
        self.temp.mkdir()
        self.use_engine("out.write_bytes(b'ok')")
        self.adapter=WhisperAdapter(self.engine,self.base,strict_hashes=False,timeout_seconds=.6)

    def use_engine(self,body):
        self.engine.write_text("#!/usr/bin/env python3\nimport os,sys,time,signal,subprocess\nfrom pathlib import Path\n"
            +"out=Path(sys.argv[sys.argv.index('-of')+1]+'.txt')\n"+body+"\n")
        self.engine.chmod(0o755)

    def test_malformed_pcm(self):
        for payload in (b"",b"RIFF",self.path.read_bytes()[:-16]):
            self.path.write_bytes(payload)
            with self.assertRaises(TranscriptionError):
                validate_audio(self.path)

    def test_gate_heldout_short_quiet_and_abort(self):
        save_wav(self.base/"silence.wav",[0]*8000)
        clips=[dict(id="quiet",split="dev",expected_title="quiet"),dict(id="silence",split="dev",expected_title=None)]
        threshold,_=calibrate(clips,self.base)
        save_wav(self.path,[6,-6]*320)
        self.assertGreaterEqual(energy(self.path),threshold)
        self.assertLess(energy(self.base/"silence.wav"),threshold)
        cancelled=threading.Event()
        cancelled.set()
        for options,expected in [({"cancel":cancelled},"cancelled"),({"deadline":0},"timeout")]:
            with self.assertRaises(TranscriptionError) as result:
                energy(self.path,**options)
            self.assertEqual(result.exception.code,expected)

    def test_ambiguous_candidates_and_immutable_input(self):
        text="Street Fighter two"
        result=ranked(text,["Street Fighter II","Street Fighter 2"])
        self.assertEqual(result["status"],"ambiguous")
        self.assertEqual(len(result["candidates"]),2)
        self.assertEqual(text,"Street Fighter two")
        self.assertEqual(ranked("",["Game"])["status"],"empty")

    def test_unexpected_outputs_cleanup_and_retry(self):
        with patch.object(tempfile,"tempdir",str(self.temp)):
            for body in ("b'X'*5000","b'\\xff'","b'x\\0y'"):
                self.use_engine("out.write_bytes("+body+")")
                result=self.adapter.transcribe(self.path,"tiny.en")
                self.assertEqual(result["error"]["code"],"invalid_output")
                self.assertEqual(list(self.temp.iterdir()),[])
            self.use_engine("out.write_text('Editable')")
            before=len(list(Path('/proc/self/fd').iterdir()))
            for _ in range(6):
                self.assertEqual(self.adapter.transcribe(self.path,"tiny.en")["text"],"Editable")
            self.assertEqual(len(list(Path('/proc/self/fd').iterdir())),before)
            self.assertEqual(list(self.temp.iterdir()),[])

    def test_descendant_cleanup(self):
        pidfile=self.base/"childpid"
        self.use_engine("child=subprocess.Popen([sys.executable,'-c','import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(12)'])\n"
                        +f"Path({str(pidfile)!r}).write_text(str(child.pid))\ntime.sleep(12)")
        with patch.object(tempfile,"tempdir",str(self.temp)):
            result=self.adapter.transcribe(self.path,"tiny.en")
        self.assertEqual(result["error"]["code"],"timeout")
        info=Path('/proc')/pidfile.read_text()/"stat"
        for _ in range(50):
            if not info.exists() or info.read_text().rsplit(")",1)[1].split()[0]=="Z":
                break
            time.sleep(.02)
        else:
            self.fail("Engine descendant still running after timeout")
        self.assertEqual(list(self.temp.iterdir()),[])
