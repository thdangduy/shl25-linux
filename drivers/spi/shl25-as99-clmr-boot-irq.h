/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef SHL25_AS99_CLMR_BOOT_IRQ_H
#define SHL25_AS99_CLMR_BOOT_IRQ_H

#include <linux/completion.h>
#include <linux/spinlock.h>
#include <linux/types.h>

#include "shl25-as99-clmr-irq-status.h"
#include "shl25-as99-clmr-spi-bridge.h"

/* Expected OEM line is TLMM GPIO75, rising edge. A future board
 * driver must resolve that GPIO through mainline Linux 6.1 pinctrl
 * and request a *threaded* IRQ (SPI transfer sleeps).
 */
struct shl25_clmr_boot_irq {
	struct completion boot_done;
	spinlock_t lock;
	const struct shl25_clmr_irq_register_ops *regs;
	void *reg_ctx;
	u32 observed_events;
	int boot_result;
	bool initialized;
	bool armed;
	bool terminal_latched;
};

/* Setup is source-only: does not allocate an IRQ or power hardware. */
int shl25_as99_clmr_boot_irq_init(
	struct shl25_clmr_boot_irq *state,
	const struct shl25_clmr_irq_register_ops *regs,
	void *reg_ctx, bool gpio75_rising_verified);

/* Future board driver's threaded IRQ handler calls this (sleepable).
 * Do not call from the top-half IRQ handler or while holding a spinlock.
 */
int shl25_as99_clmr_boot_irq_process(struct shl25_clmr_boot_irq *state);

/* Connects existing C6 boot callbacks to the C8 register decoder,
 * without registering those callbacks on any live device.
 */
extern const struct shl25_clmr_board_irq_ops
	shl25_as99_clmr_boot_irq_callbacks;

#endif
