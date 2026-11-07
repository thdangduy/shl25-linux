#!/usr/bin/env python3
"""Pin and translate the *correct* Sharp AS99 CLMR runtime DCS tables.

Correct vendor sources for CONFIG_MACH_DECKARD_AS99=y,
CONFIG_USES_SHLCDC=y, CONFIG_SHDISP_PANEL_ANDY=y:
 kernel/drivers/sharp/shdisp_lcdc/shdisp_andy.c
 kernel/drivers/sharp/shdisp_lcdc/data/shdisp_andy_data_as99.h

Do not use drivers/sharp/shdisp/shdisp_andy.c: it selects DL60/AL15 data.
No hardware is touched; output includes flags for unresolved per-device
VCOM/gamma and firmware-dependent CLMR mode. The generated arrays
must NOT be executed until CLMR, calibration and regulator gates pass.
"""
import argparse
import ast
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
FIXTURE=ROOT/"upstream/shl25-andy-as99-runtime.json"
HEADER=ROOT/"drivers/gpu/drm/panel/shl25-andy-as99-runtime.h"
OEM_SHA="65773f9045ff997cc900d4ad80f000cf190065bfbd b874ac23293de52c67557d".replace(" ","")
WAIT_SHA="490f3d0f8a6b1763cb888edb95b7d96f89cb102977092e54c86a7c6a044169b2"
FIXTURE_SHA="aa7fcd4b8a283b0935f2428df575b7d4e28038664fecbe615e61b9075d2e16f8"
GROUPS=[
 "initial1","initial1_regulator_ts1_0","initial1_regulator_ts1_1",
 "initial1_regulator_ts1_1_flicker_unadjusted",
 "initial1_regulator_ts2_0","initial1_regulator_ts2_0_flicker_unadjusted",
 "gamma","terminal","timing","initial2","power",
 "sync_ts1_0","sync_ts2_0","display_on1_1","display_on1_2",
 "display_off",
]
# The two letters are DSI DCS commands, not the Qualcomm DT generic
# packet encoding. The CLMR route must not be silently replaced by
# ordinary DSI writes without transport-mode verification.
TYPES={"DTYPE_DCS_WRITE1":1,"DTYPE_DCS_WRITE":0}
EXPECTED_COUNTS={
 "initial1":11,"initial1_regulator_ts1_0":24,
 "initial1_regulator_ts1_1":24,"initial1_regulator_ts1_1_flicker_unadjusted":18,
 "initial1_regulator_ts2_0":25,"initial1_regulator_ts2_0_flicker_unadjusted":19,
 "gamma":363,"terminal":79,"timing":19,"initial2":21,
 "power":21,"sync_ts1_0":16,"sync_ts2_0":13,
 "display_on1_1":1,"display_on1_2":1,"display_off":7,
}
# Whitelist numeric expressions from GPL source (no eval).
def number(expr, defines):
    expr=expr.strip()
    tree=ast.parse(expr,mode="eval")
    def visit(n):
        if isinstance(n,ast.Constant) and isinstance(n.value,int):return n.value
        if isinstance(n,ast.Name):
            if n.id not in defines:raise ValueError("unknown macro "+n.id)
            return defines[n.id]
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,ast.USub):return -visit(n.operand)
        if isinstance(n,ast.BinOp):
            a,b=visit(n.left),visit(n.right)
            if isinstance(n.op,ast.Add):return a+b
            if isinstance(n.op,ast.Sub):return a-b
            if isinstance(n.op,ast.Mult):return a*b
            if isinstance(n.op,(ast.Div,ast.FloorDiv)):return a//b
            if isinstance(n.op,ast.LShift):return a<<b
            if isinstance(n.op,ast.RShift):return a>>b
            if isinstance(n.op,ast.BitOr):return a|b
            if isinstance(n.op,ast.BitAnd):return a&b
        raise ValueError("unrecognized constant expression "+expr)
    return visit(tree.body)

