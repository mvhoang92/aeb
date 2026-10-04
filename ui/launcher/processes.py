"""Subprocess management and CARLA process helpers (no Tkinter dependency)."""

from __future__ import annotations

import os
import queue
import re
import signal
import socket
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set

from ui.launcher.commands import command_text


ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def port_open(host: str, port: int, timeout: float = 0.25) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


LOCAL_HOSTS = ("127.0.0.1", "localhost", "0.0.0.0", "::1")
TCP_LISTEN_STATE = "0A"


def listening_ports(tables=("/proc/net/tcp", "/proc/net/tcp6")) -> Optional[Set[int]]:
    """Local TCP ports in LISTEN state, read from the kernel without connecting.

    Returns None when the tables are unavailable (non-Linux).
    """
    ports: Set[int] = set()
    found = False
    for table in tables:
        try:
            with open(table) as stream:
                lines = stream.readlines()[1:]
        except OSError:
            continue
        found = True
        for line in lines:
            fields = line.split()
            if len(fields) > 3 and fields[3] == TCP_LISTEN_STATE:
                try:
                    ports.add(int(fields[1].rsplit(":", 1)[1], 16))
                except (IndexError, ValueError):
                    pass
    return ports if found else None


def carla_listening(host: str, port: int, timeout: float = 0.25) -> bool:
    """Is the CARLA server up?

    For a local server, read the listening-socket table instead of opening a
    connection: repeatedly connecting to and dropping the CARLA 0.9.11 RPC
    port is suspected of crashing the server. Remote hosts use port_open.
    """
    if str(host) in LOCAL_HOSTS:
        ports = listening_ports()
        if ports is not None:
            return int(port) in ports
    return port_open(host, port, timeout=timeout)


def carla_process_rows() -> List[tuple]:
    try:
        output = subprocess.check_output(
            ["pgrep", "-af", "CarlaUE4"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return []

    rows = []
    for line in output.splitlines():
        parts = line.split(maxsplit=1)
        if not parts:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        command = parts[1] if len(parts) > 1 else ""
        if "CarlaUE4-Linux-Shipping" in command or "CarlaUE4.sh" in command:
            rows.append((pid, command))
    return rows


def process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


@dataclass
class ProcessSpec:
    name: str
    command: List[str]
    cwd: Path
    environment: Optional[dict] = None


class ManagedProcess:
    def __init__(self, spec: ProcessSpec, output_queue: queue.Queue):
        self.spec = spec
        self.output_queue = output_queue
        self.process: Optional[subprocess.Popen] = None
        self.reader: Optional[threading.Thread] = None

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def start(self) -> None:
        if self.running:
            raise RuntimeError("{} đang chạy".format(self.spec.name))
        environment = os.environ.copy()
        environment["PYTHONUNBUFFERED"] = "1"
        if self.spec.environment:
            environment.update(self.spec.environment)
        self.process = subprocess.Popen(
            self.spec.command,
            cwd=str(self.spec.cwd),
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            bufsize=1,
            start_new_session=True,
        )
        self.output_queue.put(
            (
                self.spec.name,
                "START pid={} | {}\n".format(
                    self.process.pid,
                    command_text(self.spec.command),
                ),
            )
        )
        self.reader = threading.Thread(target=self._read_output, daemon=True)
        self.reader.start()

    def _read_output(self) -> None:
        assert self.process is not None
        assert self.process.stdout is not None
        for line in iter(self.process.stdout.readline, ""):
            self.output_queue.put((self.spec.name, ANSI_ESCAPE.sub("", line)))
        return_code = self.process.wait()
        self.output_queue.put(
            (
                self.spec.name,
                "EXIT code={}\n".format(return_code),
            )
        )

    def stop(self, timeout: float = 5.0) -> None:
        if not self.running or self.process is None:
            return
        try:
            os.killpg(os.getpgid(self.process.pid), signal.SIGINT)
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            try:
                self.process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
