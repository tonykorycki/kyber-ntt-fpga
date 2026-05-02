# hls/vitis_hls.bat: thin wrapper that sources Vitis settings64.bat then calls vitis_hls.exe
# Using cmd //c (MinGW-safe) and backslash paths to avoid Windows /flag parsing of forward slashes
RUN_HLS = python scripts/run_hls_win.py $(1)

# Override these on the command line to test alternate parameter sets:
#   make golden NTT_N=128 NTT_Q=3329
NTT_N ?= 4
NTT_Q ?= 17

.PHONY: all golden golden-kyber vectors twiddle hls-csim-barrett hls-csim-ntt-engine hls-csim-mul-ntt hls-csim hls-synth sim clean clean-sim clean-hls help

help:
	@echo "Targets:"
	@echo "  all                  -- full Kyber build: golden -> twiddle -> vectors -> all C-sims -> synth"
	@echo "  golden               -- run Python golden model tests with dev params n=$(NTT_N) q=$(NTT_Q)"
	@echo "  golden-kyber         -- run Python golden model tests with full Kyber params n=256 q=3329"
	@echo "  vectors              -- regenerate golden/test_vectors.txt for HLS/SV testbenches"
	@echo "  twiddle              -- regenerate hls/src/twiddle_rom.h and vivado/*.coe (M3)"
	@echo "  hls-csim-barrett     -- Vitis C-sim: barrett unit test (M2)"
	@echo "  hls-csim-ntt-engine  -- Vitis C-sim: ntt_engine unit test (M4)"
	@echo "  hls-csim-mul-ntt     -- Vitis C-sim: base-case slot multiply unit test (M5)"
	@echo "  hls-csim             -- Vitis C-sim: full pipeline tb_ntt_top (M6)"
	@echo "  hls-synth            -- HLS synthesis + IP export to vivado/ip_repo (M6)"
	@echo "  sim                  -- SystemVerilog simulation via Icarus (M8)"
	@echo "  clean                -- remove all generated artifacts (HLS build + sim)"
	@echo "  clean-sim            -- remove only sim artifacts (preserves HLS build/synthesis)"
	@echo "  clean-hls            -- remove only HLS build artifacts"

NTT_VECTORS ?= 16

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

golden:
	python golden/kyber_ntt.py --n $(NTT_N) --q $(NTT_Q)

golden-kyber:
	python golden/kyber_ntt.py --n 256 --q 3329

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

sim:
	bash scripts/run_sim.sh

clean-sim:
	rm -f sim/*.vvp sim/*.vcd sim/*.fst sim/*.log

clean-hls:
	rm -rf build/hls/

clean: clean-sim clean-hls
	rm -f hls/src/twiddle_rom.h vivado/twiddle.coe vivado/slot_zeta.coe
