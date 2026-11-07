#!/usr/bin/env python3
"""Pin selected Sharp AS99 CLMR firmware-boot register programs.

OEM: bld010105 kernel/drivers/sharp/shdisp_lcdc/shdisp_clmr.c and .h.
Generated boot register arrays do NOT power hardware or imply boot PASS.
The silicon/DET branch remains explicit, never guessed.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
FIXTURE=ROOT/"upstream/shl25-as99-clmr-boot.json"
HEADER=ROOT/"drivers/spi/shl25-as99-clmr-boot-tables.h"
OEM_C_SHA="399f2b8f050709f6c8c08c56e22260e13ba46b2edde363555ebb69487933e7f0"
OEM_H_SHA="1eb86c4756fd1afb5b815eb2739e2a5170f51ac4f9279b3917201edcc1c6249d"
FW_BYTES=59136
FW_BLOCKS=3696
BOOT_IRQ_TIMEOUT_MS=2100
DMA_POLL_MAX=100
GROUPS={
    "fw_download":7,
    "arm_init_det":6,
    "arm_init_no_det":6,
    "arm_sram2fw":7,
    "arm_boot":1,
}
TYPES={"CALI_STR":0,"CALI_OR":1}
GROUP_PATTERN=r"(?:const\s+static|static|const)\s+shdisp_clmrRegSetting_t\s+{name}\s*\[\s*\]\s*=\s*\{{(.*?)\n\}};"

def source_hash(path, expected):
    b=path.read_bytes()
    actual=hashlib.sha256(b).hexdigest()
    if actual!=expected:raise ValueError(f"OEM_SHA_MISMATCH {path.name} {actual}")
    return b.decode("utf-8",errors="replace")

def preprocess_det(body, no_det):
    out=[]
    branch=False
    active=True
    for line in body.splitlines():
        strip=line.strip()
        if strip.startswith("#ifdef SHDISP_NOT_SUPPORT_DET"):
            if branch:raise ValueError("nested unsupported DET")
            branch=True
            active=no_det
            continue
        if strip.startswith("#else") and branch:
            active=not active
            continue
        if strip.startswith("#endif") and branch:
            branch=False
            active=True
            continue
        if strip.startswith("#"):raise ValueError("unresolved preprocessor directive "+strip)
        if active:out.append(line)
    if branch:raise ValueError("unclosed DET conditional")
    return "\n".join(out)

def parse_oem(c_path,h_path):
    c=source_hash(c_path,OEM_C_SHA)
    h=source_hash(h_path,OEM_H_SHA)
    addr={k:int(v,16) for k,v in re.findall(
        r"^\s*#define\s+(SHDISP_CLMR_REG_\w+)\s+(0x[0-9A-Fa-f]+)\s*$",h,re.M)}
    m=re.search(r"^\s*#define\s+CALI_HOSTBASE_VAL\s+(0x[0-9A-Fa-f]+)\s*$",c,re.M)
    if not m:raise ValueError("missing pinned AS99 HOSTBASE")
    hostbase=int(m.group(1),16)
    assert hostbase==0x7ce0
    outputs={}
    for group in GROUPS:
        src="arm_init" if group.startswith("arm_init_") else group
        m=re.search(GROUP_PATTERN.format(name=src),c,re.S)
        if not m:raise ValueError("OEM_BOOT_TABLE_MISSING "+src)
        body=preprocess_det(m.group(1),no_det=(group=="arm_init_no_det"))
        recs=re.findall(r"\{\s*(SHDISP_CLMR_REG_\w+)\s*,\s*(CALI_\w+)\s*,\s*([^,]+),\s*([^,]+),\s*(\d+)\s*\}",body)
        entries=re.findall(r"\{\s*SHDISP_CLMR_REG_",body)
        if len(recs)!=len(entries):raise ValueError("unparsed CLMR boot record "+group)
        arr=[]
        for reg,op,data,mask,wait in recs:
            if reg not in addr:raise ValueError("unknown CLMR register "+reg)
            if op not in TYPES:raise ValueError("unsupported boot opcode "+op)
            if data.strip()=="CALI_HOSTBASE_VAL":val=hostbase
            elif re.fullmatch(r"(?:0x[0-9a-fA-F]+|[0-9]+)",data.strip()):
                val=int(data.strip(),0)
            else:raise ValueError("dynamic boot data "+data+" in "+group)
            if mask.strip()!="0x00000000" or int(wait)!=0:
                raise ValueError("unsupported mask/wait "+group)
            arr.append(dict(reg=addr[reg],name=reg,op=op,data=val,delay_us=int(wait)))
        if len(arr)!=GROUPS[group]:raise ValueError(f"{group}: record count {len(arr)}")
        outputs[group]=arr
    assert outputs["fw_download"][2]["data"]==hostbase
    assert outputs["arm_sram2fw"][3]["data"]==hostbase
    assert outputs["arm_init_det"][0]["data"]==0x30000
    assert outputs["arm_init_no_det"][0]["data"]==0x10000
    assert outputs["arm_sram2fw"][-1]["reg"]==addr["SHDISP_CLMR_REG_ARMDMA"]
    assert outputs["arm_boot"][0]["data"]==0x13
    return {
        "source_sha256":OEM_C_SHA,"register_header_sha256":OEM_H_SHA,
        "board":"CONFIG_MACH_DECKARD_AS99=y, CONFIG_SHDISP_PANEL_ANDY=y",
        "hostbase":hostbase,"fw_blocks":FW_BLOCKS,"fw_bytes":FW_BYTES,
        "hostaey_value":FW_BLOCKS-1,"irq_timeout_ms":BOOT_IRQ_TIMEOUT_MS,
        "dma_poll_max":DMA_POLL_MAX,
        "groups":outputs,
    }

def render_header(f):
    lines=[
        "/* SPDX-License-Identifier: GPL-2.0-only */",
        "/* Generated from pinned Sharp GPL SHL25 AS99 CLMR boot tables. */",
        "/* Do not use before hardware power/reset/clock and firmware validation. */",
        "#ifndef SHL25_AS99_CLMR_BOOT_TABLES_H",
        "#define SHL25_AS99_CLMR_BOOT_TABLES_H",
        "#define SHL25_CLMR_FW_BYTES 59136U",
        "#define SHL25_CLMR_FW_BLOCKS 3696U",
        "#define SHL25_CLMR_HOSTAEY_BOOT_VALUE 3695U",
        "#define SHL25_CLMR_BOOT_IRQ_TIMEOUT_MS 2100U",
        "#define SHL25_CLMR_DMA_POLL_LIMIT 100U",
        "#define SHL25_CLMR_OP_STR 0U",
        "#define SHL25_CLMR_OP_OR 1U",
        "struct shl25_clmr_regop {",
        "\tu16 reg;",
        "\tu8 op;",
        "\tu32 data;",
        "};",
    ]
    for group in GROUPS:
        lines.append(f"static const struct shl25_clmr_regop shl25_boot_{group}[] = {{")
        for r in f["groups"][group]:
            lines.append(f"\t{{ 0x{r['reg']:04x}, {TYPES[r['op']]}, 0x{r['data']:08x} }}, /* {r['name']} */")
        lines.append("};")
    lines.append("#endif /* SHL25_AS99_CLMR_BOOT_TABLES_H */")
    return "\n".join(lines)+"\n"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--oem-source",type=Path)
    p.add_argument("--oem-header",type=Path)
    p.add_argument("--write",action="store_true")
    p.add_argument("--verify",action="store_true")
    a=p.parse_args()
    if (a.oem_source is None)!=(a.oem_header is None):
        raise ValueError("must provide BOTH OEM source and header")
    if a.oem_source:
        extracted=parse_oem(a.oem_source,a.oem_header)
        serialized=json.dumps(extracted,indent=2,sort_keys=True)+"\n"
        if a.write:FIXTURE.write_bytes(serialized.encode("utf-8"))
        else:
            assert FIXTURE.read_bytes().replace(b"\r\n",b"\n")==serialized.encode("utf-8"),"OEM differs from fixture"
    f=json.loads(FIXTURE.read_bytes().replace(b"\r\n",b"\n"))
    assert f["source_sha256"]==OEM_C_SHA
    assert f["register_header_sha256"]==OEM_H_SHA
    assert f["hostbase"]==0x7ce0
    assert f["fw_bytes"]==FW_BYTES and f["fw_blocks"]==FW_BLOCKS
    assert f["irq_timeout_ms"]==BOOT_IRQ_TIMEOUT_MS and f["dma_poll_max"]==DMA_POLL_MAX
    assert f["hostaey_value"]==FW_BLOCKS-1
    for group,count in GROUPS.items():
        assert len(f["groups"][group])==count,group
        for r in f["groups"][group]:
            assert r["op"] in TYPES and 0<=r["reg"]<=0xffff and 0<=r["data"]<=0xffffffff
            assert r["delay_us"]==0
    assert f["groups"]["arm_init_det"][0]["data"]==0x30000
    assert f["groups"]["arm_init_no_det"][0]["data"]==0x10000
    output=render_header(f)
    if a.write:HEADER.write_bytes(output.encode("utf-8"))
    else:
        assert HEADER.read_bytes().replace(b"\r\n",b"\n")==output.encode("utf-8"),"CLMR boot header not deterministic"
    print("SHL25_AS99_CLMR_BOOT_OEM_TABLES_PASS", {name:len(f["groups"][name]) for name in GROUPS})
    print("SHL25_AS99_CLMR_BOOT_DET_VARIANT_EXPLICIT_PASS")
    print("SHL25_AS99_CLMR_BOOT_HDR_REGENERATE_PASS")

if __name__=="__main__":
    main()
