#!/usr/bin/env python3
"""Package a NEW Sharp 3.4 zImage + known-native initramfs into the original
Sharp SHL25 Android BOOT container, entirely offline.

Retains the original Sharp QCDT and boot addresses. Requires pinned input
SHA256 and a verified ARM zImage magic. No USB, ADB, block I/O or flashing.
Not proof the kernel boots or USB ACM works on hardware.
"""
import argparse
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import struct

from pack_k34_native_boot import BASE_SHA, BASE_BYTES, MSMS, check_cpio, sha, align

OEM_QCDT_SHA = "a71dcb36c829378ec43dc334234a0a892ef224bade3ff2d7100857c0687150bc"
ARM_ZIMAGE_MAGIC = 0x016F2818

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, type=Path)
    ap.add_argument("--kernel", required=True, type=Path)
    ap.add_argument("--kernel-sha", required=True)
    ap.add_argument("--ramdisk", required=True, type=Path)
    ap.add_argument("--ramdisk-sha", required=True)
    ap.add_argument("--init-sha", required=True)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    manifest_path = args.out.with_suffix(".json")
    if args.out.exists() or manifest_path.exists():
        raise SystemExit("REFUSE_EXISTING_OUTPUT")
    for expected in (args.kernel_sha, args.ramdisk_sha, args.init_sha):
        if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected.lower()):
            raise SystemExit("UNPINNED_INPUT_SHA256")
    base = args.base.read_bytes()
    zimage = args.kernel.read_bytes()
    ramdisk = args.ramdisk.read_bytes()
    if len(base) != BASE_BYTES or sha(base) != BASE_SHA or base[:8] != b"ANDROID!":
        raise ValueError("UNEXPECTED_SHARP_BASE_BOOT")
    if sha(zimage) != args.kernel_sha.lower():
        raise ValueError("NEW_KERNEL_SHA256_MISMATCH")
    if sha(ramdisk) != args.ramdisk_sha.lower():
        raise ValueError("RAMDISK_SHA256_MISMATCH")
    if len(zimage) < 4_000_000 or len(zimage) > 11_000_000 or \
       struct.unpack_from("<I", zimage, 0x24)[0] != ARM_ZIMAGE_MAGIC:
        raise ValueError("NEW_KERNEL_NOT_EXPECTED_ARM_ZIMAGE")
    plain = gzip.decompress(ramdisk)
    members = check_cpio(plain, args.init_sha.lower())
    if b"SHL25_NATIVE_PID1_START" not in plain:
        raise ValueError("NATIVE_PID1_SIGNATURE_MISSING")
    old_k, kaddr, old_ram, raddr, secs, saddr, tags, page, dtsz, unused = \
        struct.unpack_from("<10I", base, 8)
    if page != 2048 or secs != 0 or old_k < 7_000_000:
        raise ValueError("LEGACY_BOOT_HEADER_MISMATCH")
    old_kernel = base[page:page + old_k]
    if struct.unpack_from("<I", old_kernel, 0x24)[0] != ARM_ZIMAGE_MAGIC:
        raise ValueError("BASE_KERNEL_IS_NOT_ARM_ZIMAGE")
    old_dtoff = page + align(old_k, page) + align(old_ram, page)
    dt = base[old_dtoff:old_dtoff + dtsz]
    if sha(dt) != OEM_QCDT_SHA:
        raise ValueError("ORIGINAL_SHARP_QCDT_SHA_MISMATCH")
    magic, version, count = struct.unpack_from("<4sII", dt)
    if (magic, version, count) != (b"QCDT", 2, 8):
        raise ValueError("UNKNOWN_QCDT")
    entries = [struct.unpack_from("<6I", dt, 12 + i*24) for i in range(count)]
    if tuple(x[0] for x in entries) != MSMS or any(x[1] != 50 for x in entries):
        raise ValueError("UNKNOWN_BOARD_SELECTOR")
    cmd = base[64:576].split(b"\x00",1)[0]
    if b"init=/init" not in cmd:
        raise ValueError("BOOT_CMDLINE_NOT_NATIVE")
    hdr = bytearray(base[:page])
    struct.pack_into("<I", hdr, 8, len(zimage))
    struct.pack_into("<I", hdr, 16, len(ramdisk))
    h = hashlib.sha1()
    for item in (zimage, ramdisk, b"", dt):
        h.update(item)
        h.update(struct.pack("<I", len(item)))
    hdr[576:608] = h.digest() + b"\x00" * 12
    pad = lambda part: part + b"\x00" * (align(len(part), page) - len(part))
    payload = bytes(hdr) + pad(zimage) + pad(ramdisk) + pad(dt)
    if len(payload) > BASE_BYTES:
        raise ValueError(f"SHL25_BOOT_PARTITION_OVERFLOW bytes={len(payload)}")
    image = payload + b"\x00" * (BASE_BYTES - len(payload))
    new_k, _, new_r, _, _, _, _, new_pg, new_dt, _ = struct.unpack_from("<10I", image, 8)
    if (new_k, new_r, new_pg, new_dt) != (len(zimage),len(ramdisk),page,dtsz):
        raise ValueError("BOOT_SECTION_HEADER_ROUNDTRIP_FAIL")
    out_k = image[page:page+new_k]
    out_rstart = page+align(new_k,page)
    out_r = image[out_rstart:out_rstart+new_r]
    out_dtstart = out_rstart + align(new_r,page)
    out_dt = image[out_dtstart:out_dtstart+dtsz]
    if out_k != zimage or out_r != ramdisk or out_dt != dt:
        raise ValueError("BOOT_SECTION_PAYLOAD_ROUNDTRIP_FAIL")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(image)
    manifest = {
        "status":"OFFLINE_PACKED_NO_BOOT_TEST_NO_FLASH",
        "created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "image_sha256":sha(image), "bytes":len(image),
        "source_base_boot_sha256":BASE_SHA,
        "old_kernel_sha256":sha(old_kernel),
        "new_kernel_sha256":sha(zimage),
        "original_qcdt_sha256":sha(dt),
        "native_initramfs_sha256":sha(ramdisk),
        "native_pid1_sha256":args.init_sha.lower(),
        "cpio_entry_count":len(members),
        "kernel_load_address":hex(kaddr),
        "ramdisk_load_address":hex(raddr),
        "cmdline":cmd.decode("ascii","replace"),
        "boot_partition":"mmcblk0p13 - NOT WRITTEN",
        "recovery_partition":"mmcblk0p14 - NEVER MODIFIED",
        "verification":"hash pin, ARM zImage magic, QCDT byte identity, all section roundtrip",
        "limitations":"cannot prove USB, DSI, touch, QCDT bootloader compatibility or native PID1 runtime"
    }
    manifest_path.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf8")
    print(json.dumps(manifest,indent=2))
if __name__=="__main__": main()
