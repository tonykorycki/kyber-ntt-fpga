#!/usr/bin/env python3
"""
scripts/run_hls_win.py — Windows launcher for Vitis HLS (2025.1+)

Usage (via Makefile):
    python scripts/run_hls_win.py hls/run_hls.tcl barrett
    python scripts/run_hls_win.py hls/run_hls.tcl        # full project
"""

import os
import sys
import subprocess

VITIS_RUN = r"C:\Xilinx\2025.1\Vitis\bin\vitis-run.bat"

if len(sys.argv) < 2:
    print("Usage: run_hls_win.py <tcl_file> [mode]", file=sys.stderr)
    sys.exit(1)

tcl_file = sys.argv[1]
mode     = sys.argv[2] if len(sys.argv) > 2 else ""

env = os.environ.copy()
if mode:
    env["HLS_MODE"] = mode

work_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build", "hls")
os.makedirs(work_dir, exist_ok=True)

result = subprocess.run(
    ["cmd", "/c", VITIS_RUN, "--mode", "hls", "--work_dir", work_dir, "--tcl", tcl_file],
    env=env
)
sys.exit(result.returncode)
