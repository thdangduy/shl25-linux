#!/usr/bin/env bash
set -Eeuo pipefail
# Compile Sharp SHL25 official GPL 3.4 kernel + isolated ttyGS reuse patch.
# GitHub CI/offline build only. No flashable Android BOOT packaging, ADB or device I/O.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$ROOT/.build/oem-k34-gserial"
TARBALL="$WORK/kernel.tar.gz"
EXTRACT="$WORK/extract"
SRC="$EXTRACT/kernel"
OUT="$WORK/out"
DIST="$ROOT/dist-oem-k34-gserial"
OFFICIAL_URL="https://ad-dl02.4sh.jp/developers/oss/shl25/index_v2/download/bld010105/kernel.tar.gz"
EXPECTED_SOURCE="231315e67112ffa3b5311059ba8ad4f6b4f2213edea40a7fff001f5a3bdf27bb"
EXPECTED_PATCHED_U_SERIAL="0824f4470986ec843ded3da2f117041bf563fbb3a93550bf9b0a57343c1ada0c"
PATCH="$ROOT/patches/oem34/0001-sharp-gserial-reuse-existing-ttygs.patch"

for tool in curl sha256sum tar git make python3 arm-linux-gnueabihf-gcc; do
    command -v "$tool" >/dev/null || { echo "MISSING_TOOL: $tool"; exit 2; }
done
mkdir -p "$WORK" "$EXTRACT" "$OUT" "$DIST"
if [ ! -f "$TARBALL" ]; then
# Sharp archival server presents a TLS certificate for a different host.
    # This exception applies ONLY to this pinned public GPL tarball;
    # sha256sum --check is mandatory before extraction or execution.
    curl --insecure --fail --location --retry 2 --connect-timeout 25 --max-time 360 \
        "$OFFICIAL_URL" -o "$TARBALL"
fi
echo "$EXPECTED_SOURCE  $TARBALL" | sha256sum --check -
tar -xzf "$TARBALL" -C "$EXTRACT" --no-same-owner
test -s "$SRC/arch/arm/configs/deckard_as99_defconfig"
git -C "$EXTRACT" init -q
git -C "$EXTRACT" config core.autocrlf false
git -C "$EXTRACT" apply --check "$PATCH"
git -C "$EXTRACT" apply "$PATCH"
ACTUAL_PATCH_SHA="$(sha256sum "$SRC/drivers/usb/gadget/u_serial.c" | cut -d' ' -f1)"
[ "$ACTUAL_PATCH_SHA" = "$EXPECTED_PATCHED_U_SERIAL" ] || {
    echo "PATCH_APPLIED_SOURCE_SHA_MISMATCH=$ACTUAL_PATCH_SHA"; exit 8;
}
echo "OEM_SHARP_GSERIAL_PATCH_APPLY_PASS"
python3 "$ROOT/scripts/fix_legacy_gcc_wrapper.py" "$SRC/scripts/gcc-wrapper.py"
export ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf-
export KBUILD_BUILD_USER=shl25-ci KBUILD_BUILD_HOST=github-actions
arm-linux-gnueabihf-gcc --version | head -1
make -C "$SRC" O="$OUT" HOSTCFLAGS="-O2 -fcommon" deckard_as99_defconfig
grep -qx 'CONFIG_SHDISP=y' "$OUT/.config"
grep -qx 'CONFIG_USB_ANDROID_SH_SERIALS=y' "$OUT/.config"
grep -qx 'CONFIG_SHTPS_SY3000_TM2979_001=y' "$OUT/.config"
echo "SHL25_OEM_CONFIG_PASS"
make -C "$SRC" O="$OUT" HOSTCFLAGS="-O2 -fcommon" -j4 zImage
cp "$OUT/arch/arm/boot/zImage" "$DIST/zImage"
cp "$OUT/.config" "$DIST/kernel.config"
cat > "$DIST/SOURCE_MANIFEST.txt" <<EOF
Device: Sharp SHL25 / AS99
Source: official Sharp SHL25 GPL 01.01.05 bld010105 kernel.tar.gz
Source URL: $OFFICIAL_URL
Pinned source SHA256: $EXPECTED_SOURCE
Patch: patches/oem34/0001-sharp-gserial-reuse-existing-ttygs.patch
Patched u_serial.c SHA256: $ACTUAL_PATCH_SHA
Driver: Linux 3.4 USB gadget gserial conditional reuse
Boot image: NO; zImage only
Hardware validated: NO; full build check only
TWRP Recovery and BOOT on phone: untouched
EOF
(cd "$DIST" && sha256sum zImage kernel.config SOURCE_MANIFEST.txt > SHA256SUMS)
echo "SHL25_OEM34_GSERIAL_KERNEL_BUILD_PASS"
cat "$DIST/SHA256SUMS"
