# EOS 2000D analysis tools

These tools handle **local firmware metadata and analysis only**.

They do not download Canon firmware and they should not be used to commit
Canon ROM bytes.

## Generate a public-safe manifest

```bash
python3 tools/eos2000d/rom_manifest.py /path/to/ROM.BIN \
  --base 0xFE0C0000 \
  --output /tmp/manifest.json
```

Review the result and copy only appropriate metadata into the manifest for its
exact firmware. The 1.1.0 reference image is documented in
`docs/2000D-110/rom-manifest.json`; the 1.3.0 manifest remains separate.

## Firmware 1.1.0 QEMU preparation

The locally verified 1.1.0 profile uses ROM1 only; the supplied ROM0 fails its
logged checksum and must not be used. With qemu-eos built and the ROM kept
outside Git, inspect the available options with:

```bash
python3 tools/eos2000d/qemu_workdir.py --help
```

The 1.1.0 QEMU assumptions and direct-main experiment are documented in
`docs/2000D-110/qemu.md`. Repeated local emulator execution and its flash-identification blocker are now recorded there.
Use `qemu_probe.py --help` for private bounded debugger reports and
`qemu_smoke.py --probe-report /private/result.json` for the limited init-task-entry check.

## Probe candidate addresses locally

```bash
python3 tools/eos2000d/rom_probe.py /path/to/ROM.BIN \
  0xFE0C0000 0xFE0C1B74 0xFE0C3B34
```

Probe output includes firmware words and is intended for local reverse
engineering, not automatic publication.

## Tests

```bash
python3 -m unittest tools.eos2000d.test_rom_manifest
```

For canonical firmware-110 flash diagnostics, add `--flashif-trace` to
`qemu_probe.py --start-main --low-vectors --timeout 15`. This saves private
`flashif.jsonl` with executed access widths, registers and command descriptors,
and rejects incomplete FlashIF log coverage. Firmware bytes and raw
transactions stay outside Git. See `docs/2000D-110/flashif.md`.

### Private firmware-110 task observations

`qemu_probe.py --task-trace --sample-interval 5` requires explicit main-entry,
low-vector and hypothetical C2 flags. It writes private task/IRQ/wait records
and enables native MPU logging. `qemu_task_report.py PRIVATE_RUN_DIRECTORY`
validates a completed bounded run and emits a private summary. See
[post-startup evidence](../../docs/2000D-110/post-startup.md) for qualified
fields, reproducible commands and timing limits. Never commit raw captures
or infer complete boot from a waiting task or the final sampled PC.
