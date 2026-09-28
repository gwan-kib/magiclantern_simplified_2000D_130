# EOS 2000D feature validation matrix

## Status vocabulary

- **Disabled** — not active in the port.
- **Compiles** — builds, but has no runtime evidence.
- **QEMU-tested** — relevant behavior has been observed in the emulator.
- **Hardware-tested** — focused physical-camera test passed.
- **Experimental** — enabled for limited testing with known constraints.
- **Stable** — repeated hardware use passed the documented test plan.

CI requires any feature explicitly enabled in `platform/2000D.130/features.h` to have a machine-readable matrix entry with supporting evidence.

During bring-up, `features.h` is an explicit allowlist. Including `all_features.h` is forbidden.

| Feature | Current status | Risk | Required before enablement |
|---|---|---|---|
| Histogram | Disabled | Low–medium | stable bitmap + Live View |
| Screenshot | Disabled | Low–medium | stable bitmap + file I/O |
| Show free memory | Disabled | Low | allocator accounting + menu |
| Intervalometer | Disabled | Medium | tasking + timers + shooting control |
| Cropmarks | Disabled | Low–medium | bitmap + file I/O |
| Zebra | Disabled | Medium | Live View + bitmap |
| Focus peaking | Disabled | Medium | Live View + bitmap |
| Magic Zoom | Disabled | Medium | Live View + bitmap + GUI |
| FPS override | Disabled | High | verified timing registers + dedicated hardware tests |
| Exposure override | Disabled | High | verified exposure internals |
| White balance control | Disabled | High | persistent-property safety |
| HDR bracketing | Disabled | High | persistent-property + shooting-control safety |

The authoritative machine-readable form is `feature-matrix.json`.

## Feature promotion procedure

Before changing `features.h`:

1. add/update the matrix entry;
2. identify required stubs/constants;
3. write a focused test procedure;
4. attach static/QEMU/hardware evidence;
5. select the next status;
6. only then enable the macro.

A feature must never jump directly from Disabled to Stable.
