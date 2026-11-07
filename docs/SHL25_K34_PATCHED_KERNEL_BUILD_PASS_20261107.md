# SHL25 — patched OEM Linux 3.4 full-build evidence (2026-11-07)

**Build PASS, device boot NOT proven.**

- Branch: `feat/shl25-k34-hwprobe-20261107`
- Source commit: `6d13b6d`
- CI: https://github.com/thdangduy/shl25-linux/actions/runs/42365499990
- Official Sharp SHL25 GPL `bld010105/kernel.tar.gz` (01.01.05)
  SHA256 `231315e67112ffa3b5311059ba8ad4f6b4f2213edea40a7fff001f5a3bdf27bb`
- Host/cross compiler: Linaro GCC 4.9.4 for arm-linux-gnueabihf, archive
  SHA256 `22914118fd963f953824b58107015c6953b5bbdccbdcf25ad9fd9a2f9f11ac07`
- Original Sharp kernel `deckard_as99_defconfig` used; verified SHDISP,
  SH_SERIALS, and TM2979 touch options present.
- Patched `u_serial.c` SHA256
  `0824f4470986ec843ded3da2f117041bf563fbb3a93550bf9b0a57343c1ada0c`
- Changes to extracted GPL tree only: Python2 GCC wrapper compatibility,
  legacy timeconst Perl compatibility, two genuine cpufreq interactive
  undefined sequence-point fixes, and Sharp gserial conditional ttyGS reuse.

## Verified artifact

GitHub artifact `shl25-oem34-gserial-patched-zimage`, ID `13571289523`:

| Artifact | Bytes | SHA256 |
|---|---:|---|
| ZIP | 6,647,745 | `63979207ffd6932665f7d7febfbf03b084a86ce568a6817032ac194f51cc56d7` |
| zImage | 6,669,000 | `92fb1a6172ae5a1e21024e2a5a42dc2461e85918cfc98a267fefbc29d5abd631` |
| kernel.config | 106,131 | `32459c74c0ae627b1fd40df247b537bfe9edb2e9d2122d6de189c52ed46281ad` |

SHA verified on authorized Windows S9X0R0 under:
`Sharp-Checkpoint-20261107/K34-Patched-ZImage-CI-42365499990/`.

## New offline native test BOOT

The new `scripts/pack_shl25_k34_patched_boot.py` packs a hash-pinned
patched zImage, CI-built static ARMHF native PID1 ramdisk, and the original
Sharp QCDT into the original 17,825,792-byte Android BOOT container.
The Android BOOT container is required by legacy bootloader; Linux userspace
itself contains **no Android framework**.

Locally produced file on S9X0R0:
`Sharp-Checkpoint-20261107/SHL25-K34-PATCHED-GSERIAL-NATIVE-v2.img`.
SHA256:
`954ee3dde39e0c88c687bef3a3ad0f804be9905b5031b53bcd195ffb864432e5`.

- Exact original OEM Sharp QCDT SHA256 preserved:
  `a71dcb36c829378ec43dc334234a0a892ef224bade3ff2d7100857c0687150bc`
- Native CPIO.gz SHA256 `c5822a5c8d217c6fe3f43a06ead5db7de6f920549f5a50b1e7379d473ae77523`
- Native PID1 SHA256 `ca9fecb915fcbaafeefc7908e225b726d93c94d5739d7ae4556eeefbdb0c76e7`
- ARM zImage magic, page/addresses, section roundtrip and size checks PASS.
- **No flash, no reboot, no boot test**. USB ACM host bidirectional
  roundtrip remains unproven on patched kernel. Existing BOOT p13/TWRP p14
  partition hashes unchanged.

## Next stage

A controlled first boot must have a known recovery return path; prioritize
an explicit boot-time diagnostic/timeout over a forever-headless PID1.
Reconfirm existing verified p13 backup and TWRP p14 before any test.
The freshly built kernel came from Sharp 01.01.05 sources, but the existing
BOOT control was 01.01.03; build PASS does not prove their boot-level
compatibility. The Linux 6.1 branch remains separate and compiled, not booted.

Local full handoff:
`Sharp-Checkpoint-20261107/SHL25_NATIVE_34_TO_61_MASTER_HANDOFF_20261107.md`
