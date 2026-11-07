// SPDX-License-Identifier: GPL-2.0-only
/*
 * Sharp SHL25 AS99 CLMR firmware boot IRQ status/clear (stage C8).
 *
 * OEM shdisp_lcdc/shdisp_clmr.c shdisp_workqueue_handler_clmr().
 * Source SHA 399f2b8f050709f6c8c08c56e22260e13ba46b2edde363555ebb69487933e7f0.
 *
 * No IRQ request, driver registration or hardware caller exists here.
 * A future verified board driver must own TLMM GPIO75 trigger polarity,
 * IRQ registration/ack and CLMR boot completion lifecycle.
 */
#include <linux/errno.h>
#include <linux/types.h>

#include "shl25-as99-clmr-irq-status.h"

#define SHL25_CLMR_REG_INTR    0x0100
#define SHL25_CLMR_REG_INTSET1 0x0110
#define SHL25_CLMR_REG_INTSET2 0x0114

u32 shl25_as99_clmr_irq_decode(u32 intr, u32 intset1, u32 intset2)
{
	u32 events = 0;

	/*
	 * OEM reads byte array from C2/C4; with BE32 interpretation:
	 *   regINTR[1] & 0x01 => bit16, & 0x02 => bit17.
	 *   reg[3] & 0x02    => INTSET1 low byte bit1 (boot complete).
	 */
	if (intr & SHL25_CLMR_INTR_FW_GROUP) {
		if (intset1 & BIT(0))
			events |= SHL25_CLMR_EVENT_FWCMD_DONE;
		if (intset1 & BIT(1))
			events |= SHL25_CLMR_EVENT_BOOT_DONE;
		if (intset1 & BIT(2))
			events |= SHL25_CLMR_EVENT_EDRAM_DONE;
		if (intset1 & BIT(3))
			events |= SHL25_CLMR_EVENT_FW_ERROR;
	}
	if (intr & SHL25_CLMR_INTR_DET_GROUP) {
		if (intset2 & BIT(0))
			events |= SHL25_CLMR_EVENT_LCD_DET;
		if (intset2 & BIT(1))
			events |= SHL25_CLMR_EVENT_PSALS_DET;
		if (intset2 & BIT(2))
			events |= SHL25_CLMR_EVENT_TE;
	}
	return events;
}

/*
 * Preserve OEM: read INTR; for each enabled group read INTSETx,
 * write ZERO to that register to acknowledge, then process event.
 * Drain bounded number of repeats so a wedged IRQ cannot hang Linux.
 * This function has NO registered caller under Linux 6.1 yet.
 */
int shl25_as99_clmr_irq_drain(
	const struct shl25_clmr_irq_register_ops *ops, void *ctx, u32 *events)
{
	unsigned int i;
	u32 intr, intset1, intset2;
	u32 aggregate = 0;
	int ret;

	if (!ops || !ctx || !events || !ops->read_reg || !ops->write_reg)
		return -EINVAL;
	*events = 0;

	for (i = 0; i < SHL25_CLMR_IRQ_DRAIN_LIMIT; i++) {
		intset1 = 0;
		intset2 = 0;
		ret = ops->read_reg(ctx, SHL25_CLMR_REG_INTR, &intr);
		if (ret)
			return ret;
		if (!(intr & (SHL25_CLMR_INTR_FW_GROUP |
			      SHL25_CLMR_INTR_DET_GROUP))) {
			*events = aggregate;
			return 0;
		}

		if (intr & SHL25_CLMR_INTR_FW_GROUP) {
			ret = ops->read_reg(ctx, SHL25_CLMR_REG_INTSET1,
					    &intset1);
			if (ret)
				return ret;
			ret = ops->write_reg(ctx, SHL25_CLMR_REG_INTSET1, 0);
			if (ret)
				return ret;
		}
		if (intr & SHL25_CLMR_INTR_DET_GROUP) {
			ret = ops->read_reg(ctx, SHL25_CLMR_REG_INTSET2,
					    &intset2);
			if (ret)
				return ret;
			ret = ops->write_reg(ctx, SHL25_CLMR_REG_INTSET2, 0);
			if (ret)
				return ret;
		}
		aggregate |= shl25_as99_clmr_irq_decode(intr, intset1,
						       intset2);
	}
	/* The result is not trusted on an unacknowledged stuck IRQ. */
	*events = aggregate;
	return -ETIMEDOUT;
}
