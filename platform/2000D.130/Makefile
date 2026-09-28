# Canon EOS 2000D / 1500D / Rebel T7 — firmware 1.3.0
#
# Phase 1 safe platform skeleton.
#
# This file intentionally refuses a normal camera build until the
# firmware-specific values below have been verified against the exact
# Canon 1.3.0 ROM. Do not populate them from 2000D.110 or 1300D builds.

MODEL = 2000D
FW_VERSION = 130
TOP_DIR = ../..

# CPU architecture is a hardware property. The historical 2000D.110
# Magic Lantern port used armv5te, consistent with this DIGIC IV body.
PLATFORM_ARCH = armv5te

# These variables are intentionally empty in Phase 1.
# Promote values here only with ROM-backed evidence from ML2000D-005/008/009.
PORT_MAIN_FIRMWARE_ADDR ?=
PORT_RESTARTSTART ?=
PORT_ML_BOOT_OBJ ?=

.PHONY: preflight clean

# preflight and clean must remain usable even while the camera target is
# intentionally incomplete.
ifeq ($(filter preflight clean,$(MAKECMDGOALS)),)

ifeq ($(strip $(PORT_MAIN_FIRMWARE_ADDR)),)
$(error 2000D.130: MAIN_FIRMWARE_ADDR is intentionally unset; verify the firmware 1.3.0 ROM first (ML2000D-005 / ML2000D-008))
endif
ifeq ($(strip $(PORT_RESTARTSTART)),)
$(error 2000D.130: RESTARTSTART is intentionally unset; verify the 1.3.0 RAM/BSS/heap map first (ML2000D-005 / ML2000D-008))
endif
ifeq ($(strip $(PORT_ML_BOOT_OBJ)),)
$(error 2000D.130: ML_BOOT_OBJ is intentionally unset; verify the 1.3.0 boot/cache-hack path first (ML2000D-005 / ML2000D-009))
endif

MAIN_FIRMWARE_ADDR = $(PORT_MAIN_FIRMWARE_ADDR)
RESTARTSTART = $(PORT_RESTARTSTART)
ML_BOOT_OBJ = $(PORT_ML_BOOT_OBJ)

include ../Makefile
.DEFAULT_GOAL := $(BUILD_DIR)/cam_complete

else

preflight:
	@echo "2000D.130 Phase 1 platform skeleton"
	@echo "  MODEL=$(MODEL)"
	@echo "  FW_VERSION=$(FW_VERSION)"
	@echo "  PLATFORM_ARCH=$(PLATFORM_ARCH)"
	@echo "  firmware-specific addresses: intentionally unset"
	@echo "  normal build: intentionally blocked until ROM-backed values are supplied"

clean:
	@rm -rf -- build

endif
