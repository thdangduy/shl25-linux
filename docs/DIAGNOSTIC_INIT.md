# SHL25 Linux 6.16 — diagnostic PID1

This experiment addresses a confirmed limitation in the first physical boot attempt:
the Android 3.4 recovery ramdisk expected the removed legacy Android USB
gadget interface, so lack of ADB on Linux 6.16 did not prove a kernel crash.

The new initramfs contains a statically linked ARMHF `/init`. It is **not**
Android, not systemd, not an Ubuntu Server rootfs. It does not depend on USB or
a display driver.

Once Linux 6.16 starts the process, it mounts proc/sys/devtmpfs and waits for
`/dev/mmcblk0p32`. Before touching the partition it requires
`/sys/class/block/mmcblk0p32/uevent` to contain `PARTNAME=cache`, as verified
read-only through TWRP on the SHL25 hardware. It mounts that filesystem **read-only
first**, then remounts read/write **only to append one line** to
`/cache/shl25-616-diag.log`. The process then idles as PID1.

When the handset returns to TWRP, look for:

```text
/cache/shl25-616-diag.log
SHL25_DIAG_PID1_OK kernel=6.16... arch=armv7l cache=verified
```

- Marker exists: kernel, basic Device Tree, MMC, ext4 and `/init` ran.
- Marker absent: **inconclusive** — kernel may not have reached init, or MMC,
  DT, ext4/cache mounting, or partition enumeration may not work.

GitHub workflow `SHL25 Diagnostic Initramfs ARMHF` builds the `.cpio.gz`
and validates the static ARM executable. It **does not produce a BOOT.img,
and it does not flash anything**.

No need for VPS-ARM. The normal kernel workflow remains separate. Never
overwrite TWRP Recovery, bootloader or userdata during diagnostics.
