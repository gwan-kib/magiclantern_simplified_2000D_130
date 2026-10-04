"""Public-safe tests for debugger transaction decoding and trace completeness."""
import json
import struct
import unittest
from .qemu_flash_trace import condition_passed, decode_transfer, capture, check_mmio_coverage
from .qemu_probe import arm_register


class FlashTraceTests(unittest.TestCase):
    def test_all_arm_conditions(self):
        # Independently enumerate the ARM condition equations over all NZCV flags.
        for bits in range(16):
            n, z, c, v = [(bits >> i) & 1 for i in (3, 2, 1, 0)]
            expected = [z, 1-z, c, 1-c, n, 1-n, v, 1-v,
                        c and not z, not c or z, n == v, n != v,
                        not z and n == v, z or n != v, True, False]
            for condition, outcome in enumerate(expected):
                self.assertEqual(condition_passed(condition << 28, bits << 28), bool(outcome))

    def test_halfword_immediate_and_mask(self):
        regs = [0] * 16
        regs[4] = 0xC0000000
        instruction = (14 << 28) | (1 << 24) | (1 << 23) | (1 << 22) | (4 << 16) | (2 << 12) | 0xA | (0xD << 8) | 0xB0
        access = decode_transfer(instruction, regs)
        self.assertEqual((access['address'], access['width'], access['operation']), ('0xC00000DA', 16, 'write'))
        self.assertEqual(decode_transfer(instruction | (1 << 20), regs)['operation'], 'read')

    def test_byte_register_index_and_word(self):
        regs = [0] * 16
        regs[2], regs[3] = 0xF8000000, 2
        instruction = (14 << 28) | (1 << 26) | (1 << 25) | (1 << 24) | (1 << 23) | (1 << 22) | (1 << 20) | (2 << 16) | (1 << 12) | 3
        self.assertEqual(decode_transfer(instruction, regs)['address'], '0xF8000002')
        self.assertEqual(decode_transfer(instruction, regs)['width'], 8)
        self.assertEqual(decode_transfer(instruction & ~(1 << 22), regs)['width'], 32)

    def test_post_index_uses_original_base(self):
        regs = [0] * 16
        regs[4] = 0x1000
        instruction = (14 << 28) | (1 << 26) | (4 << 16) | 8
        self.assertEqual(decode_transfer(instruction, regs)['address'], '0x00001000')
        self.assertEqual(decode_transfer(instruction | (1 << 24), regs)['address'], '0x00000FF8')

    def test_unsupported_access_fails(self):
        with self.assertRaises(ValueError):
            decode_transfer(14 << 28, [0] * 16)

    def test_failed_condition_does_not_invent_a_read(self):
        # Synthetic conditional byte load at a trace PC, Z=1 makes HI false.
        instruction = (8 << 28) | (1 << 26) | (1 << 24) | (1 << 23) | (1 << 22) | (1 << 20)
        class Debugger:
            def memory(self, address, size):
                return struct.pack('<I', instruction)
        regs = [0] * 16
        regs[15] = 0x1D4E4
        packet = b''.join(struct.pack('<I', r) for r in regs).hex()
        result = capture(Debugger(), packet, arm_register, 1 << 30)
        self.assertEqual(result['operation'], 'skipped')
        self.assertNotIn('address', result)

    def test_complete_io_sequence(self):
        event = {'pc':'0x00001000','address':'0xC00000DC','operation':'write','value':3}
        output = '[FlashIF]\x1b[0m at init:00001000:00002000 [0xC00000DC] <- 0x3\x1b[0m: x\n'
        self.assertEqual(check_mmio_coverage([event], output), 1)
        with self.assertRaises(ValueError):
            check_mmio_coverage([], output)
        with self.assertRaises(ValueError):
            check_mmio_coverage([dict(event,value=4)], output)
        with self.assertRaises(ValueError):
            check_mmio_coverage([event], output + output)
        with self.assertRaises(ValueError):
            check_mmio_coverage([event], '[FlashIF] malformed')


if __name__ == '__main__':
    unittest.main()
