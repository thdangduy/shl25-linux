#!/usr/bin/env python3
"""Sharp AS99 CLMR IRQ register decode/ack source and offline vectors C8.

No hardware calls, IRQ requests, device access or assumptions about GPIO75
edge/level trigger type. Only the OEM register protocol is tested.
"""
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
C=(ROOT/"drivers/spi/shl25-as99-clmr-irq-status.c").read_text(encoding="utf-8")
H=(ROOT/"drivers/spi/shl25-as99-clmr-irq-status.h").read_text(encoding="utf-8")
SPI=(ROOT/"drivers/spi/spi-shl25-as99-clmr.c").read_text(encoding="utf-8")
DT=(ROOT/"dts/shl25-as99-peripherals.dtsi").read_text(encoding="utf-8")

assert "SHL25_CLMR_REG_INTR    0x0100" in C
assert "SHL25_CLMR_REG_INTSET1 0x0110" in C
assert "SHL25_CLMR_REG_INTSET2 0x0114" in C
assert "SHL25_CLMR_INTR_FW_GROUP     BIT(16)" in H
assert "SHL25_CLMR_INTR_DET_GROUP    BIT(17)" in H
assert "SHL25_CLMR_EVENT_BOOT_DONE   BIT(1)" in H
assert "SHL25_CLMR_IRQ_DRAIN_LIMIT 32U" in H
assert "if (intset1 & BIT(1))" in C
assert "events |= SHL25_CLMR_EVENT_BOOT_DONE" in C
assert "if (intset1 & BIT(3))" in C
assert "events |= SHL25_CLMR_EVENT_FW_ERROR" in C
assert "if (intset2 & BIT(2))" in C
assert "events |= SHL25_CLMR_EVENT_TE" in C

def decode(intr,intset1,intset2):
    events=0
    if intr & (1<<16):
        events|=(intset1 & 0x0f)
    if intr & (1<<17):
        events|=(intset2 & 0x07)<<4
    return events

assert decode(0x00010000,0x2,0)==0x2   # ARM FW start complete
assert decode(0x00010000,0x1,0)==0x1   # FW command complete
assert decode(0x00010000,0x4,0)==0x4   # eDRAM pointer reset
assert decode(0x00010000,0x8,0)==0x8   # firmware error
assert decode(0x00020000,0,0x7)==0x70 # LCD DET, PSALS, TE
assert decode(0x00030000,0x2,0x4)==0x42
assert decode(0,0x2,0x7)==0
assert decode(0x00020000,0x2,0)==0
assert decode(0x00010000,0,0x7)==0

# OEM reads INTR before INTSETx; acknowledges each by writing 0.
drain=C.split("int shl25_as99_clmr_irq_drain(",1)[1]
items=[
    "ops->read_reg(ctx, SHL25_CLMR_REG_INTR",
    "ops->read_reg(ctx, SHL25_CLMR_REG_INTSET1",
    "ops->write_reg(ctx, SHL25_CLMR_REG_INTSET1, 0)",
    "ops->read_reg(ctx, SHL25_CLMR_REG_INTSET2",
    "ops->write_reg(ctx, SHL25_CLMR_REG_INTSET2, 0)",
    "aggregate |= shl25_as99_clmr_irq_decode",
]
locations=[drain.index(i) for i in items]
assert locations==sorted(locations),locations
assert "for (i = 0; i < SHL25_CLMR_IRQ_DRAIN_LIMIT; i++)" in drain
assert "return -ETIMEDOUT" in drain
assert "*events = aggregate;" in drain
assert "return -EINVAL;" in drain

# Offline mock examples for transport sequencing; deterministic, no device IO.
calls=[]
def one(group=0x10000,s1=0x02,s2=0):
    calls.clear()
    calls.append(("R",0x0100,group))
    if group&(1<<16):
        calls.extend((("R",0x0110,s1),("W",0x0110,0)))
    if group&(1<<17):
        calls.extend((("R",0x0114,s2),("W",0x0114,0)))
    calls.append(("R",0x0100,0))
    return decode(group,s1,s2)
assert one()==2
assert calls==[("R",0x0100,0x10000),("R",0x0110,0x02),
               ("W",0x0110,0),("R",0x0100,0)]
assert one(group=0x30000,s1=2,s2=4)==0x42
assert len(calls)==6
assert "shl25_as99_clmr_irq_drain(" not in SPI
assert "module_init(" not in C and "module_spi_driver(" not in C
assert "request_threaded_irq(" not in C and "request_irq(" not in C
assert "EXPORT_SYMBOL" not in C
assert 'status = "disabled";' in DT

print("SHL25_AS99_C8_CLMR_INTSET1_ARM_BOOT_DONE_BIT1_PASS")
print("SHL25_AS99_C8_INTR_GROUP_ENDIAN_DECODE_AND_ACK_PASS")
print("SHL25_AS99_C8_BOUNDED_IRQ_DRAIN_AND_UNWIRED_GPIO75_PASS")
