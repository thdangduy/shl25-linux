#!/usr/bin/env bash
set -Eeuo pipefail

# Compile only: never write device partitions and never package a flashable BOOT image.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE_URL="https://github.com/msm8974-mainline/linux.git"
SOURCE_BRANCH="qcom-msm8974-6.16.y"
SOURCE_COMMIT="888dd19735240b640f925a6da4affc082c5c48a9"
WORK="$ROOT/.build"
SRC="$WORK/linux"
OBJ="$WORK/out"
DIST="$ROOT/dist"

for command in git make gcc arm-linux-gnueabihf-gcc arm-linux-gnueabihf-ld dtc sha256sum python3; do
  command -v "$command" >/dev/null || { echo "ERROR: Missing $command"; exit 2; }
done

mkdir -p "$WORK" "$OBJ" "$DIST"

if [ ! -d "$SRC/.git" ]; then
  git clone --depth 1 --single-branch --branch "$SOURCE_BRANCH" "$SOURCE_URL" "$SRC"
fi
git -C "$SRC" fetch --depth 1 origin "$SOURCE_COMMIT"
git -C "$SRC" checkout --detach "$SOURCE_COMMIT"
ACTUAL_COMMIT="$(git -C "$SRC" rev-parse HEAD)"
test "$ACTUAL_COMMIT" = "$SOURCE_COMMIT" || { echo "ERROR: wrong kernel commit"; exit 3; }

# Kernel compilation: reproducible known-good baseline qcom_defconfig.
make -C "$SRC" O="$OBJ" ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- qcom_defconfig
"$SRC/scripts/config" --file "$OBJ/.config" -d DEBUG_INFO_BTF -d DEBUG_INFO_BTF_MODULES
make -C "$SRC" O="$OBJ" ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- olddefconfig
make -C "$SRC" O="$OBJ" ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- -j"$(nproc)" zImage

# Standalone board-DTB compilation from the exact kernel headers.
DTS="$ROOT/dts/qcom-msm8974-sharp-as99.dts"
CPPSRC="$WORK/as99.preprocessed.dts"
gcc -E -P -x assembler-with-cpp -nostdinc -undef -D__DTS__ \
  -I "$SRC/include" \
  -I "$SRC/arch/arm/boot/dts" \
  -I "$SRC/arch/arm/boot/dts/qcom" \
  "$DTS" -o "$CPPSRC"

dtc -I dts -O dtb \
  -o "$DIST/qcom-msm8974-sharp-as99.dtb" \
  "$CPPSRC"

cp "$OBJ/arch/arm/boot/zImage" "$DIST/zImage"
cp "$OBJ/.config" "$DIST/kernel.config"
cp "$DTS" "$DIST/qcom-msm8974-sharp-as99.dts"

python3 - "$DIST/qcom-msm8974-sharp-as99.dtb" <<'PY'
from pathlib import Path
import struct, sys
raw=Path(sys.argv[1]).read_bytes()
assert len(raw)>0x2000, 'DTB unexpectedly small'
assert struct.unpack_from('>I',raw,0)[0] == 0xd00dfeed, 'No FDT magic'
assert struct.unpack_from('>I',raw,4)[0] == len(raw), 'FDT size mismatch'
assert b'qcom,sharp-as99' in raw, 'Sharp AS99 compatible not found'
print('AS99 DTB VALIDATION PASS:',len(raw),'bytes')
PY

cat > "$DIST/BUILD_INFO.txt" <<EOF
Project: thdangduy/shl25-linux
Kernel: msm8974-mainline/linux
Branch: $SOURCE_BRANCH
Commit: $ACTUAL_COMMIT
Architecture: ARMv7 hard-float
Device: Sharp SHL25 / AS99
Board ID: 50
Artifact status: COMPILE ONLY; NOT BOOT VALIDATED
Firmware: NO FLASHABLE IMAGE PRODUCED
EOF

(cd "$DIST" && sha256sum zImage qcom-msm8974-sharp-as99.dtb qcom-msm8974-sharp-as99.dts kernel.config > SHA256SUMS)
echo "SHL25 Linux kernel and DTB build passed."
cat "$DIST/BUILD_INFO.txt"
cat "$DIST/SHA256SUMS"
