# EOS 2000D firmware 1.3.0 ROM analysis

## Status

**Canonical ROM: not yet available to this repository.**

Phase 2 can prepare a reproducible analysis workflow, but ML2000D-008 cannot
be closed until one exact 1.3.0 image is identified by cryptographic hash.

The original BigZeeX 1.3.0 porting README claimed:

- a successful ROM dump;
- first firmware word/signature `0xEA000001` at `0xFE0C0000`;
- an intended cache-hack boot path.

Those are useful leads, but the public repository did not include the dump,
its SHA-256, byte size, extraction method, or disassembly evidence.

## Independent confirmation that firmware 1.3.0 is real

Canon currently identifies EOS 2000D firmware **1.3.0 and later** as a
firmware family used on EMEA-market cameras with certain network functions
disabled. A Canon Community thread also links to Canon UK's EOS 2000D
firmware information/download page and identifies 1.3.0 as the current UK
firmware.

Canon UK support page discovered from that thread:

https://www.canon.co.uk/support/consumer/products/cameras/eos/eos-2000d.html?detailId=tcm%3A14-2438111&productTcmUri=tcm%3A14-1655176&type=firmware

This confirms the firmware version exists, but a Canon updater package is not
automatically equivalent to a raw ROM dump. If a legitimate Canon 1.3.0
updater is obtained, preserve the original package hash and analyze/extract it
separately.

## Canonical-image policy

Do not commit Canon firmware/ROM bytes to this repository.

Once an image is obtained, record only:

- acquisition source/method;
- original filename;
- exact byte size;
- SHA-256;
- target/model/version evidence;
- assumed ROM base;
- entry-word evidence;
- analysis-tool versions;
- non-copyrighted scripts and address notes.

The canonical image should remain private/local to analysts.

## Manifest workflow

Run:

```bash
python3 tools/eos2000d/rom_manifest.py /path/to/ROM.BIN \
  --base 0xFE0C0000 \
  --output /tmp/2000d-130-manifest.json
```

Review the generated JSON before copying its non-copyrighted metadata into
`docs/2000D-130/rom-manifest.json`.

Expected lead from the original 1.3.0 port:

```text
base:       0xFE0C0000
first word: 0xEA000001
```

For a little-endian ARM image, `0xEA000001` decodes as an unconditional
branch from `0xFE0C0000` to `0xFE0C000C`. This is consistent with the
classic Canon firmware layout where the first branch jumps past a signature
header, but it still must be verified against the canonical image.

## Local address probes

Use:

```bash
python3 tools/eos2000d/rom_probe.py /path/to/ROM.BIN \
  0xFE0C0000 0xFE0C1B74 0xFE0C3B34
```

The probe output contains firmware words. Use it locally for analysis; do not
blindly commit its output.

## Preferred acquisition order

1. Ask the original 1.3.0 port author for the dump metadata and, if they are
   willing and legally able, a private way to reproduce/access the image.
2. Obtain Canon's legitimate 1.3.0 update package from Canon's support
   channel and determine whether the updater can be extracted into the code
   image needed for static analysis.
3. If neither path yields the required ROM, use a known, read-only dump
   method appropriate for this exact camera/firmware. Do not enable boot
   flags or write persistent properties merely to obtain the dump.

## Analysis project convention

Suggested project names:

```text
EOS2000D_110_reference
EOS2000D_130_canonical
EOS1300D_110_reference
```

For every discovered 1.3.0 function or constant, record:

```text
Symbol/purpose:
1.3.0 address:
Evidence:
Callers/callees:
Nearby strings:
2000D.110 equivalent:
1300D.110 equivalent (if useful):
Confidence:
Reviewed by/date:
```

Addresses should move into executable platform files only after the evidence
is recorded.
