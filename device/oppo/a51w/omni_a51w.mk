$(call inherit-product, vendor/omni/config/common.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/full_base_telephony.mk)

PRODUCT_DEVICE := a51w
PRODUCT_NAME := omni_a51w
PRODUCT_BRAND := OPPO
PRODUCT_MODEL := A51w
PRODUCT_MANUFACTURER := OPPO
PRODUCT_COPY_FILES += \
    $(LOCAL_PATH)/recovery/root/etc/recovery.fstab:recovery/root/etc/recovery.fstab
