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

module bram_mux #(
    parameter   ADDR_W = 8,
    parameter   DATA_W = 12
)(
    input logic              ps_own,

    input logic              ps_en, hls_en,
    input logic              ps_we, hls_we,
    input logic [ADDR_W-1:0] ps_addr, hls_addr,
    input logic [DATA_W-1:0] ps_din, hls_din,
    input logic [DATA_W-1:0] bram_dout,

    output logic              bram_en,
    output logic              bram_we,
    output logic [ADDR_W-1:0] bram_addr,
    output logic [DATA_W-1:0] ps_dout, hls_dout,
    output logic [DATA_W-1:0] bram_din
);

    assign bram_addr = ps_own ? ps_addr : hls_addr;
    assign bram_din  = ps_own ? ps_din  : hls_din;
    assign bram_we   = ps_own ? ps_we   : hls_we;
    assign bram_en   = ps_own ? ps_en   : hls_en;

    assign ps_dout   = bram_dout;
    assign hls_dout  = bram_dout;
    
endmodule