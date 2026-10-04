/* EOS2000D_FLASHIF_EXPERIMENT: opt-in peripheral integration. */
static void eos_fi_log(EOSState *s, const char *operation, unsigned offset,
                       unsigned width, unsigned value)
{
    if (qemu_loglevel_mask(EOS_LOG_IO))
        fprintf(stderr, "[FlashIF-experiment] %s off=%X width=%u value=%X "
                "state=%u cmd=%02X index=%u WEL=%u WIP=%u address-bytes=%u id=c22539 (hypothesis)\n",
                operation, offset, width, value, s->experimental_flashif.phase,
                s->experimental_flashif.last_command, s->experimental_flashif.id_index,
                s->experimental_flashif.wel, s->experimental_flashif.busy,
                s->experimental_flashif.address4 ? 4 : 3);
}

static void eos_fi_qemu_reset(void *opaque)
{
    EOSState *s = opaque;
    eos_fi_reset(&s->experimental_flashif);
    memory_region_rom_device_set_romd(&s->rom1, true);
    eos_fi_log(s, "reset", 0, 0, 0);
}

static bool eos_fi_mmio(unsigned address, unsigned width, bool write,
                        unsigned *value)
{
    EOSState *s = eos_state;
    if (!s->experimental_flashif.enabled || address < 0xC0000000 ||
        address > 0xC0001FFF ||
        !eos_fi_register(&s->experimental_flashif, address & 0x1ff, width, write, value))
        return false;
    memory_region_rom_device_set_romd(&s->rom1,
                                      s->experimental_flashif.phase == EOS_FI_IDLE);
    eos_fi_log(s, write ? "register-write" : "register-read", address & 0x1ff, width, *value);
    io_log("FlashIF", address, write ? MODE_WRITE : MODE_READ,
           write ? *value : 0, write ? 0 : *value,
           "experimental c22539 controller latch", 0, 0);
    return true;
}
