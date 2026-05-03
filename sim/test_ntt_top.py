"""
sim/test_ntt_top.py — cocotb testbench for ntt_top HLS IP

DUT: ntt_top (Vitis HLS v2025.1, Verilog)
Function: NTT(a), NTT(b), pointwise multiply, INTT(c) — negacyclic poly mul mod Q=3329
Parameters: N=256, Q=3329, coef_width=12 bits

Interface:
  - ap_clk / ap_rst_n (active-low)
  - s_axi_CTRL_*  : AXI-Lite slave, 32-bit data, 6-bit address
  - m_axi_MAXI_*  : AXI4 master, 64-bit addr, 32-bit data
  - interrupt      : output, pulses when done

AXI-Lite CTRL Register Map:
  0x00 : CTRL  — bit0=ap_start, bit1=ap_done, bit2=ap_idle
  0x10 : a_1   — lower 32b of physical address of array a
  0x14 : a_2   — upper 32b (always 0)
  0x1c : b_1   — lower 32b of physical address of array b
  0x20 : b_2   — upper 32b (always 0)
  0x28 : c_1   — lower 32b of physical address of array c
  0x2c : c_2   — upper 32b (always 0)

Memory layout:
  Each coefficient is 12-bit, stored as 16-bit (zero-extended) in the HLS user domain.
  The MAXI adapter has CH0_USER_DW=16 and C_M_AXI_DATA_WIDTH=32, so it packs two 16-bit
  coefficients per 32-bit AXI beat.
  For N=256 coefficients: 128 AXI beats per array, ARLEN/AWLEN=127.

  Simulated memory layout (byte-addressed):
    Array a: base_a .. base_a + 256*2 - 1  (256 half-words = 512 bytes = 128 x 32-bit words)
    Array b: base_b .. base_b + 512 - 1
    Array c: base_c .. base_c + 512 - 1

  We assign non-overlapping 4KB-aligned base addresses:
    base_a = 0x0000_1000
    base_b = 0x0000_2000
    base_c = 0x0000_3000
"""

import os
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────
N          = 256
Q          = 3329
CLK_NS     = 10        # 100 MHz

# Simulated memory base addresses (byte-addressed, 32-bit system)
BASE_A     = 0x00001000
BASE_B     = 0x00002000
BASE_C     = 0x00003000

# AXI-Lite CTRL register offsets
CTRL_OFFSET  = 0x00
A1_OFFSET    = 0x10
A2_OFFSET    = 0x14
B1_OFFSET    = 0x1C
B2_OFFSET    = 0x20
C1_OFFSET    = 0x28
C2_OFFSET    = 0x2C

CTRL_AP_START = 0x1
CTRL_AP_DONE  = 0x2
CTRL_AP_IDLE  = 0x4

# ──────────────────────────────────────────────────────────────────────────────
# Test-vector loading
# ──────────────────────────────────────────────────────────────────────────────

def load_test_vectors(path, max_vectors=3):
    """Parse golden/test_vectors.txt.

    Format (one polynomial per line, three lines per vector):
        # vector N
        <256 space-separated a coefficients>
        <256 space-separated b coefficients>
        <256 space-separated c=expected coefficients>
    """
    vectors = []
    script_dir = os.path.dirname(os.path.abspath(__file__))
    full_path  = os.path.join(script_dir, "..", path)
    full_path  = os.path.normpath(full_path)

    with open(full_path, "r", encoding="utf-8", errors="replace") as fh:
        lines = [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]

    i = 0
    while i + 2 < len(lines) and len(vectors) < max_vectors:
        a_vals    = list(map(int, lines[i].split()))
        b_vals    = list(map(int, lines[i+1].split()))
        exp_vals  = list(map(int, lines[i+2].split()))
        if len(a_vals) == N and len(b_vals) == N and len(exp_vals) == N:
            vectors.append((a_vals, b_vals, exp_vals))
        i += 3

    return vectors


# ──────────────────────────────────────────────────────────────────────────────
# AXI-Lite master driver
# ──────────────────────────────────────────────────────────────────────────────

