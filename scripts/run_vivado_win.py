#!/usr/bin/env python3
"""
scripts/run_vivado_win.py — Windows launcher for Vivado (2025.1)

Usage (via Makefile):
    python scripts/run_vivado_win.py scripts/vivado_impl.tcl
"""

import os
import sys
import subprocess

VIVADO = r"C:\Xilinx\2025.1\Vivado\bin\vivado.bat"

if len(sys.argv) < 2:
    print("Usage: run_vivado_win.py <tcl_file>", file=sys.stderr)
    sys.exit(1)

tcl_file = os.path.abspath(sys.argv[1])

log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build", "vivado")
os.makedirs(log_dir, exist_ok=True)

# Kill any lingering vivado.exe processes (including child synthesis/impl jobs)
# so -force can delete locked run directories on a re-run.
subprocess.run(["taskkill", "/F", "/IM", "vivado.exe"], capture_output=True)

result = subprocess.run(
    ["cmd", "/c", VIVADO,
     "-mode", "batch",
     "-source", tcl_file,
     "-log",    os.path.join(log_dir, "vivado.log"),
     "-journal", os.path.join(log_dir, "vivado.jou")],
)
sys.exit(result.returncode)
