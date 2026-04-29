# hls/vitis_hls.bat: thin wrapper that sources Vitis settings64.bat then calls vitis_hls.exe
# Using cmd //c (MinGW-safe) and backslash paths to avoid Windows /flag parsing of forward slashes
RUN_HLS = python scripts/run_hls_win.py $(1)

# Override these on the command line to test alternate parameter sets:
#   make golden NTT_N=128 NTT_Q=3329
NTT_N ?= 4
NTT_Q ?= 17

.PHONY: golden golden-kyber vectors twiddle hls-csim-barrett hls-csim-ntt-engine hls-csim-twist hls-csim-pointwise hls-csim hls-synth sim clean help

help:
	@echo "Targets:"
	@echo "  golden               -- run Python golden model tests with dev params n=$(NTT_N) q=$(NTT_Q)"
	@echo "  golden-kyber         -- run Python golden model tests with full Kyber params n=256 q=3329"
	@echo "  vectors              -- regenerate golden/test_vectors.txt for HLS/SV testbenches"
	@echo "  twiddle              -- regenerate hls/src/twiddle_rom.h and vivado/*.coe (M3)"
	@echo "  hls-csim-barrett     -- Vitis C-sim: barrett unit test (M2)"
	@echo "  hls-csim-ntt-engine  -- Vitis C-sim: ntt_engine unit test (M4)"
	@echo "  hls-csim-twist       -- Vitis C-sim: twist unit test (M5)"
	@echo "  hls-csim-pointwise   -- Vitis C-sim: pointwise unit test (M5)"
	@echo "  hls-csim             -- Vitis C-sim: full pipeline tb_ntt_top (M6)"
	@echo "  hls-synth            -- HLS synthesis + IP export to vivado/ip_repo (M6)"
	@echo "  sim                  -- SystemVerilog simulation via Icarus (M8)"
	@echo "  clean                -- remove all generated artifacts"

NTT_VECTORS ?= 16

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

hls-csim-twist:
	$(call RUN_HLS,hls/run_hls.tcl twist)

hls-csim-pointwise:
	$(call RUN_HLS,hls/run_hls.tcl pointwise)

hls-csim:
	$(call RUN_HLS,hls/run_hls.tcl)

hls-synth:
	$(call RUN_HLS,hls/run_hls.tcl synth)

sim:
	bash scripts/run_sim.sh

clean:
	rm -rf build/
	rm -f sim/*.vvp sim/*.vcd sim/*.fst sim/*.log
	rm -f hls/src/twiddle_rom.h vivado/twiddle.coe vivado/slot_zeta.coe
