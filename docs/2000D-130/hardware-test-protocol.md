# First physical-camera test and recovery protocol

## Status

This protocol is prepared in advance of hardware testing.

**Do not execute it yet.** The first physical-camera test remains blocked until:

- the camera is confirmed to be the exact intended model and firmware revision;
- ML2000D-013 has demonstrated the minimal payload in QEMU;
- ML2000D-014 has a passing QEMU smoke test;
- ML2000D-010 has a verified early diagnostic method;
- ML2000D-011 has only verified firmware stubs;
- a non-QEMU `autoexec.bin` has been built specifically for EOS 2000D firmware 1.3.0.

The purpose of preparing this document now is to make the eventual first hardware test deliberate and recoverable rather than improvised.

## Roles

A first hardware session should ideally have:

- one operator responsible for the camera;
- one observer recording timing, LED behavior, and recovery actions.

For a solo test, use the same checklist and record observations immediately after each boot.

## Required equipment

- Canon EOS 1500D / 2000D / Rebel T7;
- fully charged compatible battery;
- AC adapter only if it is known-good and does not complicate battery-removal recovery;
- one known-good development SD card;
- one known-good **rescue SD card** that is not bootable and contains no ML executable;
- SD card reader;
- computer with the exact test build and its hashes;
- a way to record the test log without using the camera being tested.

## Hard preflight gates

All items below must be true before inserting the development card.

### Camera identity

Record:

- marketed model name;
- Canon model identifier if exposed by tooling;
- firmware version shown in Canon's own menu.

Required value for this target:

`Firmware Ver. 1.3.0`

If the displayed firmware is not exactly 1.3.0, stop. Do not assume compatibility.

### Build identity

Record:

- Git commit;
- branch;
- build command;
- compiler version;
- `autoexec.bin` byte size;
- `autoexec.bin` SHA-256;
- source ROM SHA-256 used to derive every active firmware address;
- whether `CONFIG_QEMU` is absent.

A QEMU-only binary must never be used on hardware.

### Enabled surface

For the first test, the build must contain only the minimum loader plus the selected diagnostic payload.

Explicitly forbidden for first execution:

- full ML menu;
- modules;
- RAW video or RAW capture;
- EDMAC experiments;
- FPS/timer overrides;
- sensor-register changes;
- persistent property writes;
- boot-flag/installer experiments;
- arbitrary register pokes;
- unverified debug hooks.

### Recovery readiness

Before the first boot:

1. verify the rescue card boots the camera normally;
2. verify the camera powers off normally with the rescue card;
3. verify the battery can be removed without tools;
4. place the rescue card within reach;
5. write down the abort threshold before powering on.

## Development-card contents

The first hardware card should contain only files required by the tested boot path.

Expected minimal shape:

```text
/
└── autoexec.bin
```

If additional files become required, list them explicitly in the test record and explain why.

Do not place an installer FIR on the first-test card.

## Expected diagnostic

The current planned diagnostic convention is:

- 1 short pulse: loader/cache-patch stage reached;
- 2 short pulses: ML init-task entry reached;
- 3 short pulses: Canon init-task handoff/return reached;
- repeating fast pulses: deliberate fatal/error path.

These meanings are **not approved for hardware use until ML2000D-010 verifies the actual 1.3.0 LED method**.

Before the real test, replace this section with the exact verified pattern and expected maximum interval between stages.

## Abort threshold

The exact timeout must be selected after QEMU timing is known.

Until then:

**TBD — do not perform the test while this value is TBD.**

The final value should be deliberately generous relative to normal boot but short enough to avoid leaving a wedged camera powered indefinitely.

## First boot procedure

1. Confirm the battery is fully charged.
2. Confirm camera firmware is exactly 1.3.0.
3. Confirm the development card contents and `autoexec.bin` SHA-256.
4. Confirm `CONFIG_QEMU` is not present in the build.
5. Confirm rescue card is immediately available.
6. Start the external test log.
7. Insert the development card with the camera powered off.
8. Close the card door completely.
9. Power on once.
10. Observe only; do not press buttons during the initial boot window.
11. Record:
    - power-on time;
    - every LED transition/pattern;
    - LCD activity;
    - lens/mirror/shutter activity, if any;
    - whether Canon UI appears;
    - time to normal UI;
    - any unexpected sound or repeated mechanical action.
12. If the expected success pattern completes and Canon UI becomes normal, power off using the normal switch.
13. If the abort threshold is reached, follow the recovery procedure below.

## Recovery procedure

If the camera is unresponsive:

1. Move the power switch to OFF.
2. Wait for the final documented shutdown interval once that interval has been established.
3. If the camera remains unresponsive, open the battery door and remove the battery.
4. Do not repeatedly power-cycle the same development card.
5. Remove the development card.
6. Insert the known-good rescue card.
7. Reinsert the battery.
8. Power on.
9. Verify stock Canon operation.
10. If stock operation does not return immediately, stop all further ML testing and document the exact state before trying additional recovery actions.

Do not escalate from a failed minimal boot into installer/boot-flag changes.

## Success progression

Do not jump directly to the 10+10 acceptance run.

### Stage A — single cold boot

Require one clean boot, expected diagnostic, normal Canon operation, normal power-off, and normal rescue-card boot.

### Stage B — three cold boots

Repeat three times with battery removal between runs.

No unexplained variation is acceptable.

### Stage C — warm restart/power-cycle sampling

Perform a small number of normal OFF/ON cycles.

### Stage D — acceptance run

Only after A-C are clean:

- 10 cold boots;
- 10 warm/restart cycles;
- successful diagnostic every time;
- Canon reaches normal operation every time;
- rescue/non-ML card always restores stock behavior.

## Stop conditions

Stop the session immediately if any of the following occurs:

- rescue-card behavior differs from stock;
- unexpected persistent state survives card removal;
- repeated shutter/mirror/mechanical cycling;
- unusual heat, smell, battery behavior, or power instability;
- the LED pattern differs between identical cold boots;
- Canon UI becomes corrupt or controls are non-responsive after ML exits;
- shutdown behavior changes;
- a build/hash mismatch is discovered.

## Test record

Use `hardware-test-record.template.json` for every session.

Never overwrite an old record. Keep one immutable record per build/session.

## What this protocol does not authorize

This document does not approve physical testing by itself. It only defines the procedure once the prerequisite technical gates are satisfied.
