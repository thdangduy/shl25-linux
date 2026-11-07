#!/usr/bin/env python3
"""SHL25 AS99 BDIC-over-CLMR firmware command queue: offline test only.

Sharp GPL shdisp_lcdc/shdisp_system.[ch] proof. No I2C transactions,
SPI activity, voltage changes, kernel device binding or flash images.
"""
import argparse
import hashlib
from pathlib import Path

HEADER_SHA = "490f3d0f8a6b1763cb888edb95b7d96f89cb102977092e54c86a7c6a044169b2"
SYSTEM_SHA = "985c833167b4ae4863dddfaad805ded68e94195b60496f6472d2a9b90165f21f"
BDIC_WIRE_ADDR = 0xA8  # 8-bit Sharp firmware payload; 7-bit I2C address = 0x54
FWCMD_I2C_WRITE = 0x50
FWCMD_I2C_MASK_WRITE = 0x51
FWCMD_I2C_MULTI_WRITE = 0x52
FWCMD_I2C_READ = 0x54
FWCMD_APINO_BKL = 0x30
FWCMD_APINO_PROX = 0x50
MAX_QUEUE_BYTES = 6144
MAX_MULTI_BYTES = 20

class OfflineFirmwareQueue:
    def __init__(self, api: int):
        if api not in (FWCMD_APINO_BKL, FWCMD_APINO_PROX):
            raise ValueError("unverified firmware API class")
        self.api = api
        self.count = 1
        self.buf = bytearray()
        self.last_cmd_flag_offset = None
        self.finished = False

    def add(self, opcode: int, payload: bytes):
        if self.finished:
            raise ValueError("already finalized")
        if opcode not in (FWCMD_I2C_WRITE, FWCMD_I2C_MASK_WRITE,
                          FWCMD_I2C_MULTI_WRITE, FWCMD_I2C_READ):
            raise ValueError("unknown CLMR I2C opcode")
        if not 0 <= len(payload) <= 65535:
            raise ValueError("invalid CLMR payload length")
        if len(self.buf) + len(payload) + 4 + 17 > MAX_QUEUE_BYTES:
            raise ValueError("CLMR buffer limit")
        self.last_cmd_flag_offset = len(self.buf) + 1
        self.buf.extend((opcode, (self.api + self.count) & 0x7f))
        self.buf.extend(len(payload).to_bytes(2, "little"))
        self.buf.extend(payload)
        self.count = (self.count % 15) + 1

    def bdic_write(self, register: int, value: int):
        self.add(FWCMD_I2C_WRITE, bytes((BDIC_WIRE_ADDR, u8(register), u8(value))))

    def bdic_mask_write(self, register: int, mask: int, value: int):
        self.add(FWCMD_I2C_MASK_WRITE,
                 bytes((BDIC_WIRE_ADDR, u8(register), u8(mask), u8(value))))

    def bdic_read(self, register: int):
        self.add(FWCMD_I2C_READ, bytes((BDIC_WIRE_ADDR, u8(register))))

    def bdic_multi_write(self, register: int, values: bytes):
        if not 1 <= len(values) <= MAX_MULTI_BYTES:
            raise ValueError("OEM multi-write length must be 1..20")
        self.add(FWCMD_I2C_MULTI_WRITE,
                 bytes((BDIC_WIRE_ADDR, u8(register))) + values)

    def finish(self, notice: bool = True) -> bytes:
        if self.finished or not self.buf:
            raise ValueError("empty or already finalized")
        self.finished = True
        # OEM shdisp_FWCMD_buf_finish uses ((pos+1)^0x0f)&0x0f.
        padding = ((len(self.buf) + 1) ^ 0x0f) & 0x0f
        self.buf.extend((0xfe, 0x0f))
        self.buf.extend(bytes((0xff,)) * padding)
        if len(self.buf) > MAX_QUEUE_BYTES:
            raise ValueError("CLMR queue exceeds scratch buffer")
        if notice:
            assert self.last_cmd_flag_offset is not None
            self.buf[self.last_cmd_flag_offset] |= 0x80
        assert len(self.buf) % 16 == 0
        return bytes(self.buf)

