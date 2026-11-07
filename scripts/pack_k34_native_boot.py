#!/usr/bin/env python3
"""Offline-only Sharp SHL25 3.4 native BOOT packer.

Kernel/QCDT come bit-for-bit from verified K34 control BOOT. Replaces ONLY
the RAMDISK section with a hash-pinned native ARMHF PID1 CPIO.gz. Never uses
ADB, USB, fastboot, block devices, or phone partition I/O.
"""
import argparse
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import stat
import struct

BASE_SHA="adf071e680e4373277cb2bdf8fe0f38ef215bccaf24f7def97f8fb31dbf44b8e"
BASE_BYTES=17_825_792
MSMS=(208,209,211,212,214,215,217,218)
sha=lambda x:hashlib.sha256(x).hexdigest()
def align(n,unit):return ((n+unit-1)//unit)*unit

def check_cpio(raw,expected_init_sha):
    if not raw.startswith(b"070701"):raise ValueError("not newc initramfs")
    p=0
    contents={}
    while p+110<=len(raw):
        if raw[p:p+6]!=b"070701":raise ValueError(f"bad newc magic at {p}")
        vals=[int(raw[p+6+i*8:p+14+i*8],16) for i in range(13)]
        _,mode,uid,gid,_,_,size,_,_,rmaj,rmin,nsize,_=vals
        p+=110
        if not 1<=nsize<=4096:raise ValueError("bad cpio name size")
        name=raw[p:p+nsize-1].decode("utf8","strict")
        if name.startswith("./"):name=name[2:]
        if raw[p+nsize-1]!=0:raise ValueError("missing newc name terminator")
        p=align(p+nsize,4)
        if name=="TRAILER!!!":break
        if name.startswith("/") or ".." in Path(name).parts or name in contents:
            raise ValueError("unsafe/duplicate cpio path: "+name)
        data=raw[p:p+size]
        if len(data)!=size:raise ValueError("truncated cpio")
        p=align(p+size,4)
        contents[name]={"mode":mode,"uid":uid,"gid":gid,"sha256":sha(data),
                        "rdev_major":rmaj,"rdev_minor":rmin}
        if uid!=0 or gid!=0:raise ValueError("cpio node not root-owned: "+name)
    else:raise ValueError("missing cpio trailer")
    if "init" not in contents or not stat.S_ISREG(contents["init"]["mode"]):
        raise ValueError("missing executable regular /init")
    if not contents["init"]["mode"] & 0o111:raise ValueError("init not executable")
    if contents["init"]["sha256"]!=expected_init_sha:
        raise ValueError("init SHA differs from signed CI")
    for node,major,minor in (("dev/console",5,1),("dev/null",1,3),("dev/kmsg",1,11)):
        f=contents.get(node)
        if not f or not stat.S_ISCHR(f["mode"]) or (f["rdev_major"],f["rdev_minor"])!=(major,minor):
            raise ValueError("required char node absent or incorrect: "+node)
    return contents

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--base",required=True,type=Path)
    ap.add_argument("--ramdisk",required=True,type=Path)
    ap.add_argument("--ramdisk-sha",required=True)
    ap.add_argument("--init-sha",required=True)
    ap.add_argument("--out",required=True,type=Path)
    args=ap.parse_args()
    report=args.out.with_suffix(".json")
    if args.out.exists() or report.exists():raise SystemExit("refuse overwrite")
    if not all(len(x)==64 for x in (args.ramdisk_sha,args.init_sha)):
        raise ValueError("SHA256 inputs required")
    base=args.base.read_bytes()
    ram=args.ramdisk.read_bytes()
    if len(base)!=BASE_BYTES or sha(base)!=BASE_SHA or base[:8]!=b"ANDROID!":
        raise ValueError("K34 control image invalid or changed")
    if sha(ram)!=args.ramdisk_sha.lower():raise ValueError("RAMDISK_SHA_MISMATCH")
    cp=check_cpio(gzip.decompress(ram),args.init_sha.lower())
    if b"SHL25_NATIVE_PID1_START" not in gzip.decompress(ram):
        raise ValueError("not expected native kernel init binary")
    ksz,ka,rsz,ra,ssz,sa,ta,pg,dsz,_=struct.unpack_from("<10I",base,8)
    if pg!=2048 or ssz!=0 or ksz<7_000_000:raise ValueError("bad legacy boot header")
    kern=base[pg:pg+ksz]
    dtoff=pg+align(ksz,pg)+align(rsz,pg)
    dt=base[dtoff:dtoff+dsz]
    magic,ver,count=struct.unpack_from("<4sII",dt,0)
    if (magic,ver,count)!=(b"QCDT",2,8):raise ValueError("wrong Sharp QCDT")
    entries=[struct.unpack_from("<6I",dt,12+24*i) for i in range(count)]
    if tuple(x[0] for x in entries)!=MSMS or any(x[1]!=50 for x in entries):
        raise ValueError("unexpected MSM/board selector")
    cmd=base[64:576].split(b"\0",1)[0]
    if b"init=/init" not in cmd:raise ValueError("not expected K34 control init cmdline")
    header=bytearray(base[:pg])
    struct.pack_into("<I",header,16,len(ram))
    h=hashlib.sha1()
    for part in (kern,ram,b"",dt):
        h.update(part);h.update(struct.pack("<I",len(part)))
    header[576:608]=h.digest()+b"\0"*12
    pad=lambda x:x+b"\0"*(align(len(x),pg)-len(x))
    active=bytes(header)+pad(kern)+pad(ram)+pad(dt)
    if len(active)>BASE_BYTES:raise ValueError("image overflow")
    image=active+b"\0"*(BASE_BYTES-len(active))
    # Full roundtrip sections and QCDT table identity.
    if image[pg:pg+ksz]!=kern:raise ValueError("kernel changed")
    roff=pg+align(ksz,pg)
    if image[roff:roff+len(ram)]!=ram:raise ValueError("ramdisk differs")
    doff=roff+align(len(ram),pg)
    if image[doff:doff+len(dt)]!=dt:raise ValueError("QCDT changed")
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_bytes(image)
    manifest={
        "status":"OFFLINE_ONLY_NOT_BOOT_TESTED",
        "created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "target":"Sharp SHL25/AS99 native Linux 3.4 experimental",
        "sha256":sha(image),"bytes":len(image),"kernel_sha256":sha(kern),
        "original_qcdt_sha256":sha(dt),"native_ramdisk_sha256":sha(ram),
        "native_init_sha256":args.init_sha.lower(),
        "cpio_file_count":len(cp),
        "base_k34_control_sha256":BASE_SHA,
        "qcdt_msm_ids":MSMS,"qcdt_board_id":50,
        "kernel_load_addr":hex(ka),"ramdisk_load_addr":hex(ra),
        "cmdline":cmd.decode("ascii","replace"),
        "boot_partition":"mmcblk0p13 (NEVER WRITTEN BY PACKER)",
        "recovery_partition":"mmcblk0p14 (UNTOUCHED)",
        "usb_console":"Sharp vendor modem CDC-ACM, NOT HARDWARE PROVEN",
    }
    report.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf8")
    print(json.dumps(manifest,indent=2))

if __name__=="__main__":main()
