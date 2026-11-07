/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef SHL25_AS99_CLMR_SPI_BRIDGE_H
#define SHL25_AS99_CLMR_SPI_BRIDGE_H

#include <linux/types.h>

struct spi_device;
struct shl25_clmr_boot_prereqs;

/*
 * The AS99 CLMR IRQ source must be mapped and acknowledged by the board
 * driver. Generic SPI IRQ signaling is NOT the CLMR firmware boot IRQ.
 */
struct shl25_clmr_board_irq_ops {
	int (*arm_boot_completion)(void *ctx);
	int (*wait_boot_completion)(void *ctx, unsigned int timeout_ms);
};

/*
 * Board-only activation entry point. Not exported, invoked, or
 * wired into the SPI probe in Stage C6. All board prerequisites must
 * be checked independently by the future power/reset/IRQ driver.
 *
 * Loads sharp/shl25-as99-clmr.bin from Linux firmware loader and
 * validates its SHA-256 inside the C3 executor before any SPI I/O.
 */
int shl25_as99_clmr_bridge_boot(
	struct spi_device *spi,
	const struct shl25_clmr_boot_prereqs *prereqs,
	const struct shl25_clmr_board_irq_ops *irq_ops, void *irq_ctx);

#endif
