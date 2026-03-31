#!/usr/bin/env python3
"""
cmd-sniper - Standalone runner (no installation required)

Usage: python cmd-sniper.py [args]
       ./cmd-sniper.py [args]
"""
import sys
from pathlib import Path

# Add src to path
SRC_DIR = Path(__file__).parent / "src"
sys.path.insert(0, str(SRC_DIR))

from cli import main

if __name__ == "__main__":
    main()
