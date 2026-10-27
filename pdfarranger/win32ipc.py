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

import ctypes
import json
import os
import socket
import threading
import time

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


DEFAULT_MUTEX_NAME = r"Local\com.github.jeromerobert.pdfarranger.instance"
HANDOFF_WAIT = 2.0
_ERROR_ALREADY_EXISTS = 183


def _windows_kernel32():
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.SetLastError.argtypes = [ctypes.c_ulong]
    kernel.SetLastError.restype = None
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
    kernel.CreateMutexW.restype = ctypes.c_void_p
    kernel.OpenMutexW.argtypes = [ctypes.c_uint, ctypes.c_int, ctypes.c_wchar_p]
    kernel.OpenMutexW.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel.CloseHandle.restype = ctypes.c_int
    return kernel


_kernel32 = None


def _kernel32_dll():
    global _kernel32
    if _kernel32 is None:
        _kernel32 = _windows_kernel32()
    return _kernel32


def _close_handle(handle) -> None:
    if not handle:
        return
    try:
        _kernel32_dll().CloseHandle(handle)
    except Exception:
        pass


def _windows_mutex_claim(name: str):
    kernel = _kernel32_dll()
    kernel.SetLastError(0)
    handle = kernel.CreateMutexW(None, True, name)
    if not handle:
        return None
    if ctypes.get_last_error() == _ERROR_ALREADY_EXISTS:
        _close_handle(handle)
        return None
    return handle


def _windows_mutex_exists(name: str) -> bool:
    kernel = _kernel32_dll()
    kernel.SetLastError(0)
    handle = kernel.OpenMutexW(0x00100000, False, name)
    if not handle:
        return False
    _close_handle(handle)
    return True


def _file_claim_is_held(directory: str) -> bool:
    path = os.path.join(directory, "instance.owner")
    if not os.path.exists(path):
        return False
    try:
        fd = os.open(path, os.O_RDWR)
    except OSError:
        return False
    try:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (ImportError, OSError):
        return True
    try:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_UN)
    except (ImportError, OSError):
        pass
    os.close(fd)
    return False


def claim_is_held(mutex_name: str, directory: str) -> bool:
    if os.name == "nt":
        return _windows_mutex_exists(mutex_name)
    return _file_claim_is_held(directory)


def gtk_unique_is_enough() -> bool:
    """GTK's application id joins launches on Linux and macOS.

    On Windows that handoff does not reach a window Explorer already
    opened, so every launch uses Win32Handoff instead.
    """
    if os.environ.get("PDFARRANGER_WIN32_IPC") == "1":
        return False
    return os.name != "nt"


def _submit_once(files: list, directory: str, keep_port_on_failure: bool) -> bool:
    lock_file = os.path.join(directory, "instance.port")
    if not os.path.exists(lock_file):
        return False
    try:
        with open(lock_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
    except OSError:
        return False

    if not content or ":" not in content:
        if not keep_port_on_failure:
            try:
                os.remove(lock_file)
            except OSError:
                pass
        return False

    host, port_str = content.split(":", 1)
    try:
        port = int(port_str)
    except ValueError:
        if not keep_port_on_failure:
            try:
                os.remove(lock_file)
            except OSError:
                pass
        return False

    delivered = False
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
        delivered = True
    except (ConnectionRefusedError, socket.timeout, OSError):
        if not keep_port_on_failure:
            try:
                os.remove(lock_file)
            except OSError:
                pass
    finally:
        try:
            s.close()
        except OSError:
            pass
    return delivered


def _do_submit(files: list, directory: str | None = None, wait: float = 0.0,
               mutex_name: str | None = None) -> bool:
    if directory is None:
        directory = default_lock_dir()
    if mutex_name is None:
        mutex_name = DEFAULT_MUTEX_NAME
    deadline = time.monotonic() + max(0.0, wait)
    while True:
        keep_port = wait > 0 and claim_is_held(mutex_name, directory)
        if _submit_once(files, directory, keep_port):
            return True
        if wait <= 0 or not claim_is_held(mutex_name, directory):
            return False
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.05)


class _SubmitDescriptor:
    def __get__(self, instance, owner=None):
        def submit(files, directory=None, wait=0.0, mutex_name=None):
            if instance is not None:
                if directory is None:
                    directory = instance.directory
                if mutex_name is None:
                    mutex_name = instance.mutex_name
            else:
                if directory is None:
                    directory = default_lock_dir()
                if mutex_name is None:
                    mutex_name = DEFAULT_MUTEX_NAME
            return _do_submit(files, directory, wait, mutex_name)

        return submit


class Win32Handoff:
    submit = _SubmitDescriptor()

    def __init__(self, callback=None, ready_callback=None, directory=None, mutex_name=None):
        self.callback = callback
        self.ready_callback = ready_callback
        self.directory = directory if directory is not None else default_lock_dir()
        self.mutex_name = mutex_name if mutex_name is not None else DEFAULT_MUTEX_NAME
        self._server_sock = None
        self._thread = None
        self._last_client_thread = None
        self._stopping = threading.Event()
        self._lock_file = os.path.join(self.directory, "instance.port")
        self._mutex_handle = None
        self._owner_fd = None
        self._claimed = False

    def claim(self) -> bool:
        if self._claimed:
            return True
        if os.name == "nt":
            handle = _windows_mutex_claim(self.mutex_name)
            if handle is None:
                return False
            self._mutex_handle = handle
            self._claimed = True
            return True
        return self._claim_file()

    def _claim_file(self) -> bool:
        try:
            import fcntl
        except ImportError:
            return False
        fd = None
        try:
            os.makedirs(self.directory, exist_ok=True)
            fd = os.open(os.path.join(self.directory, "instance.owner"), os.O_CREAT | os.O_RDWR)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
            return False
        self._owner_fd = fd
        self._claimed = True
        return True

    def _release_claim(self) -> None:
        if self._mutex_handle:
            _close_handle(self._mutex_handle)
            self._mutex_handle = None
        if self._owner_fd is not None:
            try:
                os.close(self._owner_fd)
            except OSError:
                pass
            self._owner_fd = None
        self._claimed = False

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
        self._release_claim()
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
