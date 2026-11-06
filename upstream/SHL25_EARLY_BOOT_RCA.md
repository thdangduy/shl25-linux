# SHL25 upstream Linux 6.16 — early boot RCA, 2026-11-06

## Known-good experiment versus upstream kernel

- **Sharp 3.4 control + same static ARMHF PID1 v3**: PASS. It created six marker lines under `/cache/shl25-616-diag.log`, each `SHL25_DIAG_PID1_OK kernel=3.4.0 arch=armv7l cache=verified`.
- **Original upstream Linux v6.16 + Sharp DTS v3 + same PID1 v3**: BOOT image flash and SHA-256 verification PASS, but after test, the marker `/cache/shl25-616-diag.log` was **absent**. Result is **NO_PID1_PROOF**, not yet a confirmed kernel panic. TWRP Recovery is intact and eMMC cache is functional inside recovery.
- Boot image: `SHL25-UPSTREAM616-DIAG-BOOT-v3.img`, 17,825,792 bytes; SHA256 `5c85c87b3cfdf37b6d20d64e5700b7880d39816d5e8dd0147cb74d7d1500efa3`.
- BOOT partition `mmcblk0p13` matches image SHA256; Recovery `mmcblk0p14` SHA256 `a8ef5821a0eeef0bbb1f3242a5fb382719e532409da8a0756ed62eb2149a0a52` unchanged.
- TWRP 3.4 has no `/proc/last_kmsg` or `/sys/fs/pstore`; absence of logs gives no stage-specific evidence.

## Found: legacy Sharp /memory node name differs from upstream

### Sharp original BOOT

Read-only unpacking of original Sharp BOOT `SHL25-01.01.03-stock-boot-exact.img` QCDT v2 DTB yields:

- Root `/memory` with `device_type = "memory"`; `reg = <>` (empty). Sharp Android bootloader or an early firmware stage must supply actual DDR banks, since Sharp 3.4 boot succeeds.
- Children `/memory/secure_region`, `/memory/adsp_region`, `/memory/qsecom_region`, `/memory/display_mem@0` use old Qualcomm contiguous memory metadata (unlocated sizes for several regions). They CANNOT be translated blindly into modern reserved-memory physical addresses.
- OEM QCDT board ID 50 and eight MSM IDs: 208, 209, 211, 212, 214, 215, 217, 218.
- After boot, Recovery `/proc/iomem` reports separated System RAM banks: `00000000-059fffff`, `0d200000-0d8fffff`, `0dc00000-0f9fffff`, `0ff00000-0fffffff`, `11000000-11ffffff`, `13000000-7eefffff`. These are observed OS memory resources, **not** a verified bootloader DDR map or safe complete reserved-memory layout.

### Linux upstream v6.16 DTB (before fix)

- The upstream Qualcomm MSM8974 SoC include had `/memory@0` with empty `reg`, rather than the stock Sharp `/memory`.
- It also provides modern `/reserved-memory` nodes with fixed SoC example addresses. Those reservations have **not** been audited against Sharp stock DDR/security firmware and should not be assumed safe or exact board mapping.
- It is possible that the Sharp bootloader searches for `/memory` by exact path when applying its memory fixup, rather than only device_type; this is a **hypothesis** because bootloader code/loaded FDT are not available for inspection.

## Minimal board-specific correction / test

In `dts/qcom-msm8974-sharp-as99.dts`, delete inherited `/memory@0` and define the exact `/memory` naming and empty `reg = <>` from Sharp shipped QCDT. Do **not** invent DDR address ranges or edit the default reserved-memory nodes until their purpose/firmware constraints are verified.

In `upstream/verify_shl25_dtb.py`, assert compiled FDT has `/memory` with `device_type=memory`, empty reg and **no** `/memory@0`; automatically fail CI on a regression.

This correction is a controlled compatibility experiment, NOT proof that the RAM problem is fixed or kernel is bootable. Do not conflate compiler PASS, missing cache marker and physical LCD support.

### Kernel decompression note

- Working Sharp 3.4 control zImage decompresses to ~19,052,724 bytes while its boot header uses ramdisk address `0x01000000`.
- Nonworking upstream v6.16 zImage decompresses to ~22,732,520 bytes and uses the same ramdisk address.
- Both decompressed sizes nominally extend above the 16-MiB initramfs load address if one assumes a fixed output location at `0x8000`. However, **the Sharp 3.4 control demonstrably boots**, so this simple size comparison alone does NOT prove an actual overlap crash. The ARM decompressor, relocation and bootloader behavior must be understood before changing physical boot addresses.

## Next checkpoints

1. GitHub CI compile and verify FDT exact stock memory node shape.
2. Check stock Sharp bootloader's DT handoff/fixup contract and reserved-memory areas if accessible; no guessed addresses.
3. Build an independent, hash-verified diagnostic BOOT with the revised FDT only; keep the same v3 PID1 as the proven control.
4. If test is approved, flash **BOOT only**, never TWRP, with checksum and recovery preservation. Test kernel marker after returning to recovery.
5. Only after first `kernel=6.16` PID1 PASS, port real Sharp DSI/CLMR/BDIC and show an LCD terminal; then touch and native Linux GUI.
