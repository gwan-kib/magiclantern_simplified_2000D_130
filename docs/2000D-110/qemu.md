# EOS 2000D firmware 1.1.0 QEMU preparation

The local QEMU helper now accepts `--firmware 110` and `--start-main` with the
matching ROM1 image. It deliberately does not require or synthesize ROM0:
the supplied ROM0 dump failed its logged MD5 and is uniform filler. Never
substitute that image as a real ROM0.

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
`qemu-system-arm` for qemu-eos:

```bash
python3 tools/eos2000d/qemu_workdir.py --help
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
