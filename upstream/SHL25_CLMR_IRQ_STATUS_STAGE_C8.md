# SHL25 AS99 — CLMR firmware IRQ register status/clear Stage C8

Date 2026-11-07. Source/CI only. No phone hardware access.

## Sharp OEM evidence

Selected original kernel `drivers/sharp/shdisp_lcdc/shdisp_clmr.c`
SHA256 `399f2b8f050709f6c8c08c56e22260e13ba46b2edde363555ebb69487933e7f0`.
Original `shdisp_clmr.h` SHA256
`1eb86c4756fd1afb5b815eb2739e2a5170f51ac4f9279b3917201edcc1c6249d`.
Relevant source functions:
- `shdisp_workqueue_handler_clmr()`: reads CLMR INTR,
  branches to firmware status and detection status, clears
  INTSET1/INTSET2 by writing zero, then repeats while status
  remains active.
- `shdisp_workqueue_handler_clmr_intr_ARM_FW_start_comp()`:
  calls `shdisp_clmr_donefw_boot_comp()`.
- `shdisp_clmr_boot_start()`: arms completion and marks
  `fw_boot_excute=1` BEFORE ARMHOSTSYS starts the firmware.
- `shdisp_clmr_wait4fw_boot_comp()`: waits up to 2100ms and
  performs vendor-specific failsafe on timeout.

Correct register protocol:

| CLMR register | Address | Relevant status |
|---|---:|---|
| INTR | 0x0100 | byte 1 bit 0 → FW, bit 1 → DET |
| INTSET1 | 0x0110 | byte 3 bit 1 → ARM firmware startup complete |
| INTSET2 | 0x0114 | byte 3 bit 0 → LCD DET, bit 1 PSALS, bit 2 TE |

The SPI bridge returns register values as **big-endian decoded u32**,
so byte1 `regINTR[1] & 0x01` becomes bit16 (`BIT(16)`),
and `regINTR[1] & 0x02` becomes bit17 (`BIT(17)`).
Firmware startup complete is `INTSET1 & BIT(1)`.
Other INTSET1 low-byte events: bit0 FWCMD done,
bit2 eDRAM pointer reset done, bit3 firmware async error.

## Stage C8 implementation

- `drivers/spi/shl25-as99-clmr-irq-status.{c,h}`: typed event
  decoder and callback-based register read/clear worker.
- Both INTSET registers are acknowledged by writing a zero word
  AFTER reading status and BEFORE decoding/forwarding events.
- OEM drains repeated INTR bits in a loop; new code caps repeats
  at 32 to prevent wedged IRQ from blocking Linux indefinitely.
  Error returns are propagated. This is a bounded defensive
  change, not an OEM assertion about maximum interrupt count.
- `upstream/verify_shl25_clmr_irq_status.py` checks direct
  byte-order to bit mapping and firmware boot-complete vectors,
  register ordering, timeout, no IRQ registration.
- Linux build script stages
  `CONFIG_SPI_SHL25_AS99_CLMR_IRQ_DECODE=y` and checks object
  compilation alongside C6/C7.

### Unfinished and intentionally disabled

Original DTS `sharp-shdisp-clmr.dtsi` uses `interrupts=<75 0>`
on TLMM GPIO75. The real Linux 6.1 IRQ trigger polarity/type
has NOT yet been verified. C8 deliberately does not call
`request_irq()`, `request_threaded_irq()`, `complete()` or
attach any callback to the actual boot sequence. It cannot
claim ARM firmware boot-complete hardware PASS.

Next step: verify the real IRQ trigger and pinctrl from source/
hardware, wire a genuine IRQ handler and completion to C6's
boot IRQ callback contracts; verify PM8941 LVS2/L2 / GPIO19
supply adapters and CLMR reset/PLL before any hardware enable.
DTS, BOOT and TWRP remain unchanged.