def parse_header(path, wait_header):
    blob=path.read_bytes()
    digest=hashlib.sha256(blob).hexdigest()
    if digest!=OEM_SHA:raise ValueError("OEM_AS99_TABLE_HASH_MISMATCH "+digest)
    txt=blob.decode("utf-8",errors="replace")
    txt=re.sub(r"/\*.*?\*/","",txt,flags=re.S)
    txt=re.sub(r"//[^\n]*","",txt)
    defs={}
    for m in re.finditer(r"^\s*#define\s+([A-Za-z]\w*)\s+(.+?)\s*$",txt,re.M):
        key,value=m.groups()
        if value.strip().startswith("("):continue
        try:defs[key]=number(value,defs)
        except (ValueError,SyntaxError,ZeroDivisionError):pass
    wait_bytes=wait_header.read_bytes()
    assert hashlib.sha256(wait_bytes).hexdigest()==WAIT_SHA, "AS99_WAIT_HEADER_SHA_MISMATCH"
    wait_match=re.search(r"^\s*#define\s+WAIT_1FRAME_US\s+\((\d+)\)\s*$",
                         wait_bytes.decode("utf-8","replace"),re.M)
    assert wait_match, "OEM 1-frame wait macro missing"
    wait_us=int(wait_match.group(1))
    assert wait_us==16666, "Unexpected AS99 1-frame delay"
    defs["WAIT_1FRAME_US"]=wait_us
    arrays={}
    pattern=re.compile(r"static\s+char\s+(mipi_sh_andy_cmd_\w+)\s*\[(\d+)\]\s*(?:\[(\d+)\])?\s*=\s*\{(.*?)\}\s*;",re.S)
    for m in pattern.finditer(txt):
        name,outer,inner,body=m.groups()
        if inner:
            rows=re.findall(r"\{([^{}]+)\}",body)
            if len(rows)!=int(outer):raise ValueError(f"{name}: expected {outer} rows, got {len(rows)}")
            values=[]
            for row in rows:
                vals=[number(x,defs) for x in row.split(",") if x.strip()]
                if len(vals)!=int(inner):raise ValueError("wrong row width "+name)
                values.append(vals)
        else:
            values=[[number(x,defs) for x in body.replace("\n"," ").split(",") if x.strip()]]
            if len(values[0])!=int(outer):raise ValueError("wrong vector width "+name)
        for row in values:
            if any(not 0<=v<=255 for v in row):raise ValueError("out-of-range byte "+name)
        arrays[name]=values
    groups={}
    for group in GROUPS:
        m=re.search(r"static\s+struct\s+dsi_cmd_desc\s+mipi_sh_andy_cmds_"+group+r"\s*\[\]\s*=\s*\{(.*?)\};",txt,re.S)
        if m is None:raise ValueError("missing OEM group "+group)
        body=m.group(1)
        entries=re.findall(r"\{\s*(DTYPE_\w+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([^,]+)\s*,\s*(\d+)\s*,\s*(mipi_sh_andy_(?:cmd|set_val)_\w+)(?:\[(\d+)\])?\s*\}",body)
        if len(entries)!=len(re.findall(r"\{\s*DTYPE_",body)):
            raise ValueError("could not parse all records in "+group)
        records=[]
        for typ,ack,vc,flags,delay,length,symbol,index in entries:
            if typ not in TYPES or int(ack)!=1 or int(vc)!=0 or int(flags)!=0:
                raise ValueError("unknown vendor packet flags/type "+str((group,typ,ack,vc,flags)))
            original_symbol=symbol
            calibrated=symbol.startswith("mipi_sh_andy_set_val_")
            if calibrated:
                symbol=symbol.replace("mipi_sh_andy_set_val_","mipi_sh_andy_cmd_",1)
            if symbol not in arrays:raise ValueError("missing OEM payload "+original_symbol)
            rows=arrays[symbol]
            if index:
                idx=int(index)
                if idx>=len(rows):raise ValueError("out-of-bounds index "+original_symbol)
                payload=rows[idx]
            else:
                if len(rows)!=1:raise ValueError("2D command missing index "+symbol)
                payload=rows[0]
            if len(payload)!=int(length):raise ValueError(f"{group}: expected len={length} got {len(payload)} in {symbol}")
            if len(payload) not in (1,2):raise ValueError("unexpected DCS payload length "+symbol)
            # Preserve unresolved timing expression verbatim; no guessed 60Hz delay.
            try:delay_us=number(delay,defs);delay_unresolved=False
            except (ValueError,SyntaxError):
                delay_us=0
                delay_unresolved=True
            if int(length)==1 and typ!="DTYPE_DCS_WRITE":raise ValueError("DCS_SHORT mismatch")
            if int(length)==2 and typ!="DTYPE_DCS_WRITE1":raise ValueError("DCS_WRITE1 mismatch")
            records.append({
                "type":typ, "payload":payload, "delay_us":delay_us,
                "unresolved_delay_expression":delay.strip() if delay_unresolved else None,
                "source":original_symbol + (("["+index+"]") if index else ""),
                "calibration_required":calibrated or "VCOM" in original_symbol or "GAMMA" in original_symbol,
            })
        if EXPECTED_COUNTS[group] is not None and len(records)!=EXPECTED_COUNTS[group]:
            raise ValueError("unexpected command count "+group+" "+str(len(records)))
        groups[group]=records
    return {
        "source_header_sha256":digest,
        "wait_header_sha256":WAIT_SHA,
        "wait_one_frame_us":wait_us,
        "source_path":"kernel/drivers/sharp/shdisp_lcdc/data/shdisp_andy_data_as99.h",
        "selected_by":"CONFIG_MACH_DECKARD_AS99=y + CONFIG_USES_SHLCDC=y",
        "clmr_required":True,
        "calibration_from_nvmem_not_implemented":True,
        "groups":groups,
    }

