# OPPO Mirror 5 A51w - verified original A.17 BOOT and Recovery, ARM32.
DEVICE_PATH := device/oppo/a51w
TARGET_BOARD_PLATFORM := msm8916
TARGET_BOOTLOADER_BOARD_NAME := MSM8916
TARGET_NO_BOOTLOADER := true
TARGET_ARCH := arm
TARGET_ARCH_VARIANT := armv7-a-neon
TARGET_CPU_ABI := armeabi-v7a
TARGET_CPU_ABI2 := armeabi
TARGET_CPU_VARIANT := generic

# Actual A51w: uname armv7l, ro.product.cpu.abi armeabi-v7a,
# ro.zygote=zygote32, stock kernel ARM zImage magic 0x016f2818.
# Original BOOT A.17: load 0x80008000, ramdisk 0x81000000,
# tags 0x80000100, pagesize 2048, Qualcomm QCDT v3 (1,687,552 B).
TARGET_PREBUILT_KERNEL := $(DEVICE_PATH)/prebuilt/kernel
TARGET_KERNEL_ARCH := arm
TARGET_KERNEL_HEADER_ARCH := arm
BOARD_KERNEL_BASE := 0x80000000
BOARD_KERNEL_PAGESIZE := 2048
# Required by legacy Android 6 assert-max-image-size: without it,
# image-size-from-data-size divides by zero during recovery.img packaging.
# 128 KiB is a build-time image accounting block, NOT an eMMC erase size.
BOARD_FLASH_BLOCK_SIZE := 131072
BOARD_KERNEL_CMDLINE := console=ttyHSL0,115200,n8 androidboot.console=ttyHSL0 androidboot.hardware=qcom user_debug=30 msm_rtb.filter=0x3F ehci-hcd.park=3 androidboot.bootdevice=7824900.sdhci lpm_levels.sleep_disabled=1 androidboot.selinux=permissive
BOARD_MKBOOTIMG_ARGS := --kernel_offset 0x00008000 --ramdisk_offset 0x01000000 --tags_offset 0x00000100 --dt $(DEVICE_PATH)/prebuilt/dt.img

# Live A51w GPT: recovery mmcblk0p23 = 32 MiB.
BOARD_RECOVERYIMAGE_PARTITION_SIZE := 33554432
TARGET_RECOVERY_FSTAB := $(DEVICE_PATH)/recovery/root/etc/recovery.fstab
TARGET_USERIMAGES_USE_EXT4 := true

TW_THEME := portrait_hdpi
TW_BRIGHTNESS_PATH := /sys/class/leds/lcd-backlight/brightness
TW_CUSTOM_BATTERY_PATH := /sys/class/power_supply/battery
TW_INTERNAL_STORAGE_PATH := /data/media
TW_INTERNAL_STORAGE_MOUNT_POINT := data
TW_EXTERNAL_STORAGE_PATH := /external_sd
TW_EXTERNAL_STORAGE_MOUNT_POINT := external_sd
RECOVERY_SDCARD_ON_DATA := true
TW_NEW_ION_HEAP := true
RECOVERY_GRAPHICS_USE_LINELENGTH := true
TW_INPUT_BLACKLIST := accelerometer
TW_IGNORE_ABS_MT_TRACKING_ID := true

# Initial diagnostic build: no destructive operations enabled by the CI.
# Do not flash or change firmware until fastboot boot is proven.
