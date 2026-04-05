// rtl/axi_ctrl_fsm.sv — AXI-Lite slave + pipeline sequencing FSM
//
// Registers: CTRL (0x00), STATUS (0x04), CONFIG (0x08)
// FSM: IDLE -> PRE_TWIST -> NTT_A -> NTT_B -> POINTWISE -> INTT -> POST_TWIST -> DONE
