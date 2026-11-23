"""Reproducible M3A comparison. Run with: python3 -m experiments.m3a.benchmark --help"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import statistics
import sys
import unicodedata

from .transcribe import ENGINE_REVISION, MODELS, WhisperAdapter, digest

NUMBER_WORDS = {"zero":"0","one":"1","two":"2","three":"3","four":"4",
                "five":"5","six":"6","seven":"7","eight":"8","nine":"9","ten":"10"}
MATCH_THRESHOLD = 0.82
MARGIN = 0.08


def normalize(title: str) -> str:
    """NFKC, casefold, & -> and, number words 0..10 -> digits, strip punctuation."""
    s = unicodedata.normalize("NFKC", title).casefold().replace("&", " and ")
    words = re.findall(r"[^\W_]+", s, re.UNICODE)
    return " ".join(NUMBER_WORDS.get(w, w) for w in words)


def catalog_match(transcript: str, catalog: list[str]) -> str | None:
    query = normalize(transcript)
    if not query:
        return None
    scored = sorted(((difflib.SequenceMatcher(None, query, normalize(title)).ratio(), title)
                     for title in catalog), reverse=True)
    exact = [title for title in catalog if normalize(title) == query]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1 or not scored or scored[0][0] < MATCH_THRESHOLD:
        return None
    if len(scored) > 1 and scored[0][0] - scored[1][0] < MARGIN:
        return None
    return scored[0][1]


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    index = (len(values) - 1) * fraction
    low = int(index)
    return round(values[low] + (values[min(low+1, len(values)-1)] - values[low]) * (index-low), 3)


def summarize(rows: list[dict], model: str) -> dict:
    selected = [r for r in rows if r["model"] == model]
    groups = {}
    for kind in ("human", "synthetic", "silence", "noise"):
        group = [r for r in selected if r["kind"] == kind]
        valid = [r for r in group if r["ok"]]
        title = [r for r in valid if r["expected"] is not None]
        times = [r["metrics"]["elapsed_ms"] for r in valid]
        groups[kind] = {
            "samples": len(group), "successful_runs": len(valid),
            "raw_exact": {"numerator": sum(r["transcript"] == r["expected"] for r in title),
                          "denominator": len(title)},
            "normalized_exact": {"numerator": sum(normalize(r["transcript"]) == normalize(r["expected"]) for r in title),
                                 "denominator": len(title)},
            "catalog_retrieval": {"numerator": sum(r["retrieved"] == r["expected"] for r in title),
                                  "denominator": len(title)},
            "false_nonempty": {"numerator": sum(bool(r["transcript"].strip()) for r in valid if r["expected"] is None),
                               "denominator": sum(r["expected"] is None for r in valid)},
            "latency_ms": {"p50": percentile(times, 0.5), "p95": percentile(times, 0.95)},
        }
    successful = [r for r in selected if r["ok"]]
    first = [r["metrics"]["elapsed_ms"] for r in successful if r["repeat"] == 1]
    subsequent = [r["metrics"]["elapsed_ms"] for r in successful if r["repeat"] > 1]
    return {"model": model, "groups": groups,
            "fresh_process_first_run_ms": {"samples": len(first), "p50": percentile(first, 0.5), "p95": percentile(first, 0.95)},
            "fresh_process_subsequent_run_ms": {"samples": len(subsequent), "p50": percentile(subsequent, 0.5), "p95": percentile(subsequent, 0.95)},
            "peak_rss_bytes_sampled": max((r["metrics"]["peak_rss_bytes_sampled"] or 0 for r in successful), default=None),
            "cpu_seconds_total": round(sum(r["metrics"]["cpu_seconds"] for r in successful), 5),
            "temporary_disk_bytes_peak": max((r["metrics"]["temporary_disk_bytes"] for r in successful), default=None),
            "model_size_bytes": successful[0]["metrics"]["model_size_bytes"] if successful else None,
            "errors": [dict(fixture=r["fixture"],code=r["error"]["code"]) for r in selected if not r["ok"]]}


def run(args) -> dict:
    if args.engine_revision != ENGINE_REVISION and not args.mock:
        raise ValueError("Engine revision must match pinned M3A revision")
    fixture_dir = Path(args.fixtures).resolve()
    manifest = json.loads((fixture_dir / "manifest.json").read_text(encoding="utf-8"))
    catalog = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
    if not isinstance(catalog, list) or len(catalog) != len(set(catalog)) or not all(isinstance(x, str) for x in catalog):
        raise ValueError("Catalog must be a list of distinct titles")
    if manifest.get("schema") != 1 or not isinstance(manifest.get("clips"), list) or not manifest["clips"]:
        raise ValueError("Invalid fixture manifest")
    if not args.mock and (manifest.get("fixture_mode") == "mock" or any(
            c.get("provenance", {}).get("generator") == "test_tone" for c in manifest["clips"])):
        raise ValueError("Mock-only fixtures cannot be used as real ASR evidence")
    if not 1 <= args.repeats <= 20:
        raise ValueError("repeats must be 1..20")
    adapter = WhisperAdapter(Path(args.engine), Path(args.models_dir), threads=args.threads,
                             timeout_seconds=args.timeout, strict_hashes=not args.mock)
    if not args.mock:
        for model in MODELS:
            adapter._model(model)
    rows = []
    for fixture in manifest["clips"]:
        fixture_id = fixture["id"]
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", fixture_id):
            raise ValueError("Invalid fixture ID")
        path = fixture_dir / (fixture_id + ".wav")
        if path.is_symlink() or not path.is_file() or path.resolve().parent != fixture_dir:
            raise ValueError("Fixture file missing or linked: " + fixture_id)
        if digest(path) != fixture["sha256"]:
            raise ValueError("Fixture digest mismatch: " + fixture_id)
        kind = fixture["kind"]
        if kind not in ("human", "synthetic", "silence", "noise"):
            raise ValueError("Unknown fixture category")
        if kind == "human" and fixture.get("permission") not in ("consented", "redistributable"):
            raise ValueError("Human recordings require documented permission")
        expected = fixture.get("expected_title")
        if expected is not None and expected not in catalog:
            raise ValueError("Fixture title missing from fixed catalog")
        if kind in ("silence", "noise") and expected is not None:
            raise ValueError("Non-speech fixtures cannot have expected titles")
        for model in MODELS:
            for repeat in range(1, args.repeats + 1):
                result = adapter.transcribe(path, model)
                row = {"fixture": fixture_id, "kind": kind, "repeat": repeat,
                       "model": model, "expected": expected, "ok": result["ok"],
                       "transcript": result.get("text", ""),
                       "retrieved": catalog_match(result.get("text", ""), catalog) if result["ok"] else None,
                       "metrics": result.get("metrics", {}), "error": result.get("error")}
                rows.append(row)
    engine_path = Path(args.engine).resolve()
    report = {
        "schema": 1,
        "measurement_class": "mock_pipeline_only" if args.mock else "real_whisper_cpp_fresh_process",
        "decision": "collect_more_evidence",
        "decision_reason": ("Mock output does not measure speech recognition" if args.mock
                            else "Host measurements require review and physical Steam Deck M3B validation"),
        "engine": {"revision_declared": "fake_engine" if args.mock else args.engine_revision,
                   "revision_verification": "declared by operator; compare git checkout separately",
                   "binary_sha256": digest(engine_path), "path": str(engine_path)},
        "command_template": [str(engine_path), "-m", "<verified-model-path>", "-f", "<verified-fixture-wav>",
                             "-l", "en", "-t", str(args.threads), "-ng", "-nf", "-sns",
                             "-tp", "0", "-tpi", "0", "-bs", "5", "-bo", "5",
                             "-otxt", "-of", "<private-temporary-output-stem>"],
        "environment": {"platform": platform.platform(), "machine": platform.machine(),
                        "python": sys.version.split()[0], "cpu_count": os.cpu_count(),
                        "threads": args.threads, "timeout_seconds": args.timeout,
                        "repeats": args.repeats, "backend": "cpu", "model_lifecycle": "fresh_process_each_clip",
                        "first_run": "new process; may have cold filesystem cache",
                        "subsequent_runs": "new process; possibly warm filesystem cache; NOT resident model",
                        "cpu_time_scope": "child process rusage delta",
                        "rss_scope": "sampled Linux /proc VmHWM; may miss short-lived peaks",
                        "temp_disk_scope": "temporary output/log files before cleanup"},
        "settings": {"language":"en","no_gpu":True,"no_fallback":True,"suppress_nst":True,
                     "temperature":0,"temperature_increment":0,"beam_size":5,"best_of":5},
        "normalization": "NFKC + casefold + &=>and + number words zero..ten=>digits + punctuation/underscore removal + whitespace collapse",
        "catalog_matching": {"rule":"exact normalized title, otherwise SequenceMatcher ratio",
                             "threshold":MATCH_THRESHOLD,"runner_up_margin":MARGIN,"ambiguous":"no match"},
        "catalog_sha256": digest(Path(args.catalog)),
        "fixture_manifest_sha256": digest(fixture_dir / "manifest.json"),
        "fixture_provenance": {f["id"]: f.get("provenance") for f in manifest["clips"]},
        "models": {m: adapter._model(m)[1] for m in MODELS},
        "rows": rows, "summary": {m: summarize(rows, m) for m in MODELS},
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description="Offline M3A model comparison")
    parser.add_argument("--engine", required=True, help="Path to pinned whisper-cli executable")
    parser.add_argument("--models-dir", required=True)
    parser.add_argument("--fixtures", required=True, help="Directory with manifest.json and WAV clips")
    parser.add_argument("--catalog", default="experiments/m3a/catalog.json")
    parser.add_argument("--engine-revision", default=ENGINE_REVISION)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=45)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", default="experiments/m3a/local/results.json")
    parser.add_argument("--mock", action="store_true", help="Only for deterministic pipeline tests, never ASR evidence")
    args = parser.parse_args()
    try:
        report = run(args)
    except (ValueError, KeyError, OSError, TypeError) as exc:
        parser.error(str(exc))
    print(f"{report['measurement_class']}: {len(report['rows'])} runs -> {args.output}")
    for model, summary in report["summary"].items():
        print(model, "synthetic:", summary["groups"]["synthetic"]["catalog_retrieval"],
              "false inputs:", {k:summary["groups"][k]["false_nonempty"] for k in ("silence","noise")})


if __name__ == "__main__":
    main()
