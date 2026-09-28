# GUI event and button bring-up

## Safety principle

Observe first, intercept later.

The first GUI diagnostic should log button events while allowing Canon to continue handling them normally.

## Historical 2000D.110 candidate codes

These are same-body firmware 1.1.0 references, **not active 1.3.0 definitions**:

| Control | Historical candidate |
|---|---:|
| MENU | 6 |
| INFO | 7 |
| DISP press / release | 8 / 9 |
| PLAY | 0x0B |
| Q | 0x1C |
| Live View | 0x1D |
| SET press / release | 4 / 5 |
| Right press / release | 0x23 / 0x24 |
| Left press / release | 0x25 / 0x26 |
| Up press / release | 0x27 / 0x28 |
| Down press / release | 0x29 / 0x2A |
| ISO | 0x33 |
| Half-shutter press | 0x48 |
| Zoom out press / release | 0x10 / 0x11 |
| Zoom in press / release | 0x0E / 0x0F |
| Wheel left / right | 0x02 / 0x03 |
| Wheel up / down | 0x00 / 0x01 |

Historical shutdown-related candidates:

- `GMT_GUICMD_START_AS_CHECK = 0x59`;
- `GMT_GUICMD_OPEN_SLOT_COVER = 0x55`;
- `GMT_GUICMD_LOCK_OFF = 0x53`.

## Verification procedure

For firmware 1.3.0:

1. locate the GUI event dispatch path statically;
2. confirm event structure layout;
3. use a non-consuming logger;
4. press one control at a time;
5. record press and release;
6. repeat in photo mode, Live View, playback, and Canon menu where applicable;
7. identify context-dependent codes;
8. compare against historical 1.1.0 candidates;
9. only then populate `platform/2000D.130/gui.h`.

## Logger output format

Prefer a machine-readable line such as:

```text
GUI_EVENT type=<n> param=<hex> arg=<hex> obj=<hex> canon_mode=<n>
```

Do not log raw pointers if the output may be published without review.

## Menu-control acceptance set

Before a restricted ML menu can be enabled, verify at least:

- menu open/close key;
- SET/confirm;
- up/down/left/right;
- one safe back/exit path;
- half-shutter behavior;
- Live View/playback transitions.

## Failure conditions

Stop interception experiments if:

- Canon no longer receives a required key;
- half-shutter/shutter behavior changes;
- power-off/card-door events are swallowed;
- a key repeats uncontrollably;
- context changes produce ambiguous codes.

The initial diagnostic should never consume events.
