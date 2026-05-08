# sim/Makefile — cocotb simulation for ntt_top HLS IP (ap_ctrl_hs + ap_memory)
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
# HLS-generated Verilog lives in vivado/ip_repo/hdl/verilog/.
# Wildcard picks up ntt_top and all sub-modules automatically.

# ── cocotb settings ───────────────────────────────────────────────────────────
SIM       = icarus
TOPLEVEL  = ntt_top
COCOTB_TEST_MODULES = test_ntt_top

# ── Verilog sources (top-level first, then dependencies) ─────────────────────
REPO_ROOT := $(shell cd .. && pwd)
VLOG_DIR  := $(REPO_ROOT)/vivado/ip_repo/hdl/verilog

# Wildcard picks up all HLS-generated sub-modules automatically;
# re-synthesis adds/removes files without requiring Makefile edits.
VERILOG_SOURCES = $(wildcard $(VLOG_DIR)/*.v)

# $readmemh in HLS ROMs uses paths relative to vvp's CWD (sim/).
# Copy .dat files here so they resolve correctly at runtime.
$(shell cp $(VLOG_DIR)/*.dat . 2>/dev/null || true)

# ── Icarus-specific options ───────────────────────────────────────────────────
# -g2012  : enable SystemVerilog-2012 constructs used by some HLS sub-modules
COMPILE_ARGS += -g2012

# Dump waveforms for post-sim debug with GTKWave
COMPILE_ARGS += -DCOCOTB_SIM=1

# Wave dump (set WAVES=1 to enable) — writes dump.vcd in sim/
# wave_dump.v uses $dumpfile/$dumpvars; must be elaborated as a second top-level.
ifeq ($(WAVES),1)
VERILOG_SOURCES += wave_dump.v
COMPILE_ARGS    += -s wave_dump
COCOTB_HDL_TIMEUNIT      = 1ns
COCOTB_HDL_TIMEPRECISION = 1ps
endif

# ── Timeout note ──────────────────────────────────────────────────────────────
# ~12 k cycles per vector × 3 vectors × 3× headroom ≈ 110 k cycles simulated.
# Per-vector cap of 40 000 cycles is enforced inside the Python test.

# ── Include cocotb's core Makefile ────────────────────────────────────────────
# cocotb installs this at $(shell cocotb-config --makefiles)/Makefile.sim
include $(shell cocotb-config --makefiles)/Makefile.sim

# ── Convenience targets ───────────────────────────────────────────────────────
waves:
	gtkwave dump.vcd &

.PHONY: waves
