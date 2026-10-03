"""Sequential command queue, output parsing and CARLA helpers (no Tk).

Exit codes of the runners:
* 0 - every scenario-run PASSed;
* 1 - at least one algorithmic FAIL (``SystemExit(1)``), *or* an uncaught
  Python exception (traceback printed) - the parser tells them apart;
* 3 - TECHNICAL HARD-STOP from the CUDA preflight (no run directory created).
"""

from __future__ import absolute_import

import os
import re
import signal
import socket
import subprocess
import threading
import time

from ui.testbench.paths import AEB_ROOT, CARLA_LOG_FILE, CARLA_ROOT, CARLA_SCRIPT


OUTCOME_RUNNING = "running"
OUTCOME_PENDING = "pending"
OUTCOME_ALL_PASS = "all_pass"
OUTCOME_ALGO_FAIL = "algo_fail"
OUTCOME_HARD_STOP = "hard_stop"
OUTCOME_TECH_ERROR = "tech_error"
OUTCOME_STOPPED = "stopped"
OUTCOME_SKIPPED = "skipped"

OUTCOME_LABELS = {
    OUTCOME_PENDING: "Chờ",
    OUTCOME_RUNNING: "Đang chạy",
    OUTCOME_ALL_PASS: "PASS toàn bộ",
    OUTCOME_ALGO_FAIL: "Có FAIL thuật toán",
    OUTCOME_HARD_STOP: "HARD-STOP kỹ thuật",
    OUTCOME_TECH_ERROR: "Lỗi kỹ thuật",
    OUTCOME_STOPPED: "Đã dừng",
    OUTCOME_SKIPPED: "Không chạy",
}

TECHNICAL_OUTCOMES = (OUTCOME_HARD_STOP, OUTCOME_TECH_ERROR)

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
PROGRESS_LINE = re.compile(r"^\[(\d+)/(\d+)\]\s+(\S+)\s+run\s+(\d+)/(\d+)")
RESULT_LINE = re.compile(r"^\s*(PASS|FAIL)\s*\|")
RESUME_LINE = re.compile(r"Resume: bỏ qua (\d+)/(\d+)")
LOG_DIR_LINE = re.compile(r"^Log directory:\s*(.+)$")


class OutputState(object):
    """Incremental parse of one runner's stdout."""

    def __init__(self, expected_runs=0):
        self.expected_runs = int(expected_runs)
        self.jobs_total = None
        self.job_index = 0
        self.current_scenario = None
        self.current_run = None
        self.repeat = None
        self.passed = 0
        self.failed = 0
        self.resumed = 0
        self.saw_traceback = False
        self.saw_hard_stop = False
        self.log_directory = None
        self.last_error = None

    @property
    def done(self):
        return self.passed + self.failed

    def feed(self, line):
        line = ANSI_ESCAPE.sub("", line.rstrip("\r\n"))
        match = PROGRESS_LINE.match(line)
        if match:
            self.job_index = int(match.group(1))
            self.jobs_total = int(match.group(2))
            self.current_scenario = match.group(3)
            self.current_run = int(match.group(4))
            self.repeat = int(match.group(5))
            return line
        match = RESULT_LINE.match(line)
        if match:
            if match.group(1) == "PASS":
                self.passed += 1
            else:
                self.failed += 1
            return line
        match = RESUME_LINE.search(line)
        if match:
            self.resumed = int(match.group(1))
            return line
        match = LOG_DIR_LINE.match(line.strip())
        if match:
            self.log_directory = match.group(1).strip()
            return line
        if line.startswith("Traceback (most recent call last)"):
            self.saw_traceback = True
        if "TECHNICAL HARD-STOP" in line:
            self.saw_hard_stop = True
        stripped = line.strip()
        if self.saw_traceback and stripped and not line.startswith(" "):
            self.last_error = stripped
        return line


def classify_exit(returncode, state, stopped=False):
    """Map a runner exit to an outcome; technical problems never read as FAIL."""
    if stopped:
        return OUTCOME_STOPPED
    if returncode == 0:
        return OUTCOME_ALL_PASS
    if returncode == 3 or state.saw_hard_stop:
        return OUTCOME_HARD_STOP
    if returncode == 1 and not state.saw_traceback and state.failed > 0:
        return OUTCOME_ALGO_FAIL
    return OUTCOME_TECH_ERROR


LOCAL_HOSTS = ("127.0.0.1", "localhost", "0.0.0.0", "::1")
TCP_LISTEN = "0A"


def listening_ports(tables=("/proc/net/tcp", "/proc/net/tcp6")):
    """Local TCP ports in LISTEN state, read from the kernel (no connection).

    Returns ``None`` when the tables are unavailable (non-Linux).
    """
    ports = set()
    found = False
    for table in tables:
        try:
            with open(table) as stream:
                lines = stream.readlines()[1:]
        except (IOError, OSError):
            continue
        found = True
        for line in lines:
            fields = line.split()
            if len(fields) > 3 and fields[3] == TCP_LISTEN:
                try:
                    ports.add(int(fields[1].rsplit(":", 1)[1], 16))
                except (IndexError, ValueError):
                    pass
    return ports if found else None


