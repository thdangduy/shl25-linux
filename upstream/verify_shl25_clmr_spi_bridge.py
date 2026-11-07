#!/usr/bin/env python3
"""Offline C6 Sharp AS99 CLMR ROM SPI, firmware loader & safety checks.

This is NOT a device SPI test. The C6 transport object is built into
Linux 6.1 but it has no registered probe caller or power/IRQ adapter.
"""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parent.parent
SOURCE=(ROOT/"drivers/spi/shl25-as99-clmr-spi-bridge.c").read_text(encoding="utf-8")
HEADER=(ROOT/"drivers/spi/shl25-as99-clmr-spi-bridge.h").read_text(encoding="utf-8")
DTS=(ROOT/"dts/shl25-as99-peripherals.dtsi").read_text(encoding="utf-8")
SPI=(ROOT/"drivers/spi/spi-shl25-as99-clmr.c").read_text(encoding="utf-8")
BOOT=(ROOT/"drivers/spi/shl25-as99-clmr-boot.c").read_text(encoding="utf-8")

expected={
    "SHL25_CLMR_SPI_WRITE_HZ": 50000000,
    "SHL25_CLMR_SPI_READ_HZ": 20000000,
    "SHL25_CLMR_SPI_FRAME_MAX": 6144,
    "SHL25_CLMR_SPI_FRAME_OVERHEAD": 4,
    "SHL25_CLMR_SPI_FW_PAYLOAD": 6128,
    "SHL25_CLMR_SPI_FW_BLOCK":16,
    "SHL25_CLMR_OP_REG_WRITE":0xc0,
    "SHL25_CLMR_OP_REG_SELECT":0xc2,
    "SHL25_CLMR_OP_REG_FETCH":0xc4,
    "SHL25_CLMR_OP_FW_BEGIN":0xc7,
    "SHL25_CLMR_OP_FW_CONT":0xc8,
}
for name,value in expected.items():
    pattern=r"^\s*#define\s+"+name+r"\s+(0x[0-9a-fA-F]+|\d+)U?\b"
    m=re.search(pattern,SOURCE,re.M)
    assert m is not None,(name,"not found")
    assert int(m.group(1),0)==value,(name,m.group(1),value)

# The OEM stores register data as BE32: boot input HOSTAEY=3695.
def reg_write(reg,value):
    return b"\xc0"+reg.to_bytes(2,"big")+value.to_bytes(4,"big")
assert reg_write(0x0e14,3695).hex()=="c00e1400000e6f"
assert reg_write(0x1800,0x13).hex()=="c0180000000013"
assert "put_unaligned_be16(reg, frame + 1)" in SOURCE
assert "put_unaligned_be32(value, frame + 3)" in SOURCE
assert "get_unaligned_be32(reply + 1)" in SOURCE
assert "transfer.cs_change = 1;" in SOURCE
assert SOURCE.count("spi_sync_transfer(bridge->spi, &transfer, 1)")>=4
assert SOURCE.count("mutex_lock(&bridge->lock)")>=3
assert SOURCE.count("mutex_unlock(&bridge->lock)")>=3
assert "put_unaligned_le32" not in SOURCE

# The OEM eDRAM write uses a reserved 4-byte frame overhead; the
# three trailer bytes are deterministic 0 here pending device proof.
fw=bytes(i%256 for i in range(59136))
vectors=[]
for start in range(0,len(fw),6128):
    chunk=fw[start:start+6128]
    opcode=0xc7 if not start else 0xc8
    vectors.append(bytes([opcode])+chunk+bytes(3))
assert len(vectors)==10
assert len(vectors[-1])==3988
assert len(vectors[0])==6132
assert all(v[-3:]==bytes(3) for v in vectors)
assert b"".join(v[1:-3] for v in vectors)==fw
assert "frame[0] = start ? SHL25_CLMR_OP_FW_CONT :" in SOURCE
assert "SHL25_CLMR_OP_FW_BEGIN;" in SOURCE
assert "memcpy(frame + 1, fw + start, chunk)" in SOURCE
assert "transfer.len = chunk + SHL25_CLMR_SPI_FRAME_OVERHEAD;" in SOURCE
assert "memset(frame, 0, chunk + SHL25_CLMR_SPI_FRAME_OVERHEAD)" in SOURCE
assert "if (ret)\n\t\t\tbreak;" in SOURCE

# The only loader entry point must validate board gates BEFORE requesting
# firmware and C3 must SHA256-check before dispatching a single callback.
entry=SOURCE.split("int shl25_as99_clmr_bridge_boot(",1)[1]
for guard in ("!prereqs->pmic_rails_verified",
              "!prereqs->clmr_reset_verified",
              "!prereqs->spi_bus_verified",
              "!prereqs->clock_pll_verified",
              "!prereqs->boot_irq_verified",
              "prereqs->det_mode == SHL25_CLMR_DET_UNVERIFIED"):
    assert guard in entry
assert entry.index("if (!prereqs->pmic_rails_verified") < entry.index("request_firmware(")
assert entry.index("request_firmware(") < entry.index("bridge.rom_io_authorized = true;")
assert entry.index("bridge.rom_io_authorized = true;") < entry.index("shl25_as99_clmr_boot_sequence(")
assert "release_firmware(firmware);" in entry
assert "bridge.rom_io_authorized = false;" in entry
assert '"sharp/shl25-as99-clmr.bin"' in SOURCE
assert "firmware->size != 59136U" in SOURCE
assert "spi->chip_select != 0" in SOURCE
assert "SPI_CPOL | SPI_CPHA | SPI_CS_HIGH" in SOURCE
assert "crypto_shash_digest(desc, fw, len, digest)" in BOOT
assert BOOT.index("ret = shl25_clmr_verify_firmware_sha256(firmware, firmware_bytes);") < BOOT.index(
  "shl25_clmr_apply_regops(ops, ctx, shl25_boot_fw_download")
assert "shl25_as99_clmr_bridge_boot(" in HEADER

# Absent firmware/power/IRQ driver cannot call it from registered probe.
probe=SPI.split("static int shl25_clmr_spi_probe(",1)[1].split(
  "static const struct of_device_id",1)[0]
for code in (SOURCE,SPI):
    assert "module_init(" not in SOURCE
    assert "module_spi_driver(" not in SOURCE
    assert "EXPORT_SYMBOL" not in SOURCE
assert "shl25_as99_clmr_bridge_boot(" not in SPI
assert "shl25_as99_clmr_bridge_boot(" not in probe
assert "regulator_enable(" not in SOURCE
assert "gpio_set_value(" not in SOURCE
assert "status = \"disabled\";" in DTS
assert "sharp_clmr_spi: display-controller@0" in DTS

print("SHL25_AS99_C6_CLMR_REG_ENDIAN_AND_OEM_FRAME_VECTOR_PASS")
print("SHL25_AS99_C6_FW_C7_C8_TRANSFER_10_FRAMES_PASS")
print("SHL25_AS99_C6_FIRMWARE_SHA_AND_BOARD_PRECONDITIONS_PASS")
print("SHL25_AS99_C6_NO_PROBE_HARDWARE_WRITE_PASS")
