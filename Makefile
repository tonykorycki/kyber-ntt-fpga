# hls/vitis_hls.bat: thin wrapper that sources Vitis settings64.bat then calls vitis_hls.exe
# Using cmd //c (MinGW-safe) and backslash paths to avoid Windows /flag parsing of forward slashes
RUN_HLS = python scripts/run_hls_win.py $(1)

.PHONY: golden twiddle hls-csim-barrett hls-csim-ntt-engine hls-csim-twist hls-csim-pointwise hls-csim hls-synth sim clean help

help:
	@echo "Targets:"
	@echo "  golden               -- run Python golden model tests (M1)"
	@echo "  twiddle              -- regenerate hls/src/twiddle_rom.h and vivado/*.coe (M3)"
	@echo "  hls-csim-barrett     -- Vitis C-sim: barrett unit test (M2)"
	@echo "  hls-csim-ntt-engine  -- Vitis C-sim: ntt_engine unit test (M4)"
	@echo "  hls-csim-twist       -- Vitis C-sim: twist unit test (M5)"
	@echo "  hls-csim-pointwise   -- Vitis C-sim: pointwise unit test (M5)"
	@echo "  hls-csim             -- Vitis C-sim: full pipeline tb_ntt_top (M6)"
	@echo "  hls-synth            -- HLS synthesis + IP export to vivado/ip_repo (M6)"
	@echo "  sim                  -- SystemVerilog simulation via Icarus (M8)"
	@echo "  clean                -- remove all generated artifacts"

golden:
	python golden/test_ntt.py

twiddle:
	python scripts/gen_twiddle_rom.py --n 4 --q 17

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
	rm -f hls/src/twiddle_rom.h vivado/twiddle_omega.coe vivado/twiddle_psi.coe
