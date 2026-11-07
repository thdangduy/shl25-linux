// SPDX-License-Identifier: GPL-2.0-only
/*
 * Sharp SHL25 / AS99 CLMR SPI command transport — Linux 6.1 stage C0.
 *
 * Source: GPL bld010105, drivers/sharp/shdisp_lcdc/shdisp_system.c
 * Correct device compatible: sharp,mipi_spi_0 at SPI1.0 (f9923000).
 *
 * Exact register transfers:
 *  write: 0xc0, reg_hi, reg_lo, four value bytes (OEM: host little endian).
 *  read:  0xc2, reg_hi, reg_lo; separate SPI message
 *         0xc4, dummy4, collect rx bytes [1:5].
 * OEM: 50MHz write, 20MHz read, 8 bits, SPI mode 3 + CS_HIGH in DTS.
 *
 * WARNING: This is a transport implementation, NOT a complete Sharp
 * CLMR driver. No register access or firmware download is performed by
 * probe. All register I/O stays fail-closed until BDIC power/reset,
 * clock/PLL, CLMR firmware loading and validated sequencing are ready.
 * Board DTS status remains disabled. Do not claim Linux 6.1 LCD PASS.
 */
#include <linux/errno.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/slab.h>
#include <linux/spi/spi.h>
#include <linux/string.h>

#define SHL25_CLMR_SPI_WRITE_HZ 50000000U
#define SHL25_CLMR_SPI_READ_HZ  20000000U
#define SHL25_CLMR_OP_WRITE    0xc0
#define SHL25_CLMR_OP_SELECT   0xc2
#define SHL25_CLMR_OP_FETCH    0xc4

struct shl25_clmr_spi {
	struct spi_device *spi;
	struct mutex io_lock;
	bool bdic_power_validated;
	bool firmware_running;
	bool clmr_pll_clock_ready;
};

static int shl25_clmr_ensure_boot_ready(const struct shl25_clmr_spi *clmr)
{
	if (!clmr->bdic_power_validated ||
	    !clmr->clmr_pll_clock_ready)
		return -EOPNOTSUPP;

	return 0;
}

/*
 * Firmware command queue is post-boot only. Keep this separate from
 * register access required by the ROM firmware loader.
 */
static int __maybe_unused
shl25_clmr_ensure_runtime_ready(const struct shl25_clmr_spi *clmr)
{
	if (shl25_clmr_ensure_boot_ready(clmr))
		return -EOPNOTSUPP;
	if (!clmr->firmware_running)
		return -EOPNOTSUPP;
	return 0;
}

/* OEM byte ordering is explicitly preserved, never cast unaligned u32. */
static int __maybe_unused shl25_clmr_reg_write(struct shl25_clmr_spi *clmr,
					      u16 reg, const u8 data[4])
{
	u8 tx[7] = {
		SHL25_CLMR_OP_WRITE, (u8)(reg >> 8), (u8)reg,
		0, 0, 0, 0
	};
	struct spi_transfer t = {
		.tx_buf = tx,
		.len = sizeof(tx),
		.bits_per_word = 8,
		.speed_hz = SHL25_CLMR_SPI_WRITE_HZ,
	};
	int ret;

	if (!data)
		return -EINVAL;
	memcpy(tx + 3, data, 4);

	ret = shl25_clmr_ensure_boot_ready(clmr);
	if (ret)
		return ret;

	mutex_lock(&clmr->io_lock);
	ret = spi_sync_transfer(clmr->spi, &t, 1);
	mutex_unlock(&clmr->io_lock);

	return ret;
}

static int __maybe_unused shl25_clmr_reg_read(struct shl25_clmr_spi *clmr,
					     u16 reg, u8 out[4])
{
	u8 select[] = { SHL25_CLMR_OP_SELECT, (u8)(reg >> 8), (u8)reg };
	u8 fetch[] = { SHL25_CLMR_OP_FETCH, 0, 0, 0, 0 };
	u8 rx[5] = { 0 };
	struct spi_transfer addr_xfer = {
		.tx_buf = select,
		.len = sizeof(select),
		.bits_per_word = 8,
		.speed_hz = SHL25_CLMR_SPI_READ_HZ,
	};
	struct spi_transfer data_xfer = {
		.tx_buf = fetch,
		.rx_buf = rx,
		.len = sizeof(fetch),
		.bits_per_word = 8,
		.speed_hz = SHL25_CLMR_SPI_READ_HZ,
	};
	int ret;

	if (!out)
		return -EINVAL;

	ret = shl25_clmr_ensure_boot_ready(clmr);
	if (ret)
		return ret;

	mutex_lock(&clmr->io_lock);
	/* OEM uses two distinct spi_sync() calls: CS release between them. */
	ret = spi_sync_transfer(clmr->spi, &addr_xfer, 1);
	if (!ret)
		ret = spi_sync_transfer(clmr->spi, &data_xfer, 1);
	mutex_unlock(&clmr->io_lock);

	if (ret)
		return ret;

	memcpy(out, rx + 1, 4);
	return 0;
}

static int shl25_clmr_spi_probe(struct spi_device *spi)
{
	struct shl25_clmr_spi *clmr;

	clmr = devm_kzalloc(&spi->dev, sizeof(*clmr), GFP_KERNEL);
	if (!clmr)
		return -ENOMEM;

	clmr->spi = spi;
	mutex_init(&clmr->io_lock);

	/*
	 * Intentionally no register I/O or GPIO/regulator toggling here.
	 * These flags must remain false until separate Sharp CLMR firmware,
	 * BDIC power and reset/PLL drivers are implemented and verified.
	 */
	spi_set_drvdata(spi, clmr);
	dev_info(&spi->dev,
		 "AS99 CLMR SPI transport staged; power/firmware not enabled\n");
	return 0;
}

static const struct of_device_id shl25_clmr_of_match[] = {
	{ .compatible = "sharp,mipi_spi_0" },
	{ }
};
MODULE_DEVICE_TABLE(of, shl25_clmr_of_match);

static struct spi_driver shl25_clmr_spi_driver = {
	.driver = {
		.name = "shl25-as99-clmr-spi",
		.of_match_table = shl25_clmr_of_match,
	},
	.probe = shl25_clmr_spi_probe,
};
module_spi_driver(shl25_clmr_spi_driver);

MODULE_DESCRIPTION("Sharp SHL25 AS99 CLMR SPI transport (power/firmware gated)");
MODULE_LICENSE("GPL");
