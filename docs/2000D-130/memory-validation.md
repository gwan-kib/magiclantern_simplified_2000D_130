# Memory reservation and allocator validation

## Purpose

Prepare ML2000D-019 so memory safety can be measured rather than inferred once the loader/core is executable.

## What must be proven

- ML's reserved region does not overlap Canon BSS, heaps, stacks, VRAM, or other active buffers.
- `RESTARTSTART` is valid for firmware 1.3.0.
- ML allocation/free does not progressively reduce Canon or ML free memory.
- canaries around ML-owned regions remain intact.
- repeated boot/use/shutdown cycles do not change the memory map unexpectedly.

## Static phase

From firmware analysis, record:

- Canon BSS start/end;
- early allocator boundaries;
- DryOS heap(s);
- AllocateMemory/SRM pools where relevant;
- ML relocation start/end;
- known frame/display buffers.

Draw a sorted interval map before enabling the full core.

Any overlap is a hard failure.

## Runtime checkpoints

At minimum capture memory statistics at:

1. Canon startup before ML core;
2. immediately after ML reservation;
3. after ML core init;
4. after restricted menu opens;
5. after one settings/log write;
6. before shutdown.

Repeat across multiple boots.

## Canary strategy

Where practical, place guard words immediately outside ML-owned test allocations.

Example diagnostic values:

- head canary: `0x4D4C4844` ("MLHD");
- tail canary: `0x4D4C544C` ("MLTL").

These are diagnostic values only, not firmware constants.

Check canaries:

- after allocation;
- after representative task/file/menu activity;
- before free;
- before shutdown.

Any corruption stops testing.

## Leak/drift analysis

The repository includes `tools/eos2000d/memory_report.py` for structured test logs.

A future JSON input can contain records such as:

```json
[
  {
    "run": 1,
    "phase": "post-core-init",
    "free_memory": 123456,
    "canary_ok": true,
    "ml_region": {"start": 12582912, "end": 12648448},
    "canon_regions": [
      {"name": "example", "start": 1048576, "end": 2097152}
    ]
  }
]
```

The analyzer checks:

- invalid ranges;
- ML/Canon overlap;
- canary failures;
- free-memory drift beyond a configured tolerance.

## Acceptance evidence for ML2000D-019

Include:

- static interval map;
- runtime logs;
- analyzer output;
- repeated boot count;
- maximum observed free-memory drift;
- confirmation that no canary failed.
