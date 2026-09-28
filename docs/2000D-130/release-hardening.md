# Release hardening plan

## Current status

**Not release-ready.**

This document prepares the later release phase without creating an installer, boot-flag mechanism, or public test binary.

## Release gates

### Exact identity guard

A public build must refuse unsupported combinations.

At minimum it must distinguish:

- EOS 1500D / 2000D / Rebel T7 family;
- exact firmware revision 1.3.0.

A model-name match alone is insufficient.

### Reproducible build record

For every distributed artifact record:

- Git commit;
- upstream baseline commit;
- compiler/toolchain versions;
- exact build command;
- enabled config/features/modules;
- `autoexec.bin` SHA-256;
- source ROM SHA-256 used for reverse engineering.

### Evidence gates

A public test build requires:

- canonical ROM identified;
- verified loader/cache-hack constants;
- QEMU minimal payload pass;
- automated QEMU smoke pass;
- physical minimal boot pass;
- recovery/shutdown validation pass;
- restricted core/menu pass;
- feature matrix identifying every enabled capability.

### Installer policy

Do not create or distribute an installer FIR until:

- runtime `autoexec.bin` testing is stable;
- model/firmware identity checking is proven;
- boot-flag behavior and recovery are independently documented;
- at least one recovery path has been tested deliberately.

Never reuse another camera's installer FIR.

### Artifact policy

A future experimental release should include:

- `autoexec.bin`;
- checksums;
- exact supported model/firmware statement;
- known-issues/recovery instructions;
- feature matrix snapshot;
- source commit link.

Do not label an artifact stable merely because it boots.

## External beta gate

Before inviting broader testers:

- define tester prerequisites;
- require exact firmware confirmation;
- require backup/rescue card;
- define log collection;
- define stop conditions;
- cap enabled features to hardware-tested items;
- establish a way to associate every report with an exact build hash.

## Crash/log collection

Prepare to collect:

- ML logs;
- QEMU traces for reproducible cases;
- crash logs where available;
- exact camera mode at failure;
- build/hash identity.

Do not request or publish Canon firmware dumps as part of bug reports.

## Release manifest

Use `release-manifest.template.json`.

It intentionally starts with every release gate false.
