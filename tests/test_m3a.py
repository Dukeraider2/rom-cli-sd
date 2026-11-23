"""M3A fake-engine and isolation tests. These are not real ASR accuracy tests."""
import json
import os
from pathlib import Path
import stat
import tempfile
import threading
import unittest
import wave
from unittest.mock import patch

from experiments.m3a.benchmark import catalog_match, normalize, run
from experiments.m3a.fixtures import generate, save_wav
from experiments.m3a.transcribe import WhisperAdapter

ROOT = Path(__file__).resolve().parents[1]
FAKE = ROOT / "experiments/m3a/fake_engine.py"


class M3ATests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.models = self.root / "models"
        self.models.mkdir()
        for model in ("tiny.en", "base.en"):
            (self.models / f"ggml-{model}.bin").write_bytes(b"mock")
        self.fixtures = self.root / "fixtures"
        generate(self.fixtures, mock=True)
        self.adapter = WhisperAdapter(FAKE, self.models, strict_hashes=False, timeout_seconds=1)
        self.clip = self.fixtures / "mario-2.wav"

    def test_transcript_is_editable_text_only(self):
        result = self.adapter.transcribe(self.clip, "tiny.en")
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["text"], "Super Mario Bros. 2")
        self.assertEqual(set(result), {"ok", "text", "model", "metrics"})
        self.assertGreater(result["metrics"]["elapsed_ms"], 0)

    def test_empty_output(self):
        with patch.dict(os.environ, {"M3A_FAKE_MODE": "empty"}):
            result = self.adapter.transcribe(self.clip, "base.en")
        self.assertTrue(result["ok"])
        self.assertEqual(result["text"], "")

    def test_missing_model(self):
        (self.models / "ggml-tiny.en.bin").unlink()
        self.assertEqual(self.adapter.transcribe(self.clip, "tiny.en")["error"]["code"], "missing_model")

    def test_unallowlisted_model(self):
        self.assertEqual(self.adapter.transcribe(self.clip, "../secret")["error"]["code"], "invalid_model")

    def test_corrupt_model_fails_pinned_hash(self):
        strict = WhisperAdapter(FAKE, self.models)
        self.assertEqual(strict.transcribe(self.clip, "tiny.en")["error"]["code"], "invalid_model")

    def test_invalid_audio(self):
        invalid = self.root / "bad.wav"
        invalid.write_bytes(b"not a wav")
        self.assertEqual(self.adapter.transcribe(invalid, "tiny.en")["error"]["code"], "invalid_audio")

    def test_oversized_audio(self):
        big = self.root / "big.wav"
        save_wav(big, [0] * 16000 * 11)
        self.assertEqual(self.adapter.transcribe(big, "tiny.en")["error"]["code"], "invalid_audio")
        big.write_bytes(b"0" * (512 * 1024 + 1))
        self.assertEqual(self.adapter.transcribe(big, "tiny.en")["error"]["code"], "oversized_audio")

    def test_timeout_and_child_cleanup(self):
        adapter = WhisperAdapter(FAKE, self.models, strict_hashes=False, timeout_seconds=0.15)
        with patch.dict(os.environ, {"M3A_FAKE_MODE": "sleep"}):
            result = adapter.transcribe(self.clip, "tiny.en")
        self.assertEqual(result["error"]["code"], "timeout")
        self.assertLess(result["metrics"]["elapsed_ms"], 3000)

    def test_cancel_before_start(self):
        cancelled = threading.Event()
        cancelled.set()
        self.assertEqual(self.adapter.transcribe(self.clip, "tiny.en", cancelled)["error"]["code"], "cancelled")

    def test_cancel_active_child(self):
        cancelled = threading.Event()
        def stop():
            import time
            time.sleep(0.12)
            cancelled.set()
        thread = threading.Thread(target=stop)
        thread.start()
        try:
            with patch.dict(os.environ, {"M3A_FAKE_MODE": "sleep"}):
                result = self.adapter.transcribe(self.clip, "tiny.en", cancelled)
        finally:
            thread.join()
        self.assertEqual(result["error"]["code"], "cancelled")

    def test_engine_failure(self):
        with patch.dict(os.environ, {"M3A_FAKE_MODE": "fail"}):
            result = self.adapter.transcribe(self.clip, "tiny.en")
        self.assertEqual(result["error"]["code"], "engine_failure")

    def test_normalization_and_ambiguous_search(self):
        self.assertEqual(normalize("SUPER Mario Bros. Two"), normalize("Super Mario Bros. 2"))
        self.assertEqual(catalog_match("Mega Man Three", ["Mega Man 2", "Mega Man 3"]), "Mega Man 3")
        self.assertIsNone(catalog_match("", ["Metroid Prime"]))
        self.assertIsNone(catalog_match("unrelated words", ["Metroid Prime"]))

    def test_benchmark_serialization_and_mock_label(self):
        class Args:
            engine = str(FAKE)
            models_dir = str(self.models)
            fixtures = str(self.fixtures)
            catalog = str(ROOT / "experiments/m3a/catalog.json")
            engine_revision = "mock"
            threads = 2
            timeout = 1
            repeats = 2
            output = str(self.root / "results.json")
            mock = True
        report = run(Args())
        self.assertEqual(report["measurement_class"], "mock_pipeline_only")
        self.assertEqual(len(report["rows"]), 16 * 2 * 2)
        self.assertEqual(report["decision"], "collect_more_evidence")
        self.assertEqual(json.loads(Path(Args.output).read_text())["rows"][0]["expected"], "Super Mario Bros. 2")

    def test_real_runner_rejects_mock_fixture(self):
        from experiments.m3a.benchmark import run
        class Args:
            engine = str(FAKE)
            models_dir = str(self.models)
            fixtures = str(self.fixtures)
            catalog = str(ROOT / "experiments/m3a/catalog.json")
            engine_revision = "96ec4d9823e9d0211944172da35f9f29134af990"
            threads = 2
            timeout = 1
            repeats = 1
            output = str(self.root / "results.json")
            mock = False
        with self.assertRaises(ValueError):
            run(Args())

    def test_production_package_excludes_experiment(self):
        package = (ROOT / "decky/package_plugin.py").read_text()
        self.assertNotIn("experiments", package)
        for folder in ("decky", "library"):
            for path in (ROOT / folder).rglob("*.py"):
                self.assertNotIn("experiments.m3a", path.read_text())
