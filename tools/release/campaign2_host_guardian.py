#!/usr/bin/env python3
"""Host-only watchdog fixture. No device execution or vehicle-state adapter."""
from __future__ import annotations

from dataclasses import dataclass
import json
import multiprocessing
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time

CHILD_BOOTSTRAP = '''import ctypes, os, signal, sys
if ctypes.CDLL(None).prctl(1, signal.SIGKILL, 0, 0, 0) != 0: os._exit(125)
if os.getppid() != int(sys.argv[1]): os._exit(126)
os.execv(sys.argv[2], sys.argv[2:])
'''


def fixture_path(path: Path) -> Path:
    """Accept only an existing, real /tmp directory and its regular Python fixture."""
    if not path.is_absolute() or '..' in path.parts or not path.is_relative_to(Path('/tmp')):
        raise ValueError('host fixture must be beneath /tmp')
    current = Path('/')
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink():
            raise ValueError('symlink in host fixture path')
    if not path.is_dir():
        raise ValueError('host fixture directory absent')
    return path


def fixture_script(path: Path, directory: Path) -> Path:
    if not path.is_absolute() or '..' in path.parts or path.parent != directory or path.is_symlink():
        raise ValueError('fixture script must be an immediate child of host fixture')
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
        raise ValueError('fixture script is not an owned regular file')
    return path


def _leader_exited(proc: subprocess.Popen) -> bool:
    # WNOWAIT leaves the exited leader unreaped, reserving its PID/PGID until
    # the whole owned process group is stopped. Popen.poll() would reap it.
    return os.waitid(os.P_PID, proc.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None


def _live_group_members(pgid: int) -> list[int]:
    members = []
    for path in Path('/proc').iterdir():
        if not path.name.isdecimal():
            continue
        try:
            fields = path.joinpath('stat').read_text().rsplit(')', 1)[1].split()
            if int(fields[2]) == pgid and fields[0] != 'Z':
                members.append(int(path.name))
        except (OSError, IndexError, ValueError):
            continue
    return members


def _stop(proc: subprocess.Popen) -> bool:
    if os.getpgid(proc.pid) != proc.pid:
        raise RuntimeError('fixture worker lost dedicated process group')
    remaining = _live_group_members(proc.pid)
    if remaining:
        os.killpg(proc.pid, signal.SIGTERM)
        deadline = time.monotonic() + 0.5
        while time.monotonic() < deadline and _live_group_members(proc.pid):
            time.sleep(0.02)
        if _live_group_members(proc.pid):
            os.killpg(proc.pid, signal.SIGKILL)
            deadline = time.monotonic() + 0.5
            while time.monotonic() < deadline and _live_group_members(proc.pid):
                time.sleep(0.02)
    if _live_group_members(proc.pid):
        raise RuntimeError('owned fixture process group still has live members')
    proc.wait(timeout=0.5)
    return bool(remaining)


def _record(directory: Path, outcome: dict) -> None:
    path = directory / 'guardian_result.json'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(outcome, stream, sort_keys=True)
        stream.write('\n')


def _guardian(conn, directory: Path, script: Path, max_seconds: float, heartbeat_seconds: float) -> None:
    proc = None
    try:
        proc = subprocess.Popen([sys.executable, '-c', CHILD_BOOTSTRAP, str(os.getpid()),
                                 sys.executable, str(script)], cwd=directory,
                                start_new_session=True, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        conn.send({'state': 'STARTED', 'worker_pid': proc.pid})
        began = last_heartbeat = time.monotonic()
        reason = None
        leader_exited = False
        while not (leader_exited := _leader_exited(proc)):
            now = time.monotonic()
            if now - began >= max_seconds:
                reason = 'TIMEOUT'
                break
            if now - last_heartbeat >= heartbeat_seconds:
                reason = 'HEARTBEAT_LOST'
                break
            if conn.poll(min(0.05, heartbeat_seconds / 4)):
                try:
                    message = conn.recv()
                except EOFError:
                    reason = 'CONTROLLER_DISCONNECTED'
                    break
                if message == 'HEARTBEAT':
                    last_heartbeat = time.monotonic()
                else:
                    reason = 'ABORT_OR_INVALID_COMMAND'
                    break
        group_had_members = _stop(proc)
        if leader_exited and group_had_members and reason is None:
            reason = 'WORKER_EXITED_WITH_GROUP_MEMBERS_TERMINATED'
        outcome = {'decision': 'ABORTED_HOST_FIXTURE' if reason else 'HOST_FIXTURE_EXITED',
                   'reason': reason or ('EXIT_ZERO' if proc.returncode == 0 else 'WORKER_NONZERO'),
                   'exit_code': proc.returncode, 'worker_pid': proc.pid,
                   'device_write_performed': False}
        _record(directory, outcome)
        try:
            conn.send(outcome)
        except (BrokenPipeError, EOFError, OSError):
            pass
    finally:
        if proc is not None and proc.returncode is None:
            _stop(proc)
        conn.close()


@dataclass
class HostGuardian:
    process: multiprocessing.Process
    connection: object
    worker_pid: int
    directory: Path

    def heartbeat(self) -> None:
        self.connection.send('HEARTBEAT')

    def abort(self) -> None:
        self.connection.send('ABORT')

    def result(self, timeout: float = 5) -> dict:
        if not self.connection.poll(timeout):
            raise TimeoutError('guardian result missing')
        result = self.connection.recv()
        self.process.join(timeout=2)
        if self.process.is_alive():
            raise TimeoutError('guardian did not stop')
        return result


def start_host_fixture(directory: Path, script: Path, *, max_seconds: float = 5,
                       heartbeat_seconds: float = 0.5) -> HostGuardian:
    """Spawn a separate host guardian and a parent-death-killed single fixture worker."""
    directory = fixture_path(directory)
    script = fixture_script(script, directory)
    if not 0 < heartbeat_seconds <= 2 or not heartbeat_seconds < max_seconds <= 30:
        raise ValueError('invalid host fixture time limits')
    if (directory / 'guardian_result.json').exists():
        raise ValueError('fixture result already exists')
    parent, child = multiprocessing.get_context('spawn').Pipe()
    process = multiprocessing.get_context('spawn').Process(
        target=_guardian, args=(child, directory, script, max_seconds, heartbeat_seconds))
    process.start()
    child.close()
    if not parent.poll(3):
        process.terminate()
        process.join(timeout=2)
        raise TimeoutError('guardian startup failed')
    started = parent.recv()
    if started.get('state') != 'STARTED':
        raise RuntimeError('guardian did not start worker')
    return HostGuardian(process, parent, started['worker_pid'], directory)
