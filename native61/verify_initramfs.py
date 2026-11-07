#!/usr/bin/env python3
"""Fail-closed validation of the SHL25 Linux 6.1 ARMHF newc initramfs.

Tests an *archive* generated on a build host. Does not run code inside it,
read phone storage, mount partitions or access any physical hardware.
"""
import argparse
import gzip
import hashlib
import pathlib
import stat


def align4(num):
    return (num + 3) & ~3


def verify(path: pathlib.Path) -> dict:
    data = gzip.decompress(path.read_bytes())
    if not data.startswith(b"070701"):
        raise ValueError("not a Linux newc archive")
    pos = 0
    files = {}
    found_trailer = False
    while pos + 110 <= len(data):
        if data[pos:pos + 6] not in (b"070701",):
            raise ValueError("unexpected cpio header at offset %d" % pos)
        raw_fields = data[pos + 6:pos + 110]
        vals = [int(raw_fields[i:i + 8], 16) for i in range(0, 104, 8)]
        ino, mode, uid, gid, nlink, mtime, filesize, devmajor, devminor, rdevmajor, rdevminor, namesize, check = vals
        pos += 110
        if namesize < 1 or namesize > 4096:
            raise ValueError("unsafe cpio name size")
        name_end = pos + namesize
        if name_end > len(data) or data[name_end - 1] != 0:
            raise ValueError("unterminated cpio name")
        name = data[pos:name_end - 1].decode("utf-8")
        pos = align4(name_end)
        if name == "TRAILER!!!":
            found_trailer = True
            break
        if name.startswith("./"):
            name = name[2:]
        if not name or name.startswith("/") or ".." in pathlib.PurePosixPath(name).parts:
            raise ValueError("unsafe path %r" % name)
        if name in files:
            raise ValueError("duplicate cpio path %r" % name)
        if uid or gid:
            raise ValueError("nonroot archive entry %r" % name)
        end = pos + filesize
        if end > len(data):
            raise ValueError("truncated file data")
        content = data[pos:end]
        pos = align4(end)
        files[name] = dict(
            mode=mode, uid=uid, gid=gid, rdevmajor=rdevmajor,
            rdevminor=rdevminor, content=content,
        )
        if len(files) > 10000:
            raise ValueError("archive entry limit exceeded")
    if not found_trailer:
        raise ValueError("missing newc trailer")

    def require_char(name, major, minor):
        f = files.get(name)
        if not f or not stat.S_ISCHR(f["mode"]):
            raise ValueError("required character device missing: " + name)
        if (f["rdevmajor"], f["rdevminor"]) != (major, minor):
            raise ValueError("wrong devt for " + name)

    require_char("dev/console", 5, 1)
    require_char("dev/null", 1, 3)
    require_char("dev/kmsg", 1, 11)
    init = files.get("init")
    if not init or not stat.S_ISREG(init["mode"]) or not (init["mode"] & 0o111):
        raise ValueError("missing executable /init")
    if not init["content"].startswith(b"#!/bin/sh"):
        raise ValueError("unexpected /init interpreter")
    if b"SHL25_LINUX61_NATIVE_PID1_STARTED" not in init["content"]:
        raise ValueError("wrong SHL25 PID1 signature")
    if b"SHL25_DEVICE_RAM_ONLY_NO_FLASH" not in init["content"]:
        raise ValueError("RAM-only guarantee marker absent")
    busy = files.get("bin/busybox")
    if not busy or not stat.S_ISREG(busy["mode"]) or not (busy["mode"] & 0o111):
        raise ValueError("missing executable BusyBox")
    if not busy["content"].startswith(b"\x7fELF"):
        raise ValueError("BusyBox not ELF")
    if busy["content"][4] != 1 or int.from_bytes(busy["content"][18:20], "little") != 40:
        raise ValueError("BusyBox not ARMHF 32-bit ELF")
    for name in ("bin/sh", "bin/setsid", "bin/mount"):
        f = files.get(name)
        if not f or not stat.S_ISLNK(f["mode"]):
            raise ValueError("missing BusyBox applet symlink: " + name)
        if f["content"] != b"busybox":
            raise ValueError("unexpected symlink target: " + name)
    return {
        "init_sha256": hashlib.sha256(init["content"]).hexdigest(),
        "busybox_sha256": hashlib.sha256(busy["content"]).hexdigest(),
        "entries": len(files),
        "status": "SHL25_LINUX61_C11_ARMHF_PID1_CONSOLE_NODES_PASS",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=pathlib.Path)
    args = parser.parse_args()
    out = verify(args.archive)
    for name, val in out.items():
        print(name, val)


if __name__ == "__main__":
    main()
