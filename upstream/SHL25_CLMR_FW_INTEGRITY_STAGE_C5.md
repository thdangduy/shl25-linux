# Sharp SHL25 AS99 — CLMR firmware integrity gate (Stage C5)

Date: 2026-11-07. Source/CI only. Phone remains OFF charging.

## Requirement closed

Earlier CLMR Stage C3 callback executor required a boolean
`firmware_sha_verified` supplied by the future device adapter.
Without computing the hash *inside the executor*, that alone could
accept incorrectly labeled or accidentally modified firmware.

C5 now calculates SHA-256 in the Linux 6.1 bootstrap object with the
kernel `crypto_shash` API before any CLMR register writes or firmware
streaming. A mismatch returns `-EKEYREJECTED`.

- Expected byte length: 59,136 (3696 × 16).
- Sharp OEM extracted `arm_fw` SHA-256:
  `a3da76d0bbc1154a774e097bfd851026cde7a09c3983ea9315181835510145f5`.
- The comparison uses all 32 digest bytes; the C file stores **only**
  the 32-byte expected digest, not the original OEM firmware image.
- The future adapter must also explicitly validate the origin, the
  board power/reset/clock condition and the firmware-ready IRQ before
  invoking the stage C3 callback executor.
- `CONFIG_CRYPTO_SHA256=y` is enforced by Linux 6.1 CI Kconfig.
- No readiness setter or hardware adapter is installed.

## Test results

`upstream/verify_shl25_clmr_firmware_sha.py` checks the embedded
SHA bytes in the C source, presence of the crypto API and error check,
and that the entire verifier call precedes the first register write.
The local Windows test additionally hashed the actual 59,136-byte
extracted OEM binary (PASS) and checked that changing byte 0 changes
its digest (PASS). The CI version runs without the proprietary binary.

This is still **not** Linux 6.1 firmware-boot hardware PASS.
Remaining requirements include a verified `request_firmware()` adapter
for the local image, CLMR SPI bridge boot-phase I/O wiring, PM8941
rail/reset/PLL handling, DMA completion and firmware IRQ, CLMR FWCMD
transport and BDIC power sequencing, Andy panel per-device VCOM/gamma.
Parent display and SPI CLMR DT nodes stay disabled, and TWRP is untouched.
