#!/usr/bin/env python3
"""Validate SHL25 board-only 6.1 peripheral bus descriptions in *compiled* DTB.

Checks bus addresses, pinmux, IRQ, clock phandles, attached hardware, and
safe DISABLED state. This is NOT runtime driver validation. Do not pass
a kernel/DTB as fully functional merely because this validator passes.
"""
from pathlib import Path
import struct
import sys
from verify_shl25_dtb import parse_fdt

def u32seq(blob):
    if len(blob) % 4:
        raise ValueError("invalid FDT cell count")
    return struct.unpack(">"+("I"*(len(blob)//4)),blob)

def check(node,path):
    assert path in node,f"missing board bus/node {path}"
    return node[path]

def disabled(n,name):
    assert n.get("status",b"").rstrip(b"\x00")==b"disabled", \
        f"{name}: port-unfinished peripheral accidentally enabled"

def compatible(n,value):
    assert value.encode() in n.get("compatible",b"").split(b"\x00"), \
        f"{value}: unexpected compatible"

def main():
    if len(sys.argv)!=2:raise SystemExit("usage: verify_shl25_peripherals.py compiled.dtb")
    tree=parse_fdt(Path(sys.argv[1]).read_bytes())
    specs={
        "/soc/spi@f9923000":(0xf9923000,95,"qcom,spi-qup-v2.1.1"),
        "/soc/spi@f9924000":(0xf9924000,96,"qcom,spi-qup-v2.1.1"),
        "/soc/spi@f9966000":(0xf9966000,104,"qcom,spi-qup-v2.1.1"),
        "/soc/i2c@f9927000":(0xf9927000,99,"qcom,i2c-qup-v2.1.1"),
    }
    for path,(addr,irq,driver) in specs.items():
        n=check(tree,path)
        disabled(n,path)
        compatible(n,driver)
        assert u32seq(n["reg"])==(addr,0x1000),f"bad QUP physical addr: {path}"
        assert u32seq(n["interrupts"])==(0,irq,4),f"bad QUP IRQ: {path}"
        assert len(u32seq(n["clocks"]))==4,f"bad clock binding: {path}"
        assert n.get("clock-names",b"") == b"core\x00iface\x00",path
        assert "#address-cells" in n and "#size-cells" in n,path
    chips=[
        ("/soc/spi@f9923000/display-controller@0","sharp,mipi_spi_0",0),
        ("/soc/spi@f9924000/touchscreen@0","sharp,shtps_rmi",0),
        ("/soc/spi@f9966000/grip-sensor@0","sharp,shgrip_dev",0),
        ("/soc/i2c@f9927000/felica@57","sharp,felica_cen",0x57),
        ("/soc/i2c@f9927000/antenna@40","sharp,snfc_ant",0x40),
        ("/soc/i2c@f9968000/imu@68","invensense,mpu6515",0x68),
    ]
    for path,driver,address in chips:
        n=check(tree,path)
        disabled(n,path)
        compatible(n,driver)
        assert u32seq(n["reg"])==(address,),f"reg != {address}: {path}"
    assert u32seq(tree["/soc/spi@f9924000/touchscreen@0"]["interrupts"]) == (61,0)
    assert u32seq(tree["/soc/i2c@f9968000/imu@68"]["interrupts"]) == (66,1)
    assert tree["/soc/spi@f9924000/touchscreen@0"].get("spi-max-frequency") == struct.pack(">I",400000)
    assert tree["/soc/spi@f9966000/grip-sensor@0"].get("spi-max-frequency") == struct.pack(">I",960000)

    pinmux={
        "as99-spi1-default-state":("gpio0\x00gpio1\x00gpio2\x00gpio3\x00", "blsp_spi1"),
        "as99-spi2-default-state":("gpio4\x00gpio5\x00gpio6\x00gpio7\x00", "blsp_spi2"),
        "as99-spi10-default-state":("gpio53\x00gpio54\x00gpio55\x00gpio56\x00", "blsp_spi10"),
        "as99-i2c5-default-state":("gpio25\x00gpio26\x00", "blsp_i2c5"),
    }
    for suffix,(pins,function) in pinmux.items():
        found=[n for p,n in tree.items() if p.endswith("/"+suffix)]
        assert len(found)==1,f"pinmux {suffix} missing or duplicated"
        assert found[0].get("pins")==pins.encode(),suffix
        assert found[0].get("function")==function.encode()+b"\x00",suffix
    # Sharp OEM 2016 fixed voltages; these consumers must remain disabled.
    # Qualcomm MSM8974 RPM request providers live at /smd/rpm/... in v6.1.
    assert "/smd/rpm/rpm_requests/regulators-1/s1" in tree, "unexpected RPM regulator provider path"
    rail_setpoints={
        "l2":1200000,"l3":1200000,"l10":1800000,
        "l15":2100000,"l17":2800000,"l23":3000000,
    }
    for name,voltage in rail_setpoints.items():
        path="/smd/rpm/rpm_requests/regulators-1/"+name
        rail=check(tree,path)
        disabled(rail,path)
        assert u32seq(rail["regulator-min-microvolt"])==(voltage,),path
        assert u32seq(rail["regulator-max-microvolt"])==(voltage,),path
    for name in ("lvs1","lvs2","lvs3"):
        path="/smd/rpm/rpm_requests/regulators-1/"+name
        disabled(check(tree,path),path)
    print("SHL25_LINUX61_SHARP_POWER_RAIL_DTB_PASS: six fixed rails + three switched rails, all disabled")
    # Real Sharp Andy panel declaration; DSI0 and panel must remain
    # disabled until CLMR/BDIC, reset and regulator sequencing works.
    candidates=[(path,node) for path,node in tree.items()
                if path.endswith("/dsi@fd922800/panel@0")]
    assert len(candidates)==1, "SHL25 Andy panel missing/duplicated"
    panel_path,panel=candidates[0]
    disabled(panel,panel_path)
    compatible(panel,"sharp,shl25-andy")
    assert u32seq(panel["reg"])==(0,), "Sharp DSI0 panel virtual channel must be zero"
    parent=panel_path.rsplit("/",1)[0]
    disabled(tree[parent],parent)
    print("SHL25_LINUX61_ANDY_DRM_PANEL_DTB_STAGED_DISABLED_PASS")
    print("SHL25_LINUX61_PERIPHERAL_DTB_DECLARATIONS_PASS: 4 QUP buses, 6 attached chips, 4 pinmux sets")
    print("SHL25_LINUX61_PERIPHERALS_DISABLED_UNTIL_DRIVER_PORT: PASS")
    print("WARNING: compiled DTB does not establish a device driver or successful hardware probing")

if __name__=="__main__":
    main()
