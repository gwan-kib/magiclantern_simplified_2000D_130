/* SPDX-License-Identifier: GPL-2.0-or-later
 * Optional firmware-110 experiment, not verified EOS 2000D hardware.
 * Codex-authored; no Canon firmware bytes or instruction-PC dependencies.
 */
#ifndef EOS2000D_FLASHIF_H
#define EOS2000D_FLASHIF_H
#include <stdbool.h>
#include <stdint.h>
#include <string.h>

typedef enum { EOS_FI_IDLE, EOS_FI_RDID, EOS_FI_RDSR, EOS_FI_UNSUPPORTED } EosFIPhase;
typedef struct {
    bool enabled, wel, busy, address4;
    EosFIPhase phase;
    uint8_t last_command, id_index;
    uint16_t regs[16]; /* DC..FA: two observed eight-halfword descriptors */
} EosFlashIF;

static inline void eos_fi_reset(EosFlashIF *s)
{
    bool enabled = s->enabled;
    memset(s, 0, sizeof(*s));
    s->enabled = enabled;
}

/* Only this explicit option activates the hypothetical identity. Other
 * options retain legacy parsing unless flash-id is present. Reject ambiguity.
 * Returns 0=disabled, 1=selected, -1=invalid experiment options. */
static inline int eos_fi_select(EosFlashIF *s, const char *model, const char *options)
{
    unsigned seen = 0;
    memset(s, 0, sizeof(*s));
    if (!options || !strstr(options, "flash-id")) return 0;
    if (strcmp(model, "2000D") || strncmp(options, "110;", 4)) return -1;
    for (const char *p = options + 4; *p;) {
        const char *end = strchr(p, ';');
        size_t n = end ? (size_t)(end - p) : strlen(p);
        unsigned bit = n == 15 && !strncmp(p, "flash-id=c22539", n) ? 1 :
                       n == 10 && !strncmp(p, "start=main", n) ? 2 :
                       n == 11 && !strncmp(p, "vectors=low", n) ? 4 : 0;
        if (!bit || (seen & bit)) return -1;
        seen |= bit;
        if (!end) break;
        p = end + 1;
        if (!*p) return -1;
    }
    if (!(seen & 1) || ((seen & 4) && !(seen & 2))) return -1;
    s->enabled = true;
    return 1;
}

static inline void eos_fi_command(EosFlashIF *s, uint8_t command)
{
    s->last_command = command;
    s->id_index = 0;
    switch (command) {
    case 0x06: if (!s->busy) s->wel = true; s->phase = EOS_FI_IDLE; break;
    case 0x04: if (!s->busy) s->wel = false; s->phase = EOS_FI_IDLE; break;
    /* Configuration-mode latch only; addressed serial I/O is unsupported. */
    case 0xb7: if (!s->busy) s->address4 = true; s->phase = EOS_FI_IDLE; break;
    case 0xe9: if (!s->busy) s->address4 = false; s->phase = EOS_FI_IDLE; break;
    case 0x9f: s->phase = EOS_FI_RDID; break;
    case 0x05: s->phase = EOS_FI_RDSR; break;
    default: s->phase = EOS_FI_UNSUPPORTED; break;
    }
}

static inline bool eos_fi_register(EosFlashIF *s, unsigned offset,
                                   unsigned width, bool write, uint32_t *value)
{
    if (!s->enabled || (width != 1 && width != 2 && width != 4) ||
        offset < 0xdc || offset > 0xfc - width) return false;
    unsigned first = offset - 0xdc;
    if (write) {
        for (unsigned i = 0; i < width; i++) {
            unsigned byte = first + i, shift = (byte & 1) * 8;
            uint16_t mask = 0xffu << shift;
            s->regs[byte / 2] = (s->regs[byte / 2] & ~mask) |
                               (((*value >> (i * 8)) & 0xff) << shift);
        }
        if (first < 4) {
            uint8_t command = s->regs[0] >> 8;
            if (!s->regs[0] || s->regs[1] != 0x0707) s->phase = EOS_FI_IDLE;
            else if (first < 2 || s->phase == EOS_FI_IDLE) eos_fi_command(s, command);
        }
    } else {
        *value = 0;
        for (unsigned i = 0; i < width; i++) {
            unsigned byte = first + i;
            *value |= ((s->regs[byte / 2] >> ((byte & 1) * 8)) & 0xffu) << (i * 8);
        }
    }
    return true;
}

static inline bool eos_fi_bank_write(EosFlashIF *s, unsigned offset,
                                      unsigned width, uint8_t value)
{
    if (!s->enabled) return false;
    if (!offset && width == 1 && s->regs[8] == 0x0707 && s->regs[9] == 0x0707)
        eos_fi_command(s, value);
    else { s->last_command = value; s->id_index = 0; s->phase = EOS_FI_UNSUPPORTED; }
    /* Never store command bytes into the canonical ROM backing memory. */
    return true;
}

static inline bool eos_fi_bank_read(EosFlashIF *s, unsigned offset,
                                     unsigned width, uint32_t *value)
{
    static const uint8_t experimental_id[3] = {0xc2, 0x25, 0x39};
    if (!s->enabled || s->phase == EOS_FI_IDLE || width != 1 || offset >= 0x100)
        return false;
    if (s->phase == EOS_FI_RDID) {
        *value = s->id_index < 3 ? experimental_id[s->id_index++] : 0xff;
    } else if (s->phase == EOS_FI_RDSR) {
        *value = (s->busy ? 1u : 0u) | (s->wel ? 2u : 0u);
    } else *value = 0xff; /* Explicit unsupported response; not a chip fact. */
    return true;
}
#endif
