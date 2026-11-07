/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef SHL25_AS99_CLMR_IRQ_STATUS_H
#define SHL25_AS99_CLMR_IRQ_STATUS_H

#include <linux/bits.h>
#include <linux/types.h>

/* Values from selected Sharp bld010105 shdisp_lcdc/shdisp_clmr.c. */
#define SHL25_CLMR_INTR_FW_GROUP     BIT(16) /* OEM regINTR[1] & 1 */
#define SHL25_CLMR_INTR_DET_GROUP    BIT(17) /* OEM regINTR[1] & 2 */

#define SHL25_CLMR_EVENT_FWCMD_DONE  BIT(0)
#define SHL25_CLMR_EVENT_BOOT_DONE   BIT(1)
#define SHL25_CLMR_EVENT_EDRAM_DONE  BIT(2)
#define SHL25_CLMR_EVENT_FW_ERROR    BIT(3)
#define SHL25_CLMR_EVENT_LCD_DET     BIT(4)
#define SHL25_CLMR_EVENT_PSALS_DET   BIT(5)
#define SHL25_CLMR_EVENT_TE         BIT(6)

#define SHL25_CLMR_IRQ_DRAIN_LIMIT 32U

/* Callback transport is injected by a future board IRQ handler; C8
 * does NOT request GPIO75 or select an unverified IRQ trigger mode.
 */
struct shl25_clmr_irq_register_ops {
	int (*read_reg)(void *ctx, u16 reg, u32 *out);
	int (*write_reg)(void *ctx, u16 reg, u32 value);
};

u32 shl25_as99_clmr_irq_decode(u32 intr, u32 intset1, u32 intset2);
int shl25_as99_clmr_irq_drain(
	const struct shl25_clmr_irq_register_ops *ops, void *ctx, u32 *events);

#endif
