#!/usr/bin/env bash
# scripts/run_sim.sh — Run SystemVerilog simulation (Icarus Verilog)
set -euo pipefail

cd "$(dirname "$0")/.."

# Compile
iverilog -g2012 -o sim/tb_ntt_top.vvp \
    rtl/twiddle_rom.sv \
    rtl/pre_post_twist.sv \
    rtl/axi_ctrl_fsm.sv \
    rtl/ntt_top.sv \
    sim/tb_ntt_top.sv

# Run
vvp sim/tb_ntt_top.vvp
