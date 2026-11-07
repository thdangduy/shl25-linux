#!/usr/bin/env python3
"""Offline AS99 CLMR bootstrap plan verification; no handset actions."""
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
PLAN=json.loads((ROOT/"upstream/shl25-as99-clmr-boot.json").read_text(encoding="utf-8"))
C=(ROOT/"drivers/spi/shl25-as99-clmr-boot.c").read_text(encoding="utf-8")
H=(ROOT/"drivers/spi/shl25-as99-clmr-boot.h").read_text(encoding="utf-8")
SPI=(ROOT/"drivers/spi/spi-shl25-as99-clmr.c").read_text(encoding="utf-8")
DTS=(ROOT/"dts/shl25-as99-peripherals.dtsi").read_text(encoding="utf-8")
DISPLAY=(ROOT/"dts/shl25-as99-display.dtsi").read_text(encoding="utf-8")

assert PLAN["board"]=="CONFIG_MACH_DECKARD_AS99=y, CONFIG_SHDISP_PANEL_ANDY=y"
assert PLAN["fw_blocks"]==3696 and PLAN["fw_bytes"]==59136
assert PLAN["hostbase"]==0x7ce0 and PLAN["hostaey_value"]==3695
assert PLAN["irq_timeout_ms"]==2100 and PLAN["dma_poll_max"]==100
g=PLAN["groups"]
assert {k:len(v) for k,v in g.items()}=={
    "fw_download":7,"arm_init_det":6,"arm_init_no_det":6,
    "arm_sram2fw":7,"arm_boot":1}
assert [r["reg"] for r in g["fw_download"]]==[0x0e00,0x0e04,0x0e1c,0x0e18,0x0e08,0x0e10,0x0e0c]
assert [r["reg"] for r in g["arm_sram2fw"]]==[0x1824,0x1838,0x1828,0x182c,0x1830,0x1834,0x1824]
assert g["arm_sram2fw"][-1]["data"]==0x11
assert g["arm_boot"]==[dict(reg=0x1800,name="SHDISP_CLMR_REG_ARMHOSTSYS",
                           op="CALI_STR",data=0x13,delay_us=0)]
assert g["arm_init_det"][0]["data"]==0x30000
assert g["arm_init_no_det"][0]["data"]==0x10000
assert g["arm_init_det"][1:]==g["arm_init_no_det"][1:]
assert "shl25_clmr_ensure_boot_ready" in SPI
assert "shl25_clmr_ensure_runtime_ready" in SPI
assert SPI.count("shl25_clmr_ensure_boot_ready(clmr);")==2
assert "if (!clmr->firmware_running)" in SPI
assert "firmware_running = true" not in SPI
assert "bdic_power_validated = true" not in SPI
assert "clmr_pll_clock_ready = true" not in SPI
for marker in (
    "!ready->pmic_rails_verified", "!ready->clmr_reset_verified",
    "!ready->spi_bus_verified", "!ready->clock_pll_verified",
    "!ready->firmware_sha_verified", "!ready->boot_irq_verified",
    "ready->det_mode == SHL25_CLMR_DET_ENABLED",
    "ready->det_mode == SHL25_CLMR_DET_NOT_SUPPORTED",
    "return -ETIMEDOUT;", "return -EOPNOTSUPP;",
    "if (firmware_bytes != SHL25_CLMR_FW_BYTES)",):
    assert marker in C,marker

# Device-facing functions must NOT be called by existing SPI probe.
probe=SPI.split("static int shl25_clmr_spi_probe(",1)[1].split(
    "static const struct of_device_id",1)[0]
for forbidden in ("shl25_as99_clmr_boot_sequence(", "shl25_clmr_reg_write(",
                  "shl25_clmr_reg_read(", "request_firmware(", "regulator_enable(",
                  "spi_sync_transfer(", "gpio_set_value("):
    assert forbidden not in probe,forbidden
