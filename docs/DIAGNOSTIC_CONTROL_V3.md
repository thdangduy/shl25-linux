# SHL25 Diagnostic v3 — kernel 3.4 control before 6.16 retry

The Linux 6.16 v2 flash completed with correct BOOT and TWRP Recovery hashes, but no `/cache/shl25-616-diag.log` was created when the owner returned to TWRP. That alone cannot distinguish early kernel/DT failure from MMC/init issues.

## Verified on actual SHL25 (2026-11-06)
- TWRP Recovery: Linux 3.4.0; ADB works.
- `/proc/filesystems` on Sharp 3.4 has **no devtmpfs**. `/dev` is tmpfs managed by userspace. This makes the v2 static initramfs incompatible as a control test.
- `/sys/class/block/mmcblk0p32/uevent` includes `PARTNAME=cache`; `dev` contains `259:0` during TWRP.
- `/dev/block/mmcblk0p32` is mounted at `/cache` as ext4 by TWRP. The new diagnostic init must not depend on that userspace-created path.
- BOOT v2 retained QCDT v2 entries and matched BOOT/Recovery SHA256 postflash.

## v3 source change
`diagnostics/init.c` now creates `/dev/console` and `/dev/kmsg` nodes if missing and, **only when** `PARTNAME=cache` is verified for `mmcblk0p32`, obtains the major:minor from sysfs and uses `mknod` for `/dev/mmcblk0p32`. It validates the resulting node is a block device with the expected device number.

The previous devtmpfs-only assumption is removed. All existing restrictions remain: only the verified cache partition may be mounted, read-only before rw remount; BOOT, Recovery, userdata and bootloader are untouched.

## Next experiment
1. GitHub Actions builds static ARMHF v3 PID1 and validates the resulting CPIO.
2. Create a diagnostic control BOOT with **known-bootable Sharp 3.4 kernel + verified original Qualcomm QCDT** and the new v3 initramfs; never replace Recovery.
3. Verify SHA256 of the generated image, the staged file, and BOOT after any write. Keep Ubuntu 3.4 rollback available.
4. Reboot to run the control; return to TWRP using established power-key method.
5. If marker is created, cache/PID1 diagnostics are validated on known-good kernel: investigate mainline 6.16 kernel/DT/memory/boot-protocol next. If absent, debug the logger before any new 6.16 flash.

This control test validates only the diagnostic mechanism, **not** Ubuntu 24.04 or Linux 6.16 boot.
