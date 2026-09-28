# Restricted core bring-up plan

## Goal

Bring up the smallest useful Magic Lantern core after the minimal loader has already proven safe in QEMU and on hardware.

This document prepares ML2000D-018 through ML2000D-022 without enabling any firmware-specific API prematurely.

## Order of operations

The core should be expanded in this order:

1. task primitives;
2. debug logging;
3. memory allocation/free;
4. semaphores and queues;
5. timers;
6. file I/O read-only;
7. file I/O write/create/rename/remove;
8. GUI event observation;
9. bitmap display;
10. restricted menu.

Do not enable a later layer merely because it compiles.

## Evidence rule

Every firmware-address-backed API must have:

- exact firmware 1.3.0 ROM SHA-256;
- address;
- identification method;
- historical comparison, if used;
- static review;
- QEMU observation when practical;
- hardware observation before it becomes part of the stable core.

The machine-readable evidence file is:

`docs/2000D-130/stub-evidence.json`

CI validates that any active `NSTUB` / `THUMB_FN` in `platform/2000D.130/stubs.S` has a matching evidence record.

## Subsystem staging

### A. Tasking

Candidate interfaces:

- `task_create`;
- task-info/current-task helpers;
- `msleep`.

First test:

- create one harmless diagnostic task;
- emit a bounded log/LED marker;
- exit cleanly.

### B. Logging

Candidate interfaces:

- `DryosDebugMsg`;
- any safe existing ML/QEMU debug channel.

Do not depend on logging for recovery.

### C. Memory

Candidate interfaces:

- malloc/free equivalents;
- ML reserved-memory accounting.

Use the procedure in `memory-validation.md`.

### D. Synchronization

Bring up one primitive at a time:

- semaphore create/take/give;
- message queue create/send/receive;
- timer create/start/stop.

Each gets a bounded self-test before use by the menu/core.

### E. File I/O

Start read-only.

Then test write operations in a dedicated ML test directory.

Do not touch Canon configuration files.

Target interfaces include:

- open;
- read;
- write;
- seek;
- close;
- create;
- remove;
- rename.

### F. GUI input

Use the plan in `gui-bringup.md`.

Initial goal is observation, not interception.

### G. Display

Use the plan in `display-bringup.md`.

Initial goal is a harmless overlay that can always be removed.

### H. Restricted menu

Use `restricted-core.md`.

The first menu must expose only diagnostic/status functions and safe file-backed settings.

## Promotion rule

A subsystem progresses through:

`Disabled → Static-verified → QEMU-tested → Hardware-tested → Core-approved`

No core code should depend on a subsystem before it reaches the required stage for that test.
