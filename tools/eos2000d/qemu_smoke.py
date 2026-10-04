#!/usr/bin/env python3
"""Run or inspect an EOS QEMU boot log and require ordered progress markers."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Sequence

try:
    from .qemu_workdir import ROM1_110_SHA256
except ImportError:
    from qemu_workdir import ROM1_110_SHA256

STARTUP_110_PCS = (
    "0xFE0C0000", "0xFE0C000C", "0xFE0C0638", "0xFE0C3A38",
    "0xFE0C3A6C", "0x00029898", "0xFE0C3B0C", "0x00005254", "0xFE129718",
)

def check_startup_report(report: dict) -> tuple[bool, str]:
    """Require measured debugger stops, not translated-code or setup messages."""
    if report.get("error") or report.get("returncode") != 0:
        return False, "probe failed or QEMU exited abnormally"
    if report.get("rom1_sha256") != ROM1_110_SHA256:
        return False, "report does not identify the canonical 1.1.0 ROM1"
    copy = report.get("ram_copy", {})
    if copy.get("matches_rom_source") is not True:
        return False, "ROM-to-RAM copy was not verified"
    stages = report.get("stages", [])
    if not isinstance(stages, list) or any(not isinstance(stage, dict) for stage in stages):
        return False, "invalid debugger stage list"
    observed = [stage.get("pc") for stage in stages]
    cursor = 0
    for pc in STARTUP_110_PCS:
        try:
            cursor = observed.index(pc, cursor) + 1
        except ValueError:
            return False, f"missing ordered debugger stop: {pc}"
    return True, "all 110 startup debugger stops found in order"


def find_ordered_markers(text: str, markers: Sequence[str]) -> tuple[bool, str]:
    if not markers:
        return False, "no expected markers configured"

    cursor = 0
    for marker in markers:
        index = text.find(marker, cursor)
        if index < 0:
            return False, f"missing marker after offset {cursor}: {marker}"
        cursor = index + len(marker)

    return True, "all markers found in order"


def run_command(command: Sequence[str], timeout: float) -> tuple[str, int | None, bool]:
    proc = subprocess.Popen(
        list(command),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    timed_out = False
    try:
        output, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        proc.terminate()
        try:
            output, _ = proc.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            output, _ = proc.communicate()

    return output, proc.returncode, timed_out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe-report", type=Path, help="validate a private 110 qemu_probe.py JSON report through init-task entry; not a full boot test")
    parser.add_argument("--log-in", type=Path, help="inspect an existing QEMU log")
    parser.add_argument("--log-out", type=Path, help="save captured QEMU output")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument(
        "--expect",
        action="append",
        default=[],
        help="required marker; repeat in expected chronological order",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="command to run after --, e.g. -- qemu-system-arm ...",
    )
    args = parser.parse_args()

    if args.probe_report:
        if args.log_in or args.command or args.expect:
            parser.error("--probe-report cannot be combined with logs, commands, or --expect")
        try:
            report = json.loads(args.probe_report.read_text(encoding="utf-8"))
            if not isinstance(report, dict):
                raise ValueError("expected a JSON object")
            ok, reason = check_startup_report(report)
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            print(f"invalid probe report: {exc}")
            return 1
        print(reason)
        if ok:
            print("110 init-task entry verified; full boot and hardware safety remain unproven")
        return 0 if ok else 1

    if args.log_in and args.command:
        parser.error("use either --log-in or a command, not both")
    if not args.log_in and not args.command:
        parser.error("provide --log-in or a command after --")

    return_code: int | None = None
    timed_out = False

    if args.log_in:
        output = args.log_in.read_text(encoding="utf-8", errors="replace")
    else:
        command = args.command
        if command and command[0] == "--":
            command = command[1:]
        if not command:
            parser.error("empty command")
        output, return_code, timed_out = run_command(command, args.timeout)

    if args.log_out:
        args.log_out.write_text(output, encoding="utf-8")

    ok, reason = find_ordered_markers(output, args.expect)
    print(reason)

    if not ok:
        return 1

    # QEMU normally remains alive; reaching the timeout after all expected
    # markers is acceptable. An early non-zero exit is not.
    if not args.log_in and not timed_out and return_code not in (0, None):
        print(f"QEMU exited early with status {return_code}")
        return 1

    if timed_out:
        print("QEMU timeout reached after expected markers; treated as smoke-test success")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
