// SPDX-License-Identifier: GPL-2.0-only
/*
 * Sharp SHL25 / AS99 BDIC panel VSP/VSN source-verified sequence (C4).
 *
 * Source: Sharp OEM bld010105 shdisp_lcdc/data/shdisp_bl71y6_ctrl.h
 * SHA256 f4a034bc613339c92b04c9df94f5a5adcb06ab51dfab53e9ba2ee095e9d2f69b
 *
 * Transactions MUST go through the already running Sharp CLMR FWCMD
 * channel (not guessed Linux I2C). No hardware adapter, probe or caller
 * is provided: the display and CLMR DT nodes remain disabled.
 */
#include <linux/errno.h>
#include <linux/kernel.h>
#include <linux/types.h>

#include "shl25-as99-bdic-power.h"
#include "shl25-as99-bdic-power-tables.h"

static int shl25_bdic_apply(const struct shl25_bdic_fwcmd_ops *ops,
			    void *ctx, const struct shl25_bdic_regop *table,
			    size_t count)
{
	size_t i;
	int ret;

	for (i = 0; i < count; ++i) {
		const struct shl25_bdic_regop *entry = &table[i];

		switch (entry->op) {
		case SHL25_BDIC_OP_STR:
			ret = ops->write_reg(ctx, entry->reg, entry->data);
			break;
		case SHL25_BDIC_OP_SET:
			/* OEM shdisp_bdic_IO_set_bit_reg: mask=val. */
			ret = ops->mask_write_reg(ctx, entry->reg,
						  entry->data, entry->data);
			break;
		case SHL25_BDIC_OP_CLR:
			/* OEM shdisp_bdic_IO_clr_bit_reg: data=0. */
			ret = ops->mask_write_reg(ctx, entry->reg,
						  0, entry->mask);
			break;
		case SHL25_BDIC_OP_RMW:
			ret = ops->mask_write_reg(ctx, entry->reg,
						  entry->data, entry->mask);
			break;
		case SHL25_BDIC_OP_BANK:
			/* OEM uses CLMR FWCMD opcode 0x5F (bank select). */
			ret = ops->bank_select(ctx, entry->data);
			break;
		default:
			return -EOPNOTSUPP;
		}
		if (ret)
			return ret;
		if (entry->wait_us)
			ops->delay_us(ctx, entry->wait_us);
	}
	return 0;
}

/*
 * Caller must have separately brought up CLMR firmware and verified the
 * BDIC chip version. This source-only module has no hardware caller.
 */
int shl25_as99_bdic_power_sequence(
	const struct shl25_bdic_fwcmd_ops *ops, void *ctx,
	const struct shl25_bdic_power_ready *ready,
	enum shl25_bdic_power_action action)
{
	const struct shl25_bdic_regop *table;
	size_t count;

	if (!ops || !ctx || !ready)
		return -EINVAL;
	if (!ready->board_power_verified ||
	    !ready->clmr_firmware_running ||
	    !ready->clmr_fwcmd_channel_verified ||
	    !ready->bdic_chipver_read_verified)
		return -EOPNOTSUPP;
	if (!ops->write_reg || !ops->mask_write_reg ||
	    !ops->bank_select || !ops->delay_us)
		return -EOPNOTSUPP;

	switch (action) {
	case SHL25_BDIC_ACTIVE:
		table = shl25_bdic_active;
		count = ARRAY_SIZE(shl25_bdic_active);
		break;
	case SHL25_BDIC_STANDBY:
		table = shl25_bdic_standby;
		count = ARRAY_SIZE(shl25_bdic_standby);
		break;
	case SHL25_BDIC_VSP_ON:
		table = shl25_bdic_vsp_on;
		count = ARRAY_SIZE(shl25_bdic_vsp_on);
		break;
	case SHL25_BDIC_VSP_OFF:
		table = shl25_bdic_vsp_off;
		count = ARRAY_SIZE(shl25_bdic_vsp_off);
		break;
	case SHL25_BDIC_VSN_ON:
		if (ready->chipver == 0) {
			table = shl25_bdic_vsn_on_ts1;
			count = ARRAY_SIZE(shl25_bdic_vsn_on_ts1);
		} else {
			table = shl25_bdic_vsn_on;
			count = ARRAY_SIZE(shl25_bdic_vsn_on);
		}
		break;
	case SHL25_BDIC_VSN_OFF:
		table = shl25_bdic_vsn_off;
		count = ARRAY_SIZE(shl25_bdic_vsn_off);
		break;
	default:
		return -EINVAL;
	}
	return shl25_bdic_apply(ops, ctx, table, count);
}
