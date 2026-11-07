#!/usr/bin/env bash
set -Eeuo pipefail
# Build with fakeroot to encode correct character-device metadata in CPIO.
# The CI runner is unprivileged; no real /dev nodes are created on the host.
if [ -z "${FAKEROOTKEY:-}" ]; then
    command -v fakeroot >/dev/null || { echo "TOOL_MISSING: fakeroot"; exit 2; }
    exec fakeroot -- bash "$0" "$@"
fi
# SHL25 Linux 6.1 native RAM-only initramfs, never flashes.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$ROOT/.build/linux61-native"
DIST="$ROOT/dist-linux61-native"
FS="$WORK/rootfs"
rm -rf "$FS"
mkdir -p "$FS/bin" "$FS/sbin" "$FS/dev/pts" "$FS/proc" "$FS/sys" "$FS/tmp" "$FS/run" "$FS/etc" "$DIST"
# Kernel opens /dev/console before executing /init: required for PID1
# diagnostics even when USB/DRM are not initialized. Preserve null/kmsg.
mknod -m 0600 "$FS/dev/console" c 5 1
mknod -m 0666 "$FS/dev/null" c 1 3
mknod -m 0600 "$FS/dev/kmsg" c 1 11
for name in qemu-arm curl dpkg-deb sha256sum cpio gzip file arm-linux-gnueabihf-readelf mknod python3; do
    command -v "$name" >/dev/null || { echo "TOOL_MISSING: $name"; exit 2; }
done

# Exact SHA-pinned ARMHF BusyBox used for native K34 hardware proof.
URL="https://ports.ubuntu.com/ubuntu-ports/pool/main/b/busybox/busybox-static_1.36.1-6ubuntu3_armhf.deb"
SHA="fdcc7a041fa4c652aa8914bf79559703ea226f8516e63279e85b8a0dfc4aac76"
DEB="$WORK/busybox-static_1.36.1-6ubuntu3_armhf.deb"
if [ ! -f "$DEB" ]; then
    curl --fail --location --retry 3 --connect-timeout 15 --max-time 120 "$URL" -o "$DEB"
fi
printf '%s  %s\n' "$SHA" "$DEB" | sha256sum -c -
EXTRACT="$WORK/pkg"
rm -rf "$EXTRACT"
mkdir -p "$EXTRACT"
dpkg-deb -x "$DEB" "$EXTRACT"
BUSYBOX="$(find "$EXTRACT" -type f -name busybox -print -quit)"
test -n "$BUSYBOX" || { echo "NO_STATIC_BUSYBOX"; exit 3; }
cp "$BUSYBOX" "$FS/bin/busybox"
chmod 0755 "$FS/bin/busybox"
file "$FS/bin/busybox"
arm-linux-gnueabihf-readelf -h "$FS/bin/busybox" | grep -q 'Machine:.*ARM'
if arm-linux-gnueabihf-readelf -l "$FS/bin/busybox" | grep -q INTERP; then echo REFUSE_DYNAMIC_BUSYBOX; exit 4; fi
if arm-linux-gnueabihf-readelf -d "$FS/bin/busybox" 2>/dev/null | grep -q NEEDED; then echo REFUSE_LINKED_LIBRARIES; exit 5; fi
for app in sh ash mount umount mkdir cat ls ln head sleep uname setsid echo printf grep dmesg ps free date id stat test hexdump sha256sum chmod chown env sync mknod stty cut awk wc sort sed tail find kill poweroff reboot; do
    ln -s busybox "$FS/bin/$app"
done
cp "$ROOT/native61/init" "$FS/init"
chmod 0755 "$FS/init"
printf 'SHL25 native Linux 6.1 diagnostics, RAM-only\n' > "$FS/etc/issue"
printf 'export PATH=/bin:/sbin\nexport PS1="shl25-6.1# "\n' > "$FS/etc/profile"
# QEMU syntax + execution smoke: never execute PID1 mounts on build host.
qemu-arm -cpu cortex-a15 "$FS/bin/busybox" sh -n "$FS/init"
ASH="$(qemu-arm -cpu cortex-a15 "$FS/bin/busybox" sh -c 'printf SHL25_LINUX61_ASH_ARMV7_OK')"
test "$ASH" = "SHL25_LINUX61_ASH_ARMV7_OK"
echo "$ASH"
find "$FS" -exec touch -h -d '@0' {} +
(
  cd "$FS"
  find . -print0 | LC_ALL=C sort -z |
    cpio --null --quiet --reproducible -o -H newc --owner=0:0 |
    gzip -9 -n > "$DIST/native-initramfs.cpio.gz"
)
test "$(stat -c %s "$DIST/native-initramfs.cpio.gz")" -gt 700000
printf '%s\n' \
    "Linux: upstream v6.1 ARMv7 MSM8974Pro" \
    "Userspace: original SHL25 native61/init + Ubuntu static ARMHF BusyBox" \
    "BusyBox URL: $URL" \
    "BusyBox .deb SHA256: $SHA" \
    "PID1: /init; USB configfs CDC ACM; ttyGS0 BusyBox ash" \
    "No eMMC mount, flash, repartition or modem config" \
    "C11: dev/console (5,1), dev/null (1,3), dev/kmsg (1,11) verified by archive parser" \
    "Device boot verified: NO" \
    "TWRP Recovery and BOOT modified: NO" \
    > "$DIST/SOURCE_MANIFEST.txt"
cp "$ROOT/native61/init" "$DIST/init"
cp "$ROOT/scripts/build-linux61-native-initramfs.sh" "$DIST/build-script.sh"
(cd "$DIST" && sha256sum native-initramfs.cpio.gz init build-script.sh SOURCE_MANIFEST.txt > SHA256SUMS)
gzip -t "$DIST/native-initramfs.cpio.gz"
python3 "$ROOT/native61/verify_initramfs.py" "$DIST/native-initramfs.cpio.gz"
echo SHL25_LINUX61_NATIVE_INITRAMFS_QEMU_AND_ARCHIVE_PASS
cat "$DIST/SHA256SUMS"
