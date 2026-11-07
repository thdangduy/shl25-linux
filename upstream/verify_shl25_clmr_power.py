#!/usr/bin/env python3
"""Offline Sharp AS99 CLMR PM8941 supply/regulator order verifier (C7).

Optional --oem-dir checks hashes and expressions from the exact OEM
sources. Default CI checks pinned map and source guards without OEM files.
No hardware IO is performed.
"""
from pathlib import Path
import argparse
import hashlib
import json

ROOT=Path(__file__).resolve().parent.parent
fixture=json.loads((ROOT/"upstream/shl25-as99-clmr-board-power.json").read_text(encoding="utf-8"))
c=(ROOT/"drivers/spi/shl25-as99-clmr-power.c").read_text(encoding="utf-8")
h=(ROOT/"drivers/spi/shl25-as99-clmr-power.h").read_text(encoding="utf-8")
spi=(ROOT/"drivers/spi/spi-shl25-as99-clmr.c").read_text(encoding="utf-8")
dts=(ROOT/"dts/shl25-as99-peripherals.dtsi").read_text(encoding="utf-8")
dts_disp=(ROOT/"dts/shl25-as99-display.dtsi").read_text(encoding="utf-8")
pins={x["name"]:x["sha256"] for x in fixture["source"]}

assert fixture["board"]=="CONFIG_MACH_DECKARD_AS99"
assert fixture["panel"]=="CONFIG_SHDISP_PANEL_ANDY"
assert fixture["spi"]["node"]=="spi@f9923000"
assert fixture["spi"]["disabled_under_linux61"] is True
assert fixture["spi"]["mode"]=="CPOL|CPHA|CS_HIGH"
assert fixture["spi"]["chip_select"]==0
assert fixture["regulators"][0]["consumer"]=="clmr_vdd_18tx"
assert fixture["regulators"][0]["supply"]=="pm8941_lvs2"
assert fixture["regulators"][0]["enable_order"]==1
assert fixture["regulators"][0]["delay_after_enable_us"]==1000
assert fixture["regulators"][1]["consumer"]=="clmr_vdd_12lp"
assert fixture["regulators"][1]["supply"]=="pm8941_l2"
assert fixture["regulators"][1]["microvolts"]==1200000
assert fixture["regulators"][1]["load_uA"]==100000
assert fixture["regulators"][1]["enable_order"]==2
assert fixture["regulators"][1]["delay_after_enable_us"]==1000
assert fixture["core_switch"]["pin"]==19
assert fixture["core_switch"]["polarity"]=="active-high"
assert fixture["gpio"]["clmr_reset_tlmm"]==85
assert fixture["gpio"]["clmr_pllonctl_tlmm"]==8
assert fixture["gpio"]["clmr_hint_irq_tlmm"]==75
assert fixture["gpio"]["clmr_te_tlmm"]==12
assert fixture["irq"]["linux61_irq_type"]=="unverified"

for token in ("!ready->oem_supply_mapping_verified",
              "!ready->core_gpio_active_high_verified",
              "!ready->as99_board_revision_verified",
              "!ready->pm8941_parent_rails_verified",
              "gpiod_direction_output(res->core_switch, 0)",
              "regulator_set_voltage(res->vdd_12lp,",
              "regulator_set_load(res->vdd_12lp, SHL25_CLMR_LP_LOAD_UA)",
              "SHL25_CLMR_LP_UV 1200000",
              "SHL25_CLMR_LP_LOAD_UA 100000",
              "if (res->power_on)",
              "return -EOPNOTSUPP",
              "disable_first:"):
    assert token in c,token
enable=c.split("int shl25_as99_clmr_power_enable(",1)[1].split(
  "int shl25_as99_clmr_power_disable(",1)[0]
sequence=["shl25_clmr_power_gate(res, ready)","gpiod_direction_output(res->core_switch, 0)",
          "regulator_enable(res->vdd_18tx)", "usleep_range(1000, 1100)",
          "regulator_enable(res->vdd_12lp)","gpiod_set_value_cansleep(res->core_switch, 1)",
          "res->power_on = true"]
loc=[enable.index(x) for x in sequence]
assert loc==sorted(loc),loc
assert enable.count("usleep_range(1000, 1100)")>=2
assert enable.index("disable_first:")<enable.index("regulator_disable(res->vdd_18tx)")
disable=c.split("int shl25_as99_clmr_power_disable(",1)[1]
seq=["shl25_clmr_power_gate(res, ready)",
     "gpiod_set_value_cansleep(res->core_switch, 0)",
     "regulator_disable(res->vdd_12lp)",
     "regulator_disable(res->vdd_18tx)"]
