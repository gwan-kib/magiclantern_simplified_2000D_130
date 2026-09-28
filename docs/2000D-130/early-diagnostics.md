# Early boot diagnostics for EOS 2000D firmware 1.3.0

## Goal

Provide one observable signal that works before normal Magic Lantern display
and file I/O are available.

## Historical card-LED candidate

Both historical **2000D.110** and **1300D.110** ports define:

```c
CARD_LED_ADDRESS 0xC0220134
LEDON             0x46
LEDOFF            0x44
```

This agreement across two closely related DIGIC IV+ cameras makes the
register a strong candidate for the 2000D hardware, but it is **not yet
verified for the 1.3.0 development target**.

The active `platform/2000D.130/consts.h` therefore intentionally does not
define these values.

## Static verification strategy

Once the canonical 1.3.0 image is available:

1. Locate the 1.1.0 routine(s) that access `0xC0220134`.
2. Match those routines into 1.3.0 using control flow and nearby
   constants/strings.
3. Confirm the same MMIO register is written during card/indicator activity.
4. Confirm the values corresponding to LED on/off.
5. Record disassembly evidence before enabling the constant.

If the direct literal is optimized through a peripheral base register, trace
the resulting effective address rather than requiring the full literal to
appear in the instruction stream.

## First diagnostic payload design

The first 2000D payload should be simpler than the current graphical
`minimal/hello-world`.

Preferred order:

1. loader enters;
2. verified LED register emits one short pulse;
3. ML init-task hook is entered;
4. verified LED register emits two short pulses;
5. Canon `init_task` is called;
6. post-init hook emits three short pulses;
7. Canon startup continues.

Suggested meanings:

| Pattern | Meaning |
|---|---|
| 1 pulse | loader/cache patch executed |
| 2 pulses | ML init-task entry reached |
| 3 pulses | Canon init-task returned / post-init reached |
| repeating fast pulses | deliberate fatal diagnostic path |

A first version should avoid the bitmap subsystem entirely.

## Delay strategy

Using `msleep` introduces another firmware stub dependency. For the earliest
possible LED-only test, a bounded volatile busy loop can be used only for
human-visible diagnostic spacing if it is safe at that boot stage. Once
`msleep` is verified for 1.3.0, switch to the DryOS sleep primitive.

Timing accuracy is irrelevant for this diagnostic; code-path distinction is
the goal.

## Secondary debug channel

The historical 2000D.110 stubs contain `DryosDebugMsg`, but the serial
print stub is not established there. Therefore serial output is not currently
a reliable independent channel for 1.3.0.

QEMU debug output remains valuable during Phase 3, but it does not replace a
physical observable diagnostic for the first hardware test.

## Exit gate for ML2000D-010

This issue can close after the 1.3.0 LED method is backed by exact firmware or
hardware evidence and a minimal payload can use it without depending on the
full ML GUI.
