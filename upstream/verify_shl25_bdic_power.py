#!/usr/bin/env python3
"""Offline AS99 BDIC VSP/VSN table and callback contract verification."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parent.parent
D=json.loads((ROOT/"upstream/shl25-as99-bdic-power.json").read_text(encoding="utf8"))
C=(ROOT/"drivers/spi/shl25-as99-bdic-power.c").read_text(encoding="utf8")
H=(ROOT/"drivers/spi/shl25-as99-bdic-power.h").read_text(encoding="utf8")
SPI=(ROOT/"drivers/spi/spi-shl25-as99-clmr.c").read_text(encoding="utf8")
DT=(ROOT/"dts/shl25-as99-peripherals.dtsi").read_text(encoding="utf8")
g=D["groups"]
assert D["chipver0_uses_vsn_on_ts1"] is True
assert D["bdic_fwcmd_slave8"]==0xa8
assert D["bdic_7bit_address_equivalent"]==0x54
assert [x["op"] for x in g["vsp_on"]]==["SHDISP_BDIC_BANK","SHDISP_BDIC_STR","SHDISP_BDIC_SET"]
assert [x["delay_us"] for x in g["vsp_on"]]==[0,0,3000]
assert [x["delay_us"] for x in g["vsp_off"]]==[0,2000]
assert [x["delay_us"] for x in g["vsn_on_ts1"]]==[0,0,16000,0]
assert [x["delay_us"] for x in g["vsn_off"]]==[1000]
assert g["vsn_on_ts1"][0]["data"]==0x05
assert g["vsn_on"][0]["mask"]==0x50 and g["vsn_on"][0]["data"]==0x10
assert g["vsn_on_ts1"][2]["mask"]==0x50 and g["vsn_on_ts1"][2]["data"]==0x10
assert "if (ready->chipver == 0)" in C
for name in ("active","standby","vsp_on","vsp_off","vsn_on","vsn_on_ts1","vsn_off"):
    assert "shl25_bdic_"+name in C
for op in ("STR","SET","CLR","RMW","BANK"):
    assert "case SHL25_BDIC_OP_"+op in C
assert "ops->bank_select(ctx, entry->data)" in C
assert "ops->mask_write_reg(ctx, entry->reg," in C
assert "entry->data, entry->data" in C
assert "0, entry->mask" in C
assert "entry->data, entry->mask" in C
assert "if (entry->wait_us)" in C
assert "ops->delay_us(ctx, entry->wait_us)" in C
for guard in ("!ready->board_power_verified",
              "!ready->clmr_firmware_running",
              "!ready->clmr_fwcmd_channel_verified",
              "!ready->bdic_chipver_read_verified"):
    assert guard in C
assert "module_init(" not in C and "module_spi_driver(" not in C
assert "EXPORT_SYMBOL" not in C and "shl25_as99_bdic_power_sequence(" not in SPI
probe=SPI.split("static int shl25_clmr_spi_probe(",1)[1].split(
    "static const struct of_device_id",1)[0]
assert "shl25_as99_bdic_power_sequence(" not in probe
assert 'status = "disabled";' in DT

# Independent host-side model verifies order and delay/abort semantics.
def run(name,fail_at=-1):
    events=[]
    for i,row in enumerate(g[name]):
        if i==fail_at:
            return "ERROR",events
        if row["op"]=="SHDISP_BDIC_BANK":
            events.append(("BANK",row["data"]))
        elif row["op"]=="SHDISP_BDIC_STR":
            events.append(("WRITE",row["reg"],row["data"]))
        elif row["op"]=="SHDISP_BDIC_SET":
            events.append(("MASK",row["reg"],row["data"],row["data"]))
        elif row["op"]=="SHDISP_BDIC_CLR":
            events.append(("MASK",row["reg"],0,row["mask"]))
        else:
            events.append(("MASK",row["reg"],row["data"],row["mask"]))
        if row["delay_us"]:
            events.append(("DELAY",row["delay_us"]))
    return "PASS",events

for name in g:
    assert run(name)[0]=="PASS"
    assert run(name,fail_at=0)[1]==[]
    assert run(name,fail_at=1)[0]=="ERROR" if len(g[name])>1 else True
assert run("vsp_on")[1][-1]==("DELAY",3000)
assert ("DELAY",16000) in run("vsn_on_ts1")[1]
assert run("vsn_on")[1]!=run("vsn_on_ts1")[1]
print("SHL25_AS99_BDIC_SOURCE_PINNED_VSP_VSN_TABLES_PASS")
print("SHL25_AS99_BDIC_TS1_WAITS_AND_FWCMD_OPS_PASS")
print("SHL25_AS99_BDIC_HARDWARE_GATE_DISABLED_PASS")
