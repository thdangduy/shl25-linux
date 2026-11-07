/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef SHL25_AS99_CLMR_BOOT_H
#define SHL25_AS99_CLMR_BOOT_H
#include <linux/types.h>

/* The selection is a sourced OEM compile-time variant, not an auto-guess. */
enum shl25_clmr_det_mode {
	SHL25_CLMR_DET_UNVERIFIED = 0,
	SHL25_CLMR_DET_ENABLED,
	SHL25_CLMR_DET_NOT_SUPPORTED,
};

/*
 * All fields are intentionally FALSE until verified by *separate* board
 * power/clock/reset/calibration drivers. Nothing in probe sets them.
 */
struct shl25_clmr_boot_prereqs {
	bool pmic_rails_verified;
	bool clmr_reset_verified;
	bool spi_bus_verified;
	bool clock_pll_verified;
	bool firmware_sha_verified;
	bool boot_irq_verified;
	enum shl25_clmr_det_mode det_mode;
};

/*
 * The adapter MUST:
 *  - use Sharp SPI (register read C2/C4, write C0 + BE 32-bit word);
 *  - stream exactly 59,136 bytes with OEM C7/C8 framing;
 *  - arm completion BEFORE ARMHOSTSYS boot register is written;
 *  - return 0 only for successful command/IRQ completion.
 * No hardware adapter is wired in this stage.
 */
struct shl25_clmr_boot_ops {
	/* CLMR DEVCODE preflight runs only AFTER firmware SHA verification,
	 * but BEFORE the first destructive register write. */
	int (*validate_device)(void *ctx);
	int (*write_reg)(void *ctx, u16 reg, u32 value);
	int (*read_reg)(void *ctx, u16 reg, u32 *value);
	int (*stream_firmware)(void *ctx, const u8 *fw, size_t bytes);
	int (*arm_boot_completion)(void *ctx);
	int (*wait_boot_completion)(void *ctx, unsigned int timeout_ms);
};

int shl25_as99_clmr_boot_sequence(
	const struct shl25_clmr_boot_ops *ops, void *ctx,
	const struct shl25_clmr_boot_prereqs *ready,
	const u8 *firmware, size_t firmware_bytes);

#endif
