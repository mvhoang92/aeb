"""CARLA server page: settings, start/stop/cleanup and command."""

from __future__ import annotations

import os
import signal
import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import List

from ui.launcher.commands import (
    server_command,
    server_environment,
    server_preview_command,
)
from ui.launcher.config import CARLA_ROOT, CARLA_SCRIPT
from ui.launcher.processes import (
    ManagedProcess,
    ProcessSpec,
    carla_process_rows,
    carla_listening,
    process_alive,
)


class ServerPageMixin:
    """Mixed into ``AebLauncher``; uses its Tk variables and helpers."""

    def _build_server_tab(self) -> None:
        page = self.server_tab

        connection = self._form(self._card(page, "Kết nối"))
        self._field(
            connection,
            "Host",
            ttk.Entry(connection, textvariable=self.host, width=16),
            row=0,
        )
        self._field(
            connection,
            "Port",
            ttk.Spinbox(connection, from_=1, to=65535, textvariable=self.port, width=8),
            row=0,
            column=1,
        )

        launch_card = self._card(page, "Khởi động simulator")
        launch = self._form(launch_card)
        quality = ttk.Combobox(
            launch,
            textvariable=self.server_quality,
            values=("Low", "Epic"),
            state="readonly",
            width=12,
        )
        self._field(launch, "Chất lượng đồ họa", quality, row=0)
        quality.bind("<<ComboboxSelected>>", lambda _event: self._refresh_command_preview())
        ttk.Checkbutton(
            launch,
            text="NVIDIA PRIME render offload",
            variable=self.nvidia_offload,
            command=self._refresh_command_preview,
        ).grid(row=0, column=2, columnspan=2, sticky=tk.W, padx=(self.theme.px(20), 0))
        ttk.Checkbutton(
            launch,
            text="Stable mode: port rõ ràng, tắt sound, window 1280x720",
            variable=self.server_stable_mode,
            command=self._refresh_command_preview,
        ).grid(row=1, column=0, columnspan=4, sticky=tk.W, pady=(self.theme.px(4), 0))
        self._note(
            launch_card,
            "Launcher không thêm -opengl. Stable mode giảm tải UE4 và khóa đúng "
            "RPC port. Nút dọn CARLA treo chỉ dùng khi port offline nhưng process "
            "CarlaUE4 vẫn còn chạy ngầm.",
        )

        self._action(page, "Bật CARLA", self._start_server, "Primary.TButton")
        self._action(page, "Dừng CARLA", self._stop_server, "Danger.TButton")
        self._action(page, "Dọn CARLA treo", self._cleanup_carla_processes)
        self.server_command = self._command_preview(page)

    def _server_spec(self) -> ProcessSpec:
        port = self._int_value(self.port, 2000)
        command = server_command(
            self.server_quality.get(),
            port,
            self.server_stable_mode.get(),
        )
        environment = server_environment(self.nvidia_offload.get())
        return ProcessSpec("CARLA Server", command, CARLA_ROOT, environment)

    def _server_preview_command(self) -> List[str]:
        return server_preview_command(
            self._server_spec().command,
            self.nvidia_offload.get(),
        )

    def _start_server(self) -> None:
        if not CARLA_SCRIPT.is_file():
            messagebox.showerror("Thiếu CARLA", "Không thấy {}".format(CARLA_SCRIPT))
            return
        port = self._int_value(self.port, 2000)
        if carla_listening(self.host.get(), port):
            messagebox.showinfo(
                "Server đã bật",
                "Port {} đã mở. Có thể CARLA đang được bật bên ngoài launcher.".format(
                    port
                ),
            )
            return
        rows = carla_process_rows()
        if rows and not messagebox.askyesno(
            "Có CARLA process treo",
            (
                "Port {} chưa mở nhưng vẫn thấy {} process CarlaUE4.\n"
                "Dọn các process này rồi bật lại CARLA?"
            ).format(port, len(rows)),
        ):
            return
        if rows:
            self._cleanup_carla_processes(confirm=False)
        self._start_process("server", self._server_spec())

    def _stop_server(self) -> None:
        self._stop_process("server")

    def _cleanup_carla_processes(self, confirm: bool = True) -> None:
        rows = carla_process_rows()
        if not rows:
            messagebox.showinfo("CARLA", "Không thấy process CarlaUE4 đang treo.")
            return
        if confirm:
            preview = "\n".join(
                "pid={} {}".format(pid, command[:120])
                for pid, command in rows[:4]
            )
            if len(rows) > 4:
                preview += "\n..."
            if not messagebox.askyesno(
                "Dọn CARLA treo",
                "Sẽ gửi tín hiệu dừng tới các process sau:\n\n{}".format(preview),
            ):
                return

        pids = [pid for pid, _command in rows]
        self._append_log(
            "CARLA Server",
            "Cleanup requested for pids: {}\n".format(
                ", ".join(str(pid) for pid in pids)
            ),
        )
        for pid in pids:
            try:
                os.kill(pid, signal.SIGINT)
            except OSError:
                pass
        time.sleep(1.5)
        for pid in pids:
            if process_alive(pid):
                try:
                    os.kill(pid, signal.SIGTERM)
                except OSError:
                    pass
        time.sleep(0.5)
        still_alive = [pid for pid in pids if process_alive(pid)]
        if still_alive:
            for pid in still_alive:
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
            self._append_log(
                "CARLA Server",
                "Force killed pids: {}\n".format(
                    ", ".join(str(pid) for pid in still_alive)
                ),
            )
        self._check_server_now()

    def _restart_carla_blocking(self) -> bool:
        port = self._int_value(self.port, 2000)
        self._append_log(
            "CARLA Server",
            "Restart requested before launching scenario\n",
        )
        managed = self.processes.get("server")
        if managed is not None and managed.running:
            self._append_log("CARLA Server", "Stopping launcher-managed CARLA\n")
            managed.stop(timeout=8.0)

        rows = carla_process_rows()
        if rows:
            self._append_log(
                "CARLA Server",
                "Stopping external CarlaUE4 pids: {}\n".format(
                    ", ".join(str(pid) for pid, _command in rows)
                ),
            )
            for pid, _command in rows:
                try:
                    os.kill(pid, signal.SIGINT)
                except OSError:
                    pass
            deadline = time.time() + 8.0
            while time.time() < deadline and carla_process_rows():
                self.root.update()
                time.sleep(0.25)
            for pid, _command in carla_process_rows():
                try:
                    os.kill(pid, signal.SIGTERM)
                except OSError:
                    pass
            time.sleep(1.0)
            for pid, _command in carla_process_rows():
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass

        spec = self._server_spec()
        try:
            process = ManagedProcess(spec, self.output_queue)
            process.start()
            self.processes["server"] = process
            self._update_process_label()
        except (OSError, RuntimeError) as exc:
            messagebox.showerror("Không bật được CARLA", str(exc))
            return False

        deadline = time.time() + 90.0
        while time.time() < deadline:
            self.root.update()
            if carla_listening(self.host.get(), port, timeout=0.5):
                self._append_log(
                    "CARLA Server",
                    "Port {} online after restart\n".format(port),
                )
                return True
            time.sleep(0.5)
        messagebox.showerror(
            "CARLA chưa sẵn sàng",
            "Đã restart nhưng port {} chưa online sau 90 giây.".format(port),
        )
        return False
