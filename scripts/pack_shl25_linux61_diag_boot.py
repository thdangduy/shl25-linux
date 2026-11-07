#!/usr/bin/env python3
"""C12: offline-only SHL25 6.1 BOOT image packer, no USB/ADB/flash.

Use the SHA-verified real K34 native v5 BOOT as the legacy boot-header and
QCDT-v2 template. Replace zImage, native ARMHF initramfs and the ONE shared
AS99 DTB payload in the original 8-selector QCDT table. The ORIGINAL Sharp
3.4 FDT must never be paired with upstream Linux 6.1.

Input and output are host regular files. Never writes any phone partition.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import struct
import sys

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "native61"))
from verify_initramfs import verify as verify_initramfs

SHA_K34_GOLDEN_BOOT = "b0d52a1fce11070791607b14e476ca8a67209483fb7cafcfb7209b5be22b849f"
SHA_ORIGINAL_QCDT = "a71dcb36c829378ec43dc334234a0a892ef224bade3ff2d7100857c0687150bc"
EXPECTED_BOOT_SIZE = 17_825_792
EXPECTED_MSM_IDS = (208, 209, 211, 212, 214, 215, 217, 218)
ARM_ZIMAGE_MAGIC = 0x016F2818
FDT_MAGIC = b"\xd0\x0d\xfe\xed"
FDT_SLOT_OFFSET = 2048
FDT_SLOT_SIZE = 212992


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def check_pin(label, data, expected):
    if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected.lower()):
        raise ValueError(label + ": requires an explicit 64-character SHA256")
    actual = sha256(data)
    if actual != expected.lower():
        raise ValueError("%s SHA256 mismatch (actual %s)" % (label, actual))
    return actual


def align(num, page):
    return ((num + page - 1) // page) * page


def parse_legacy_boot(base):
    if len(base) != EXPECTED_BOOT_SIZE or base[:8] != b"ANDROID!":
        raise ValueError("K34 golden BOOT image format/length mismatch")
    head = struct.unpack_from("<10I", base, 8)
    oldk, kaddr, oldr, raddr, secs, saddr, tags, pg, dtsz, unused = head
    if (kaddr, raddr, secs, saddr, tags, pg, dtsz, unused) != (
        32768, 16777216, 0, 15728640, 256, 2048, 215040, 0
    ):
        raise ValueError("legacy BOOT load addresses/layout unexpected")
    cmd = base[64:576].split(b"\0", 1)[0]
    if b"init=/init" not in cmd:
        raise ValueError("legacy native BOOT has no init=/init")
    dt_start = pg + align(oldk, pg) + align(oldr, pg)
    if dt_start + dtsz > len(base):
        raise ValueError("golden BOOT QCDT section truncated")
    dt = base[dt_start:dt_start + dtsz]
    check_pin("original K34 QCDT", dt, SHA_ORIGINAL_QCDT)
    if struct.unpack_from("<4sII", dt) != (b"QCDT", 2, 8):
        raise ValueError("not exact legacy Sharp QCDT v2 x8")
    selectors = []
    for i in range(8):
        entry = struct.unpack_from("<6I", dt, 12 + i * 24)
        selectors.append(entry)
        if (entry[0], entry[1], entry[2], entry[3], entry[4], entry[5]) != (
            EXPECTED_MSM_IDS[i], 50, 0, 0x10000, FDT_SLOT_OFFSET, FDT_SLOT_SIZE
        ):
            raise ValueError("unknown Sharp QCDT selector: %s" % (entry,))
    if dt[FDT_SLOT_OFFSET:FDT_SLOT_OFFSET + 4] != FDT_MAGIC:
        raise ValueError("original Sharp FDT slot missing")
    if dt.count(FDT_MAGIC) != 1:
        raise ValueError("expected exactly ONE original shared Sharp FDT")
    return head, cmd, dt, selectors


def validate_linux_dtb(blob):
    if len(blob) < 1024 or len(blob) > FDT_SLOT_SIZE:
        raise ValueError("Linux 6.1 AS99 DTB outside shared QCDT slot")
    if blob[:4] != FDT_MAGIC:
        raise ValueError("not an FDT")
    totalsize = struct.unpack_from(">I", blob, 4)[0]
    if totalsize != len(blob):
        raise ValueError("Linux 6.1 DTB FDT header totalsize mismatch")
    if b"Sharp AQUOS SERIE SHL25" not in blob:
        raise ValueError("wrong DTB model/board identity")
    if b"qcom,sharp-as99" not in blob:
        raise ValueError("Linux 6.1 DTB lacks Sharp AS99 compatible")
    return totalsize


def pack(base, kernel, ramdisk, dtb, init_sha):
    head, cmd, original_qcdt, selectors = parse_legacy_boot(base)
    oldk, kaddr, oldr, raddr, secs, saddr, tags, page, dtsz, unused = head
    if not (4_000_000 <= len(kernel) <= 12_000_000):
        raise ValueError("kernel size not plausible for ARM zImage")
    if struct.unpack_from("<I", kernel, 0x24)[0] != ARM_ZIMAGE_MAGIC:
        raise ValueError("kernel missing ARM zImage magic")
    if len(ramdisk) > 3_000_000 or len(ramdisk) < 700000:
        raise ValueError("native ARMHF initramfs size unexpected")
    new_dtsize = validate_linux_dtb(dtb)

    # Preserve QCDT v2 x8 selectors EXACTLY, including the fixed
    # 212,992-byte shared DTB allocation for potential firmware fixups.
    qcdt = bytearray(original_qcdt)
    qcdt[FDT_SLOT_OFFSET:FDT_SLOT_OFFSET + FDT_SLOT_SIZE] = (
        dtb + b"\0" * (FDT_SLOT_SIZE - len(dtb))
    )
    qcdt = bytes(qcdt)
    if qcdt[:FDT_SLOT_OFFSET] != original_qcdt[:FDT_SLOT_OFFSET]:
        raise ValueError("QCDT board selector area modified")
    if qcdt.count(FDT_MAGIC) != 1:
        raise ValueError("unexpected FDT copies in QCDT")
    for i, selector in enumerate(selectors):
        if struct.unpack_from("<6I", qcdt, 12 + i * 24) != selector:
            raise ValueError("QCDT selector changed")

    hdr = bytearray(base[:page])
    struct.pack_into("<I", hdr, 8, len(kernel))
    struct.pack_into("<I", hdr, 16, len(ramdisk))
    # Android BOOT v0 SHA1 includes payload+32-bit length of all sections,
    # including the 0-byte second-stage and QCDT DT section.
    digest = hashlib.sha1()
    for segment in (kernel, ramdisk, b"", qcdt):
        digest.update(segment)
        digest.update(struct.pack("<I", len(segment)))
    hdr[576:608] = digest.digest() + b"\0" * 12
    padding = lambda b: b + b"\0" * (align(len(b), page) - len(b))
    payload = bytes(hdr) + padding(kernel) + padding(ramdisk) + padding(qcdt)
    if len(payload) > EXPECTED_BOOT_SIZE:
        raise ValueError("BOOT p13 partition capacity exceeded")
    image = payload + b"\0" * (EXPECTED_BOOT_SIZE - len(payload))
    # Strict unpack/roundtrip verification to catch payload displacement.
    h2 = struct.unpack_from("<10I", image, 8)
    if h2 != (len(kernel), kaddr, len(ramdisk), raddr,
              secs, saddr, tags, page, dtsz, unused):
        raise ValueError("BOOT header roundtrip failed")
    kernel_out = image[page:page + len(kernel)]
    ram_start = page + align(len(kernel), page)
    ram_out = image[ram_start:ram_start + len(ramdisk)]
    dt_start = ram_start + align(len(ramdisk), page)
    dt_out = image[dt_start:dt_start + len(qcdt)]
    if (kernel_out, ram_out, dt_out) != (kernel, ramdisk, qcdt):
        raise ValueError("BOOT sections roundtrip mismatch")
    if image[dt_start + dtsz:] != b"\0" * (len(image) - dt_start - dtsz):
        raise ValueError("trailing partition padding nonzero")
    if image[64:576] != base[64:576]:
        raise ValueError("Sharp cmdline changed")
    if image[page + align(len(kernel), page) + align(len(ramdisk), page) +
             FDT_SLOT_OFFSET:][:len(dtb)] != dtb:
        raise ValueError("wrong Linux 6.1 FDT payload")
    return image, {
        "status": "OFFLINE_PACKED_NOT_FLASHED_NOT_BOOT_TESTED",
        "target": "Sharp SHL25 / AS99 Linux 6.1 RAM-only PID1",
        "base_golden_k34_sha256": SHA_K34_GOLDEN_BOOT,
        "original_sharp_qcdt_sha256": SHA_ORIGINAL_QCDT,
        "new_linux61_qcdt_sha256": sha256(qcdt),
        "kernel_sha256": sha256(kernel),
        "ramdisk_sha256": sha256(ramdisk),
        "as99_dtb_sha256": sha256(dtb),
        "native_init_sha256": init_sha.lower(),
        "image_sha256": sha256(image),
        "image_bytes": len(image),
        "qcdt_version": 2,
        "qcdt_selector_count": 8,
        "qcdt_shared_dtb_size": FDT_SLOT_SIZE,
        "linux61_fdt_totalsize": new_dtsize,
        "kernel_load": hex(kaddr),
        "ramdisk_load": hex(raddr),
        "cmdline": cmd.decode("ascii", errors="replace"),
        "recovery": "mmcblk0p14 NEVER written by this packer",
        "boot_partition": "mmcblk0p13 NEVER written by this packer",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("base", "kernel", "ramdisk", "dtb", "out"):
        parser.add_argument("--" + name, required=True, type=Path)
    for name in ("kernel-sha", "ramdisk-sha", "dtb-sha", "init-sha"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    for path in (args.base, args.kernel, args.ramdisk, args.dtb):
        if not path.is_file():
            raise ValueError("required input is not a regular file: " + str(path))
    base = args.base.read_bytes()
    check_pin("known-good on-device K34 BOOT", base, SHA_K34_GOLDEN_BOOT)
    kernel = args.kernel.read_bytes()
    ram = args.ramdisk.read_bytes()
    dtb = args.dtb.read_bytes()
    check_pin("kernel", kernel, args.kernel_sha)
    check_pin("native initramfs", ram, args.ramdisk_sha)
    check_pin("Linux 6.1 AS99 DTB", dtb, args.dtb_sha)
    verified = verify_initramfs(args.ramdisk)
    if verified["init_sha256"] != args.init_sha.lower():
        raise ValueError("native PID1 SHA256 mismatch")
    image, report = pack(base, kernel, ram, dtb, verified["init_sha256"])
    path = args.out
    manifest = path.with_suffix(".json")
    if path.exists() or manifest.exists():
        raise ValueError("refuse to replace existing staged BOOT or manifest")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as output:
        output.write(image)
    report["created_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        with manifest.open("x", encoding="utf-8") as output:
            json.dump(report, output, indent=2)
            output.write("\n")
    except Exception:
        path.unlink(missing_ok=True)
        raise
    print(json.dumps(report, indent=2))
    print("C12_OFFLINE_QCDT_BOOT_IMAGE_PACK_AND_VERIFY_PASS_NO_PHONE_IO")


if __name__ == "__main__":
    main()