class AxiLiteMaster:
    """Minimal AXI-Lite master.  Drives s_axi_CTRL_* on ntt_top."""

    def __init__(self, dut):
        self.dut = dut
        # Idle defaults
        dut.s_axi_CTRL_AWVALID.value = 0
        dut.s_axi_CTRL_AWADDR.value  = 0
        dut.s_axi_CTRL_WVALID.value  = 0
        dut.s_axi_CTRL_WDATA.value   = 0
        dut.s_axi_CTRL_WSTRB.value   = 0xF
        dut.s_axi_CTRL_BREADY.value  = 1   # always accept write responses
        dut.s_axi_CTRL_ARVALID.value = 0
        dut.s_axi_CTRL_ARADDR.value  = 0
        dut.s_axi_CTRL_RREADY.value  = 1   # always accept read data

    async def write(self, addr, data):
        """Perform one AXI-Lite write transaction."""
        dut = self.dut
        await RisingEdge(dut.ap_clk)

        # Present address and data simultaneously (most AXI-Lite slaves accept this)
        dut.s_axi_CTRL_AWVALID.value = 1
        dut.s_axi_CTRL_AWADDR.value  = addr
        dut.s_axi_CTRL_WVALID.value  = 1
        dut.s_axi_CTRL_WDATA.value   = data & 0xFFFFFFFF
        dut.s_axi_CTRL_WSTRB.value   = 0xF

        # Wait for AWREADY and WREADY
        aw_done = False
        w_done  = False
        for _ in range(100):
            await RisingEdge(dut.ap_clk)
            if int(dut.s_axi_CTRL_AWREADY.value) and not aw_done:
                dut.s_axi_CTRL_AWVALID.value = 0
                aw_done = True
            if int(dut.s_axi_CTRL_WREADY.value) and not w_done:
                dut.s_axi_CTRL_WVALID.value = 0
                w_done = True
            if aw_done and w_done:
                break

        if not (aw_done and w_done):
            dut._log.error(f"AXI-Lite write timeout at addr=0x{addr:02x}")

        # Wait for BVALID (write response); BREADY already asserted
        for _ in range(100):
            await RisingEdge(dut.ap_clk)
            if int(dut.s_axi_CTRL_BVALID.value):
                break

    async def read(self, addr):
        """Perform one AXI-Lite read transaction.  Returns 32-bit data."""
        dut = self.dut
        await RisingEdge(dut.ap_clk)

        dut.s_axi_CTRL_ARVALID.value = 1
        dut.s_axi_CTRL_ARADDR.value  = addr

        for _ in range(100):
            await RisingEdge(dut.ap_clk)
            if int(dut.s_axi_CTRL_ARREADY.value):
                dut.s_axi_CTRL_ARVALID.value = 0
                break

        # Wait for RVALID; RREADY already asserted
        for _ in range(100):
            await RisingEdge(dut.ap_clk)
            if int(dut.s_axi_CTRL_RVALID.value):
                return int(dut.s_axi_CTRL_RDATA.value)

        dut._log.error(f"AXI-Lite read timeout at addr=0x{addr:02x}")
        return 0


# ──────────────────────────────────────────────────────────────────────────────
# AXI4 slave memory model
# ──────────────────────────────────────────────────────────────────────────────

