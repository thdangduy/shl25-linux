# SHL25 Linux 6.1 — C11 native PID1 console archive gate

Date: 2026-11-08. Real SHL25 is connected via Windows S9X0R0
and ADB TWRP Recovery (kernel 3.4), battery charged per owner.
No experimental BOOT flashed by C11. Recovery preserved.

## Live SHA verification before any writing

Read-only hashes from `adb shell sha256sum`:
- BOOT mmcblk0p13 = `b0d52a1fce11070791607b14e476ca8a67209483fb7cafcfb7209b5be22b849f` (golden K34 native BusyBox v5).
- Recovery mmcblk0p14 = `a8ef5821a0eeef0bbb1f3242a5fb382719e532409da8a0756ed62eb2149a0a52` (TWRP).
- Local golden K34 image `Sharp-Checkpoint-20261107/SHL25-K34-NATIVE-BUSYBOX-SHELL-QEMU-v5.img` has identical BOOT hash and 17,825,792-byte length.

## Found and fixed in native Linux 6.1 initramfs

The previous independent ARMHF initramfs CI 42381597113,
SHA `2fbb7bbcb20317715805fe91f0e9a53115898ec6656472e30e4bb91044f21870`,
lacked the three POSIX character device nodes. Archive verifier
**correctly fails** on original with
`ValueError: required character device missing: dev/console`.
That makes kernel-to-PID1 console visibility unreliable.

Changes:
- `scripts/build-linux61-native-initramfs.sh` wraps the archive
  construction in **fakeroot** to encode proper device nodes, without
  requiring privileged GitHub runner access.
- Adds `/dev/console` character 5:1 mode 0600,
  `/dev/null` 1:3 mode 0666 and `/dev/kmsg` 1:11 mode 0600.
- `native61/verify_initramfs.py` checks newc archive structure,
  no traversal/duplicates, uid/gid=0, nodes' major/minors,
  executable ARMHF BusyBox, executable shell-script PID1
  and exact safety markers.
- Existing QEMU ARMHF interpreter check remains.
- GitHub workflow `linux61-native-initramfs.yml` installs
  fakeroot and runs independent archive validation.
- This is **source/CI gate only**, not Linux 6.1 hardware boot PASS.

## C12: First controlled hardware test plan

1. Confirm latest C11 native initramfs CI SUCCESS and download
   **matching SHA-pinned** artifact.
2. Obtain matching clean Linux 6.1 zImage, validated SHL25 AS99 DTB
   from latest successful Linux 6.1 CI.
3. Package an **offline** Qualcomm Android BOOT v0 for Sharp legacy
   board: preserve 2048-byte page, kernel address 0x8000,
   ramdisk address 0x01000000, tags address 0x100 and
   `init=/init` cmdline from K34 golden BOOT.
4. QCDT v2 must retain eight OEM board selector entries:
   MSM IDs 208,209,211,212,214,215,217,218; board ID 50.
   They all refer to ONE existing Sharp DT slot at offset 2048;
   replace the FDT in that slot with the Linux 6.1 DTB,
   respecting length and original QCDT allocation. Do not
   substitute an OEM Linux3.4 DTB for the 6.1 DTB.
5. Strict image roundtrip and partition-size checks; preserve
   local golden K34 BOOT and live TWRP p14.
6. On owner-authorized hardware trial, write BOOT p13 **only**,
   never Recovery p14. Use a bounded observation period;
   look for Linux6.1 USB gadget/ttyACM0 and signed PID1 marker.
7. If boot is inconclusive/no USB, return to TWRP using known
   supported hardware path and restore exact known-good K34
   BOOT bytes from host. No guesses on battery gauge.
8. CI artifact success is **not** boot pass. No claim LCD,
   CLMR, touch or Wi-Fi before real run.

Known issues still requiring investigation:
- Sharp firmware bootloader fixups of DTB memory `reg=<0 0>`
  are source-inferred but not verified on Linux6.1.
- USB gadget PHY/controller and DRM remain unproven on 6.1.
- The OEM Sharp CLMR/BDIC panel driver is intentionally disabled
  in DT, and this first test is headless/serial, NOT full GUI.
