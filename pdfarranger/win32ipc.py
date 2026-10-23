# Copyright (C) 2026 pdfarranger contributors
#
# pdfarranger is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import json
import os
import socket
import threading

try:
    from gi.repository import GLib
except (ImportError, ValueError):
    GLib = None


def encode_files(files: list) -> bytes:
    return (json.dumps(list(files)) + "\n").encode("utf-8")


def decode_files(payload: bytes | str) -> list:
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    return json.loads(payload.strip())


def default_lock_dir() -> str:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
        if not base:
            base = os.path.expanduser(r"~\AppData\Local")
        return os.path.join(base, "pdfarranger")
    return os.path.expanduser("~/.local/share/pdfarranger")


def gtk_unique_is_enough() -> bool:
    if os.environ.get("PDFARRANGER_WIN32_IPC") == "1":
        return False
    if os.name != "nt":
        return True
    if GLib is None:
        return False
    major = getattr(GLib, "MAJOR_VERSION", 0)
    minor = getattr(GLib, "MINOR_VERSION", 0)
    return major > 2 or (major == 2 and minor >= 44)


def _do_submit(files: list, directory: str | None = None) -> bool:
    if directory is None:
        directory = default_lock_dir()
    lock_file = os.path.join(directory, "instance.port")
    if not os.path.exists(lock_file):
        return False
    try:
        with open(lock_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
    except OSError:
        return False

    if not content or ":" not in content:
        return False

    host, port_str = content.split(":", 1)
    try:
        port = int(port_str)
    except ValueError:
        return False

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2.0)
    try:
        s.connect((host, port))
        s.sendall(encode_files(files))
        try:
            s.shutdown(socket.SHUT_WR)
        except OSError:
            pass
        try:
            s.recv(1024)
        except OSError:
            pass
        return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        try:
            os.remove(lock_file)
        except OSError:
            pass
        return False
    finally:
        try:
            s.close()
        except OSError:
            pass


class _SubmitDescriptor:
    def __get__(self, instance, owner=None):
        if instance is not None:
            return lambda files, directory=None: _do_submit(
                files, instance.directory if directory is None else directory
            )
        return lambda files, directory=None: _do_submit(
            files, default_lock_dir() if directory is None else directory
        )


class Win32Handoff:
    submit = _SubmitDescriptor()

    def __init__(self, callback=None, ready_callback=None, directory=None):
        self.callback = callback
        self.ready_callback = ready_callback
        self.directory = directory if directory is not None else default_lock_dir()
        self._server_sock = None
        self._thread = None
        self._last_client_thread = None
        self._stopping = threading.Event()
        self._lock_file = os.path.join(self.directory, "instance.port")

    def start(self, callback=None) -> None:
        if callback is not None:
            self.callback = callback
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind(("127.0.0.1", 0))
        self._server_sock.listen(5)
        host, port = self._server_sock.getsockname()[:2]
        os.makedirs(self.directory, exist_ok=True)
        with open(self._lock_file, "w", encoding="utf-8") as f:
            f.write(f"{host}:{port}\n")
        self._stopping.clear()
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()
        if self.ready_callback:
            self.ready_callback()

    def _listen(self) -> None:
        while not self._stopping.is_set():
            try:
                client_sock, _addr = self._server_sock.accept()
            except (OSError, socket.error):
                break
            if self._stopping.is_set():
                try:
                    client_sock.close()
                except Exception:
                    pass
                break
            t = threading.Thread(target=self._handle_client, args=(client_sock,), daemon=True)
            self._last_client_thread = t
            t.start()

    def _handle_client(self, client_sock: socket.socket) -> None:
        try:
            client_sock.settimeout(5.0)
            file_obj = client_sock.makefile("rb")
            line = file_obj.readline()
            if line:
                files = decode_files(line)
                self._notify(files)
            try:
                client_sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
        except Exception:
            pass
        finally:
            try:
                client_sock.close()
            except Exception:
                pass

    def _notify(self, files: list) -> None:
        if not self.callback:
            return
        if GLib and hasattr(GLib, "idle_add") and hasattr(GLib, "main_depth") and GLib.main_depth() > 0:
            GLib.idle_add(self.callback, files)
        else:
            self.callback(files)

    def wait_idle(self, timeout: float | None = None) -> None:
        thread = self._last_client_thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=timeout)

    def stop(self) -> None:
        self._stopping.set()
        if self._server_sock:
            try:
                self._server_sock.close()
            except Exception:
                pass
            self._server_sock = None
        if os.path.exists(self._lock_file):
            try:
                os.remove(self._lock_file)
            except OSError:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
