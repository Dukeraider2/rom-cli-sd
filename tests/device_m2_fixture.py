"""Publish an original NROM fixture via M2 RPC into a new, disposable library."""
import argparse
import functools
import hashlib
import json
import tempfile
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from library.decky_api import Service
from library.platforms import PLATFORMS, discover, destination
from library.provider_http import Network
from library.queue import Queue


def cartridge():
    # Set the NES background palette, then spin. All program and CHR bytes are original.
    program = bytes.fromhex("78 d8 a9 00 8d 00 20 8d 01 20 2c 02 20 10 fb "
                            "a9 3f 8d 06 20 a9 00 8d 06 20 a9 21 8d 07 20 "
                            "4c 1e 80")
    prg = program.ljust(16384 - 6, b"\xea") + bytes.fromhex("00 80 00 80 00 80")
    return b"NES\x1a" + bytes([1, 1]) + bytes(10) + prg + bytes(8192)


def run(parent, suite=None, expected_root=None):
    stage = Path(tempfile.mkdtemp(prefix="m2-playable-", dir=parent)).resolve()
    mirror = stage / "mirror"
    mirror.mkdir()
    name = "M2 Palette Test.nes"
    image = cartridge()
    (mirror / name).write_bytes(image)
    if suite:
        home = Path.home()
        row = discover(suite, home)
        folder = destination(row, "nes", write=True)
        if folder.parent != expected_root.resolve(strict=True) or (folder / name).exists():
            raise ValueError("Expected a matching disposable suite root with an unused fixture name")
    else:
        suite = "emudeck"
        home = stage
        folder = stage / "roms/nes"
        folder.mkdir(parents=True)
        settings = stage / ".config/EmuDeck/settings.sh"
        settings.parent.mkdir(parents=True)
        settings.write_text('romsPath=~/roms\n')
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(mirror))
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        queue = Queue(stage / "catalog", Network(f"http://127.0.0.1:{server.server_port}/", True), home)
        try:
            api = Service(queue)
            def rpc(op, **args):
                result = api.request(1, op, args)
                if not result["ok"]:
                    raise RuntimeError(result["error"])
                return result["data"]
            item = rpc("search", provider="mirror", query="Palette", system="nes", page=1, file_page=1)["results"][0]
            selection = dict(result=item["id"], platform=suite, system="nes")
            preview = rpc("get_result", **selection)
            if Path(preview["destination"]).parent != folder or not preview["can_install"]:
                raise RuntimeError("Destination changed or the preview rejected installation")
            job = rpc("enqueue", token=preview["token"], confirmed=True)["id"]
            deadline = time.monotonic() + 30
            while True:
                status = rpc("get_progress", job=job)["state"]
                if status == "completed":
                    break
                if status in ("failed", "cancelled", "needs_attention") or time.monotonic() >= deadline:
                    raise RuntimeError(status)
                time.sleep(.05)
            output = Path(preview["destination"])
            assert output.parent == folder and output.read_bytes() == image
            assert not rpc("get_result", **selection)["can_install"]
            print(json.dumps({"installed": str(output), "sha256": hashlib.sha256(image).hexdigest(),
                              "job": status, "duplicate_blocked": True}))
        finally:
            queue.close()
            server.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parent", type=Path, help="Existing writable parent on the selected device")
    parser.add_argument("--configured-suite", choices=PLATFORMS)
    parser.add_argument("--expected-rom-root", type=Path,
                        help="Explicit disposable ROM root of the configured suite")
    args = parser.parse_args()
    if bool(args.configured_suite) != bool(args.expected_rom_root):
        parser.error("--configured-suite and --expected-rom-root must be supplied together")
    run(args.parent, args.configured_suite, args.expected_rom_root)
