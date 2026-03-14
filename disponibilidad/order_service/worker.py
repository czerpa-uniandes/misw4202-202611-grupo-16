from __future__ import annotations

import threading
import time
from typing import Callable


class OrderWorker(threading.Thread):
    """Worker en background que desacopla al API de /orders del procesamiento."""

    def __init__(
        self,
        poll_fn: Callable[[], tuple[int, dict] | None],
        process_fn: Callable[[dict], None],
        ack_fn: Callable[[int], None],
        interval_seconds: float = 1.0,
    ) -> None:
        super().__init__(daemon=True)
        self.poll_fn = poll_fn
        self.process_fn = process_fn
        self.ack_fn = ack_fn
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()

    def run(self) -> None:
        while not self._stop_event.is_set():
            message = self.poll_fn()
            if not message:
                time.sleep(self.interval_seconds)
                continue

            message_id, order = message
            self.process_fn(order)
            self.ack_fn(message_id)

    def stop(self) -> None:
        self._stop_event.set()