loc=[disable.index(x) for x in seq]
assert loc==sorted(loc),loc
assert "shl25_as99_clmr_power_enable(" in h
assert "shl25_as99_clmr_power_disable(" in h
assert "shl25_as99_clmr_power_enable(" not in spi
assert "module_init(" not in c and "module_spi_driver(" not in c
assert "EXPORT_SYMBOL" not in c
assert "status = \"disabled\";" in dts
assert "status = \"disabled\";" in dts_disp

def optional_oem(oem):
    if not oem:return
    src={}
    for name,expected in pins.items():
        item=(oem/name).read_bytes()
        assert hashlib.sha256(item).hexdigest()==expected,name
        src[name]=item.decode("utf-8",errors="replace")
    clmr=src["sharp-shdisp-clmr.dtsi"]
    assert "clmr_vdd_18tx-supply = <&pm8941_lvs2>" in clmr
    assert "clmr_vdd_12lp-supply = <&pm8941_l2>" in clmr
    assert "shdisp_clmr,reg-gpio = <&pm8941_gpios 19 0>" in clmr
    assert "interrupts = <75 0>" in clmr
    assert "spi-cpol;" in clmr and "spi-cpha;" in clmr and "spi-cs-high;" in clmr
    oem_c=src["shdisp_clmr.c"]
    assert '{"clmr_vdd_18tx",   REG_VS' in oem_c
    assert '{"clmr_vdd_12lp",   REG_LDO, 1200000, 1200000, 100000, 1 * 1000}' in oem_c
    assert oem_c.index("regulator_enable(reg_ptr[i])") < oem_c.index(
        "gpio_set_value(shdisp_clmr_ctrl.core_reg_gpio, 1)")
    system=src["shdisp_system.h"]
    for macro,value in (("CLMR_RESET","85"),("CLMR_PLLONCTL","8"),
                        ("CLMR_HINT","75")):
        assert "SHDISP_GPIO_NUM_"+macro in system and value in system
    print("SHL25_AS99_C7_ALL_OEM_SOURCE_SHA256_AND_POWER_MAPPING_PASS")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--oem-dir",type=Path)
    p.add_argument("--oem-clmr-c",type=Path)
    p.add_argument("--oem-system-h",type=Path)
    args=p.parse_args()
    # OEM reference files are in two distinct checkpoint folders.
    if args.oem_dir:
        src={}
        for name in ("sharp-shdisp-clmr.dtsi","sharp-as99-shdisp.dtsi","sharp-as99.dtsi"):
            raw=(args.oem_dir/name).read_bytes()
            assert hashlib.sha256(raw).hexdigest()==pins[name]
            src[name]=raw.decode("utf-8",errors="replace")
        for name,file in (("shdisp_clmr.c",args.oem_clmr_c),("shdisp_system.h",args.oem_system_h)):
            assert file, "missing original OEM "+name
            raw=file.read_bytes()
            assert hashlib.sha256(raw).hexdigest()==pins[name]
            src[name]=raw.decode("utf-8",errors="replace")
        clmr=src["sharp-shdisp-clmr.dtsi"]
        assert "clmr_vdd_18tx-supply = <&pm8941_lvs2>" in clmr
        assert "clmr_vdd_12lp-supply = <&pm8941_l2>" in clmr
        assert "shdisp_clmr,reg-gpio = <&pm8941_gpios 19 0>" in clmr
        assert "interrupts = <75 0>" in clmr
        assert "spi-cpol;" in clmr and "spi-cpha;" in clmr and "spi-cs-high;" in clmr
        source=src["shdisp_clmr.c"]
        assert '{"clmr_vdd_18tx",   REG_VS' in source
        assert '{"clmr_vdd_12lp",   REG_LDO, 1200000, 1200000, 100000, 1 * 1000}' in source
        assert source.index("regulator_enable(reg_ptr[i])") < source.index(
            "gpio_set_value(shdisp_clmr_ctrl.core_reg_gpio, 1)")
        system=src["shdisp_system.h"]
        for name,value in (("CLMR_RESET","85"),("CLMR_PLLONCTL","8"),("CLMR_HINT","75")):
            import re
            assert re.search("SHDISP_GPIO_NUM_"+name+r"\s+\("+value+r"\)",system)
        print("SHL25_AS99_C7_ALL_OEM_SOURCE_SHA256_AND_POWER_MAPPING_PASS")
    print("SHL25_AS99_C7_2_RAIL_POWER_ORDER_AND_ROLLBACK_PASS")
    print("SHL25_AS99_C7_PM8941_MAPPING_AND_DT_DISABLED_PASS")

if __name__=="__main__":main()
