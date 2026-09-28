# Bitmap display and Live View bring-up

## Goal

Prepare ML2000D-021 without activating historical display addresses.

The first display milestone is a harmless bitmap overlay that can be cleared without corrupting Canon UI.

## Historical 2000D.110 references

Firmware 1.1.0 included candidates such as:

- bitmap / display state pointers in the `0x318xx` region;
- `YUV422_LV_BUFFER_DISPLAY_ADDR` based near `0x318C8`;
- `DISPLAY_STATEOBJ` based near `0x318B8`;
- direct YUV buffer addresses such as `0x40D07800`, `0x4C233800`, `0x4F11D800`;
- EDMAC display-related registers in the `0xC0F04xxx` range.

These values are **not valid 1.3.0 evidence** and are not enabled.

## Bring-up order

### 1. Bitmap geometry

Determine:

- visible width/height;
- pitch;
- pixel format;
- safe drawable region;
- whether Canon uses multiple bitmap buffers.

### 2. Bitmap VRAM pointer

Identify the active bitmap surface and confirm it changes only as expected across:

- photo mode;
- Live View;
- Canon menu;
- playback.

### 3. Palette / color behavior

Verify one non-destructive color index at a time.

Do not assume historical color constants are stable.

### 4. Redraw / dirty signaling

Determine how to request a redraw or mark the bitmap dirty without fighting Canon's renderer.

### 5. Harmless overlay test

Draw a tiny diagnostic mark in a known-safe corner.

Then:

- clear it;
- enter/exit Canon menu;
- enter/exit playback;
- enter/exit Live View;
- power off normally.

No persistent corruption is acceptable.

### 6. YUV / Live View buffers

Only after bitmap drawing is stable, identify basic YUV display buffers.

Do not enable:

- RAW capture;
- EDMAC copy experiments;
- display-buffer redirection;
- sensor/timing changes.

## Evidence record

For each active display pointer/register, record:

- canonical ROM hash;
- address;
- identification method;
- state(s) where valid;
- expected size/pitch;
- static/QEMU/hardware evidence.

## Acceptance evidence

ML2000D-021 closes only after a test overlay draws and clears reliably without corrupting Canon UI across the supported display states.
