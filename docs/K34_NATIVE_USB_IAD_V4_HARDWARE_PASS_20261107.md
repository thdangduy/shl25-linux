# SHL25 / AS99 — native Linux 3.4 CDC ACM USB serial: real-hardware PASS

Date: 2026-11-07. Authorized Windows computer S9X0R0, SHL25 serial
356594053328037. Repository: thdangduy/shl25-linux.

## Verified hardware baseline
Sharp OEM 2016 Linux 3.4 with own static ARMHF /init and no Android
framework. Before this experiment, the device successfully booted /init
and wrote several `SHL25_NATIVE_PID1 kernel=3.4.0 arch=armv7l` lines
to `/cache/shl25-k34-native.pid1.log`.

The v3 USB trace `/cache/shl25-k34-native.usb.trace` establishes:
- All gadget sysfs writes `enable`, `functions=modem`,
  `unlocked`, USB vendor/product/serial and transport succeeded.
- USB reached CONFIGURED in one boot, and /dev/ttyGS0 was opened.
- Windows nevertheless returned Code 10 on usbser.sys for
  VID_18D1 PID_0001 MI_00, and separately enumerated MI_01.
- setupapi.dev.log reported CM_PROB_FAILED_START,
  NTSTATUS 0xc000000e. Root cause candidate was host CDC function grouping.

## Source change, isolated and evidence-grounded

Sharp GPL source `bld010105/kernel.tar.gz`, pinned source hash
`231315e67112ffa3b5311059ba8ad4f6b4f2213edea40a7fff001f5a3bdf27bb`.

With CONFIG_USB_ANDROID_SH_SERIALS, Sharp's f_acm.c explicitly
excluded its Interface Association Descriptor (IAD), even though the
CDC ACM function uses two separate interfaces, control and data.

Microsoft Windows documentation:
- https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/usb-interface-association-descriptor
- https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/enumeration-of-the-composite-parent-device

Kernel patch:
- `patches/oem34/0001-sharp-gserial-reuse-existing-ttygs.patch`
- `patches/oem34/0002-sharp-usb-acm-enable-iad.patch`
  restores already-defined IAD to full/high/superspeed descriptor arrays
  and its dynamic first-interface assignment; non-Sharp behavior unchanged.
- f_acm.c original SHA256:
  `c92f419579eb648d12df41873aa9944fcbbaf890c4e720f941e1029e0b05c039`.
- f_acm.c patched SHA256:
  `4fe8207f89b6f8e803018da346bc07d809ff3af7d54a78f6daa17d7df0e61509`.
- Patch generator `scripts/prepare_oem34_acm_iad_patch.py`,
  replay on original OEM source via `git apply --check` and
  `git apply`: PASS with byte-exact hash.
- Native PID1 `diagnostics/k34_native_init.c` sets bDeviceClass=239
  (0xEF), bDeviceSubClass=2, bDeviceProtocol=1, modem-only function,
  vendor ID 0x18D1, new test PID 0x0002, genuine serial 356594053328037.

Commit containing changes: `14fdf24`.

## CI and standalone image, SHA-verified on Windows

- Native CPIO build GitHub Actions 42368607296: SUCCESS.
  `native-initramfs.cpio.gz` SHA256:
  `248cf97346b1afa25f49fc8c999faa3816e8f56c225aceceb9c22a6edc89c301`.
- OEM kernel IAD build GitHub Actions 42368607335: SUCCESS.
  `zImage` bytes: 6,669,160. SHA256:
  `60119f9754a8b55f8488e7281d5d7ba4e2053b1c3b1509e0ac1ef9d00a41e312`.
- Offline BOOT image (OEM QCDT section unchanged):
  `Sharp-Checkpoint-20261107/SHL25-K34-NATIVE-IAD-WINDOWS-v4.img`
  bytes 17,825,792, SHA256:
  `1e8e93a67347e5ca8835585a016763b4ff790632fb4910f6846209291aaf8a83`.
- TWRP only wrote BOOT p13; post-write readback SHA matched image.
  TWRP Recovery p14 SHA unchanged:
  `a8ef5821a0eeef0bbb1f3242a5fb382719e532409da8a0756ed62eb2149a0a52`.
- Kernel K34 rollback image remains staged in device cache, SHA
  `adf071e680e4373277cb2bdf8fe0f38ef215bccaf24f7def97f8fb31dbf44b8e`.

## Native Linux 3.4 v4 live USB serial: PASS

Windows (no driver install):
- USB Composite `USB\\VID_18D1&PID_0002\\356594053328037`: OK.
- `USB Serial Device (COM21)`: status OK; usbser.sys.
- Booted from real SHL25 BOOT p13 into standalone Linux 3.4 PID1,
  without Android OS or adbd.
- Windows successfully opened COM21 and sent `info` and `help`.
  Device returned:

```text
SHL25 Native Linux 3.4 diagnostic console
shl25> info
SHL25 native PID1, Linux 3.4.0, machine armv7l
shl25> help
Commands: help info cpu mem fb touch usb
```

A host-side initial write attempt timed out but a subsequent attempt
completed; PnP ended fully OK. The repeatability test later performed
**eight separate close/open/info cycles: 8/8 PASS**.

Additional commands executed over the standalone Linux USB serial:
- `cpu`: four ARMv7 processor entries; NEON/VFPv4 reported.
- `mem`: MemTotal 1,833,228 kB.
- `fb`: `U:1080x1920p-0`.
- `touch`: `shtps_rmi`.
- `usb`: `CONFIGURED`.

Host evidence saved on S9X0R0:
- `Sharp-Checkpoint-20261107/SHL25_K34_USB_IAD_V4_HOST_MONITOR.log`
- `Sharp-Checkpoint-20261107/SHL25_NATIVE_K34_COM21_HARDWARE_COMMANDS.txt`
- `Sharp-Checkpoint-20261107/SHL25_NATIVE_K34_COM21_RECONNECT_TEST.txt`

## What this does and does not prove
PASS: OEM Linux kernel 3.4 native PID1, eMMC marker writes, USB
two-way CDC ACM console, Linux ARMv7/proc/mem/framebuffer/input
enumeration without Android framework. Reproducible host USB connection.

NOT YET VERIFIED: general-purpose Linux shell, visible live LCD graphics
under native boot, actual touch event delivery, Wi-Fi/modem functioning
without Android, Linux 6.1 boot/driver port. Linux 6.1 clean CI build
is a separate offline result, not proof of running on device.

## Next engineering step
Build a static BusyBox or similar native Linux shell into initramfs and
attach an interactive serial shell to /dev/ttyGS0. Preserve existing
native diagnostic commands and USB IAD setup. Test framebuffer display
and real touch events, then carry proven clock/PMIC/eMMC/DSI/touch/USB
sequences to Linux 6.1. No AOSP and no VPS-ARM.

Protect Recovery p14 and keep p13 rollback. TWRP battery percentage is
known unreliable and should not be used as charging evidence.
