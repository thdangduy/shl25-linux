#!/usr/bin/env python3
"""Source-only regression guard for Sharp AS99 CLMR SPI transport stage C0.

The protocol was transcribed from the selected Sharp GPL
drivers/sharp/shdisp_lcdc/shdisp_system.c; this is not a device test.
"""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/"drivers/spi/spi-shl25-as99-clmr.c"
DTS=ROOT/"dts/shl25-as99-peripherals.dtsi"

def check():
    s=SOURCE.read_text(encoding="utf8")
    d=DTS.read_text(encoding="utf8")
    required={
        "SHL25_CLMR_SPI_WRITE_HZ":50000000,
        "SHL25_CLMR_SPI_READ_HZ":20000000,
        "SHL25_CLMR_OP_WRITE":0xc0,
        "SHL25_CLMR_OP_SELECT":0xc2,
        "SHL25_CLMR_OP_FETCH":0xc4,
    }
    for name,expected in required.items():
        m=re.search(r"^\s*#define\s+"+name+r"\s+(0x[0-9a-f]+|\d+)U?\b",s,re.M)
        assert m and int(m.group(1),0)==expected,(name,expected)
    assert '"sharp,mipi_spi_0"' in s
    assert '.probe = shl25_clmr_spi_probe' in s
    assert "module_spi_driver(shl25_clmr_spi_driver)" in s
    assert 'if (!data)' in s and 'memcpy(tx + 3, data, 4)' in s
    assert "SHL25_CLMR_OP_WRITE, (u8)(reg >> 8), (u8)reg" in s
    assert "SHL25_CLMR_OP_SELECT, (u8)(reg >> 8), (u8)reg" in s
    assert "SHL25_CLMR_OP_FETCH, 0, 0, 0, 0" in s
    assert "memcpy(out, rx + 1, 4)" in s
    assert s.count("spi_sync_transfer(clmr->spi,")>=3
    # The register read uses two separate SPI messages, matching OEM CS.
    read=s.split("static int __maybe_unused shl25_clmr_reg_read(",1)[1].split(
        "static int shl25_clmr_spi_probe(",1)[0]
    assert read.count("spi_sync_transfer(clmr->spi,")==2
    probe=s.split("static int shl25_clmr_spi_probe(",1)[1].split(
        "static const struct of_device_id",1)[0]
    # Source-level assertion that the probe never touches hardware.
    for dangerous in ("spi_sync_transfer(", "spi_write(", "gpio_set_value(",
                      "regulator_enable(", "request_firmware("):
        assert dangerous not in probe,dangerous
    assert "bool bdic_power_validated;" in s
    assert "bool firmware_running;" in s
    assert "bool clmr_pll_clock_ready;" in s
    assert "shl25_clmr_ensure_boot_ready" in s
    assert "if (!clmr->bdic_power_validated ||" in s
    assert "shl25_clmr_ensure_runtime_ready" in s
    assert "if (!clmr->firmware_running)" in s
    assert s.count("ret = shl25_clmr_ensure_boot_ready(clmr);")==2
    assert "bdic_power_validated = true" not in s
    assert "firmware_running = true" not in s
    assert "clmr_pll_clock_ready = true" not in s
    assert 'as99_spi1: spi@f9923000' in d
    assert '"sharp,mipi_spi_0"' in d
    assert 'status = "disabled";' in d
    # Expected frame examples for human review; these are reference
    # encodings, not live SPI communication.
    register=0x1234
    data=bytes([0xde,0xad,0xbe,0xef])
    write=bytes([0xc0,register>>8,register&0xff])+data
    select=bytes([0xc2,register>>8,register&0xff])
    fetch=bytes([0xc4,0,0,0,0])
    assert write.hex()=="c01234deadbeef"
    assert select.hex()=="c21234"
    assert fetch.hex()=="c400000000"
    print("SHL25_AS99_CLMR_SPI_OEM_PROTOCOL_GOLDEN_FRAMES_PASS")
    print("SHL25_AS99_CLMR_SPI_PROBE_NO_HARDWARE_WRITES_PASS")
    print("SHL25_AS99_CLMR_SPI_DTS_DISABLED_PASS")

if __name__=="__main__":
    check()
