#!/usr/bin/env bash
set -Eeuo pipefail

# Build standalone native Linux ARMv7 initramfs. No phone, no partitions.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$ROOT/.build/diagnostic-root"
DIST="$ROOT/dist-diagnostic"
mkdir -p "$TMP/dev" "$TMP/proc" "$TMP/sys" "$TMP/cache" "$DIST"

for bin in arm-linux-gnueabihf-gcc arm-linux-gnueabihf-readelf cpio gzip file sha256sum; do
  command -v "$bin" >/dev/null || { echo "ERROR missing tool: $bin"; exit 2; }
done

arm-linux-gnueabihf-gcc -static -no-pie -Os -Wall -Wextra -Werror \
  -o "$TMP/init" "$ROOT/diagnostics/init.c"
chmod 0755 "$TMP/init"

echo "ARMHF INIT ELF:"
file "$TMP/init"
arm-linux-gnueabihf-readelf -h "$TMP/init" | grep -E 'Class:|Machine:|Entry point'
if arm-linux-gnueabihf-readelf -l "$TMP/init" | grep -q INTERP; then
  echo 'ERROR: /init is dynamically linked, requires loader'
  exit 3
fi
arm-linux-gnueabihf-readelf -h "$TMP/init" | grep -q 'Machine:.*ARM' || exit 4

# CPIO newc: available to Linux 6.16 initramfs unpacker.
(
  cd "$TMP"
  find . -print0 | sort -z | cpio --null -o --format=newc --owner=0:0 --quiet
) | gzip -9n > "$DIST/shl25-diag-initramfs.cpio.gz"

gzip -t "$DIST/shl25-diag-initramfs.cpio.gz"
gzip -dc "$DIST/shl25-diag-initramfs.cpio.gz" | cpio -it --quiet | grep -q '^init$' \
  || { echo 'ERROR: cpio does not contain init'; exit 5; }

cp "$ROOT/diagnostics/init.c" "$DIST/init.c"
cat > "$DIST/BUILD_INFO.txt" <<EOF
Project: thdangduy/shl25-linux
Artifact: native Linux diagnostic initramfs for ARMv7/ARMHF
PID1: statically linked /init; NOT Android; NOT Ubuntu 24.04
Source: diagnostics/init.c
Writes: ONLY /cache/shl25-616-diag.log, after verifying PARTNAME=cache
Storage checks: DEVNAME=mmcblk0p32, GPT PARTNAME=cache, ext4
Safety: no flash action, no boot image produced
Status: compile/CPIO validation only; NOT BOOT VALIDATED on SHL25
EOF
(cd "$DIST"; sha256sum shl25-diag-initramfs.cpio.gz init.c > SHA256SUMS)
echo 'DIAGNOSTIC_INITRAMFS_BUILD_PASS'
cat "$DIST/BUILD_INFO.txt"
cat "$DIST/SHA256SUMS"