def carla_listening(host, port):
    """Is CARLA up?  For a local server, check the listening-socket table
    instead of connecting: repeatedly opening and closing raw connections to
    the CARLA 0.9.11 RPC port is avoided because the server is fragile."""
    if str(host) in LOCAL_HOSTS:
        ports = listening_ports()
        if ports is not None:
            return int(port) in ports
    return port_open(host, port)


def port_open(host, port, timeout=0.25):
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except (OSError, ValueError):
        return False


def carla_command(quality="Low"):
    return [str(CARLA_SCRIPT), "-quality-level={}".format(quality)]


def carla_environment(base=None):
    environment = dict(os.environ if base is None else base)
    environment["__NV_PRIME_RENDER_OFFLOAD"] = "1"
    environment["__GLX_VENDOR_LIBRARY_NAME"] = "nvidia"
    return environment


def carla_command_text(quality="Low"):
    return (
        "cd {} && __NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia "
        "./CarlaUE4.sh -quality-level={}".format(CARLA_ROOT, quality)
    )


def start_carla(quality="Low", log_file=CARLA_LOG_FILE):
    """Start CARLA detached (own session) with the documented command."""
    stream = open(str(log_file), "ab")
    try:
        process = subprocess.Popen(
            carla_command(quality),
            cwd=str(CARLA_ROOT),
            env=carla_environment(),
            stdin=subprocess.DEVNULL,
            stdout=stream,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    finally:
        stream.close()
    return process.pid


def runner_environment(base=None):
    environment = dict(os.environ if base is None else base)
    environment["PYTHONUNBUFFERED"] = "1"
    # The runners must not inherit the GUI interpreter's re-exec marker.
    environment.pop("AEB_TESTBENCH_REEXEC", None)
    return environment


class CommandQueue(object):
    """Run planned commands one after another in a worker thread.

    ``emit(event, payload)`` is called from the worker thread; the GUI pushes
    those events into a ``queue.Queue`` and drains it on the Tk thread.
    Events: ``start`` (index), ``line`` (index, text), ``progress`` (index,
    state), ``end`` (index, outcome, returncode, state), ``finished``
    (outcomes).
    """

    INTERRUPT_GRACE_S = 10.0
    TERMINATE_GRACE_S = 8.0

    def __init__(self, commands, emit, stop_on_technical=True, cwd=AEB_ROOT, popen=None):
        self.commands = list(commands)
        self.emit = emit
        self.stop_on_technical = stop_on_technical
        self.cwd = str(cwd)
        self.popen = popen or subprocess.Popen
        self.outcomes = [OUTCOME_PENDING] * len(self.commands)
        self._process = None
        self._stop_queue = False
        self._stop_current = False
        self._lock = threading.Lock()
        self._thread = None

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        self._thread = threading.Thread(target=self._run, name="testbench-queue")
        self._thread.daemon = True
        self._thread.start()

    def stop_current(self):
        with self._lock:
            self._stop_current = True
            process = self._process
        if process is not None:
            threading.Thread(target=self._interrupt, args=(process,)).start()

    def stop_queue(self):
        self._stop_queue = True
        self.stop_current()

    def _interrupt(self, process):
        """SIGINT first so the runner's ``finally`` restores CARLA settings."""
        for sig, grace in (
            (signal.SIGINT, self.INTERRUPT_GRACE_S),
            (signal.SIGTERM, self.TERMINATE_GRACE_S),
            (signal.SIGKILL, 0.0),
        ):
            if process.poll() is not None:
                return
            try:
                os.killpg(process.pid, sig)
            except (OSError, ProcessLookupError):
                return
            deadline = time.time() + grace
            while grace and time.time() < deadline:
                if process.poll() is not None:
                    return
                time.sleep(0.1)

    def _run(self):
        for index, command in enumerate(self.commands):
            if self._stop_queue:
                self.outcomes[index] = OUTCOME_SKIPPED
                continue
            self._stop_current = False
            self.outcomes[index] = OUTCOME_RUNNING
            self.emit("start", (index,))
            state = OutputState(command.scenario_runs)
            returncode = None
            try:
                process = self.popen(
                    command.argv,
                    cwd=self.cwd,
                    env=runner_environment(),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1,
                    start_new_session=True,
                )
            except OSError as exc:
                state.last_error = str(exc)
                self.emit("line", (index, "Không khởi động được lệnh: {}".format(exc)))
                outcome = OUTCOME_TECH_ERROR
            else:
                with self._lock:
                    self._process = process
                for line in iter(process.stdout.readline, ""):
                    text = state.feed(line)
                    self.emit("line", (index, text))
                    self.emit("progress", (index, state))
                process.stdout.close()
                returncode = process.wait()
                with self._lock:
                    self._process = None
                outcome = classify_exit(returncode, state, stopped=self._stop_current)
            self.outcomes[index] = outcome
            self.emit("end", (index, outcome, returncode, state))
            if outcome in TECHNICAL_OUTCOMES and self.stop_on_technical:
                self._stop_queue = True
        self.emit("finished", (list(self.outcomes),))
