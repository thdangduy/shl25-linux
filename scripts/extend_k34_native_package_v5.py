#!/usr/bin/env python3
"""Add SHA-pinned, static ARMHF BusyBox ash and hardware probes to K34 initramfs."""
from pathlib import Path
p=Path(__file__).resolve().parent/"package-k34-native-initramfs.sh"
data=p.read_text(encoding="utf8")
if "BUSYBOX_ARMHF_SHA" in data:raise SystemExit("ALREADY_EXTENDED")
def sub(old,new):
    global data
    if data.count(old)!=1: raise SystemExit("EXPECTED_UNIQUE_PACKAGE_ANCHOR "+repr(old))
    data=data.replace(old,new,1)
sub('mkdir -p "$FS/dev" "$FS/proc" "$FS/sys" "$FS/cache"',
'''mkdir -p "$FS/dev" "$FS/proc" "$FS/sys" "$FS/cache" "$FS/bin" "$FS/sbin" "$FS/tmp" "$FS/etc" "$FS/dev/input" "$FS/dev/graphics"
# Canonical Ubuntu 24.04 Noble ARMHF static BusyBox package, not a vendor ROM.
# SHA256 pinned to packages.ubuntu.com/noble/armhf/busybox-static/download
BUSYBOX_ARMHF_URL="https://ports.ubuntu.com/ubuntu-ports/pool/main/b/busybox/busybox-static_1.36.1-6ubuntu3_armhf.deb"
BUSYBOX_ARMHF_SHA="fdcc7a041fa4c652aa8914bf79559703ea226f8516e63279e85b8a0dfc4aac76"
BUSYBOX_DEB="$DIST/busybox-static-armhf.deb"
if [ ! -f "$BUSYBOX_DEB" ]; then
    curl --fail --location --retry 3 --connect-timeout 15 --max-time 120 "$BUSYBOX_ARMHF_URL" -o "$BUSYBOX_DEB"
fi
echo "$BUSYBOX_ARMHF_SHA  $BUSYBOX_DEB" | sha256sum --check -
mkdir -p "$DIST/extracted"
dpkg-deb -x "$BUSYBOX_DEB" "$DIST/extracted"
BUSYBOX_FILE="$(find "$DIST/extracted" -type f -name busybox -print -quit)"
test -n "$BUSYBOX_FILE"
cp "$BUSYBOX_FILE" "$FS/bin/busybox"
chmod 0755 "$FS/bin/busybox"
# Reject dynamic ELF and incorrect CPU machine before packaging.
arm-linux-gnueabihf-readelf -h "$FS/bin/busybox" | grep -q 'Machine:.*ARM'
if arm-linux-gnueabihf-readelf -l "$FS/bin/busybox" | grep -q INTERP; then
    echo "REFUSE_DYNAMIC_BUSYBOX"; exit 6
fi
file "$FS/bin/busybox"
for app in sh ash ls cat grep dmesg uname free ps mount umount df hexdump od stat head tail \
  chmod chown echo test printf sleep find sort sed awk cut wc date tr mkdir mknod sync id env \
  kill expr readlink basename dirname; do
    ln -s busybox "$FS/bin/$app"
done
ln -s ../bin/busybox "$FS/sbin/mdev"
cat > "$FS/etc/profile" <<'EOF'
export PATH=/bin:/sbin
export HOME=/
export TERM=vt100
export PS1='shl25-k34# '
EOF
''')
sub('chmod 0755 "$FS/init"\nfile "$FS/init"',
'''chmod 0755 "$FS/init"
# Bundle read-only enumerator and RAM-overlay LCD proof; both compiled ARMHF static.
for tool in k34_fbdiag k34_fbtext k34_hwprobe; do
    case "$tool" in
      k34_fbdiag) src="$ROOT/diagnostics/k34_fbdiag.c"; out="$FS/sbin/fbdiag" ;;
      k34_fbtext) src="$ROOT/diagnostics/k34_fbtext.c"; out="$FS/sbin/fbtext" ;;
      k34_hwprobe) src="$ROOT/diagnostics/k34_hwprobe.c"; out="$FS/sbin/hwprobe" ;;
    esac
    arm-linux-gnueabihf-gcc -std=gnu11 -O2 -static -march=armv7-a -mfpu=neon -mfloat-abi=hard \
      -Wall -Wextra -Werror "$src" -o "$out"
    chmod 0755 "$out"
    if arm-linux-gnueabihf-readelf -l "$out" | grep -q INTERP; then
      echo "REFUSE_DYNAMIC_TOOL $out"; exit 7
    fi
done
file "$FS/init" "$FS/bin/busybox" "$FS/sbin/"*
''')
sub('Environment: standalone static ARMHF Linux 3.4 diagnostic PID1',
    'Environment: standalone static ARMHF Linux 3.4 PID1 with interactive USB shell')
sub('Userspace: diagnostics/k34_native_init.c (no Android framework)',
    '''Userspace: diagnostics/k34_native_init.c and Ubuntu armhf busybox-static 1.36.1
BusyBox source: $BUSYBOX_ARMHF_URL
BusyBox package SHA256: $BUSYBOX_ARMHF_SHA
Shell: /bin/sh (BusyBox ash) launched only on user serial shell command
Hardware utilities: /sbin/hwprobe, /sbin/fbdiag, /sbin/fbtext
Android framework: NONE''')
sub("USB: experimental Sharp vendor 'modem' CDC-ACM gadget; host link unproven",
    "USB: Sharp CDC ACM IAD (0xEF/0x02/0x01), previously proven with COM21")
sub('Validated on hardware: NO — offline initramfs package only',
    'Validated on hardware: v4 PID1/CDC ACM PASS, NEW v5 BusyBox shell and LCD tools not yet tested')
sub('sha256sum native-initramfs.cpio.gz rootfs/init SOURCE_MANIFEST.txt > SHA256SUMS',
    'sha256sum native-initramfs.cpio.gz rootfs/init rootfs/bin/busybox rootfs/sbin/fbtext rootfs/sbin/hwprobe SOURCE_MANIFEST.txt > SHA256SUMS')
p.write_text(data,encoding="utf8",newline="\n")
print("SHL25_K34_NATIVE_PACKAGE_V5_READY")
