#!/usr/bin/env python3
"""Stage C9: source-verified Sharp AS99 boot completion coordinator.

Checks the dormant Linux 6.1 callback glue and offline failure vectors.
No phone, IRQ registration, kernel execution or hardware stimulation.
"""
import argparse
import hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
C=(ROOT/"drivers/spi/shl25-as99-clmr-boot-irq.c").read_text(encoding="utf-8")
H=(ROOT/"drivers/spi/shl25-as99-clmr-boot-irq.h").read_text(encoding="utf-8")
BRIDGE=(ROOT/"drivers/spi/shl25-as99-clmr-spi-bridge.c").read_text(encoding="utf-8")
REGS=(ROOT/"drivers/spi/shl25-as99-clmr-irq-status.c").read_text(encoding="utf-8")
SPI=(ROOT/"drivers/spi/spi-shl25-as99-clmr.c").read_text(encoding="utf-8")
DT=(ROOT/"dts/shl25-as99-peripherals.dtsi").read_text(encoding="utf-8")
OEM_SHA="399f2b8f050709f6c8c08c56e22260e13ba46b2edde363555ebb69487933e7f0"

p=argparse.ArgumentParser()
p.add_argument("--oem-clmr-c",type=Path)
a=p.parse_args()
if a.oem_clmr_c:
    content=a.oem_clmr_c.read_bytes()
    assert hashlib.sha256(content).hexdigest()==OEM_SHA
    oem=content.decode("utf-8",errors="replace")
    request=oem.split("static int shdisp_clmr_request_irq(void)",2)[-1]
    assert "IRQF_TRIGGER_RISING" in request
    assert "shdisp_clmr_irq" in request and "devm_request_irq(" in request
    assert "shdisp_clmr_boot_start()" in oem
    assert "init_completion(&clmr_ctrl->fw_boot_comp)" in oem
    assert "shdisp_clmr_donefw_boot_comp()" in oem
    assert "wait_for_completion_timeout(&clmr_ctrl->fw_boot_comp, waittime)" in oem
    print("SHL25_AS99_C9_OEM_IRQ_GPIO75_TRIGGER_RISING_HASH_PIN_PASS")

for term in (
    "struct completion boot_done", "spinlock_t lock",
    "const struct shl25_clmr_irq_register_ops *regs",
    "bool armed", "bool initialized",
    "shl25_as99_clmr_boot_irq_process(",
    "shl25_as99_clmr_boot_irq_callbacks",
):
    assert term in H,term

init=C.split("int shl25_as99_clmr_boot_irq_init(",1)[1].split(
    "static int shl25_clmr_arm_boot(",1)[0]
assert init.index("if (!gpio75_rising_verified)") < init.index("init_completion(&state->boot_done)")
assert "state->armed = false;" in init and "state->initialized = true;" in init
assert "if (state->initialized)" in init

arm=C.split("static int shl25_clmr_arm_boot(",1)[1].split(
    "static int shl25_clmr_wait_boot(",1)[0]
assert arm.index("reinit_completion(&state->boot_done)") < arm.index("state->armed = true;")
assert "if (state->armed)" in arm and "return -EBUSY;" in arm
assert "spin_lock_irqsave" in arm and "spin_unlock_irqrestore" in arm

wait=C.split("static int shl25_clmr_wait_boot(",1)[1].split(
    "int shl25_as99_clmr_boot_irq_process(",1)[0]
assert "wait_for_completion_timeout" in wait
assert "msecs_to_jiffies(timeout_ms)" in wait
assert "state->boot_result = -ETIMEDOUT" in wait
assert "state->armed = false;" in wait

process=C.split("int shl25_as99_clmr_boot_irq_process(",1)[1]
assert "shl25_as99_clmr_irq_drain(state->regs, state->reg_ctx, &events)" in process
assert "state->observed_events |= events" in process
assert "SHL25_CLMR_EVENT_BOOT_DONE" in process
assert "SHL25_CLMR_EVENT_FW_ERROR" in process
assert "events & SHL25_CLMR_EVENT_FW_ERROR ? -EIO : 0" in process
assert "state->boot_result = ret ? ret :" in process
assert process.index("spin_unlock_irqrestore(&state->lock, flags)") < process.index(
    "complete(&state->boot_done)")
assert "const struct shl25_clmr_board_irq_ops shl25_as99_clmr_boot_irq_callbacks" in C
assert ".arm_boot_completion = shl25_clmr_arm_boot" in C
assert ".wait_boot_completion = shl25_clmr_wait_boot" in C

# Offline event result oracle mirrors C9 priority of transport failures
# and FW error over an otherwise-positive boot completion.
BOOT=1<<1
ERROR=1<<3
def terminal(armed,events,ret):
    if not armed or not(ret or events&(BOOT|ERROR)):
        return None
    return ret if ret else (-5 if events&ERROR else 0)
assert terminal(True,BOOT,0)==0
assert terminal(True,ERROR,0)==-5
assert terminal(True,BOOT|ERROR,0)==-5
assert terminal(True,BOOT,-110)==-110
assert terminal(False,BOOT,0) is None
assert terminal(True,0,0) is None
assert terminal(True,0,-110)==-110

# This is still source-only. No request_irq, GPIO access, or calls from
# registered SPI probes are permitted.
assert "devm_request_irq(" not in C.split("*/",1)[1]
assert "request_threaded_irq(" not in C.split("*/",1)[1]
assert "module_init(" not in C and "module_spi_driver(" not in C
assert "EXPORT_SYMBOL" not in C
assert "shl25_as99_clmr_boot_irq_init(" not in SPI
assert "shl25_as99_clmr_boot_irq_process(" not in SPI
assert "shl25_as99_clmr_boot_irq_callbacks" not in BRIDGE
assert "shl25_as99_clmr_irq_drain(" in REGS
assert 'status = "disabled";' in DT
print("SHL25_AS99_C9_IRQ_BOOT_COMPLETE_ARM_WAIT_AND_ERROR_PRIORITY_PASS")
print("SHL25_AS99_C9_THREAD_CALLBACK_NO_HARDIRQ_SPI_OR_PROBE_PASS")
