# EOS 2000D firmware 1.1.0 QEMU preparation

The local QEMU helper accepts `--firmware 110` and `--start-main` with the
matching ROM1 image. It deliberately does not require or synthesize ROM0:
the supplied ROM0 dump failed its logged MD5 and is uniform filler. Never
substitute that image as a real ROM0.

## First-run preparation and result (2026-10-03)

- Host: Windows build `10.0.26200.9457`; Git `2.49.0.windows.1`; Python
  `3.13.5`.
- WSL `2.7.10` and kernel `6.18.33.2` are installed. The current-user WSL
  registry lists `Ubuntu-22.04` (WSL 2), but both `wsl --list --verbose` and
  direct `wsl -d Ubuntu-22.04` fail with
  `Wsl/Service/E_ACCESSDENIED`. No `gcc`, `make`, `cmake`, `ninja`, or native
  `qemu-system-arm` is on PATH.
- Docker Desktop is installed and launches, but its Linux engine pipe is
  absent. The `com.docker.service` service is stopped; starting it returns
  access denied because this Windows account is not an administrator.
- qemu-eos branch `qemu-eos-v4.2.1`, commit
  `4b667a1d3c08ab7a55835d15ddbd884fa754946d` (shallow checkout). The Magic
  Lantern patcher applied the model/profile to `hw/eos/eos.c`,
  `hw/eos/model_list.c`, and `hw/eos/model_list.h`. No qemu-eos compatibility
  changes were made. The main source checkout completed, but recursive
  submodule initialization was interrupted before all submodules reached their
  pinned commits. The patch is local to the sibling qemu-eos checkout and is
  not committed to this repository.
- ROM1 was extracted privately, rechecked at 33,554,432 bytes and SHA-256
  `7c17f49c5521ffe2fa140371a1bcb6353874b94d5c2669982b86f35e639c1a12`, and
  copied to the 2000D/110 QEMU workdir. ROM0 was not extracted or copied.
- The helper accepted ROM1 and created 64 MiB SD and 16 MiB CF test images.
  The generated workdir and ROM are outside both Git repositories.
- No QEMU executable could be built or launched. Normal-reset and direct-main
  runs were therefore **not attempted**. There is no measured initial PC,
  ROM entry, stall, MMIO trace, or copied-to-RAM observation. No smoke markers
  were added because no execution proved them.
- Static evidence shows the `cstart` path calls RAM address `0x00029898`.
  qemu-eos does not itself copy ROM1 into that address during machine setup;
  whether an earlier Canon bootstrap populates it is unknown without the run.

The blocker is access to the already registered Ubuntu distribution and the
Docker service from this restricted Windows session. The source of
`Wsl/Service/E_ACCESSDENIED` cannot be distinguished here from a Codex sandbox
restriction versus a Windows account/policy restriction. Do not try to elevate
or change Windows security policy from this task. To proceed, this session
needs approved access to `Ubuntu-22.04` or another Linux build environment; if
Windows requires elevation or a policy change, a Windows administrator must
approve that exact access change. The Docker service also needs administrator
attention if Docker is the chosen route.

The QEMU `qemu-eos-v4.2.1` DIGIC IV defaults map ROM1 from `0xF8000000`; the
2000D profile assigns a 32 MiB image, aliased at `0xF8000000`, `0xFA000000`,
`0xFC000000`, and `0xFE000000`. Thus the 1.1.0 main entry at file offset
`0xC0000` is available at `0xFE0C0000`. `ROM0_SIZE=0` skips ROM0 loading.
The public implementation details are in the upstream
[`eos.c` ROM alias and initialization code](https://github.com/reticulatedpines/qemu-eos/blob/qemu-eos-v4.2.1/hw/eos/eos.c#L1628-L1649),
[`eos.c` ROM0 handling](https://github.com/reticulatedpines/qemu-eos/blob/qemu-eos-v4.2.1/hw/eos/eos.c#L1730-L1739),
and [`model_list.c` DIGIC IV defaults](https://github.com/reticulatedpines/qemu-eos/blob/qemu-eos-v4.2.1/hw/eos/model_list.c#L90-L99).

## Local procedure

Copy the verified ROM1 file (kept outside Git) to
`<workdir>/2000D/110/ROM1.BIN`, then use the workdir path below with a built
`qemu-system-arm` for qemu-eos. From WSL, convert Windows paths to `/mnt/<drive>/...`.

```bash
python3 tools/eos2000d/qemu_workdir.py --help
python3 tools/eos2000d/qemu_workdir.py /path/to/qemu-workdir --firmware 110 --command
python3 tools/eos2000d/qemu_workdir.py /path/to/qemu-workdir --firmware 110 --start-main --command
```

The helper validates image size and recorded SHA-256 before preparing its
working directory. Keep the ROM file outside Git. Starting at the reported
main entry is a controlled direct-entry experiment; it does not establish
full reset/peripheral behavior. A real QEMU run has not yet been completed.

This Windows host lacks the QEMU executable and the required WSL distribution
is inaccessible, so the new profile has only unit-test validation here. No
physical-camera test, boot flag, installer, or firmware-update image is part
of this work.
