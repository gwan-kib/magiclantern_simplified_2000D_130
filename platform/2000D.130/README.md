# EOS 2000D / Rebel T7 — firmware 1.3.0 platform status

This directory is a **safe Phase 1 skeleton**, not a working camera port.

A normal build is intentionally blocked until firmware-specific constants
are verified against an exact Canon 1.3.0 ROM dump. This prevents historical
addresses from older firmware or related cameras from accidentally becoming
executable code.

## Established without copying firmware addresses

- Model family: Canon EOS 1500D / 2000D / Rebel T7.
- Target firmware for this directory: 1.3.0.
- Hardware generation: DIGIC IV+.
- Architecture: `armv5te`. The historical Magic Lantern 2000D.110 port
  used this architecture; firmware updates do not change the camera CPU.
- Physical capabilities represented in `internals.h`: Live View, movie
  recording, and 4:3 display.

## Historical 2000D.110 reference

An older Magic Lantern development branch contains a real
`platform/2000D.110` port. It is valuable because it confirms the same
camera hardware was previously approached using:

- ROM base candidate `0xFE0C0000`;
- restart/memory-reservation candidate `0xC80000`;
- cache-hack loader candidate `boot-d45-ch.o`;
- new-style DryOS task-hook logic.

These are **reference candidates only** for firmware 1.3.0. None are enabled
in this directory.

The old 1.1.0 source also contains many hard-coded startup, DryOS, GUI,
display, and I/O addresses. Those values are deliberately absent here.

## Original 1.3.0 experimental-fork observations

The README from the experimental 1.3.0 fork reported:

- successful ROM dump;
- firmware signature `0xea000001` at `0xFE0C0000`;
- intended `boot-d45-ch.o` loader;
- task-structure / DryOS mapping as a compile blocker.

The public repository did not contain the ROM, a ROM hash, a
`platform/2000D.130` implementation, or disassembly evidence for those
claims. They therefore remain leads until reproduced.

## Required before normal builds are enabled

1. Identify the exact 1.3.0 ROM by size and SHA-256.
2. Verify ROM mapping and the main firmware entry.
3. Map RAM/BSS/heap behavior and establish a safe `RESTARTSTART`.
4. Verify the cache-hack/startup patch path and choose `ML_BOOT_OBJ`.
5. Determine the exact DryOS `task` and `task_attr` layouts.
6. Add only the minimal verified firmware stubs required for the first
   payload.

## Safe checks

Run:

```bash
make -C platform/2000D.130 preflight
```

This confirms that the build system can find the target and reports the
known architecture without creating an executable camera binary.

Running a normal `make` is expected to fail loudly until the verified
firmware-specific variables are populated. That failure is intentional.

## Do not

- copy addresses from `2000D.110`, `1300D`, `1100D`, or any other
  camera into executable definitions;
- select `CONFIG_TASK_STRUCT_*` solely to make compilation pass;
- enable persistent property writes;
- create or reuse an installer FIR;
- put any output from this skeleton on a physical camera.
