#!/usr/bin/env python3
"""Offline Sharp AS99 CLMR eDRAM SPI stream regression (NO hardware I/O).

Derived from Sharp GPL bld010105, shdisp_lcdc/shdisp_system.c:
shdisp_SYS_clmr_sio_eDram_transfer(), and shdisp_clmr_fw.h.
Frames are not flashed, transported or embedded into Linux images.
"""
import argparse
import hashlib
from pathlib import Path

SOURCE_SHA256 = "985c833167b4ae4863dddfaad805ded68e94195b60496f6472d2a9b90165f21f"
FIRMWARE_SHA256 = "a3da76d0bbc1154a774e097bfd851026cde7a09c3983ea9315181835510145f5"
FW_BLOCKS = 3696
FW_BLOCK_BYTES = 16
FIRMWARE_BYTES = FW_BLOCKS * FW_BLOCK_BYTES
EDRAM_BASE = 0x7CE0
SPI_BUFFER_BYTES = 16 * 16 * 24
HEADER_RESERVED_BYTES = 4
TRANSFER_BLOCK_BYTES = 16
MAX_PAYLOAD = ((SPI_BUFFER_BYTES - HEADER_RESERVED_BYTES) // TRANSFER_BLOCK_BYTES) * TRANSFER_BLOCK_BYTES

def packetize(payload: bytes, mode: int = 0):
    """Offline-only byte vectors, not authorization for hardware transfer.

    OEM copies data starting at position 1, but transfers 4 + N bytes.
    Three trailing bytes are conservatively set to zero for deterministic
    fixtures; actual board protocol still requires vendor and hardware study.
    """
    if mode not in (0, 2):
        raise ValueError("unsupported eDRAM write mode")
    if not payload or len(payload) % FW_BLOCK_BYTES:
        raise ValueError("firmware must be nonempty and 16-byte aligned")
    result = []
    for start in range(0, len(payload), MAX_PAYLOAD):
        chunk = payload[start:start + MAX_PAYLOAD]
        opcode = 0xC7 if mode == 0 and start == 0 else 0xC8
        result.append(bytes((opcode,)) + chunk + bytes(3))
    return result

def verify():
    assert MAX_PAYLOAD == 6128
    assert SPI_BUFFER_BYTES == 6144
    assert FIRMWARE_BYTES == 59136
    assert EDRAM_BASE == 0x7CE0
    lengths = (16, MAX_PAYLOAD, MAX_PAYLOAD + 16, FIRMWARE_BYTES)
    for n in lengths:
        sample = bytes((i * 17 + 3) & 255 for i in range(n))
        for mode in (0, 2):
            frames = packetize(sample, mode)
            assert len(frames) == (n + MAX_PAYLOAD - 1) // MAX_PAYLOAD
            assert frames[0][0] == (0xC7 if mode == 0 else 0xC8)
            assert all(f[0] == 0xC8 for f in frames[1:])
            assert all(HEADER_RESERVED_BYTES + 16 <= len(f) <= SPI_BUFFER_BYTES for f in frames)
            assert all(f[-3:] == bytes(3) for f in frames)
            assert b"".join(f[1:-3] for f in frames) == sample
    image = bytes((i * 17 + 3) & 255 for i in range(FIRMWARE_BYTES))
    frames = packetize(image)
    assert len(frames) == 10 and len(frames[-1]) == 3988
    assert packetize(bytes(16), mode=2)[0][0] == 0xC8
    for bad in (b"", bytes(1), bytes(15), bytes(17)):
        try:
            packetize(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("accepted unaligned/empty image")
    try:
        packetize(bytes(16), mode=1)
    except ValueError:
        pass
    else:
        raise AssertionError("accepted read opcode as write mode")
    print("SHL25_AS99_CLMR_FW_EDRAM_PACKET_VECTOR_PASS size=59136 frames=10 max_payload=6128")
    print("SHL25_AS99_CLMR_FW_NO_OEM_BINARY_IN_CI_PASS")

def check_oem(source_path: Path | None, firmware_path: Path | None):
    if source_path is not None:
        raw=source_path.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==SOURCE_SHA256,"OEM shdisp_system.c SHA changed"
        txt=raw.decode("utf-8",errors="replace")
        for token in ("int cmdSize = 4;", "int blockSize = 16;",
                      "((i == 0) && (mode == 0)) ? 0xC7 : 0xC8",
                      "spi_transfer_buf + 1"):
            assert token in txt, "OEM protocol expression missing "+token
        print("SHL25_AS99_CLMR_OEM_EDRAM_SOURCE_HASH_PASS")
    if firmware_path is not None:
        raw=firmware_path.read_bytes()
        assert len(raw)==FIRMWARE_BYTES,"OEM CLMR firmware length mismatch"
        assert hashlib.sha256(raw).hexdigest()==FIRMWARE_SHA256,"OEM CLMR firmware SHA mismatch"
        frames=packetize(raw)
        assert b"".join(f[1:-3] for f in frames)==raw
        print("SHL25_AS99_CLMR_OEM_FW_SHA_AND_PACKETIZATION_PASS",len(frames))

if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--oem-source",type=Path)
    p.add_argument("--oem-firmware",type=Path)
    a=p.parse_args()
    verify()
    check_oem(a.oem_source,a.oem_firmware)
