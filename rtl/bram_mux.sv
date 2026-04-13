// rtl/bram_mux.sv — BRAM port arbitrator
//
// Routes BRAM port B between PS (write inputs / read output) and
// HLS IP (compute), based on whether the HLS core is idle.
//
// ps_own = 1: PS controls BRAM  (HLS idle, ap_idle=1)
// ps_own = 0: HLS controls BRAM (computation in progress)
//
// This is the only RTL file with combinational logic.
// All other .sv files are purely structural.
