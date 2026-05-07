import threading
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .config import SAVE_DIR, TRACKED_FILES


class _DebounceHandler(FileSystemEventHandler):
    def __init__(self, callback: Callable, debounce_secs: float = 3.0) -> None:
        self._callback = callback
        self._debounce = debounce_secs
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def on_modified(self, event) -> None:
        if event.is_directory:
            return
        if Path(event.src_path).name in TRACKED_FILES:
            self._schedule()

    def _schedule(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._debounce, self._callback)
            self._timer.daemon = True
            self._timer.start()

    def cancel(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None


class SaveWatcher:
    def __init__(self, callback: Callable) -> None:
        self._callback = callback
        self._observer: Observer | None = None
        self._handler: _DebounceHandler | None = None
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        if not SAVE_DIR.exists():
            return
        self._handler = _DebounceHandler(self._callback)
        self._observer = Observer()
        self._observer.schedule(self._handler, str(SAVE_DIR), recursive=True)
        self._observer.start()
        self._running = True

    def stop(self) -> None:
        if not self._running:
            return
        if self._handler:
            self._handler.cancel()
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
        self._handler = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running
