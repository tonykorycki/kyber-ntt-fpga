`ifdef COCOTB_SIM
module wave_dump;
initial begin
    $dumpfile("dump.vcd");
    $dumpvars(0, ntt_top);
end
endmodule
`endif
