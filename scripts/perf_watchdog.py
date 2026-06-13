import os
import sys
import threading
import time
import traceback
from typing import Optional


def _env_int(name: str, default: int) -> int:
    try:
        return int(str(os.environ.get(name, str(default))).strip())
    except Exception:
        return int(default)


class SlowFrameWatchdog:
    """
    Low-overhead watchdog for the pygame main loop.

    This does not profile every line. Instead, it samples the main thread stack
    when a frame is still running after the configured threshold, which is the
    practical signal needed when the sim visibly hangs or stutters.
    """

    def __init__(self, name: str = "PCD", threshold_ms: Optional[int] = None) -> None:
        self.name = str(name)
        self.threshold_ms = int(_env_int("PCD_SLOW_FRAME_MS", 250) if threshold_ms is None else threshold_ms)
        self.stack_limit = max(4, int(_env_int("PCD_SLOW_STACK_LIMIT", 18)))
        self.repeat_ms = max(self.threshold_ms, int(_env_int("PCD_SLOW_REPEAT_MS", 1000)))
        self.poll_ms = max(10, min(100, int(self.threshold_ms / 4) if self.threshold_ms > 0 else 100))
        self._enabled = self.threshold_ms > 0
        self._lock = threading.Lock()
        self._active = False
        self._label = ""
        self._start_s = 0.0
        self._seq = 0
        self._last_report_seq = -1
        self._last_report_s = 0.0
        self._main_thread_id = threading.get_ident()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @property
    def enabled(self) -> bool:
        return bool(self._enabled)

    def start(self) -> None:
        if not self._enabled or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name=f"{self.name}SlowFrameWatchdog", daemon=True)
        self._thread.start()
        print(
            f"[PERF] slow-frame watchdog enabled threshold={self.threshold_ms}ms "
            f"(set PCD_SLOW_FRAME_MS=0 to disable)"
        )

    def stop(self) -> None:
        self._stop.set()

    def begin_frame(self, label: str = "main_loop") -> None:
        if not self._enabled:
            return
        with self._lock:
            self._active = True
            self._label = str(label)
            self._start_s = time.perf_counter()
            self._seq += 1

    def end_frame(self) -> None:
        if not self._enabled:
            return
        with self._lock:
            self._active = False

    def _run(self) -> None:
        poll_s = max(0.01, float(self.poll_ms) / 1000.0)
        threshold_s = max(0.001, float(self.threshold_ms) / 1000.0)
        repeat_s = max(threshold_s, float(self.repeat_ms) / 1000.0)
        while not self._stop.wait(poll_s):
            with self._lock:
                active = bool(self._active)
                label = str(self._label)
                start_s = float(self._start_s)
                seq = int(self._seq)
                last_seq = int(self._last_report_seq)
                last_report_s = float(self._last_report_s)
            if not active or start_s <= 0.0:
                continue
            now_s = time.perf_counter()
            elapsed_s = now_s - start_s
            if elapsed_s < threshold_s:
                continue
            if seq == last_seq and (now_s - last_report_s) < repeat_s:
                continue
            self._report(label, elapsed_s)
            with self._lock:
                self._last_report_seq = seq
                self._last_report_s = now_s

    def _report(self, label: str, elapsed_s: float) -> None:
        frame = sys._current_frames().get(int(self._main_thread_id))
        elapsed_ms = int(round(float(elapsed_s) * 1000.0))
        if frame is None:
            print(f"[PERF][SLOW] {label} running {elapsed_ms}ms; main-thread stack unavailable")
            return
        stack = traceback.extract_stack(frame, limit=self.stack_limit)
        current = stack[-1] if stack else None
        if current is not None:
            print(
                f"[PERF][SLOW] {label} running {elapsed_ms}ms "
                f"(threshold {self.threshold_ms}ms); current {current.filename}:{current.lineno} in {current.name}"
            )
        else:
            print(f"[PERF][SLOW] {label} running {elapsed_ms}ms (threshold {self.threshold_ms}ms)")
        for entry in stack:
            print(f"  File \"{entry.filename}\", line {entry.lineno}, in {entry.name}")
            if entry.line:
                print(f"    {entry.line}")


def create_slow_frame_watchdog(name: str = "PCD") -> SlowFrameWatchdog:
    watchdog = SlowFrameWatchdog(name=name)
    watchdog.start()
    return watchdog