class Axi4SlaveMemory:
    """Dictionary-backed AXI4 slave.

    Responds to read/write bursts on m_axi_MAXI_*.

    Data layout: byte-addressed dictionary.  Keys are byte addresses.
    Each 32-bit AXI beat holds two 12-bit coefficients packed as:
      bits [15: 0] = coef[2*i]     (lower half-word)
      bits [31:16] = coef[2*i+1]   (upper half-word)
    """

    def __init__(self, dut):
        self.dut  = dut
        self.mem  = {}   # byte_addr (int) -> byte_value (int 0..255)
        self._running = True

        # Drive all slave-side input signals to idle
        dut.m_axi_MAXI_AWREADY.value  = 0
        dut.m_axi_MAXI_WREADY.value   = 0
        dut.m_axi_MAXI_BVALID.value   = 0
        dut.m_axi_MAXI_BRESP.value    = 0
        dut.m_axi_MAXI_BID.value      = 0
        dut.m_axi_MAXI_BUSER.value    = 0
        dut.m_axi_MAXI_ARREADY.value  = 0
        dut.m_axi_MAXI_RVALID.value   = 0
        dut.m_axi_MAXI_RDATA.value    = 0
        dut.m_axi_MAXI_RLAST.value    = 0
        dut.m_axi_MAXI_RRESP.value    = 0
        dut.m_axi_MAXI_RID.value      = 0
        dut.m_axi_MAXI_RUSER.value    = 0

    # ------------------------------------------------------------------
    # Coefficient packing helpers
    # ------------------------------------------------------------------

    def write_array(self, base_addr, coeffs):
        """Store N 12-bit coefficients into simulated memory at base_addr.

        Packing: two coefficients per 32-bit word (little-endian half-words).
          word[i] bits [15:0]  = coeffs[2*i]
          word[i] bits [31:16] = coeffs[2*i+1]
        Byte layout (little-endian):
          byte base+4i+0 = coeffs[2i] & 0xFF
          byte base+4i+1 = (coeffs[2i] >> 8) & 0xFF
          byte base+4i+2 = coeffs[2i+1] & 0xFF
          byte base+4i+3 = (coeffs[2i+1] >> 8) & 0xFF
        """
        for i in range(len(coeffs) // 2):
            c0 = coeffs[2*i]   & 0xFFFF
            c1 = coeffs[2*i+1] & 0xFFFF
            word = (c1 << 16) | c0
            addr = base_addr + i * 4
            self.mem[addr+0] = (word >>  0) & 0xFF
            self.mem[addr+1] = (word >>  8) & 0xFF
            self.mem[addr+2] = (word >> 16) & 0xFF
            self.mem[addr+3] = (word >> 24) & 0xFF

    def read_array(self, base_addr, n=N):
        """Read N 12-bit coefficients from simulated memory."""
        coeffs = []
        for i in range(n // 2):
            addr = base_addr + i * 4
            b0 = self.mem.get(addr+0, 0)
            b1 = self.mem.get(addr+1, 0)
            b2 = self.mem.get(addr+2, 0)
            b3 = self.mem.get(addr+3, 0)
            word = (b3 << 24) | (b2 << 16) | (b1 << 8) | b0
            coeffs.append(word & 0xFFFF)
            coeffs.append((word >> 16) & 0xFFFF)
        return coeffs

    def _read_word(self, byte_addr):
        b0 = self.mem.get(byte_addr+0, 0)
        b1 = self.mem.get(byte_addr+1, 0)
        b2 = self.mem.get(byte_addr+2, 0)
        b3 = self.mem.get(byte_addr+3, 0)
        return (b3 << 24) | (b2 << 16) | (b1 << 8) | b0

    def _write_word(self, byte_addr, data, strb=0xF):
        for lane in range(4):
            if strb & (1 << lane):
                self.mem[byte_addr + lane] = (data >> (8 * lane)) & 0xFF

    # ------------------------------------------------------------------
    # AXI4 slave coroutines
    # ------------------------------------------------------------------

    async def handle_writes(self):
        """Accept AW channel bursts, then accept W-channel beats, send B response."""
        dut = self.dut
        while self._running:
            # Wait for AWVALID
            await RisingEdge(dut.ap_clk)
            if not int(dut.m_axi_MAXI_AWVALID.value):
                continue

            # Latch address and length
            addr  = int(dut.m_axi_MAXI_AWADDR.value)
            awlen = int(dut.m_axi_MAXI_AWLEN.value)   # AXI4: beats = awlen+1
            awid  = int(dut.m_axi_MAXI_AWID.value)

            # Accept the address
            dut.m_axi_MAXI_AWREADY.value = 1
            await RisingEdge(dut.ap_clk)
            dut.m_axi_MAXI_AWREADY.value = 0

            # Accept data beats
            dut.m_axi_MAXI_WREADY.value = 1
            beats_remaining = awlen + 1
            byte_addr = addr
            while beats_remaining > 0:
                await RisingEdge(dut.ap_clk)
                if int(dut.m_axi_MAXI_WVALID.value):
                    data = int(dut.m_axi_MAXI_WDATA.value)
                    strb = int(dut.m_axi_MAXI_WSTRB.value)
                    self._write_word(byte_addr, data, strb)
                    byte_addr += 4
                    beats_remaining -= 1

            dut.m_axi_MAXI_WREADY.value = 0

            # Send write response
            dut.m_axi_MAXI_BVALID.value = 1
            dut.m_axi_MAXI_BRESP.value  = 0   # OKAY
            dut.m_axi_MAXI_BID.value    = awid
            for _ in range(200):
                await RisingEdge(dut.ap_clk)
                if int(dut.m_axi_MAXI_BREADY.value):
                    break
            dut.m_axi_MAXI_BVALID.value = 0

    async def handle_reads(self):
        """Accept AR channel requests and return R-channel data beats."""
        dut = self.dut
        while self._running:
            await RisingEdge(dut.ap_clk)
            if not int(dut.m_axi_MAXI_ARVALID.value):
                continue

            addr  = int(dut.m_axi_MAXI_ARADDR.value)
            arlen = int(dut.m_axi_MAXI_ARLEN.value)
            arid  = int(dut.m_axi_MAXI_ARID.value)

            # Accept the address
            dut.m_axi_MAXI_ARREADY.value = 1
            await RisingEdge(dut.ap_clk)
            dut.m_axi_MAXI_ARREADY.value = 0

            # Send data beats
            beats = arlen + 1
            byte_addr = addr
            for beat_idx in range(beats):
                data = self._read_word(byte_addr)
                is_last = (beat_idx == beats - 1)

                dut.m_axi_MAXI_RVALID.value = 1
                dut.m_axi_MAXI_RDATA.value  = data
                dut.m_axi_MAXI_RLAST.value  = 1 if is_last else 0
                dut.m_axi_MAXI_RRESP.value  = 0   # OKAY
                dut.m_axi_MAXI_RID.value    = arid

                # Hold until RREADY accepted
                for _ in range(200):
                    await RisingEdge(dut.ap_clk)
                    if int(dut.m_axi_MAXI_RREADY.value):
                        break
                byte_addr += 4

            dut.m_axi_MAXI_RVALID.value = 0
            dut.m_axi_MAXI_RLAST.value  = 0

    def stop(self):
        self._running = False


# ──────────────────────────────────────────────────────────────────────────────
# Reset helper
# ──────────────────────────────────────────────────────────────────────────────

async def reset_dut(dut, cycles=20):
    dut.ap_rst_n.value = 0
    await ClockCycles(dut.ap_clk, cycles)
    dut.ap_rst_n.value = 1
    await ClockCycles(dut.ap_clk, 5)


# ──────────────────────────────────────────────────────────────────────────────
# Main test
# ──────────────────────────────────────────────────────────────────────────────

@cocotb.test()
async def test_ntt_top_poly_mul(dut):
    """Load test vectors, run ntt_top for each, compare c to expected."""

    # ── Clock ────────────────────────────────────────────────────────────────
    clock = Clock(dut.ap_clk, CLK_NS, units="ns")
    cocotb.start_soon(clock.start())

    # ── Instantiate drivers ───────────────────────────────────────────────────
    axilite = AxiLiteMaster(dut)
    memory  = Axi4SlaveMemory(dut)

    # Start the AXI4 slave coroutines in the background
    cocotb.start_soon(memory.handle_writes())
    cocotb.start_soon(memory.handle_reads())

    # ── Reset ─────────────────────────────────────────────────────────────────
    await reset_dut(dut, cycles=20)

    # ── Load test vectors ─────────────────────────────────────────────────────
    vectors = load_test_vectors("golden/test_vectors.txt", max_vectors=3)
    if not vectors:
        dut._log.error("No test vectors loaded — check golden/test_vectors.txt path")
        assert False, "No test vectors loaded"

    dut._log.info(f"Loaded {len(vectors)} test vector(s)")

    # ── Test loop ─────────────────────────────────────────────────────────────
    total_pass = 0
    total_fail = 0

    for vec_idx, (a_coeffs, b_coeffs, expected) in enumerate(vectors):
        dut._log.info(f"=== Vector {vec_idx} ===")

        # -- Load arrays into simulated memory --------------------------------
        memory.write_array(BASE_A, a_coeffs)
        memory.write_array(BASE_B, b_coeffs)
        # Zero c so any stale data is cleared
        memory.write_array(BASE_C, [0] * N)

        # -- Write pointer registers ------------------------------------------
        await axilite.write(A1_OFFSET, BASE_A)
        await axilite.write(A2_OFFSET, 0)
        await axilite.write(B1_OFFSET, BASE_B)
        await axilite.write(B2_OFFSET, 0)
        await axilite.write(C1_OFFSET, BASE_C)
        await axilite.write(C2_OFFSET, 0)

        # -- Poll ap_idle before starting (must be 1 after reset) -------------
        for _ in range(200):
            ctrl_val = await axilite.read(CTRL_OFFSET)
            if ctrl_val & CTRL_AP_IDLE:
                break
            await ClockCycles(dut.ap_clk, 5)
        else:
            dut._log.error(f"Vector {vec_idx}: DUT not idle before ap_start")

        # -- Assert ap_start --------------------------------------------------
        await axilite.write(CTRL_OFFSET, CTRL_AP_START)
        dut._log.info(f"Vector {vec_idx}: ap_start asserted")

        # -- Poll ap_done (bit1 of CTRL register) -----------------------------
        # HLS synthesis report shows latency ~12621 cycles; allow 3x headroom
        timeout_cycles = 40000
        done = False
        for _ in range(timeout_cycles // 10):
            await ClockCycles(dut.ap_clk, 10)
            ctrl_val = await axilite.read(CTRL_OFFSET)
            if ctrl_val & CTRL_AP_DONE:
                done = True
                break

        if not done:
            dut._log.error(f"Vector {vec_idx}: TIMEOUT — ap_done never asserted "
                           f"after {timeout_cycles} cycles")
            total_fail += N
            continue

        dut._log.info(f"Vector {vec_idx}: ap_done asserted")

        # -- Read result array c from simulated memory ------------------------
        c_coeffs = memory.read_array(BASE_C, N)

        # -- Compare to golden expected ---------------------------------------
        vec_pass = 0
        vec_fail = 0
        mismatch_log = []

        for i, (got, exp) in enumerate(zip(c_coeffs, expected)):
            # Reduce both modulo Q for comparison robustness
            got_r = got % Q
            exp_r = exp % Q
            if got_r == exp_r:
                vec_pass += 1
            else:
                vec_fail += 1
                if len(mismatch_log) < 8:   # cap log spam
                    mismatch_log.append(f"  c[{i}]: got={got_r}, expected={exp_r}")

        total_pass += vec_pass
        total_fail += vec_fail

        if vec_fail == 0:
            dut._log.info(f"[PASS] Vector {vec_idx}: all {N} coefficients correct")
        else:
            dut._log.error(
                f"[FAIL] Vector {vec_idx}: {vec_fail}/{N} coefficients wrong"
            )
            for msg in mismatch_log:
                dut._log.error(msg)

        # Allow the DUT to return to idle before the next vector
        await ClockCycles(dut.ap_clk, 20)

    # ── Final summary ─────────────────────────────────────────────────────────
    total = total_pass + total_fail
    dut._log.info("=" * 60)
    dut._log.info(f"SUMMARY: {total_pass}/{total} coefficients correct across "
                  f"{len(vectors)} vector(s)")
    if total_fail == 0:
        dut._log.info("ALL TESTS PASSED")
    else:
        dut._log.error(f"FAILURES: {total_fail} coefficients mismatched")

    memory.stop()
    assert total_fail == 0, f"{total_fail} coefficient mismatches across {len(vectors)} vectors"
