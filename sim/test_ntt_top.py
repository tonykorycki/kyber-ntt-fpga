"""
sim/test_ntt_top.py — cocotb testbench for ntt_top HLS IP (ap_ctrl_hs + ap_memory)

DUT: ntt_top (Vitis HLS, ap_ctrl_hs interface)
Function: NTT(a), NTT(b), pointwise multiply, INTT(c) — negacyclic poly mul mod Q=3329
Parameters: N=256, Q=3329, coef_width=12 bits

Interface:
  ap_clk                  — clock
  ap_rst                  — synchronous reset, active-high
                            (confirm from generated Verilog; some HLS versions use ap_rst_n)
  ap_start                — pulse high for one cycle to start
  ap_done                 — asserts for one cycle when result is ready
  ap_idle                 — high when DUT is idle and ready to accept ap_start

  For each array x in {a, b, c}:
    x_address0[7:0]       — BRAM address (0..255)
    x_ce0                 — chip enable (active-high)
    x_we0                 — write enable (active-high)
    x_d0[11:0]            — write data
    x_q0[11:0]            — read data (valid one cycle after ce0+address presented)

Memory model:
  Each BramModel instance is a synchronous 256×12 RAM. Pre-load a and b before
  asserting ap_start; read c after ap_done.
"""

import os
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

N      = 256
Q      = 3329
CLK_NS = 10   # 100 MHz


def load_test_vectors(path, max_vectors=3):
    """Parse golden/test_vectors.txt — three lines per vector: a, b, expected_c."""
    vectors   = []
    script_dir = os.path.dirname(os.path.abspath(__file__))
    full_path  = os.path.normpath(os.path.join(script_dir, "..", path))

    with open(full_path, "r", encoding="utf-8", errors="replace") as fh:
        lines = [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]

    i = 0
    while i + 2 < len(lines) and len(vectors) < max_vectors:
        a_v   = list(map(int, lines[i].split()))
        b_v   = list(map(int, lines[i+1].split()))
        exp_v = list(map(int, lines[i+2].split()))
        if len(a_v) == N and len(b_v) == N and len(exp_v) == N:
            vectors.append((a_v, b_v, exp_v))
        i += 3

    return vectors


class BramModel:
    """Synchronous 256×12 BRAM model for one ap_memory port.

    Responds one cycle after address + ce are presented (matches HLS ram_1p assumption).
    Pre-load contents via preload() before simulation starts.
    """

    def __init__(self, dut, name, n=N):
        self.dut  = dut
        self.mem  = [0] * n
        self.n    = n
        self.ce   = getattr(dut, f"{name}_ce0")
        self.we   = getattr(dut, f"{name}_we0")
        self.addr = getattr(dut, f"{name}_address0")
        self.din  = getattr(dut, f"{name}_d0")
        self.dout = getattr(dut, f"{name}_q0")
        self.dout.value = 0

    def preload(self, coeffs):
        for i, v in enumerate(coeffs[:self.n]):
            self.mem[i] = int(v) & 0xFFF

    def read_all(self):
        return list(self.mem)

    @staticmethod
    def _to_int(sig, default=0):
        try:
            return int(sig.value)
        except ValueError:
            return default  # X/Z during reset

    async def run(self):
        while True:
            await RisingEdge(self.dut.ap_clk)
            if self._to_int(self.ce):
                addr = self._to_int(self.addr) % self.n
                if self._to_int(self.we):
                    self.mem[addr] = self._to_int(self.din) & 0xFFF
                self.dout.value = self.mem[addr]


async def reset_dut(dut, cycles=20):
    dut.ap_start.value = 0
    dut.ap_rst.value   = 1  
    await ClockCycles(dut.ap_clk, cycles)
    dut.ap_rst.value   = 0
    await ClockCycles(dut.ap_clk, 5)


@cocotb.test()
async def test_ntt_top_poly_mul(dut):
    """Load test vectors, run ntt_top for each, compare c to expected."""

    cocotb.start_soon(Clock(dut.ap_clk, CLK_NS, unit="ns").start())

    bram_a = BramModel(dut, "a")
    bram_b = BramModel(dut, "b")
    bram_c = BramModel(dut, "c")

    cocotb.start_soon(bram_a.run())
    cocotb.start_soon(bram_b.run())
    cocotb.start_soon(bram_c.run())

    await reset_dut(dut)

    max_v   = int(os.environ.get("NTT_MAX_VECTORS", 64))
    vectors = load_test_vectors("golden/test_vectors.txt", max_vectors=max_v)
    if not vectors:
        assert False, "No test vectors loaded — check golden/test_vectors.txt"

    dut._log.info(f"Loaded {len(vectors)} test vector(s)")

    total_pass = 0
    total_fail = 0

    for vec_idx, (a_coeffs, b_coeffs, expected) in enumerate(vectors):
        dut._log.info(f"=== Vector {vec_idx} ===")

        bram_a.preload(a_coeffs)
        bram_b.preload(b_coeffs)
        bram_c.preload([0] * N)

        # Wait for ap_idle
        for _ in range(200):
            if int(dut.ap_idle.value):
                break
            await ClockCycles(dut.ap_clk, 5)
        else:
            dut._log.error(f"Vector {vec_idx}: DUT not idle before ap_start")

        # Pulse ap_start for one cycle
        dut.ap_start.value = 1
        await RisingEdge(dut.ap_clk)
        dut.ap_start.value = 0
        dut._log.info(f"Vector {vec_idx}: ap_start pulsed")

        # Poll ap_done — HLS synthesis: ~12621 cycles; allow 3× headroom
        done = False
        for _ in range(40000):
            await RisingEdge(dut.ap_clk)
            if int(dut.ap_done.value):
                done = True
                break

        if not done:
            dut._log.error(f"Vector {vec_idx}: TIMEOUT — ap_done never asserted")
            total_fail += N
            continue

        dut._log.info(f"Vector {vec_idx}: ap_done asserted")

        # Wait one extra cycle: the final write to c[255] lands on the same edge
        # as ap_done; the BRAM model coroutine needs one more cycle to process it.
        await ClockCycles(dut.ap_clk, 1)

        c_result = bram_c.read_all()

        vec_pass = 0
        vec_fail = 0
        mismatch_log = []

        for i, (got, exp) in enumerate(zip(c_result, expected)):
            got_r = got % Q
            exp_r = exp % Q
            if got_r == exp_r:
                vec_pass += 1
            else:
                vec_fail += 1
                if len(mismatch_log) < 8:
                    mismatch_log.append(f"  c[{i}]: got={got_r}  expected={exp_r}")

        total_pass += vec_pass
        total_fail += vec_fail

        if vec_fail == 0:
            dut._log.info(f"[PASS] Vector {vec_idx}: all {N} coefficients correct")
        else:
            dut._log.error(f"[FAIL] Vector {vec_idx}: {vec_fail}/{N} wrong")
            for msg in mismatch_log:
                dut._log.error(msg)

        await ClockCycles(dut.ap_clk, 20)

    total = total_pass + total_fail
    dut._log.info("=" * 60)
    dut._log.info(f"SUMMARY: {total_pass}/{total} correct across {len(vectors)} vector(s)")
    if total_fail == 0:
        dut._log.info("ALL TESTS PASSED")
    else:
        dut._log.error(f"FAILURES: {total_fail} coefficients mismatched")

    assert total_fail == 0, f"{total_fail} mismatches across {len(vectors)} vectors"
