#!/usr/bin/env python3
"""Extract AS99 Sharp BDIC VSP/VSN power tables from pinned GPL source.

No live I2C, CLMR firmware commands, regulator changes or handset access.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
DEST=ROOT/"upstream/shl25-as99-bdic-power.json"
HEADER=ROOT/"drivers/spi/shl25-as99-bdic-power-tables.h"
PINS={
    "control":"f4a034bc613339c92b04c9df94f5a5adcb06ab51dfab53e9ba2ee095e9d2f69b",
    "as99":"79bebee79c31f2a0d39637dc0de5c6b596f4f196cdbd73e0017df7b069dab18b",
    "registers":"d78408db969bd0ff9cf2efdec97e2cd5c4158a16cbaf6777238b8ee17404ae62",
    "driver":"ae1d0d78dc639c881c80c857a781e510341fdd66e92c8481e88088b4b02c3206",
}
NAMES={"active":3,"standby":3,"vsp_on":3,"vsp_off":2,"vsn_on":1,"vsn_on_ts1":4,"vsn_off":1}
OPS={"SHDISP_BDIC_STR":0,"SHDISP_BDIC_SET":1,"SHDISP_BDIC_CLR":2,
     "SHDISP_BDIC_RMW":3,"SHDISP_BDIC_BANK":4}

def read_pinned(path,expected):
    data=path.read_bytes()
    digest=hashlib.sha256(data).hexdigest()
    if digest!=expected:raise ValueError(f"BDIC_OEM_SOURCE_HASH_MISMATCH: {path} {digest}")
    return data.decode("utf-8",errors="replace")

def extract(ctrl, as99, registers, driver):
    txt=read_pinned(ctrl,PINS["control"])
    variant=read_pinned(as99,PINS["as99"])
    defs=read_pinned(registers,PINS["registers"])
    impl=read_pinned(driver,PINS["driver"])
    assert "shdisp_bdic_vsn_on_ts1" in impl
    assert "shdisp_bdic_vsp_on" in impl
    def values(source):
        return {m.group(1):int(m.group(2),16) for m in re.finditer(
            r"^\s*#define\s+(BDIC_REG_\w+)\s+\(?\s*(0x[0-9a-fA-F]+)\s*\)?",source,re.M)}
    symbols=values(defs)
    symbols.update(values(variant))
    assert symbols["BDIC_REG_CPM1_VAL_TS1"]==5
    groups={}
    for name,count in NAMES.items():
        match=re.search(r"const\s+shdisp_bdicRegSetting_t\s+shdisp_bdic_"+name+r"\s*\[\s*\]\s*=\s*\{(.*?)\};",txt,re.S)
        if not match:raise ValueError("BDIC_TABLE_MISSING "+name)
        body=match.group(1)
        rows=re.findall(
            r"\{\s*(BDIC_REG_\w+)\s*,\s*(SHDISP_BDIC_\w+)\s*,\s*([^,]+)\s*,\s*([^,]+)\s*,\s*(\d+)\s*\}",
            body,re.S)
        assert len(rows)==body.count("{"),"BDIC_UNPARSED_TABLE "+name
        arr=[]
        for reg,op,val,mask,delay in rows:
            if op not in OPS or reg not in symbols:
                raise ValueError("unknown BDIC symbol "+str((reg,op,name)))
            def val_of(token):
                token=token.strip()
                if token in symbols:return symbols[token]
                if re.fullmatch(r"0x[0-9A-Fa-f]+",token):return int(token,16)
                if re.fullmatch(r"[0-9]+",token):return int(token)
                raise ValueError("unresolved BDIC value "+token)
            v=val_of(val); m=val_of(mask); d=int(delay)
            if not all(0<=x<=255 for x in (v,m,symbols[reg])):
                raise ValueError("BDIC byte overflow")
            if d<0 or d>1000000:raise ValueError("BDIC unreasonable wait")
            arr.append(dict(reg=symbols[reg],reg_symbol=reg,op=op,data=v,mask=m,delay_us=d))
        if len(arr)!=count:raise ValueError("incorrect table count "+name)
        groups[name]=arr
    assert groups["vsn_on_ts1"][2]["delay_us"]==16000
    assert groups["vsp_on"][-1]["delay_us"]==3000
    assert groups["vsn_off"][-1]["delay_us"]==1000
    assert groups["vsp_off"][-1]["delay_us"]==2000
    return {"source_sha256":PINS,"selected_board":"CONFIG_MACH_DECKARD_AS99",
            "bdic_fwcmd_slave8":0xa8,"bdic_7bit_address_equivalent":0x54,
            "chipver0_uses_vsn_on_ts1":True,"groups":groups}

def render_header(data):
    lines=[
        "/* SPDX-License-Identifier: GPL-2.0-only */",
        "/* Sharp OEM AS99 BDIC VSP/VSN register tables, source-pinned. */",
        "/* Not executable until CLMR firmware queue and power gates verified. */",
        "#ifndef SHL25_AS99_BDIC_POWER_TABLES_H",
        "#define SHL25_AS99_BDIC_POWER_TABLES_H",
        "#define SHL25_BDIC_OP_STR 0",
        "#define SHL25_BDIC_OP_SET 1",
        "#define SHL25_BDIC_OP_CLR 2",
        "#define SHL25_BDIC_OP_RMW 3",
        "#define SHL25_BDIC_OP_BANK 4",
        "struct shl25_bdic_regop {",
        "\tu8 reg;",
        "\tu8 op;",
        "\tu8 data;",
        "\tu8 mask;",
        "\tu32 wait_us;",
        "};",
    ]
    for name in NAMES:
        lines.append(f"static const struct shl25_bdic_regop shl25_bdic_{name}[] = {{")
        for row in data["groups"][name]:
            lines.append("\t{ "+f"0x{row['reg']:02x}, {OPS[row['op']]}, 0x{row['data']:02x}, 0x{row['mask']:02x}, {row['delay_us']}"+f" }}, /* {row['reg_symbol']} */")
        lines.append("};")
    lines.append("#endif /* SHL25_AS99_BDIC_POWER_TABLES_H */")
    return "\n".join(lines)+"\n"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--ctrl",type=Path)
    p.add_argument("--as99",type=Path)
    p.add_argument("--registers",type=Path)
    p.add_argument("--driver",type=Path)
    p.add_argument("--write",action="store_true")
    p.add_argument("--verify",action="store_true")
    a=p.parse_args()
    paths=(a.ctrl,a.as99,a.registers,a.driver)
    if any(p is not None for p in paths) and not all(p is not None for p in paths):
        raise ValueError("all 4 original OEM sources required")
    if all(p is not None for p in paths):
        source=extract(*paths)
        data=(json.dumps(source,sort_keys=True,indent=2)+"\n").encode("utf-8")
        if a.write:DEST.write_bytes(data)
        else:assert DEST.read_bytes().replace(b"\r\n",b"\n")==data,"source vs fixture changed"
    fixture=json.loads(DEST.read_bytes().replace(b"\r\n",b"\n"))
    assert fixture["source_sha256"]==PINS
    assert fixture["selected_board"]=="CONFIG_MACH_DECKARD_AS99"
    assert fixture["chipver0_uses_vsn_on_ts1"] is True
    assert fixture["bdic_fwcmd_slave8"]==0xa8
    for name,count in NAMES.items():
        assert len(fixture["groups"][name])==count,name
        for row in fixture["groups"][name]:
            assert row["op"] in OPS
    assert fixture["groups"]["vsn_on_ts1"][2]["delay_us"]==16000
    assert fixture["groups"]["vsp_on"][-1]["delay_us"]==3000
    header=render_header(fixture).encode("utf-8")
    if a.write:HEADER.write_bytes(header)
    else:assert HEADER.read_bytes().replace(b"\r\n",b"\n")==header, "BDIC_HEADER_DIFFERS_FROM_PINNED"
    print("SHL25_AS99_BDIC_POWER_TABLES_OEM_PIN_PASS", {name:len(fixture["groups"][name]) for name in NAMES})
    print("SHL25_AS99_BDIC_VSP_VSN_TS1_WAIT_VALUES_PASS")
    print("SHL25_AS99_BDIC_POWER_GENERATION_DETERMINISTIC_PASS")

if __name__=="__main__":main()
