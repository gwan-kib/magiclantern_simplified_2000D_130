# Magic Lantern — Canon EOS 2000D / Rebel T7 port

> **Experimental porting repository. Not ready for installation on a physical camera.**

This fork tracks current Magic Lantern development while building support for the **Canon EOS 1500D / 2000D / Rebel T7 on firmware 1.3.0**.

The public fork this work started from contained early ROM/cache-hack notes, but the camera-specific platform implementation was not present. This repository therefore treats those notes as leads until they are independently verified against the exact 1.3.0 ROM.

## Port status

Current active milestone: **Phase 2 — Reverse engineering / minimum firmware interface**

- Upstream source baseline: `reticulatedpines/magiclantern_simplified:dev`
- Target firmware: **1.3.0**
- Phase 0 repository baseline: **complete**
- `platform/2000D.130/` safe skeleton: **implemented**
- Current-generation minimal build infrastructure: **working and CI-tested on 1100D.105**
- Canonical 2000D firmware 1.3.0 ROM/hash: **not yet verified**
- 2000D.130 boot/memory/task addresses: **not yet verified**
- 2000D.130 minimal payload: **blocked on Phase 2 ROM/stub work**
- QEMU execution: **not demonstrated yet**
- Physical-camera execution: **not approved yet**

Start here:

- [2000D porting and safety guide](docs/2000D-porting.md)
- [Staged issue backlog](docs/2000D-issue-backlog.md)
- [Phase 2 ROM analysis workflow](docs/2000D-130/rom-analysis.md)
- [Phase 2 cache-hack map](docs/2000D-130/cache-hack-map.md)
- [Early diagnostic plan](docs/2000D-130/early-diagnostics.md)
- [Minimum stub checklist](docs/2000D-130/minimal-stubs.md)
- [GitHub issues](https://github.com/gwan-kib/magiclantern_simplified_2000D_130/issues)

Do not copy firmware addresses from other cameras. The EOS 1300D can be useful as a late DIGIC 4+ structural reference, but all 2000D constants must be derived from and verified against the 2000D firmware 1.3.0 ROM.

---

## Upstream Magic Lantern

Magic Lantern (ML) is a software enhancement that offers increased
functionality to the excellent Canon DSLR cameras.

It's an open framework, licensed under GPL, for developing extensions to the
official firmware.

Magic Lantern is not a *hack*, or a modified firmware, **it is an
independent program that runs alongside Canon's own software**.
Each time you start your camera, Magic Lantern is loaded from your memory
card. The project's modification enables the ability to run software
from the memory card.

ML is being developed by photo and video enthusiasts, adding
functionality such as HDR images and video, timelapse, motion
detection, focus assist tools, manual audio controls and much more.

For more details on Magic Lantern see:
http://www.magiclantern.fm/

The sibling QEMU repository used for camera emulation is:
https://github.com/reticulatedpines/qemu-eos

Current ML-team-supported qemu-eos branch noted by upstream:
https://github.com/reticulatedpines/qemu-eos/tree/qemu-eos-v4.2.1
