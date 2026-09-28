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

Review the result and copy only appropriate metadata into
`docs/2000D-130/rom-manifest.json`.

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