def u8(n: int) -> int:
    if not isinstance(n, int) or not 0 <= n <= 255:
        raise ValueError("not an 8-bit register/data value")
    return n

def verify():
    q = OfflineFirmwareQueue(FWCMD_APINO_PROX)
    q.bdic_write(0x12,0x34)
    frame=q.finish()
    assert frame.hex()=="50d10300a81234fe0f"+"ff"*7
    q=OfflineFirmwareQueue(FWCMD_APINO_BKL)
    q.bdic_mask_write(0x80,0x0f,0x09)
    frame=q.finish()
    assert frame[:8].hex()=="51b10400a8800f09"
    assert len(frame)==16
    q=OfflineFirmwareQueue(FWCMD_APINO_BKL)
    q.bdic_multi_write(0x18,bytes((1,2,3)))
    frame=q.finish()
    assert frame[:9].hex()=="52b10500a818010203"
    q=OfflineFirmwareQueue(FWCMD_APINO_PROX)
    q.bdic_read(0x4a)
    frame=q.finish()
    assert frame[:6].hex()=="54d10200a84a"
    q=OfflineFirmwareQueue(FWCMD_APINO_BKL)
    q.bdic_write(0x10,0x20)
    q.bdic_write(0x11,0x21)
    frame=q.finish()
    assert frame[1] == 0x31 and frame[8] == 0xb2
    assert len(frame)==16
    q=OfflineFirmwareQueue(FWCMD_APINO_BKL)
    for i in range(15):
        q.bdic_write(i,i)
    frame=q.finish()
    assert frame[1]==0x31
    assert frame[14*7+1] & 0x7f == 0x3f
    for bad in (0,21):
        try:
            OfflineFirmwareQueue(FWCMD_APINO_BKL).bdic_multi_write(0x01,bytes(bad))
        except ValueError:
            pass
        else:
            raise AssertionError("accepted invalid multi-write length")
    # BDIC operations depend on the already-booted Sharp CLMR firmware.
    # No direct i2c_msg is synthesized by this script.
    print("SHL25_AS99_BDIC_FWCMD_QUEUE_VECTOR_PASS slave8=0xA8 slave7=0x54")
    print("SHL25_AS99_BDIC_CLMR_FIRMWARE_DEPENDENCY_GATED_PASS")

def verify_oem(header: Path | None, source: Path | None):
    if header is not None:
        blob=header.read_bytes()
        assert hashlib.sha256(blob).hexdigest()==HEADER_SHA
        txt=blob.decode("utf-8",errors="replace")
        for name,val in (("I2C_1BYTE_WRITE","0x50"),("I2C_1BYTE_MASK_WRITE","0x51"),
                         ("I2C_MULTI_WRITE","0x52"),("I2C_1BYTE_READ","0x54")):
            assert "SHDISP_CLMR_FWCMD_"+name in txt and val in txt
        assert "SHDISP_CLMR_BDIC_SLAVE_ADDR ( 0xA8 )" in txt
        print("SHL25_AS99_BDIC_FWCMD_HEADER_HASH_PASS")
    if source is not None:
        blob=source.read_bytes()
        assert hashlib.sha256(blob).hexdigest()==SYSTEM_SHA
        txt=blob.decode("utf-8",errors="replace")
        for token in ("shdisp_FWCMD_buf_add(", "shdisp_FWCMD_buf_finish(",
                      "shdisp_FWCMD_doKick(", "shdisp_SYS_clmr_sio_eDram_transfer(",
                      "SHDISP_CLMR_FWCMD_I2C_1BYTE_WRITE"):
            assert token in txt
        print("SHL25_AS99_BDIC_FWCMD_SOURCE_HASH_PASS")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--oem-header",type=Path)
    p.add_argument("--oem-source",type=Path)
    a=p.parse_args()
    verify()
    verify_oem(a.oem_header,a.oem_source)
