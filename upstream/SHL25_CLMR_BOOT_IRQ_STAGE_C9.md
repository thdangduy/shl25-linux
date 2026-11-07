# SHL25 AS99 — CLMR ARM firmware boot IRQ/completion Stage C9

2026-11-07. Windows source/CI only, SHL25 handset not accessed.

## New evidence from authoritative selected Sharp OEM

Original `drivers/sharp/shdisp_lcdc/shdisp_clmr.c`, SHA256
`399f2b8f050709f6c8c08c56e22260e13ba46b2edde363555ebb69487933e7f0`:

- `shdisp_clmr_request_irq()` calls
  `devm_request_irq(..., shdisp_clmr_irq, ..., IRQF_TRIGGER_RISING, ...)`.
- AS99 OEM `sharp-shdisp-clmr.dtsi` identifies this CLMR HINT line as
  `interrupts = <75 0>` on `msmgpio`. Therefore the original
  firmware implementation uses **GPIO75, rising edge** even though
  the old DTS leaves trigger selector at 0.
- Hardware IRQ only schedules a workqueue; the workqueue performs
  SPI reads/ACK, not the hard IRQ handler.
- Firmware startup complete: INTR[1] bit0, INTSET1 byte3 bit1;
  the old C8 decoder handles this precisely.
- OEM `shdisp_clmr_boot_start()` resets/arms a completion before
  triggering ARM boot and `shdisp_clmr_wait4fw_boot_comp()` waits
  `2100ms`, using `wait_for_completion_timeout()`.
  `shdisp_clmr_donefw_boot_comp()` only completes if boot is armed.
- Firmware async error: INTSET1 byte3 bit3.

## Implemented C9

New code in `drivers/spi/shl25-as99-clmr-boot-irq.{c,h}`.

`shl25_as99_clmr_boot_irq_init()` constructs a guarded completion
context with injected C8 SPI register read/write callbacks.
It requires explicitly asserted `gpio75_rising_verified`, and
performs **no IRQ request, GPIO access, probe, or hardware I/O**.

`shl25_as99_clmr_boot_irq_callbacks` provides the already defined
C6 `arm_boot_completion` and `wait_boot_completion` contract.
Arm resets completion state BEFORE the C3 ARMHOSTSYS boot command;
wait uses Linux completion with passed timeout (C3 currently 2100ms).

A future real Linux 6.1 **threaded** IRQ handler must call
`shl25_as99_clmr_boot_irq_process()`. It invokes C8's bounded
register INTR/INTSET1/INTSET2 read/ACK decoder through the supplied
sleepable SPI callbacks, saves observed events and completes the
armed boot transaction on BOOT_DONE, FW_ERROR or read/ACK failure.
FW_ERROR or transport error wins over an otherwise positive
BOOT_DONE; timeout returns `-ETIMEDOUT`.
`terminal_latched` prevents repeated completion and premature rearm
while a waiting thread still consumes its previous event.

`upstream/verify_shl25_clmr_boot_irq.py` checks source-pinned OEM
IRQ trigger, arm/wait/error and callback contracts, offline status
oracles, no hard-IRQ SPI and no probe registration. Linux 6.1 cross
compile stages `CONFIG_SPI_SHL25_AS99_CLMR_BOOT_IRQ=y`.

## Critical remaining constraints

No source file registers IRQ GPIO75, and no kernel adapter is yet
wiring C6 SPI reg access into C8/C9 or C7 PM8941 GPIO19 core switch.
That is an intentional fail-closed dependency: real Linux 6.1
TLMM/pinctrl and SPMI PM8941 regulator/GPIO bindings must be reviewed
and the power/reset/clock/IRQ sequencing validated.

C9 passing Python tests or compiling in CI does **not** indicate
SHL25 hardware boot or Linux 6.1 LCD PASS. The vendor CLMR firmware
binary is not embedded or pushed. The phone and TWRP were not used.
