/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef SHL25_AS99_BDIC_POWER_H
#define SHL25_AS99_BDIC_POWER_H
#include <linux/types.h>

/* No device binding/probe or live power toggles exist in Stage C4. */
enum shl25_bdic_power_action {
	SHL25_BDIC_ACTIVE,
	SHL25_BDIC_STANDBY,
	SHL25_BDIC_VSP_ON,
	SHL25_BDIC_VSP_OFF,
	SHL25_BDIC_VSN_ON,
	SHL25_BDIC_VSN_OFF,
};

struct shl25_bdic_power_ready {
	bool board_power_verified;
	bool clmr_firmware_running;
	bool clmr_fwcmd_channel_verified;
	bool bdic_chipver_read_verified;
	u8 chipver; /* OEM (BDIC_REG_VERSION >> 4) & 0x0f */
};

struct shl25_bdic_fwcmd_ops {
	int (*write_reg)(void *ctx, u8 addr, u8 data);
	int (*mask_write_reg)(void *ctx, u8 addr, u8 data, u8 mask);
	int (*bank_select)(void *ctx, u8 bank);
	void (*delay_us)(void *ctx, unsigned int delay);
};

int shl25_as99_bdic_power_sequence(
	const struct shl25_bdic_fwcmd_ops *ops, void *ctx,
	const struct shl25_bdic_power_ready *ready,
	enum shl25_bdic_power_action action);

#endif
