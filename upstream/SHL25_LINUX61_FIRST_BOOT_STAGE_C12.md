# SHL25 Linux 6.1 — C12 first boot test image

Date: 2026-11-08 (Asia/Singapore). Exact Windows target S9X0R0.
Owner reports battery charged and phone currently in TWRP recovery.

## Source and binary provenance

- Source branch `feat/shl25-linux61-port-20261107`.
- C11 CPIO/console fix commit `c7b820d`, independent native
  initramfs CI `42395559038` **SUCCESS**; artifact ZIP SHA256
  `140a0f183e484df6a395a500f1534232d98977270e0fc22c4f69f479317b01ed`.
- ARMHF native initramfs `8f61462f337490858b3c5b057e55c87e33874d4f8ab92b6bfeecc8728b59eaf7`;
  PID1 source SHA `bc36fdc78295626cab4e3a1f6d2200d4b24494eff5a21310b7f05dc63cc345ac`.
  C11 independent newc parser confirms /dev/console 5:1,
  /dev/null 1:3, /dev/kmsg 1:11; ARMv7 BusyBox and PID1.
- Kernel and AS99 DTB from Linux 6.1 CI `42394061052` SUCCESS,
  commit `13cd355`, artifact ZIP
  `bf0c1b12b8aedddcaa0c1e4287e1ac2f4ed936169e4e02d1107c31c94d38fede`.
  Kernel zImage SHA256
  `78c6402fe5824c297aa55a420af67d211a407f85be07132aed483af3c564f929`.
  AS99 FDT SHA256
  `266b4a0dcd6eb2f7c7b989c7a54cb604f13fd16f28e1879697934ac045c04eb3`.
- Kernel C11 build run `42395559034` pending at C12 staging.
  The C11 code modified *only* native initramfs scripts and
  documents, so the kernel from prior successful run has the
  same staged driver logic; do not claim same commit provenance.

## Real hardware read-only preflight

- On-device BOOT p13 K34 native v5 SHA256:
  `b0d52a1fce11070791607b14e476ca8a67209483fb7cafcfb7209b5be22b849f`.
- Local identical `Sharp-Checkpoint-20261107/SHL25-K34-NATIVE-BUSYBOX-SHELL-QEMU-v5.img`.
- TWRP Recovery p14 SHA256:
  `a8ef5821a0eeef0bbb1f3242a5fb382719e532409da8a0756ed62eb2149a0a52`.
- Recovery kernel 3.4, ADB serial bound to AS99.

## Offline C12 packer

New `scripts/pack_shl25_linux61_diag_boot.py`. All input
binaries require independent SHA-256 pins, and base golden
K34 BOOT is an exact hash requirement.
Preserves K34 legacy BOOT v0:
2048-byte page, kernel addr 0x8000, ramdisk addr 0x01000000,
second addr 0x00f00000, tags addr 0x00000100,
native `init=/init` kernel command line.

Exactly preserves Sharp QCDT v2 header/8-selector table and
board ID 50 for MSM 208,209,211,212,214,215,217,218.
The common 212,992-byte Sharp FDT slot begins at QCDT+2048.
It is overwritten with the new Linux 6.1 AS99 FDT and
zero-padded to keep legacy selector offsets/sizes intact.
The OEM K34 FDT must **NOT** be paired with new kernel.

Strict checks include ARM zImage magic, full FDT header/model,
native BusyBox/newc nodes, BOOT capacity 17,825,792,
all sections payload roundtrip, no old FDT duplicates,
and trailing zero padding. No device access is possible
from this offline-only packer.

Packaged offline result in local checkpoint:
`Sharp-Checkpoint-20261107/Linux61-FirstBoot-C12/SHL25-LINUX61-DIAG-C12-BOOT.img`
and matching JSON manifest.

- image SHA256
  `dc03e4f3cf2e272531ed8d7e6f846a8d664c955db412b4ddc3fd6f499117271e`.
- bytes 17,825,792.
- New QCDT section SHA256
  `c826e5d6686df867f48c0a1bd4b390633ca17013290428503c6f184c8e0ff223`.
- FDT totalsize 38,592.
- Stage result `C12_OFFLINE_QCDT_BOOT_IMAGE_PACK_AND_VERIFY_PASS_NO_PHONE_IO`.

## Hardware test acceptance

This BOOT is a **diagnostic experiment**, NOT proven safe
or bootable on hardware. Display/touch/CLMR nodes stay disabled.
First acceptance: Linux 6.1 reaches ARMHF /init, USB gadget exposes
CDC ACM and COM device, PID1 logs `SHL25_LINUX61_NATIVE_PID1_STARTED`.
Absence of USB may be PHY/UDC issue, not necessarily CPU boot fail.

Before a future real flash: stage an exact K34 v5 rollback
on Windows and in recovery TMPFS; record on-device recovery
SHA before/after. Never write p14. Keep test bounded, with
confirmed owner ability to enter TWRP using hardware keys
if a headless kernel does not expose ADB/CDC.

**Do not mark Linux 6.1 hardware PASS from packing or CI.**
