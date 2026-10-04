"""Public-safe tests compiling the same C helper that runs inside qemu-eos."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

CASES = {
    'reset': 's.wel=true; s.busy=true; s.phase=EOS_FI_RDID; s.id_index=2; s.regs[0]=9; eos_fi_reset(&s); assert(s.enabled && !s.wel && !s.busy && s.phase==EOS_FI_IDLE && !s.id_index && !s.regs[0]);',
    'wren': 'eos_fi_command(&s,6); assert(s.wel && !s.busy && s.phase==EOS_FI_IDLE);',
    'rdid': 'eos_fi_command(&s,0x9f); for(unsigned i=0;i<3;i++){assert(eos_fi_bank_read(&s,i,1,&v)); assert(v==id[i]);}',
    'status_idle': 'eos_fi_command(&s,5); assert(eos_fi_bank_read(&s,0,1,&v) && v==0);',
    'status_bits': 'eos_fi_command(&s,6); eos_fi_command(&s,5); assert(eos_fi_bank_read(&s,0,1,&v) && v==2); s.busy=true; assert(eos_fi_bank_read(&s,0,1,&v) && v==3);',
    'repeat_id': 'eos_fi_command(&s,0x9f); eos_fi_bank_read(&s,0,1,&v); eos_fi_bank_read(&s,1,1,&v); eos_fi_command(&s,0x9f); assert(eos_fi_bank_read(&s,0,1,&v) && v==0xc2);',
    'beyond_id': 'eos_fi_command(&s,0x9f); for(unsigned i=0;i<5;i++){assert(eos_fi_bank_read(&s,i,1,&v)); assert(v==(i<3?id[i]:0xff));} assert(s.id_index==3);',
    'reset_after_command': 'eos_fi_command(&s,6); eos_fi_command(&s,0x9f); eos_fi_reset(&s); assert(!eos_fi_bank_read(&s,0,1,&v) && !s.wel);',
    'address_mode': 'eos_fi_command(&s,0xb7); assert(s.address4 && s.phase==EOS_FI_IDLE && !s.wel); eos_fi_command(&s,0xe9); assert(!s.address4 && s.last_command==0xe9); eos_fi_command(&s,0xb7); eos_fi_reset(&s); assert(!s.address4); s.busy=true; eos_fi_command(&s,0xb7); assert(!s.address4);',
    'unknown': 'eos_fi_command(&s,0x42); assert(s.phase==EOS_FI_UNSUPPORTED); assert(eos_fi_bank_read(&s,0,1,&v) && v==0xff && !s.wel);',
    'wel_transitions': 'eos_fi_command(&s,6); eos_fi_command(&s,0x9f); eos_fi_command(&s,5); assert(s.wel); eos_fi_command(&s,4); assert(!s.wel); s.busy=true; eos_fi_command(&s,6); assert(!s.wel);',
    'controller_transaction': 'v=0x9f0e; assert(eos_fi_register(&s,0xdc,2,true,&v)); assert(s.phase==EOS_FI_IDLE); v=0x707; eos_fi_register(&s,0xde,2,true,&v); assert(s.phase==EOS_FI_RDID); eos_fi_bank_read(&s,0,1,&v); assert(v==0xc2); v=0; eos_fi_register(&s,0xdc,2,true,&v); assert(s.phase==EOS_FI_IDLE); assert(!eos_fi_bank_read(&s,0,1,&v));',
    'write_window': 'v=0x07070707; eos_fi_register(&s,0xec,4,true,&v); assert(eos_fi_bank_write(&s,0,1,6) && s.wel);',
    'widths': 'v=0x12345678; assert(eos_fi_register(&s,0xe0,4,true,&v)); v=0; eos_fi_register(&s,0xe0,2,false,&v); assert(v==0x5678); eos_fi_register(&s,0xe2,2,false,&v); assert(v==0x1234); v=0xab; eos_fi_register(&s,0xe1,1,true,&v); eos_fi_register(&s,0xe0,2,false,&v); assert(v==0xab78); assert(!eos_fi_register(&s,0xfb,2,false,&v)); assert(!eos_fi_register(&s,0xffffffff,2,false,&v)); assert(!eos_fi_register(&s,0xe0,3,false,&v)); eos_fi_command(&s,0x9f); assert(!eos_fi_bank_read(&s,0,4,&v));',
    'disabled': 's.enabled=false; EosFlashIF before=s; v=7; assert(!eos_fi_register(&s,0xdc,2,true,&v)); assert(!eos_fi_bank_write(&s,0,1,6)); assert(!eos_fi_bank_read(&s,0,1,&v)); assert(!memcmp(&s,&before,sizeof(s)) && v==7);',
    'parser_valid': 'assert(eos_fi_select(&s,"2000D","110;start=main;vectors=low;flash-id=c22539")==1 && s.enabled); assert(eos_fi_select(&s,"2000D","110;flash-id=c22539")==1);',
    'parser_default': 'assert(eos_fi_select(&s,"2000D","110;start=main;vectors=low")==0 && !s.enabled); assert(eos_fi_select(&s,"1300D","110")==0 && !s.enabled); assert(eos_fi_select(&s,"2000D",NULL)==0);',
    'parser_model': 'assert(eos_fi_select(&s,"1300D","110;flash-id=c22539")==-1 && !s.enabled); assert(eos_fi_select(&s,"2000D","130;flash-id=c22539")==-1); assert(eos_fi_select(&s,"1200D","110;flash-id=c22539")==-1);',
    'parser_invalid': 'const char *bad[]={"110x;flash-id=c22539","110;flash-id=20bb19","110;flash-id=c22539x","110;flash-id=c22539;flash-id=c22539","110;flash-id=c22539;","110;vectors=low;flash-id=c22539","110;boot=1;flash-id=c22539"}; for(unsigned i=0;i<sizeof(bad)/sizeof(bad[0]);i++) assert(eos_fi_select(&s,"2000D",bad[i])==-1 && !s.enabled);',
}

class FlashIFModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        header = Path(__file__).with_name('eos2000d_flashif.h').resolve()
        branches = '\n'.join(f'if (!strcmp(argv[1], {json.dumps(name)})) {{ {code} return 0; }}' for name, code in CASES.items())
        source = '#include <assert.h>\n#include "eos2000d_flashif.h"\nint main(int argc,char **argv){assert(argc==2); EosFlashIF s={0}; s.enabled=true; uint32_t v=0; const uint8_t id[3]={0xc2,0x25,0x39};\n'+branches+'\nreturn 2;}\n'
        (cls.root/'test.c').write_text(source)
        cls.binary=cls.root/'test'
        subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-I',str(header.parent),str(cls.root/'test.c'),'-o',str(cls.binary)],check=True,capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

class FlashIFIntegrationTests(unittest.TestCase):
    def test_glue_applies_idempotently_and_preserves_legacy_paths(self):
        from .qemu_eos_patch import patch_flashif_texts
        header = '#include "target/arm/cpu.h"\n    uint32_t flash_state_machine;\n'
        source = ('#include "sysemu/sysemu.h"\n// io range access\n'
                  '    return eos_handler(addr, type, 0);\n'
                  '    eos_handler(addr, type, val);\n'
                  '    fprintf(stderr, "ROM read: %x %x\\n", (int)addr, (int)size);\n'
                  '    if (strcmp(s->model->name, MODEL_NAME_1300D) == 0)\n'
                  '    eos_init_cpu();\n'
                  '    /* hijack machine option "firmware" */\n')
        out = patch_flashif_texts(header, source)
        self.assertEqual(patch_flashif_texts(*out), out)
        self.assertIn('eos_fi_mmio(addr, size, false', out[1])
        self.assertIn('eos_fi_mmio(addr, size, true', out[1])
        self.assertLess(out[1].index('eos_fi_select('), out[1].index('    eos_init_cpu();'))
        self.assertIn('if (eos_state->experimental_flashif.enabled)', out[1])
        for line in source.splitlines():
            self.assertIn(line, out[1])

for name in CASES:
    def check(self, case=name):
        result=subprocess.run([str(self.binary),case],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
    setattr(FlashIFModelTests,'test_'+name,check)

if __name__=='__main__': unittest.main()
