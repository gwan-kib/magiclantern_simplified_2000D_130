# Restricted Magic Lantern core policy

## Purpose

Define the first integrated ML configuration for ML2000D-022 before any user feature expansion.

## Allowed initial capabilities

Once their dependencies are hardware-tested:

- core tasking;
- memory allocation;
- debug/status logging;
- read-only file access;
- controlled log/settings file writes in ML-owned paths;
- button navigation required for the ML menu;
- bitmap menu rendering;
- About / Port Status / Debug Status pages;
- explicit exit/back behavior.

## Explicitly disabled

The first restricted core must not enable:

- `CONFIG_PROP_REQUEST_CHANGE`;
- RAW Live View or RAW photo capture;
- RAW/MLV recording modules;
- EDMAC experiments;
- FPS override;
- frame ISO/shutter overrides;
- sensor register writes;
- arbitrary DIGIC register pokes;
- installer/boot-flag code;
- persistent Canon property changes;
- unverified modules;
- feature bundles via `#include "all_features.h"`.

## Settings policy

Initial persistent settings must be ML-owned files on the SD card only.

Do not use Canon NVRAM properties for settings.

## Menu policy

Initial menu entries should be limited to:

- Port status;
- firmware/build identity;
- memory status;
- diagnostic log controls;
- safe settings-file test;
- clean menu exit.

Avoid feature toggles until the feature matrix contains evidence for them.

## Build policy

`platform/2000D.130/features.h` remains an explicit allowlist.

Do not include `all_features.h` for this port during bring-up.

CI enforces this rule through `tools/eos2000d/feature_matrix.py` and `port_policy.py`.

## Promotion gate

The restricted core is ready for feature work only after:

- repeated normal boot/shutdown;
- no memory overlap/leak evidence;
- stable file I/O;
- stable GUI navigation;
- stable bitmap overlay/menu;
- Canon photo/video basics still behave normally;
- rescue-card stock boot remains unchanged.
