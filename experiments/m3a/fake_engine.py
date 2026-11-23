#!/usr/bin/env python3
"""Deterministic fake whisper-cli. NEVER use as ASR accuracy evidence."""
import argparse
import os
from pathlib import Path
import sys
import time

TRANSCRIPTS = {
    "mario-2": "Super Mario Bros. 2", "mario-3": "Super Mario Bros. 3",
    "metroid-prime": "Metroid Prime", "metroid-prime-2": "Metroid Prime 2: Echoes",
    "mega-man-2": "Mega Man 2", "mega-man-3": "Mega Man 3",
    "zelda": "The Legend of Zelda", "zelda-past": "The Legend of Zelda: A Link to the Past",
    "sonic": "Sonic the Hedgehog", "sonic-2": "Sonic the Hedgehog 2",
    "chrono": "Chrono Trigger", "street-fighter-2": "Street Fighter II",
    "mario-2-noisy": "Super Mario Bros. 2",
    "metroid-prime-noisy": "Metroid Prime",
}


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-f", required=True)
    parser.add_argument("-m", required=True)
    parser.add_argument("-of", required=True)
    args, _ = parser.parse_known_args()
    mode = os.getenv("M3A_FAKE_MODE", "")
    if mode == "sleep":
        time.sleep(5)
    if mode == "fail":
        return 17
    text = TRANSCRIPTS.get(Path(args.f).stem, "")
    if mode == "empty":
        text = ""
    if mode == "hallucinate":
        text = "A fictional game"
    Path(args.of + ".txt").write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
