"""Isolated CLI entry point, including when invoked from another working directory."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from library.cli import main

if __name__ == "__main__":
    sys.exit(main())

