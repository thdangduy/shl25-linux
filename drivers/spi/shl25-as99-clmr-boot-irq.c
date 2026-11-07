// SPDX-License-Identifier: GPL-2.0-only
/*
 * Sharp SHL25 / AS99 CLMR boot-completion broker (Stage C9).
 *
 * OEM shdisp_clmr.c devm_request_irq(..., IRQF_TRIGGER_RISING, ...);
 * shdisp_clmr_boot_start(): reinit completion before ARM start;
 * INTSET1 bit1: ARM FW startup-complete, INTSET1 bit3: async error.
 *
 * This bridge has no IRQ request, platform driver or probe registration.
 * The OEM GPIO75 mapping must be validated by a future Linux 6.1 board
 * driver before GPIO/PMIC/clock hardware can be enabled.
 */
#include <linux/completion.h>
#include <linux/errno.h>
#include <linux/jiffies.h>
#include <linux/spinlock.h>

#include "shl25-as99-clmr-boot-irq.h"

int shl25_as99_clmr_boot_irq_init(
	struct shl25_clmr_boot_irq *state,
	const struct shl25_clmr_irq_register_ops *regs,
	void *reg_ctx, bool gpio75_rising_verified)
{
	if (!state || !regs || !reg_ctx)
		return -EINVAL;
	if (!gpio75_rising_verified)
		return -EOPNOTSUPP;
	if (!regs->read_reg || !regs->write_reg)
		return -EOPNOTSUPP;
	if (state->initialized)
		return -EALREADY;

	init_completion(&state->boot_done);
	spin_lock_init(&state->lock);
	state->regs = regs;
	state->reg_ctx = reg_ctx;
	state->observed_events = 0;
	state->boot_result = -EINPROGRESS;
	state->armed = false;
	state->terminal_latched = false;
	state->initialized = true;
	return 0;
}

static int shl25_clmr_arm_boot(void *ctx)
{
	struct shl25_clmr_boot_irq *state = ctx;
	unsigned long flags;

	if (!state || !state->initialized)
		return -EOPNOTSUPP;

	spin_lock_irqsave(&state->lock, flags);
	if (state->armed) {
		spin_unlock_irqrestore(&state->lock, flags);
		return -EBUSY;
	}
	reinit_completion(&state->boot_done);
	state->boot_result = -EINPROGRESS;
	state->observed_events = 0;
	state->terminal_latched = false;
	state->armed = true;
	spin_unlock_irqrestore(&state->lock, flags);
	return 0;
}

static int shl25_clmr_wait_boot(void *ctx, unsigned int timeout_ms)
{
	struct shl25_clmr_boot_irq *state = ctx;
	unsigned long flags;
	unsigned long completed;
	int ret;

	if (!state || !state->initialized || !timeout_ms)
		return -EINVAL;

	completed = wait_for_completion_timeout(&state->boot_done,
						msecs_to_jiffies(timeout_ms));
	spin_lock_irqsave(&state->lock, flags);
	if (!completed) {
		state->armed = false;
		state->boot_result = -ETIMEDOUT;
		ret = -ETIMEDOUT;
	} else {
		ret = state->boot_result;
		state->armed = false;
	}
	spin_unlock_irqrestore(&state->lock, flags);
	return ret;
}

/* Called only from future verified Linux 6.1 threaded IRQ context.
 * shl25_as99_clmr_irq_drain() uses sleeping SPI read/write callbacks.
 */
int shl25_as99_clmr_boot_irq_process(struct shl25_clmr_boot_irq *state)
{
	unsigned long flags;
	u32 events = 0;
	bool signal = false;
	int ret;

	if (!state || !state->initialized)
		return -EOPNOTSUPP;
	ret = shl25_as99_clmr_irq_drain(state->regs, state->reg_ctx, &events);

	spin_lock_irqsave(&state->lock, flags);
	state->observed_events |= events;
	if (state->armed && !state->terminal_latched &&
	    (ret || (events & (SHL25_CLMR_EVENT_BOOT_DONE |
			      SHL25_CLMR_EVENT_FW_ERROR)))) {
		/* Error and stuck-IRQ have priority over boot complete. */
		state->boot_result = ret ? ret :
			(events & SHL25_CLMR_EVENT_FW_ERROR ? -EIO : 0);
		state->terminal_latched = true;
		signal = true;
	}
	spin_unlock_irqrestore(&state->lock, flags);
	if (signal)
		complete(&state->boot_done);
	return ret;
}

/* Future board code may pass (&shl25_as99_clmr_boot_irq_callbacks,
 * boot_irq_context) into the C6 bridge; no caller exists yet.
 */
const struct shl25_clmr_board_irq_ops shl25_as99_clmr_boot_irq_callbacks = {
	.arm_boot_completion = shl25_clmr_arm_boot,
	.wait_boot_completion = shl25_clmr_wait_boot,
};
