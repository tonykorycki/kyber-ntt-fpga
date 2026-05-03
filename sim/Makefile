# sim/Makefile — cocotb simulation for ntt_top HLS IP
#
# Requires:
#   - cocotb (pip install cocotb)
#   - Icarus Verilog (iverilog / vvp)
#
# Usage:
#   make              — run simulation
#   make clean        — remove build artifacts
#   make waves        — open waveform in GTKWave (requires GTKWave)
#
# The HLS-generated IP lives entirely in vivado/ip_repo/hdl/verilog/.
# All sub-modules are listed explicitly so iverilog resolves them without
# needing a library search path.

# ── cocotb settings ───────────────────────────────────────────────────────────
SIM       = icarus
TOPLEVEL  = ntt_top
MODULE    = test_ntt_top

# ── Verilog sources (top-level first, then dependencies) ─────────────────────
REPO_ROOT := $(shell cd .. && pwd)
VLOG_DIR  := $(REPO_ROOT)/vivado/ip_repo/hdl/verilog

# Wildcard picks up all HLS-generated sub-modules automatically;
# re-synthesis adds/removes files without requiring Makefile edits.
VERILOG_SOURCES = $(wildcard $(VLOG_DIR)/*.v)

# ── Icarus-specific options ───────────────────────────────────────────────────
# -g2012  : enable SystemVerilog-2012 constructs used by some HLS sub-modules
COMPILE_ARGS += -g2012

# Dump waveforms for post-sim debug with GTKWave
COMPILE_ARGS += -DCOCOTB_SIM=1

# Wave dump via cocotb's built-in VCD support (set WAVES=1 to enable)
ifeq ($(WAVES),1)
COCOTB_HDL_TIMEUNIT      = 1ns
COCOTB_HDL_TIMEPRECISION = 1ps
export COCOTB_ENABLE_COVERAGE = 0
# iverilog will write sim_build/ntt_top.vcd; open with:
#   gtkwave sim_build/ntt_top.vcd
PLUSARGS += +dumpfile=sim_build/ntt_top.vcd +dumpvars=0
endif

# ── Timeout (cycles × CLK_NS gives wall time) ─────────────────────────────────
# ~12 k cycles per vector × 3 vectors × 3× headroom = ~110 k cycles
# At 10 ns/cycle that is 1.1 ms simulated time.  cocotb has no global
# timeout by default; the per-poll loop in the test caps each vector at
# 40 000 cycles.

# ── Include cocotb's core Makefile ────────────────────────────────────────────
# cocotb installs this at $(shell cocotb-config --makefiles)/Makefile.sim
include $(shell cocotb-config --makefiles)/Makefile.sim

# ── Convenience targets ───────────────────────────────────────────────────────
waves:
	gtkwave sim_build/ntt_top.vcd &

.PHONY: waves
