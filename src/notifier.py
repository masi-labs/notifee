import queue
import threading
import requests
from concurrent.futures import Future

class Notifier:
    def __init__(
        self,
        url: str,
        max_workers: int = 10,
        max_queue_size: int = 1000,
        timeout: int = 30,
    ):
        self._url = url
        self._session = requests.Session()
        self._queue = queue.Queue(maxsize=max_queue_size)
        self._workers = []
        for _ in range(max_workers):
            worker = threading.Thread(target=self._worker)
            worker.start()
            self._workers.append(worker)

    def _worker(self):
        while True:
            try:
                message, future = self._queue.get(block=True)
                if message is None:
                    break
                self._session.post(self._url, json=message)
                # POST and resolve future
            except queue.Empty:
                break

    def notify(self, message: str) -> Future:
        future = Future()
        self._queue.put((message, future))
        return future

    def shutdown(self, timeout: int = None):
        # Signal workers to stop    
        for _ in self._workers:
            self._queue.put((None, None))
        # Wait for workers to finish
        for worker in self._workers:
            worker.join(timeout=timeout)
