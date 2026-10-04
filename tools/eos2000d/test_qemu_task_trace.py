"""Synthetic public fixtures: no Canon ROM, disassembly, or captured memory."""
import json
import copy
import tempfile
import subprocess
import sys
from pathlib import Path
import struct
import unittest

from . import qemu_task_trace as trace
from .qemu_probe import arm_register
from .qemu_task_report import parse_events, parse_mmio, extract_assertion, summarize


def synthetic_task(pointer='0x00002000', name='TaskA', qualified=True):
    return dict(pointer=pointer, name=name, name_qualified_by_creation=qualified,
        entry='0x00009000', id='0x00000001', name_pointer='0x00008000',
        state_byte=0, wait_kind_byte=0, object='0x00000000')


def synthetic_event(operation='sample', step=1):
    registers=['0x00000000']*16
    registers[13:16]=['0x00004000','0x00005000','0x00006000']
    return dict(operation=operation,step=step,time_monotonic_ns=step*100,
        pc=registers[15],sp=registers[13],lr=registers[14],registers=registers,
        current={'pointer':'0x00000000'})


def created_event():
    event=synthetic_event('created-tcb')
    event['created']=synthetic_task()
    return event


def lines(events):
    return '\n'.join(json.dumps(e) for e in events)


class ObserverTests(unittest.TestCase):
    def debugger(self):
        # All data generated here; address choices are arbitrary low-RAM test data.
        raw=bytearray(0x54)
        for offset,value in [(0xC,0x9000),(0x10,7),(0x1C,0x4000),
                             (0x20,0x200),(0x24,0x8000),(0x40,1),(0x50,0x4180)]:
            struct.pack_into('<I',raw,offset,value)
        data={0x2000:bytes(raw),0x8000:b'TaskA\0'+bytes(58),trace.CURRENT_SLOT:struct.pack('<I',0x2000)}
        class Debugger:
            def memory(self,address,size):
                return data[address][:size]
        return Debugger(),data

    def test_names_require_canonical_creation_fields(self):
        debugger,data=self.debugger()
        self.assertIsNone(trace.task_snapshot(debugger,0x2000)['name'])
        descriptor=struct.pack('<6I',5,0x9000,7,0,0x200,0x8000)
        task=trace.qualify_created(debugger,0x2000,descriptor)
        self.assertEqual((task['name'],task['entry'],task['stack_size']),('TaskA','0x00009000',512))
        changed=bytearray(data[0x2000]);struct.pack_into('<I',changed,0xC,0x9004);data[0x2000]=bytes(changed)
        with self.assertRaises(ValueError):trace.current_snapshot(debugger)

    def test_creation_mismatch_and_short_records_fail(self):
        debugger,data=self.debugger()
        with self.assertRaises(ValueError):trace.qualify_created(debugger,0x2000,struct.pack('<6I',5,0x9004,7,0,0x200,0x8000))
        with self.assertRaises(ValueError):trace.task_snapshot(debugger,0x2001)
        with self.assertRaises(ValueError):trace.task_snapshot(debugger,0xFFFFFFF0)
        data[0x2000]=bytes(12)
        with self.assertRaises(ValueError):trace.task_snapshot(debugger,0x2000)
        with self.assertRaises(ValueError):trace.u32(bytes(3))

    def test_samples_at_scheduler_pc_are_not_switches(self):
        debugger,_=self.debugger()
        regs=[0]*16;regs[4]=0x2000;regs[15]=0x1980
        packet=b''.join(struct.pack('<I',r) for r in regs).hex()
        event=trace.capture(debugger,packet,arm_register,'sample')
        self.assertEqual(event['operation'],'sample');self.assertNotIn('new',event)

    def test_bounded_ascii_name_only(self):
        debugger,data=self.debugger()
        for raw in [b'X'*64,b'Bad\xff\0'+bytes(58),b'\0'+bytes(63)]:
            data[0x8000]=raw
            self.assertIsNone(trace.cstring(debugger,0x8000))
        self.assertIsNone(trace.cstring(debugger,0x10000000))


