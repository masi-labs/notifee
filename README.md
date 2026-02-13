# notifee

A Python library that sends HTTP POST notifications to a configured endpoint. Non-blocking, concurrent, and designed to handle message spikes without exhausting resources.

## Installation

```bash
pip install notifee
```

## Quick start

```python
from notifee import Notifier

notifier = Notifier("http://localhost:8080/notify")

future = notifier.notify("something happened")

# check the result whenever you want
response = future.result()  # blocks until done
print(response.status_code)

notifier.shutdown()
```

## Usage

### Construction

```python
notifier = Notifier(
    url="http://localhost:8080/notify",
    max_workers=10,       # concurrent sender threads (default: 10)
    max_queue_size=1000,  # max queued messages (default: 1000)
    timeout=30,           # request timeout in seconds (default: 30)
)
```

### Sending messages

`notify()` enqueues the message and returns immediately with a `concurrent.futures.Future`:

```python
future = notifier.notify("user signed up")
```

The future resolves with the HTTP `Response` on success, or raises the exception on failure:

```python
try:
    response = future.result()
except Exception as e:
    print(f"notification failed: {e}")
```

You can also attach a callback instead of blocking:

```python
def on_done(future):
    if future.exception():
        print(f"failed: {future.exception()}")

future.add_done_callback(on_done)
```

### Handling backpressure

If the internal queue is full, `notify()` raises `QueueFullError` immediately — it never blocks:

```python
from notifee import Notifier, QueueFullError

try:
    notifier.notify(message)
except QueueFullError:
    print("too many pending notifications, dropping message")
```

### Shutdown

Graceful shutdown drains the queue and waits for in-flight requests:

```python
notifier.shutdown(timeout=10)
```

Or use it as a context manager:

```python
with Notifier("http://localhost:8080/notify") as notifier:
    notifier.notify("hello")
    notifier.notify("world")
# queue drained, workers stopped
```

## How it works

```
notify(msg) -> [bounded Queue] -> N worker threads -> HTTP POST
    |                                    |
 returns Future                   resolves Future
 immediately                    (response or error)
```

- **Bounded queue** absorbs bursts without unbounded memory growth
- **Fixed worker pool** limits concurrent connections (no file descriptor exhaustion)
- **Shared connection pool** reuses HTTP connections for efficiency
- **Fail-fast** on overload — caller gets `QueueFullError`, never blocks

## Requirements

- Python 3.10+
- `requests`
