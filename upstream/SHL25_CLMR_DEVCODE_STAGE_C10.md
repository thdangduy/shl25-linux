# SHL25 / AS99 — CLMR silicon identity preflight Stage C10

Date 2026-11-07. Source-only on Windows S9X0R0, no SHL25 hardware I/O.

## OEM source

From selected Sharp GPL bld010105 `shdisp_lcdc/shdisp_clmr.c`
SHA256 `399f2b8f050709f6c8c08c56e22260e13ba46b2edde363555ebb69487933e7f0`
and `shdisp_clmr.h`
SHA256 `1eb86c4756fd1afb5b815eb2739e2a5170f51ac4f9279b3917201edcc1c6249d`.

- `SHDISP_CLMR_REG_DEVCODE = 0x0300`.
- `SHDISP_CLMR_DEVCODE_VALUE = 0x00004002`.
- `shdisp_clmr_lcdc_devcheck()` reads CLMR DEVCODE via
  Sharp SPI C2/C4, converts 4-byte result to host-order value
  and rejects a mismatched 0x4002.

## Linux 6.1 changes

- `shl25-as99-clmr-boot.h`: C3 callback contract includes
  mandatory `validate_device()` before register programming.
- `shl25-as99-clmr-boot.c`: invokes `validate_device()` only
  AFTER computing the actual firmware SHA-256, but BEFORE
  `fw_download[7]` register writes and firmware transfer.
  Any error aborts without register writes.
- `shl25-as99-clmr-spi-bridge.c`: C6 validates by reading
  register 0x0300 through existing C2/C4 BE32 reader and returns
  `-ENODEV` if the result is not 0x00004002.
- `upstream/verify_shl25_clmr_devcode.py`: OEM SHA source proof,
  exact register/value and BE32 vectors, call ordering and
  mandatory gate; CI runs without original OEM files.
- `scripts/build-upstream-linux61.sh`: C10 regression and manifest
  included in clean pinned Linux 6.1 kernel build.

This validates target identity but NOT full PMIC, PLL, reset timing
or the CLMR startup sequence on a handset. The bridge remains
unconnected to any SPI probe and display/CLMR nodes remain disabled.
Known-good K34 BOOT and TWRP remain untouched.

Next: audit OEM reset GPIO85 and PLLONCTL GPIO8 sequence and Linux
6.1 PM8941 supply/GPIO binding; then add a board adapter with
verified real IRQ GPIO75 rising-edge driver and C7/C9 hooks,
only enable for controlled hardware tests after owner permits.
