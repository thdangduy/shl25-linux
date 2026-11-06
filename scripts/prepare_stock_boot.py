#!/usr/bin/env python3
"""Prepare original A51w ARM zImage and QCDT v3 from OTA A.17 via byte range.
Never reads or writes the phone. Validates ZIP CRC32 + fixed OEM boot hashes.
"""
import hashlib, pathlib, subprocess, struct, zlib
URL="https://downloads.oppo.com.s3.amazonaws.com/firmware/A51w/Mirror5EX_11_OTA_017_all_201610281415.zip"
BOOT_SHA="36befcf242bf04d45c2bbff5b93976288aa3dfe2e1bfb7edca0abd5920fe258b"
KERNEL_SHA="163d25276cb4bb264d58a342a1853b552fd50a0c3425e544a8f65a270572fce4"
QCDT_SHA="c740b0433fa07b3c9c7aa1ea153bb2b2a629d595f3cd7f8f6f7793c5bd79f79d"
start=54120591
compressed=8310720
out=pathlib.Path("device/oppo/a51w/prebuilt")
out.mkdir(parents=True,exist_ok=True)
temp=out/"stock_boot.zip_part"
subprocess.run(["curl","-k","--fail","-L","--retry","4","--connect-timeout","15",
 "--max-time","180","-sS","--range",f"{start}-{start+38+compressed-1}",
 "--output",str(temp),URL],check=True)
data=temp.read_bytes()
h=struct.unpack_from("<I5H3I2H",data,0)
assert h[0]==0x04034b50 and h[3]==8 and h[9]==8
assert data[30:38]==b"boot.img"
payload=data[38:38+compressed]
assert len(payload)==compressed
boot=zlib.decompress(payload,-15)
assert len(boot)==9674024 and zlib.crc32(boot)&0xffffffff==517980753
assert hashlib.sha256(boot).hexdigest()==BOOT_SHA
assert boot[:8]==b"ANDROID!"
ksz,kaddr,rsz,raddr,ssz,saddr,tags,page,dt_len=struct.unpack_from("<9I",boot,8)
assert (ksz,kaddr,rsz,raddr,tags,page,dt_len)==(7148840,0x80008000,832378,0x81000000,0x80000100,2048,1687552)
align=lambda x:(x+page-1)//page*page
kernel=boot[page:page+ksz]
dtoff=page+align(ksz)+align(rsz)+align(ssz)
dt=boot[dtoff:dtoff+dt_len]
assert kernel[0x24:0x28]==bytes.fromhex("18286f01") # ARM zImage magic
assert dt[:4]==b"QCDT" and dt[4:8]==bytes.fromhex("03000000")
assert hashlib.sha256(kernel).hexdigest()==KERNEL_SHA
assert hashlib.sha256(dt).hexdigest()==QCDT_SHA
(out/"kernel").write_bytes(kernel)
(out/"dt.img").write_bytes(dt)
temp.unlink()
print("A51W_OTA_A17_KERNEL_QCDT_HASH_PASS",len(kernel),len(dt),flush=True)
