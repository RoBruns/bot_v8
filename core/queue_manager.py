import threading
from typing import List, Optional


class QueueManager:
    """Thread-safe CPF queue with pause/stop controls."""

    def __init__(self, cpfs: List[str]):
        self._cpfs = list(cpfs)
        self._index = 0
        self._lock = threading.Lock()
        self._pause_event = threading.Event()
        self._stop_event = threading.Event()
        self._pause_event.set()  # not paused by default

    def next_cpf(self) -> Optional[str]:
        """Returns next CPF or None if queue is exhausted or stopped."""
        self._pause_event.wait()  # blocks if paused
        if self._stop_event.is_set():
            return None
        with self._lock:
            if self._index >= len(self._cpfs):
                return None
            cpf = self._cpfs[self._index]
            self._index += 1
            return cpf

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

    def stop(self):
        self._stop_event.set()
        self._pause_event.set()  # unblock any waiting workers

    @property
    def is_paused(self) -> bool:
        return not self._pause_event.is_set()

    @property
    def is_stopped(self) -> bool:
        return self._stop_event.is_set()

    @property
    def progress(self) -> int:
        return self._index

    @property
    def total(self) -> int:
        return len(self._cpfs)
