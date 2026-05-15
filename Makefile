RUN_HLS    = python scripts/run_hls_win.py $(1)
RUN_VIVADO = python scripts/run_vivado_win.py $(1)

# Override these on the command line to test alternate parameter sets:
#   make golden NTT_N=128 NTT_Q=3329
NTT_N ?= 4
NTT_Q ?= 17

.PHONY: all golden golden-kyber vectors twiddle hls-csim-barrett hls-csim-ntt-engine hls-csim-mul-ntt hls-csim hls-synth vivado-impl export bitstream sim clean clean-sim clean-hls clean-vivado help

help:
	@echo "Targets:"
	@echo "  all                  -- full build: golden -> twiddle -> vectors -> C-sims -> synth -> sim -> vivado-impl -> export"
	@echo "  golden               -- run Python golden model tests with dev params n=$(NTT_N) q=$(NTT_Q)"
	@echo "  golden-kyber         -- run Python golden model tests with full Kyber params n=256 q=3329"
	@echo "  vectors              -- regenerate golden/test_vectors.txt for HLS/SV testbenches"
	@echo "  twiddle              -- regenerate hls/src/twiddle_rom.h and vivado/*.coe (M3)"
	@echo "  hls-csim-barrett     -- Vitis C-sim: barrett unit test (M2)"
	@echo "  hls-csim-ntt-engine  -- Vitis C-sim: ntt_engine unit test (M4)"
	@echo "  hls-csim-mul-ntt     -- Vitis C-sim: base-case slot multiply unit test (M5)"
	@echo "  hls-csim             -- Vitis C-sim: full pipeline tb_ntt_top (M6)"
	@echo "  hls-synth            -- HLS synthesis + IP export to vivado/ip_repo (M6)"
	@echo "  vivado-impl          -- Vivado synthesis + implementation + bitstream (M7)"
	@echo "  export               -- copy bitstream + HWH to bitstream/ folder"
	@echo "  bitstream            -- full flow: hls-synth -> vivado-impl -> export"
	@echo "  sim                  -- cocotb RTL simulation; NTT_MAX_VECTORS=N WAVES=1"
	@echo "  clean-vivado         -- remove Vivado project and build logs (force fresh rebuild)"
	@echo "  clean                -- remove all generated artifacts (HLS build + sim)"
	@echo "  clean-sim            -- remove only sim artifacts (preserves HLS build/synthesis)"
	@echo "  clean-hls            -- remove only HLS build artifacts"

NTT_VECTORS     ?= 16
NTT_MAX_VECTORS ?= 64
WAVES           ?= 0

all:
	@echo "=== Kyber NTT full build (n=256, q=3329) ==="
	@echo ""
	@echo "--- Golden model ---"
	$(MAKE) golden-kyber
	@echo ""
	@echo "--- Twiddle ROM (M3) ---"
	$(MAKE) twiddle NTT_N=256 NTT_Q=3329
	@echo ""
	@echo "--- Test vectors ---"
	$(MAKE) vectors NTT_N=256 NTT_Q=3329 NTT_VECTORS=64
	@echo ""
	@echo "--- HLS C-sim: Barrett (M2) ---"
	$(MAKE) hls-csim-barrett
	@echo ""
	@echo "--- HLS C-sim: NTT engine (M4) ---"
	$(MAKE) hls-csim-ntt-engine
	@echo ""
	@echo "--- HLS C-sim: base-case multiply (M5) ---"
	$(MAKE) hls-csim-mul-ntt
	@echo ""
	@echo "--- HLS C-sim: full pipeline (M6) ---"
	$(MAKE) hls-csim
	@echo ""
	@echo "--- HLS synthesis + IP export (M6) ---"
	$(MAKE) hls-synth
	@echo ""
	@echo "--- RTL simulation: 64 vectors (M8) ---"
	$(MAKE) sim
	@echo ""
	@echo "--- Vivado implementation + bitstream (M7) ---"
	$(MAKE) vivado-impl
	@echo ""
	@echo "--- Export bitstream ---"
	$(MAKE) export

golden:
	python golden/test_kyber_ntt.py --n $(NTT_N) --q $(NTT_Q)

golden-kyber:
	python golden/test_kyber_ntt.py --n 256 --q 3329

vectors:
	python golden/gen_test_vectors.py --n $(NTT_N) --q $(NTT_Q) --vectors $(NTT_VECTORS)

twiddle:
	python scripts/gen_twiddle_rom.py --n $(NTT_N) --q $(NTT_Q)

hls-csim-barrett:
	$(call RUN_HLS,hls/run_hls.tcl barrett)

hls-csim-ntt-engine:
	$(call RUN_HLS,hls/run_hls.tcl ntt_engine)

hls-csim-mul-ntt:
	$(call RUN_HLS,hls/run_hls.tcl mul_ntt)

hls-csim:
	$(call RUN_HLS,hls/run_hls.tcl)

hls-synth:
	$(call RUN_HLS,hls/run_hls.tcl synth)
	@echo ""
	@echo "Synthesis complete."
	@echo "  Timing/area report : build/hls/ntt_hls/solution1/syn/report/ntt_top_csynth.rpt"
	@echo "  IP catalog export  : vivado/ip_repo"

vivado-impl:
	$(call RUN_VIVADO,scripts/vivado_impl.tcl)
	@echo ""
	@echo "Implementation complete."
	@echo "  Bitstream : vivado/proj/ntt_accel/ntt_accel.runs/impl_1/ntt_bd_wrapper.bit"
	@echo "  HWH       : vivado/proj/ntt_accel/ntt_accel.gen/sources_1/bd/ntt_bd/hw_handoff/ntt_bd.hwh"
	@echo "  Logs      : build/vivado/vivado.log"

export:
	powershell -ExecutionPolicy Bypass -File scripts/export_bitstream.ps1
	@echo "Exported to bitstream/"

bitstream:
	$(MAKE) hls-synth
	$(MAKE) vivado-impl
	$(MAKE) export

sim:
	wsl --cd "$(CURDIR)/sim" -- bash -c "source ~/cocotb-venv/bin/activate && make clean && make NTT_MAX_VECTORS=$(NTT_MAX_VECTORS) WAVES=$(WAVES)"

clean-sim:
	rm -rf sim/sim_build/
	rm -f sim/*.vvp sim/*.vcd sim/*.fst sim/*.log sim/results.xml

clean-hls:
	rm -rf build/hls/

clean-vivado:
	rm -rf vivado/proj/ build/vivado/

clean: clean-sim clean-hls
	rm -f hls/src/twiddle_rom.h vivado/twiddle.coe vivado/slot_zeta.coe
