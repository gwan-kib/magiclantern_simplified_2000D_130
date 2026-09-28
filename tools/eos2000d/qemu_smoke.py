#!/usr/bin/env python3
"""Run or inspect an EOS QEMU boot log and require ordered progress markers."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Sequence


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
