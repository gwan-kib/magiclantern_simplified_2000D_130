# Firmware 1.1.0 post-startup observations

**Classification: QEMU + Experiment throughout.** Direct main entry, low
vectors and the hypothetical `flash-id=c22539` are explicit assumptions.
These results do not describe a physical T7 boot. KI-019 remains open.

The first observed unserved peripheral request is the initial Intercom/MPU
send. Startup then waits for completion bit `0x2`; PowerMgr is functioning
as an idle task, not a demonstrated deadlock. No QEMU behavior was changed:
the correct initial request-line state and a matching 2000D MPU response
remain unverified. No firmware instructions, waits or assertions were changed.

## Reproduction and bounds

Base: `dev` commit `104848b191cc0cb53d446d604fde9a809ae4596b` (merged PR #39).
qemu-eos base: `4b667a1d3c08ab7a55835d15ddbd884fa754946d`, with the existing
repository patcher. Canonical ROM1 is 33,554,432 bytes, SHA-256
`7c17f49c5521ffe2fa140371a1bcb6353874b94d5c2669982b86f35e639c1a12`.
The 315,804-byte RAM bootstrap again matches the ROM byte for byte, SHA-256
`9c57fd4e542d72f3e96a6c5641e91d85f3edb9f1364dbba1049118c587d179e2`.
ROM0 was not loaded or fabricated. PR #40 subsequently merged into `dev`
(`db4a4b46cc6d595d49fdf83b1cb6fa605e77b80f`); its RAM-read checks, smoke
validation and minimal-rebuild fixes are preserved in this branch.

The unchanged probe reproduced all nine established startup PCs plus
`29FC`, `FE0C1DD0`, Startup, TaskMain, manager, PowerMgr and HotPlug in
**two 30-second runs**, both ending at `FE2BA330`. FlashIF coverage was
353 actual MMIO transfers per run, matching debugger observations exactly.
A 120-second baseline also reproduced this state. Two 60-second instrumented
runs reached all eight named tasks, with 363/385 switches and 11 periodic
samples each. Longer runs were used to qualify the handshake.

Two final **120-second** handshake runs recorded:

| Measurement | Run 1 | Run 2 |
|---|---:|---:|
| Observer records | 17,942 | 17,873 |
| Task switches | 860 | 858 |
| Created / entered tasks, including idle and init | 10 / 10 | 10 / 10 |
| Periodic samples, interval 5 seconds | 23 | 23 |
| Timer IRQ reason `09` | 2,760 | 2,746 |
| DMA IRQ reason `2F` | 5 | 5 |
| UART IRQ reason `3A` | 1 | 1 |
| PropMgr dispatches | 11 | 11 |
| HotPlug timed-wait returns (status 9) | 409 | 409 |
| Intercom sends / MPU request-register writes | 1 / 1 | 1 / 1 |
| Global assertion entry `3CBC` hits | 0 | 0 |
| Final sampled PC | `000019D0` | `FE2BA318` |

The different final PCs do not change the repeated pending handshake.
Debugger timestamps and the requested timeout are **host wall time**, not
120 seconds of guest execution. Breakpoints and file I/O perturb timing.
Two preliminary runs logging to Windows storage reached only the nine early
markers within 30 seconds; rerunning with Linux-native logs reproduced the
later milestones without changing QEMU. An interrupted run before the WSL
restart is not counted as a completed experiment.

## Tasks: creation, entry and deepest observed state

Creation call sites are calls to RAM `38FC`; the table lists their caller
return PC. Actual TCB initialization is observed at RAM `43D8`.
Every table row was created and entered in both final runs. PCs in the last
column are selected, repeatable observation points, not a claim to have
measured every instruction or the numerically largest address executed.

| Task | Creation caller return | Entry / argument | Repeated state / deepest relevant observation |
|---|---|---|---|
| PowerMgr | `FE2BA430` | `FE2BA2F4` / 0 | Mode 1 power wait, IRQ wake and reselection; baseline `FE2BA330` |
| DbgMgr | `FE2C1530` | `FE2C1438` / `2D2AE4` | Two manager messages, then receive wait `75D0`, return `FE2C13F0` |
| Startup | `FE0D3E54` | `FE0D3C94` / `2D2DA0` | First callback `FE0C1F9C`; sequence index 1, remaining mask 2; receive `75D0`, return `FE0D3CB0` |
| TaskMain | `FE0C1DD0` | `FE0C12AC` / 0 | Console semaphore wait, object `144ACC`, low-level wait linkage `1B34` |
| PropMgr | `FE2C1530` | `FE2C1438` / `66A874` | Initialization callback `FE10B8F0`, 11 dispatches `FE10BC90`, then queue receive |
| NFCMgr | `FE2C1530` | `FE2C1438` / `671470` | Two dispatches, property-change debug message, then queue receive |
| HotPlug | `FE0C6EEC` | `FE0C69DC` / 0 | GPIO checks, HDMI connect branch, flag wait `7164`; repeatedly returns at `FE0C6C68` |
| EventMgr | `FE2C1530` | `FE2C1438` / `671998` | One manager dispatch, then queue receive |

Creation names are accepted only after bounded ASCII and exact agreement
between the creation descriptor and TCB entry, argument, stack size and name
pointer. Samples never guess a name from arbitrary memory. Shared manager
entries are distinguished by their qualified TCB and argument.

## Scheduler and limited task fields

Canonical stores and dispatch loads validate current-task slot `31170`:
RAM `1980`, `1D28` and IRQ scheduler `1D94` store the selected R4 pointer;
each observed store is single-stepped and checked against the slot. RAM
`41DC` loads this slot; `41F8` loads the argument after the entry load at
`41F4`, before `41FC` dispatches the entry. RAM `43D8` follows creation-field
stores. The task stride is `0x54` in the task-ID lookup arithmetic.

Qualified observation offsets: entry `+0C`, argument `+10`, wait object
`+14`, allocated stack base `+1C`, stack size `+20`, name pointer `+24`,
ID `+40`, state byte `+49`, wait-kind byte `+4D`, saved SP `+50`.
Wait linkage at `1B34` stores state 1; wake unlink at `19CC` clears bit 0.
Other state bits and the complete context, linkage and task-attribute layouts
remain unresolved. No `CONFIG_TASK_STRUCT_V*` or `CONFIG_TASK_ATTR_STRUCT_V*`
variant, physical stub, or firmware-1.3.0 constant is selected.

## PowerMgr and HotPlug

`FE2BA32C` is conditional `MCR p15,0,R0,c15,c8,2`, with R0 zero when the
mode at `[R5+8]` is 1. qemu-eos maps this CP15 register to `ARM_CP_WFI`
in `target/arm/helper.c`. `FE2BA330` is the following conditional branch,
not itself a terminal self-loop. The return path restores IRQ flags and
returns to the mode check. The captured power words remain `(1,1,1,0)`;
1,886/1,876 mode checks, timer IRQs and repeated switches show ongoing wakes.
The observer does not single-step or bypass WFI.

Canonical input table `FE87B204` uses 8-byte register/mask records:

| Logical input | Register | Mask | Firmware path for QEMU value `10C` |
|---|---|---|---|
| `3B` (59) | `C022F48C` | `80` | Return 0 at `FE0C69F4`; USB state remains disconnected |
| `4E` (78) | `C022F48C` | `04000000` | Return 0 at `FE0C6A7C`; active-low HDMI **connect** branch |

The HDMI connect branch and its debug message were actually observed.
Returning zero does not mean disconnected for both inputs. These are
firmware logical-input semantics; electrical behavior and physical GPIO
mapping still need independent verification. No card-detect interpretation
or causal startup blocker is established for this register.

HotPlug waits for flag bit 1 on handle `4C0004`, underlying object `1474CC`,
with timeout argument 50 (`FE0C6C64 -> 7164`). It repeatedly returns status 9
(the wrapper's timeout mapping), clears bit 1 at `FE0C6C70 -> 7370`, and
polls again. This is a **timed event-flag wait**, not a semaphore deadlock.

## Waits and interrupts

| Primitive | Qualified callable / observed path | Meaning / producers |
|---|---|---|
| Sleep | `3780` | Scheduler delay path; no explicit sleep call observed in these final runs |
| Semaphore waits | `3270` / `3220` | Timed / fixed-deadline wrappers both call `4958`; `3220` is not a release. Release wrapper `3358` calls `4928` (static only). Console object `144ACC` waits through the lower kernel API; console-input producer not observed |
| Event flag wait / set / clear | `7164` / `7328` / `7370` | `SystemIF::KerFlag.c`; timed HotPlug wake by timer; no flag-set wrapper call observed |
| Queue receive / send / try-send | `75D0` / `7750` / `7814` | Manager messages and Startup completion notification |
| Scheduler wait / wake linkage | `1B34` / `19CC` | Runtime object and state transitions; timeout wake need not call the public flag-set wrapper |

Manager queue handle / underlying wait-object pairs are DbgMgr
`360002/148714`, Startup `3A0004/148740`, PropMgr `400006/14876C`, NFCMgr
`460008/148798`, EventMgr `50000A/1487C4`. Message receive timeout argument
zero denotes the indefinite path here. Waiting is not by itself failure.

**Numbers and labels in this paragraph are emulator observations.** Reason
read `504` uses `C0201004`, where reason = IRQ number times 4. At `548`,
handler pointers are `09 -> FE0C0B28`, `2F -> FE124500`, and
`3A -> FE0C3BA8`. At `588`, `C0201010` acknowledges/re-enables the serviced
number. Native logs record enable and trigger operations; these are distinct
from actual guest handler entry. `628` records unchanged-task IRQ returns;
`1D94` captures IRQ-driven switches. Run 1 includes 408 timer-driven
PowerMgr-to-HotPlug switches and 1,634 PowerMgr-to-PowerMgr returns.
The model's 10 ms DryOS timer configuration is observed, not a timing
calibration for this instrumented experiment. DMA initialization copies and
console UART activity do not demonstrate SD, RTC, GPIO or MPU IRQs.
No MPU `50` or SIO3 `36` reason was observed.

## First unserved request: Intercom/MPU initialization

This is a repeatable **experimental handshake limitation**, not a finding
that the whole scheduler is deadlocked.

1. Startup initializes Intercom: `FE2984FC` writes `0C` to `C020302C`,
   then `FE298504/FE29850C` configure `C0820308/C082030C` with
   `1/13020010`. Canon registers handlers `50 -> FE298370` and
   `36 -> FE2983F4` in this firmware path.
2. At `FE10C2AC`, Canon registers completion callback `FE0C3A10` with
   user argument 2. The observation at `FE10C1DC` confirms global `316BC`
   contains initialized flag 0, property object `66A844`, callback
   `FE0C3A10`, argument 2.
3. Startup enters send `FE298564` once from `FE10FC80`, with four input
   bytes `04 02 00 00`. This is the queued guest message, not an observed
   wire transfer. The driver queues its transmit buffer and calls the GPIO
   writer at `FE2985F4`; actual MMIO is `FE121EC8`, return `FE2985F8`:
   `C022D0C4 <- 0083DC00`.
4. `hw/eos/mpu.c:eos_handle_mpu` starts with a zero-initialized status
   latch. Its request mask is `00100000`. Both zero and `0083DC00` have
   that bit clear; the falling-edge branch requires the **previous** bit
   set. Consequently this first write generates no MREQ IRQ. The logs
   show only initialization and the request write, no SIO3 data transfer,
   response bytes or MPU/SIO3 handler entry in either final run.
5. The canonical receive callback `FE10BF78` requires event/class 2,
   code 0 and initialized flag 0 before invoking the registered completion
   callback. `FE0C3A10` forwards user mask 2 to `FE0D3FF8`. No such callback
   or notification occurs. Startup's second record mask `20000002` loses
   `20000000` after its first callback returns, leaving **2**. It cannot
   advance its sequence queue until that condition completes.

Static producer logic is consistent with the measured stall; an actual
successful MPU response is not yet observed. What remains missing is a
verified initial request-line/bootloader state and correct 2000D MPU
handshake semantics. A guessed idle-latch value or arbitrary reply would
change the experiment rather than validate hardware. No correction or
injected event was made. Tracking: [GitHub issue #41](https://github.com/gwan-kib/magiclantern_simplified_2000D_130/issues/41), separate from open KI-019.
Exit criterion: independently justify the initial
state and protocol, then demonstrate a real guest-triggered transfer,
completion callback and sequence advance in at least two bounded runs.

Generic MPU warnings printed at QEMU startup are **not** guest traffic.
The final task mode enables native `mpu` logging explicitly because
`io,int` alone omits these transfers. Missing logging in an earlier run
cannot establish that MPU initialization never occurred.

## Properties, storage, display and assertions

PropMgr really dispatches initialization `FE10B8F0` and 11 messages via
`FE10BC90 -> FE2BDC94`; this is more evidence than task creation. It then
waits on its queue. That does not prove completed MPU property exchange.
DbgMgr/NFCMgr/EventMgr also process messages before waiting.

No SDIO controller transactions, SD IRQ, filesystem task, successful mount,
CF ATA transaction or file/directory access was observed. Existing generated
SD/CF images are virtual inputs, not proof of a mount, and were not edited
for this investigation. Generic DMA setup/copies are separate evidence.

No GUI task creation/entry, GUI event loop, LCD enable, qualified VRAM buffer
or complete display-controller startup was observed. An HDMI branch and the
serial `BackLightOff` warning are not full GUI startup. Later sequence
callbacks have not executed while bit 2 is pending; this does not by itself
establish the entire storage/display ordering.

All final probes armed global RAM assertion entry `3CBC` and stopped if
reached; none did. Canon debug entry `FE11F3C8` was observed 21 times per
final run. This qualifies the observed debug call path, not every possible
fatal/reset path in the ROM. No conclusion is based solely on final PC.

## Tooling, commands and evidence boundary

The optional task observer uses debugger hardware breakpoints, register and
memory reads, plus one-instruction steps at verified straight-line observer
PCs to re-arm recurring stops. It checks committed scheduler stores and
fails on a different next PC. It does not write ROM/RAM, alter disk images,
skip waits, inject IRQs or install a payload. Raw memory, Canon debug strings
and disassembly remain private. Host timestamps are not guest timing.

```sh
# Baseline; add explicit --watch-at PCs from the reproduction section above.
python3 tools/eos2000d/qemu_probe.py "$WORKDIR" --binary "$QEMU" \
  --log-dir "$PRIVATE/baseline-30" --start-main --low-vectors \
  --flash-id c22539 --repeat 2 --timeout 30 --flashif-trace --stop-at 0x3cbc

# Final repeated handshake observation, using Linux-native private logs.
python3 tools/eos2000d/qemu_probe.py "$WORKDIR" --binary "$QEMU" \
  --log-dir "$PRIVATE/handshake-120" --start-main --low-vectors \
  --flash-id c22539 --repeat 2 --timeout 120 --flashif-trace \
  --task-trace --sample-interval 5
python3 tools/eos2000d/qemu_task_report.py "$PRIVATE/handshake-120/low-vectors-1"
python3 -m unittest discover -s tools/eos2000d -t .
```

`qemu_task_report.py` rejects truncated/malformed event records, inconsistent
creation identities, switch stores, entry PCs, IRQ reasons and assertions.
Its output is private until reviewed. Public tests use generated synthetic
TaskA records, not firmware excerpts or captured traces. The existing 56
tests are preserved; the initial expanded suite had 69 tests. After integrating
concurrently merged PR #40, all 75 tests pass, including its six additional
regressions. Existing captures pass its strengthened full-copy checker. CI exercises the
new tests and the reference-camera build/safety gates.

This observer, parser, tests and analysis were authored by Codex under the
user's explicit diagnostic-tooling request. Independent review remains
necessary. No ML injection, camera-ready payload, installer, boot flag,
physical camera/card access or active firmware-1.3.0 change is included.
