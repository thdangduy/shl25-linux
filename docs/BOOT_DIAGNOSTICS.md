# SHL25 Linux 6.16 — first boot diagnostics

## Verified

- Sharp SHL25 / AS99, Snapdragon MSM8974Pro, Sharp OEM kernel 3.4.0.
- BOOT mmcblk0p13: exactly 17,825,792 bytes. TWRP Recovery mmcblk0p14 is separate.
- Original Qualcomm bootloader uses the Android BOOT v0 image with QCDT v2 and board ID 50 for MSM IDs 208,209,211,212,214,215,217,218.
- First experimental Linux 6.16 zImage cross-built successfully. Draft Sharp AS99 DTS compiled to 43,947-byte DTB.
- First BOOT trial did not return ADB or show an initialized display. TWRP was recovered using Sharp power-key sequence.
- First test reused the TWRP/Android 3.4 init ramdisk. USB setup referenced legacy /sys/class/android_usb while the new kernel enables USB ConfigFS. Therefore missing ADB alone does not prove mainline kernel crashed.
- Initial CONFIG_DRM_MSM=m and no module loader in ramdisk. Sharp panel still needs a board driver.
- CONFIG_PSTORE was disabled. TWRP has no /proc/last_kmsg or /sys/fs/pstore.

## Read-only OEM log investigation

Sharp eMMC partition named log (/dev/block/mmcblk0p29) holds 37 PANC/GZIP records. Most recent readable old Sharp-kernel entries include 'Kernel panic - not syncing: POWER KEY 4 s pressed', which denotes forced power-key reboot. They do NOT establish a Linux 6.16 kernel panic. The 2026/1970-like reset timestamp values are not all trustworthy because RTC may be unset.

## What the CI build establishes

CI proves the pinned MSM8974 mainline zImage and Sharp board DTB can be cross-compiled. It does not prove boots, working USB, display, charger, modem, Wi-Fi, power management, working Ubuntu 24.04 ARMHF PID 1, or Recovery boot key handling.

## Next bring-up steps

1. Create a separate, minimal static diagnostic initramfs that records staged boot markers to storage, with read-only mounts until device probing is understood.
2. Adapt USB ConfigFS gadget, rather than using old TWRP/Android USB init.
3. Build DRM MSM into the kernel, and port the Sharp 1080p Andy/CLMR/IR2E71Y6 display sequence.
4. Enable pstore only after verifying Sharp memory reservations and a correct ramoops DT node.
5. Test exact Qualcomm QCDT v2 boot packaging and board ID/ramdisk memory addresses offline. Preserve TWRP and known-good BOOT recovery path.
6. Prepare a true Ubuntu ARMHF init/root rather than a chroot started from TWRP init.

**No CI step in this repository should flash or write to a phone.**
