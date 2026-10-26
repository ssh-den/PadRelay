"""One bounded terminal reader for a mapper session, portable to Windows."""

import queue
import sys
import threading
from typing import TextIO


class ConsoleInput:
    def __init__(self, stream: TextIO | None = None):
        self._stream = stream or sys.stdin
        self._lines: queue.Queue[str] = queue.Queue(maxsize=32)
        self._closed = threading.Event()
        self._eof = threading.Event()
        self._thread = threading.Thread(
            target=self._read, name="mapper-console", daemon=True
        )
        self._thread.start()

    def _read(self) -> None:
        try:
            while not self._closed.is_set():
                line = self._stream.readline()
                if not line:
                    break
                while not self._closed.is_set():
                    try:
                        self._lines.put(line.rstrip("\r\n"), timeout=0.1)
                        break
                    except queue.Full:
                        continue
        finally:
            self._eof.set()

    def pop(self) -> str | None:
        try:
            return self._lines.get_nowait()
        except queue.Empty:
            if self._eof.is_set():
                raise EOFError("Terminal input closed") from None
            return None

    def close(self) -> None:
        # A blocked console read cannot be interrupted portably; the sole daemon
        # exits on its next read. The mapper process owns this reader's lifetime.
        self._closed.set()
