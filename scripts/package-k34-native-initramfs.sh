#!/usr/bin/env bash
set -Eeuo pipefail
# Build only an ARMHF native Linux 3.4 initramfs. No BOOT image or device access.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist-k34-native"
FS="$DIST/rootfs"
rm -rf "$FS"
mkdir -p "$FS/dev" "$FS/proc" "$FS/sys" "$FS/cache"
arm-linux-gnueabihf-gcc -std=gnu11 -O2 -static -march=armv7-a -mfpu=neon -mfloat-abi=hard \
    -Wall -Wextra -Werror "$ROOT/diagnostics/k34_native_init.c" -o "$FS/init"
chmod 0755 "$FS/init"
file "$FS/init"
arm-linux-gnueabihf-readelf -h "$FS/init" | head -28
# Reproducible archive metadata and device nodes under fakeroot.
export FS DIST
fakeroot bash -ec '
    mknod "$FS/dev/console" c 5 1
    mknod "$FS/dev/null" c 1 3
    mknod "$FS/dev/kmsg" c 1 11
    chmod 0600 "$FS/dev/console" "$FS/dev/kmsg"
    chmod 0666 "$FS/dev/null"
    cd "$FS"
    find . -print0 | LC_ALL=C sort -z | cpio --null -o -H newc --owner=0:0 > "$DIST/native-initramfs.cpio"
'
gzip -n -9 -f "$DIST/native-initramfs.cpio"
gzip -dc "$DIST/native-initramfs.cpio.gz" | cpio -tv | head -35
test -s "$DIST/native-initramfs.cpio.gz"
cat > "$DIST/SOURCE_MANIFEST.txt" <<EOF
Device: Sharp SHL25/AS99
Environment: standalone static ARMHF Linux 3.4 diagnostic PID1
Kernel: NOT INCLUDED — original OEM 3.4 and QCDT are kept separately on Windows
Userspace: diagnostics/k34_native_init.c (no Android framework)
USB: experimental Sharp vendor 'modem' CDC-ACM gadget; host link unproven
Storage: only optional cache marker; no boot/recovery flash or wipe
Boot image: NONE
Validated on hardware: NO — offline initramfs package only
EOF
(cd "$DIST" && sha256sum native-initramfs.cpio.gz rootfs/init SOURCE_MANIFEST.txt > SHA256SUMS)
echo SHL25_NATIVE_K34_INITRAMFS_BUILD_PASS
cat "$DIST/SHA256SUMS"