class ParserTests(unittest.TestCase):
    def test_task_switch_wait_and_summary(self):
        switch=synthetic_event('switch',2);switch['current']=synthetic_task()
        switch.update(old=synthetic_task(),new=synthetic_task(),committed_pointer='0x00002000')
        wait=synthetic_event('flag-wait',3);wait['current']=synthetic_task()
        wait['registers'][0]='0x00000100'
        events=parse_events(lines([created_event(),switch,wait]))
        report=summarize(events)
        self.assertEqual(report['tasks'][0]['switches_in'],1)
        self.assertEqual(report['tasks'][0]['waits'],{'flag-wait:0x00000100':1})
        self.assertNotIn('raw_tcb',json.dumps(report))

    def test_unqualified_names_and_switch_mismatch_fail(self):
        sample=synthetic_event();sample['current']=synthetic_task()
        with self.assertRaises(ValueError):parse_events(lines([sample]))
        switch=synthetic_event('switch',2);switch.update(old=switch['current'],new=synthetic_task(),committed_pointer='0x00002004')
        with self.assertRaises(ValueError):parse_events(lines([created_event(),switch]))
        bad=created_event();bad['created']['name_qualified_by_creation']=False
        with self.assertRaises(ValueError):parse_events(lines([bad]))

    def test_entry_mismatch_and_identity_drift_fail(self):
        event=synthetic_event('entry',2);event['current']=synthetic_task()
        with self.assertRaises(ValueError):parse_events(lines([created_event(),event]))
        event['operation']='sample';event['current']['id']='0x00000002'
        with self.assertRaises(ValueError):parse_events(lines([created_event(),event]))

    def test_malformed_and_reordered_logs_fail(self):
        for text in ['', '{', '[]', lines([synthetic_event(step=2)]), lines([created_event(),created_event()])]:
            with self.subTest(text=text), self.assertRaises(ValueError):parse_events(text)
        for key,value in [('step',True),('time_monotonic_ns',-1),('operation','unknown'),('pc','0x123'),('registers',[])]:
            event=synthetic_event();event[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):parse_events(lines([event]))
        a=synthetic_event();b=synthetic_event(step=2);b['time_monotonic_ns']=0
        with self.assertRaises(ValueError):parse_events(lines([a,b]))

    def test_irq_reasons_handlers_and_acknowledgements(self):
        events=[]
        for step,op in enumerate(['irq-reason','irq-handler','irq-ack','irq-return'],1):
            event=synthetic_event(op,step);event.update(irq=7,reason=28,handler='0x00007000');events.append(event)
        parsed=parse_events(lines(events));self.assertEqual(summarize(parsed)['irq_reason_counts'],{'7':1})
        events[0]['reason']=29
        with self.assertRaises(ValueError):parse_events(lines(events))

    def test_native_mmio_and_warning_distinction(self):
        text='[MPU] FIXME: generic configuration\n[DMA1] Copy [0x00001000] -> [0x00002000]\n'
        text+='[*unk*]\x1b[0m at 0x00001000:00002000 [0xC0000004] <- 0xA\n'
        text+='[INT] at TaskA:00001004:00002000 [0xC0201004] -> 0x1C\n'
        records=parse_mmio(text)
        self.assertEqual(len(records),2);self.assertEqual(records[1]['task'],'TaskA')
        self.assertEqual(records[0]['value'],10)
        with self.assertRaises(ValueError):parse_mmio('[INT] at bad [0xC0201004] -> 0x1C')

    def test_assertion_needs_explicit_stop_and_valid_fields(self):
        self.assertIsNone(extract_assertion({'final_pc':'0x00003CDC'}))
        record=dict(caller_return='0x00005000',filename_pointer='0x00006000',
                    expression='synthetic',filename='fixture.c',line=123,arguments=['0x00000000']*4)
        result=dict(stop_address='0x00003CBC',assertion=record)
        self.assertEqual(extract_assertion(result)['line'],123)
        for broken in [dict(result,stop_address='0x00004000'),dict(result,assertion=dict(record,line=-1)),
                       dict(result,assertion=dict(record,arguments=[]))]:
            with self.assertRaises(ValueError):extract_assertion(broken)

    def test_probe_option_guards_fail_before_rom_access(self):
        script=Path(__file__).with_name('qemu_probe.py')
        for options in [ ['--task-trace'], ['--sample-interval','1'],
                         ['--timeout','nan'], ['--timeout','inf'],
                         ['--sample-interval','-1'] ]:
            completed=subprocess.run([sys.executable,str(script),'.','--binary','/unused',
                '--log-dir','/unused',*options],capture_output=True,text=True)
            self.assertEqual(completed.returncode,2)
            self.assertNotIn('Traceback',completed.stderr)

    def test_short_payload_and_false_name_qualification_fail(self):
        event=synthetic_event('intercom-send');event.update(payload='00')
        event['registers'][1]='0x00000004'
        with self.assertRaises(ValueError):parse_events(lines([event]))
        event=synthetic_event(step=2);event['current']=synthetic_task(qualified=False)
        with self.assertRaises(ValueError):parse_events(lines([created_event(),event]))


    def test_intercom_payload_is_exact_hex_at_boundary_lengths(self):
        for size in [1, 2, 128]:
            event=synthetic_event('intercom-send')
            event['registers'][1]=f'0x{size:08X}'
            event['payload']='aB'*size
            self.assertEqual(len(parse_events(lines([event]))),1)
        for size,payload in [(0,''),(129,'00'*129),(2,'00  '),(2,' 00 '),
                             (2,'00\t '),(2,'0G00'),(2,'000'),(2,'000000')]:
            event=synthetic_event('intercom-send')
            event['registers'][1]=f'0x{size:08X}'
            event['payload']=payload
            with self.subTest(size=size,payload=payload),self.assertRaises(ValueError):
                parse_events(lines([event]))

    def test_task_wait_object_must_survive_validation(self):
        for value in [None, [], '0x123', 0]:
            event=created_event();event['created']['object']=value
            with self.subTest(value=value),self.assertRaises(ValueError):
                parse_events(lines([event]))
        event=created_event();del event['created']['object']
        with self.assertRaises(ValueError):parse_events(lines([event]))

    def test_malformed_switch_tasks_have_line_errors(self):
        for value in [None, [], 7, 'bad']:
            event=synthetic_event('switch',2)
            event.update(old=event['current'],new=value,committed_pointer='0x00002000')
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,'observer line 2'):
                parse_events(lines([created_event(),event]))


