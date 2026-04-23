#!/usr/bin/env bash
# scripts/run_sim.sh — Run SystemVerilog simulation (Icarus Verilog)
#
# Prerequisites: RTL files must exist (M7+). Run after HLS synthesis exports the IP.
set -euo pipefail

REPO_ROOT="$(dirname "$0")/.."

RTL_FILES=(
    "$REPO_ROOT/rtl/bram_mux.sv"
    "$REPO_ROOT/rtl/ntt_top_wrapper.sv"
)
TB="$REPO_ROOT/rtl/tb/tb_ntt_top.sv"

for f in "${RTL_FILES[@]}"; do
    if [[ ! -f "$f" ]]; then
        echo "ERROR: $f not found. RTL must be implemented (M7) before simulation." >&2
        exit 1
    fi
done

iverilog -g2012 -o "$REPO_ROOT/sim/tb_ntt_top.vvp" \
    "${RTL_FILES[@]}" "$TB"

vvp "$REPO_ROOT/sim/tb_ntt_top.vvp"