def render_header(fixture):
    groups=fixture["groups"]
    lines=[
        "/* SPDX-License-Identifier: GPL-2.0-only */",
        "/* Auto-generated. OEM Sha256 "+OEM_SHA+" */",
        "/* SHL25 AS99 CLMR runtime tables: DO NOT SEND before CLMR/power/calibration. */",
        "#ifndef SHL25_ANDY_AS99_RUNTIME_H",
        "#define SHL25_ANDY_AS99_RUNTIME_H",
        "struct shl25_andy_runtime_rec {",
        "\tu8 dtype;", "\tu8 len;", "\tu8 payload[2];",
        "\tu32 delay_us;", "\tbool calibration_required;",
        "\tbool delay_unresolved;",
        "};",
    ]
    for name in GROUPS:
        lines.append("static const struct shl25_andy_runtime_rec shl25_as99_"+name+"[] __maybe_unused = {")
        for rec in groups[name]:
            p=rec["payload"]
            pstr=", ".join(f"0x{x:02x}" for x in p)
            lines.append(f"\t{{ {TYPES[rec['type']]}, {len(p)}, {{ {pstr} }}, {rec['delay_us']}, "+
                         f"{str(rec['calibration_required']).lower()}, "+
                         f"{str(rec['unresolved_delay_expression'] is not None).lower()} }},")
        lines.append("};")
    lines.append("#endif /* SHL25_ANDY_AS99_RUNTIME_H */")
    return "\n".join(lines)+"\n"

def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("--extract-oem",type=Path)
    cli.add_argument("--wait-header",type=Path)
    cli.add_argument("--write",action="store_true")
    cli.add_argument("--verify",action="store_true")
    args=cli.parse_args()
    if args.extract_oem:
        if args.wait_header is None:
            raise ValueError("--wait-header required with --extract-oem")
        obj=parse_header(args.extract_oem,args.wait_header)
        serialized=json.dumps(obj,sort_keys=True,indent=2)+"\n"
        if args.write:FIXTURE.write_text(serialized,encoding="utf-8")
        else:
            assert FIXTURE.read_text(encoding="utf-8")==serialized, "OEM data differs from fixture"
    fixture_bytes=FIXTURE.read_bytes()
    if args.verify and hashlib.sha256(fixture_bytes).hexdigest()!=FIXTURE_SHA:
        raise ValueError("STAGE_B_AS99_RUNTIME_FIXTURE_SHA_CHANGED")
    data=json.loads(fixture_bytes.decode("utf-8"))
    if data["source_header_sha256"]!=OEM_SHA:raise ValueError("source header provenance changed")
    if data.get("wait_header_sha256")!=WAIT_SHA or data.get("wait_one_frame_us")!=16666:
        raise ValueError("AS99 one-frame wait provenance changed")
    for k in GROUPS:
        if k not in data["groups"]:raise ValueError("missing group "+k)
    output=render_header(data)
    if args.write:HEADER.write_text(output,encoding="utf-8")
    if args.verify or not args.write:
        assert HEADER.read_text(encoding="utf-8")==output,"Generated Linux 6.1 runtime source differs from pinned data"
    if args.verify:
        driver=(ROOT/"drivers/gpu/drm/panel/panel-sharp-shl25-andy.c").read_text(encoding="utf-8")
        prep=driver.split("static int shl25_andy_prepare(",1)[1]
        assert prep.count("ret = shl25_andy_require_runtime_ready(ctx);")==1, "UNSAFE_DRM_PREPARE_WITHOUT_GUARD"
        assert prep.index("ret = shl25_andy_require_runtime_ready(ctx);") < prep.index("ctx->dsi->mode_flags |= MIPI_DSI_MODE_LPM;"), "GUARD_AFTER_DSI_WRITE"
        assert '#include "shl25-andy-as99-runtime.h"' in driver, "AS99_RUNTIME_NOT_COMPILED"
        assert "bool clmr_transport_ready;" in driver and "bool calibration_valid;" in driver
        print("SHL25_AS99_DRM_PREPARE_FAIL_CLOSED_UNTIL_CLMR_CALIBRATION_PASS")
    count=sum(len(v) for v in data["groups"].values())
    dynamic=sum(r["calibration_required"] for v in data["groups"].values() for r in v)
    assert count==662 and dynamic==471, "AS99 runtime count/calibration regression"
    missing_wait=sum(r["unresolved_delay_expression"] is not None for v in data["groups"].values() for r in v)
    assert missing_wait==0, "AS99 delay source not resolved"
    print(f"SHL25_AS99_RUNTIME_TABLES_PASS groups={len(data['groups'])} records={count} "+
          f"need_calibration={dynamic} unresolved_delays={missing_wait}")
    print("SHL25_AS99_RUNTIME_CLMR_DEPENDENCY_GATED=PASS")

if __name__=="__main__":main()