class ReportBoundaryTests(unittest.TestCase):
    def result(self):
        from .qemu_smoke import STARTUP_110_PCS, RAM_COPY_110, RAM_COPY_110_SHA256
        from .qemu_workdir import ROM1_110_SHA256
        return dict(returncode=0,rom1_sha256=ROM1_110_SHA256,firmware='110',
            bounded_stop=True,experimental_flash_id='c22539',task_events=1,
            ram_copy=dict(matches_rom_source=True,size=315804,
                ram_sha256=RAM_COPY_110_SHA256,**{k:hex(v) for k,v in RAM_COPY_110.items()}),
            stages=[dict(pc=pc) for pc in STARTUP_110_PCS])

    def run_report(self,result,events=None):
        script=Path(__file__).with_name('qemu_task_report.py')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'result.json').write_text(json.dumps(result))
            (root/'tasks.jsonl').write_text(lines([created_event()] if events is None else events))
            (root/'output.log').write_text('[MPU] FIXME: generic configuration\n')
            return subprocess.run([sys.executable,str(script),tmp],capture_output=True,text=True)

    def test_valid_report_and_repeated_invocation(self):
        for _ in range(2):
            completed=self.run_report(self.result())
            self.assertEqual(completed.returncode,0,completed.stderr)
            self.assertEqual(json.loads(completed.stdout)['events'],1)

    def test_report_requires_canonical_startup_and_complete_event_count(self):
        mutations=[('rom1_sha256','0'*64),('returncode',-9),('bounded_stop','true'),
                   ('firmware','130'),('task_events',2),('task_events',True),
                   ('stages',[]),('ram_copy',{})]
        for key,value in mutations:
            result=self.result();result[key]=value
            with self.subTest(key=key):
                completed=self.run_report(result)
                self.assertEqual(completed.returncode,2,completed.stdout+completed.stderr)
                self.assertNotIn('Traceback',completed.stderr)
        for key in ['rom1_sha256','task_events']:
            result=self.result();del result[key]
            completed=self.run_report(result)
            self.assertEqual(completed.returncode,2,completed.stdout+completed.stderr)

    def test_nonobject_result_is_a_controlled_rejection(self):
        for result in [None,[],7,'truncated']:
            with self.subTest(result=result):
                completed=self.run_report(result)
                self.assertEqual(completed.returncode,2,completed.stderr)
                self.assertNotIn('Traceback',completed.stderr)


if __name__=='__main__':unittest.main()
