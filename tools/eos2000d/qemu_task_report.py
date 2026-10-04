#!/usr/bin/env python3
"""Validate private observer logs and summarize bounded QEMU experiments.

Codex-authored diagnostic tooling. Summaries are also private until reviewed:
addresses and synthetic public tests are safe; raw memory/disassembly is not.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re

try:
    from .qemu_smoke import check_startup_report
except ImportError:
    from qemu_smoke import check_startup_report

HEX = re.compile(r"0x[0-9A-Fa-f]{8}\Z")
OPERATIONS = frozenset(('sample', 'context', 'switch', 'created-tcb', 'create-call',
    'entry', 'sleep', 'message-receive', 'message-send', 'message-try-send',
    'wait-link', 'wake-unlink', 'flag-wait', 'flag-set', 'flag-clear',
    'semaphore-wait', 'semaphore-wait-unbounded', 'sequence-notify',
    'sequence-mask-updated', 'manager-dispatch', 'property-dispatch',
    'gpio-read', 'irq-reason', 'irq-handler', 'irq-ack', 'irq-return',
    'power-mode', 'flag-wait-result', 'debug-call', 'intercom-send', 'intercom-configured'))
WAIT_OPERATIONS = frozenset(('sleep', 'message-receive', 'flag-wait', 'semaphore-wait', 'semaphore-wait-unbounded'))
ANSI = re.compile(r"\x1b\[[0-9;]*m")
MMIO = re.compile(r"\[([^\]\s]+)\]\s+at\s+(?:(\S+):)?([0-9A-Fa-f]{8}|0x[0-9A-Fa-f]{8}):([0-9A-Fa-f]{8})\s+\[0x([0-9A-Fa-f]{8})\]\s+(->|<-)\s+0x([0-9A-Fa-f]+)(?=\\s|$)")


def integer(value, label, maximum=None):
    if type(value) is not int or value < 0 or (maximum is not None and value > maximum):
        raise ValueError('invalid ' + label)
    return value


def address(value):
    if not isinstance(value, str) or not HEX.fullmatch(value):
        raise ValueError('invalid 32-bit address')
    return value.upper().replace('0X', '0x')


def identity(task):
    if not isinstance(task, dict):
        raise ValueError('task must be an object')
    pointer = address(task.get('pointer'))
    if pointer == '0x00000000':
        return pointer, None
    for key in ('entry', 'id', 'name_pointer', 'object'):
        address(task.get(key))
    name = task.get('name')
    if name is not None and (not isinstance(name, str) or not name or len(name) > 63
                             or not all(32 <= ord(c) < 127 for c in name)):
        raise ValueError('invalid task name')
    for key in ('state_byte', 'wait_kind_byte'):
        integer(task.get(key), key, 255)
    if name is not None and task.get('name_qualified_by_creation') is not True:
        raise ValueError('unqualified task name')
    if type(task.get('name_qualified_by_creation')) is not bool:
        raise ValueError('missing name qualification')
    return pointer, name


def parse_events(text):
    """Reject malformed/truncated, reordered or inconsistent observer records."""
    events, known, last_time = [], {}, -1
    for number, line in enumerate(text.splitlines(), 1):
        try:
            event = json.loads(line)
            if not isinstance(event, dict) or event.get('operation') not in OPERATIONS:
                raise ValueError('unknown observer operation')
            if integer(event.get('step'), 'step') != number:
                raise ValueError('noncontiguous observer step')
            now = integer(event.get('time_monotonic_ns'), 'timestamp')
            if now < last_time:
                raise ValueError('timestamps went backwards')
            last_time = now
            for key in ('pc', 'sp', 'lr'):
                address(event.get(key))
            registers = event.get('registers')
            if not isinstance(registers, list) or len(registers) != 16:
                raise ValueError('expected 16 ARM registers')
            for register in registers:
                address(register)
            if any(address(event[key]) != address(registers[i]) for key, i in (('pc',15),('sp',13),('lr',14))):
                raise ValueError('register metadata disagrees')
            op = event['operation']
            if op == 'create-call':
                name = event.get('name')
                if name is not None and (not isinstance(name, str) or not name or len(name) > 63
                                         or not all(32 <= ord(c) < 127 for c in name)):
                    raise ValueError('invalid creation-call name')
            tasks = [event.get('current')]
            if op == 'created-tcb':
                created = event.get('created')
                pointer, name = identity(created)
                if not name or not created['name_qualified_by_creation'] or pointer in known:
                    raise ValueError('unqualified or duplicate task creation')
                known[pointer] = {k:created[k] for k in ('name', 'entry', 'id', 'name_pointer')}
            if op == 'switch':
                tasks += [event.get('old'), event.get('new')]
                identity(event.get('new'))
                if address(event.get('committed_pointer')) != address(event['new'].get('pointer')):
                    raise ValueError('switch store disagrees with selected task')
                if event['old'] != event['current']:
                    raise ValueError('switch old task disagrees')
            for task in tasks:
                pointer, name = identity(task)
                if name is not None and (pointer not in known or
                    any(task[k] != known[pointer][k] for k in known[pointer])):
                    raise ValueError('task name lacks matching creation record')
            if op == 'entry' and address(event['current'].get('entry')) != address(event['pc']):
                raise ValueError('entry disagrees with creation')
            if op in ('irq-reason', 'irq-handler', 'irq-ack'):
                integer(event.get('irq'), 'IRQ', 255)
                if op == 'irq-reason' and integer(event.get('reason'), 'IRQ reason') != event['irq'] * 4:
                    raise ValueError('IRQ reason disagrees')
                if op == 'irq-handler':
                    address(event.get('handler'))
            if op == 'gpio-read':
                address(event.get('address'))
                for key in ('logical_input', 'mask', 'value'):
                    integer(event.get(key), key, 0xFFFFFFFF)
            if op == 'intercom-send':
                payload = event.get('payload')
                size = int(registers[1], 16)
                if not isinstance(payload, str) or not 0 < size <= 128 or len(payload) != size * 2 or not re.fullmatch(r'[0-9a-fA-F]+', payload):
                    raise ValueError('invalid bounded Intercom payload')
                bytes.fromhex(payload)
            events.append(event)
        except (ValueError, TypeError, KeyError) as error:
            raise ValueError(f'observer line {number}: {error}') from error
    if not events:
        raise ValueError('empty observer log')
    return events


def parse_mmio(text):
    """Decode native access records; warnings never become guest transfers."""
    records = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = ANSI.sub('', raw)
        match = MMIO.search(line)
        if not match:
            if ' at ' in line and '[0x' in line and (' -> ' in line or ' <- ' in line):
                raise ValueError(f'malformed MMIO line {number}')
            continue
        module, task, pc, lr, reg, arrow, value = match.groups()
        records.append(dict(module=module, task=task, pc=address('0x'+pc.removeprefix('0x')),
            lr=address('0x'+lr), address=address('0x'+reg),
            operation='read' if arrow == '->' else 'write', value=integer(int(value,16), 'MMIO value', 0xFFFFFFFF)))
    return records


def extract_assertion(result):
    """Return a qualified assertion capture, never infer one from final PC."""
    if 'assertion' not in result:
        return None
    record = result['assertion']
    if result.get('stop_address') != '0x00003CBC' or not isinstance(record, dict):
        raise ValueError('assertion lacks a matching stop')
    for key in ('caller_return', 'filename_pointer'):
        address(record.get(key))
    integer(record.get('line'), 'assertion line')
    for key in ('expression', 'filename'):
        if record.get(key) is not None and not isinstance(record[key], str):
            raise ValueError('invalid assertion string')
    args = record.get('arguments')
    if not isinstance(args, list) or len(args) != 4:
        raise ValueError('invalid assertion arguments')
    for arg in args:
        address(arg)
    return record


def summarize(events, mmio=()):
    tasks, operations, irqs, create_calls = {}, Counter(), Counter(), {}
    for event in events:
        op = event['operation']; operations[op] += 1
        if op == 'create-call':
            create_calls[event.get('name')] = event['lr']
        if op == 'created-tcb':
            t = event['created']
            tasks[t['pointer']] = dict(name=t['name'], entry=t['entry'], creation_return=create_calls.get(t['name']), creation_helper_return=event['lr'],
                entry_hits=0, switches_in=0, waits={}, observed_pcs=[], last_state=None)
        t = tasks.get(event['current']['pointer'])
        if t:
            t['last_state'] = {k:event['current'][k] for k in ('state_byte','wait_kind_byte','object')}
            if event['pc'] not in t['observed_pcs']: t['observed_pcs'].append(event['pc'])
            if op == 'entry': t['entry_hits'] += 1
            if op in WAIT_OPERATIONS:
                key = op + ':' + event['registers'][0]
                t['waits'][key] = t['waits'].get(key,0) + 1
        if op == 'switch' and event['new']['pointer'] in tasks:
            tasks[event['new']['pointer']]['switches_in'] += 1
        if op == 'irq-reason': irqs[str(event['irq'])] += 1
    return dict(classification='QEMU + Experiment', events=len(events),
        observed_span_seconds=(events[-1]['time_monotonic_ns']-events[0]['time_monotonic_ns'])/1e9,
        operations=dict(operations), irq_reason_counts=dict(irqs), tasks=list(tasks.values()),
        mmio_modules=dict(Counter(r['module'] for r in mmio)),
        note='Wall-clock debugger span is not guest time; selected PCs do not measure every instruction.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', type=Path, help='private completed probe directory')
    args = p.parse_args()
    try:
        result = json.loads((args.directory/'result.json').read_text())
        ok, reason = check_startup_report(result)
        if not ok:
            raise ValueError(reason)
        if result.get('bounded_stop') is not True or result.get('firmware') != '110' or result.get('experimental_flash_id') != 'c22539':
            raise ValueError('expected a completed bounded C2 experiment')
        events = parse_events((args.directory/'tasks.jsonl').read_text())
        if integer(result.get('task_events'), 'task event count') != len(events):
            raise ValueError('task event count disagrees with completed probe')
        report = summarize(events,parse_mmio((args.directory/'output.log').read_text(errors='replace')))
        report['assertion'] = extract_assertion(result)
        print(json.dumps(report,indent=2))
    except (ValueError, OSError) as error:
        p.error(str(error))


if __name__ == '__main__':
    main()