assert "shl25_as99_clmr_boot_sequence(" not in SPI
assert "module_init(" not in C and "module_spi_driver(" not in C
assert "EXPORT_SYMBOL" not in C
assert "status = \"disabled\";" in DTS
assert "status = \"disabled\";" in DISPLAY
assert "as99_spi1: spi@f9923000" in DTS

# Verify the invocation chronology in the C executor and the exact IRQ
# arming order rather than only checking the existence of each token.
boot=C.split("int shl25_as99_clmr_boot_sequence(",1)[1]
timeline=[
    "shl25_boot_fw_download",
    "SHL25_CLMR_REG_HOSTAEY",
    "ops->stream_firmware(ctx, firmware, firmware_bytes)",
    "shl25_clmr_apply_regops(ops, ctx, arm_init, arm_init_count)",
    "shl25_boot_arm_sram2fw",
    "for (attempt = 0; attempt < SHL25_CLMR_DMA_POLL_LIMIT; attempt++)",
    "ops->arm_boot_completion(ctx)",
    "shl25_boot_arm_boot",
    "ops->wait_boot_completion(ctx",
]
pos=[boot.index(x) for x in timeline]
assert pos==sorted(pos),("INCORRECT_BOOT_STAGE_ORDER",pos)
assert boot.index("if (!ready->pmic_rails_verified") < boot.index("shl25_boot_fw_download")
assert boot.index("if (ready->det_mode == SHL25_CLMR_DET_ENABLED") < boot.index("shl25_boot_fw_download")
assert "if (attempt == SHL25_CLMR_DMA_POLL_LIMIT)" in boot
assert "if (!(dma_state & 1U))" in boot
assert "SHL25_CLMR_BOOT_IRQ_TIMEOUT_MS" in boot

# Deterministic offline model of OEM register order (NOT C hardware test).
def simulate(selected, dma_busy_cycles, fail_at=None):
    events=[]
    state=0x10
    def write(rec):
        if fail_at==len(events):raise IOError("mock register failure")
        events.append(("W",rec["reg"],rec["data"]))
    for rec in g["fw_download"]:write(rec)
    events.append(("W",0x0e14,3695))
    events.append(("FW",59136,10))
    for rec in g[selected]:
        if rec["op"]=="CALI_OR":
            events.append(("R",rec["reg"]))
            rec=dict(rec,data=state|rec["data"])
        write(rec)
    for rec in g["arm_sram2fw"]:write(rec)
    for attempt in range(100):
        events.append(("DMA",attempt))
        if attempt>=dma_busy_cycles:break
    else:
        return "ETIMEDOUT",events
    events.append(("ARM_IRQ",2100))
    for rec in g["arm_boot"]:write(rec)
    events.append(("BOOT_COMPLETE",2100))
    return "PASS",events

for mode in ("arm_init_det","arm_init_no_det"):
    result,ev=simulate(mode,3)
    assert result=="PASS"
    assert ev[0]==("W",0x0e00,0x12)
    assert ev[7]==("W",0x0e14,3695)
    assert ev[8]==("FW",59136,10)
    assert ev[-2]==("W",0x1800,0x13)
    assert ev[-3]==("ARM_IRQ",2100)
result,ev=simulate("arm_init_det",100)
assert result=="ETIMEDOUT"
assert not any(e[0]=="BOOT_COMPLETE" for e in ev)
try:
    simulate("arm_init_det",2,fail_at=2)
except IOError:
    pass
else:
    raise AssertionError("failed to abort on transport error")

print("SHL25_AS99_CLMR_BOOT_STAGE_C3_OEM_ORDER_AND_DMA_BOUND_PASS")
print("SHL25_AS99_CLMR_BOOT_STAGE_C3_DET_BRANCHES_AND_IRQ_ORDER_PASS")
print("SHL25_AS99_CLMR_BOOT_STAGE_C3_NO_LIVE_PROBE_OR_UNVERIFIED_IO_PASS")
