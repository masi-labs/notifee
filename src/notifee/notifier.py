import queue
import threading
from types import TracebackType

from concurrent.futures import Future
import requests


from notifee.exceptions import QueueFullError
from notifee.formatters import MessageFormatter, DefaultFormatter

_SENTINEL = None


class Notifier:
    def __init__(
        self,
        url: str,
        max_workers: int = 10,
        max_queue_size: int = 1000,
        timeout: int = 30,
        session: requests.Session | None = None,
        formatter: MessageFormatter | None = None,
    ) -> None:
        self._url = url
        self._timeout = timeout
        self._session = session or requests.Session()
        self._formatter = formatter or DefaultFormatter()
        self._queue = queue.Queue(maxsize=max_queue_size)
        self._shutdown = False
        self._workers = []
        for _ in range(max_workers):
            worker = threading.Thread(target=self._worker, daemon=True)
            worker.start()
            self._workers.append(worker)

    def _worker(self) -> None:
        while True:
            item = self._queue.get()
            if item is _SENTINEL:
                break
            message, future = item
            try:
                payload = self._formatter.format_message(message)
                response = self._session.post(
                    self._url,
                    json=payload,
                    timeout=self._timeout,
                )
                response.raise_for_status()
                future.set_result(response)
            except Exception as e:  # pylint: disable=broad-exception-caught
                future.set_exception(e)

    def notify(self, message: str) -> Future[requests.Response]:
        if self._shutdown:
            raise RuntimeError("Notifier is shut down")
        future = Future()
        try:
            self._queue.put_nowait((message, future))
        except queue.Full as exc:
            raise QueueFullError(
                f"Queue is full (max size: {self._queue.maxsize})"
            ) from exc
        return future

    def shutdown(self, timeout: float | None = None) -> None:
        self._shutdown = True
        for _ in self._workers:
            self._queue.put(_SENTINEL)
        for worker in self._workers:
            worker.join(timeout=timeout)
        self._session.close()

    def __enter__(self) -> "Notifier":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        self.shutdown()
        return False
