"""Read atomically replaced Unity progress without denying Windows delete sharing.

Use this for live monitoring. Ordinary Python open() can prevent File.Replace.
This module does not launch or modify simulations.
"""
import ctypes
import json
import os
import time
from pathlib import Path


def read_bytes(path):
    if os.name != 'nt':
        return Path(path).read_bytes()
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                       wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    close = kernel.CloseHandle
    close.argtypes = [wintypes.HANDLE]
    read = kernel.ReadFile
    read.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                     ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
    handle = create(str(Path(path).resolve()), 0x80000000, 7, None, 3, 0x80, None)
    if handle == wintypes.HANDLE(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        chunks = []
        buffer = ctypes.create_string_buffer(65536)
        count = wintypes.DWORD()
        while True:
            if not read(handle, buffer, len(buffer), ctypes.byref(count), None):
                raise ctypes.WinError(ctypes.get_last_error())
            if not count.value:
                return b''.join(chunks)
            chunks.append(buffer.raw[:count.value])
    finally:
        close(handle)


def read_progress(path, attempts=100):
    for attempt in range(attempts):
        try:
            return json.loads(read_bytes(path).decode('utf-8-sig'))
        except OSError as error:
            if getattr(error, 'winerror', None) not in (2, 5, 32, 33) or attempt + 1 == attempts:
                raise
            time.sleep(.02)
