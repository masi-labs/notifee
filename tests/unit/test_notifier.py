import threading
from unittest.mock import MagicMock, patch

import pytest
import requests

from notifee import Notifier, QueueFullError


class TestNotifierConstruction:
    def test_default_parameters(self):
        mock_session = MagicMock(spec=requests.Session)
        notifier = Notifier("http://localhost:8080", session=mock_session)
        assert notifier._url == "http://localhost:8080"
        assert notifier._timeout == 30
        assert notifier._queue.maxsize == 1000
        assert len(notifier._workers) == 10
        assert notifier._session is mock_session
        assert notifier._shutdown is False
        notifier.shutdown()

    def test_custom_parameters(self):
        mock_session = MagicMock(spec=requests.Session)
        notifier = Notifier(
            url="http://example.com",
            max_workers=5,
            max_queue_size=50,
            timeout=10,
            session=mock_session,
        )
        assert notifier._url == "http://example.com"
        assert notifier._timeout == 10
        assert notifier._queue.maxsize == 50
        assert len(notifier._workers) == 5
        notifier.shutdown()

    def test_creates_session_if_not_provided(self):
        with patch("notifee.notifier.requests.Session") as mock_session_cls:
            notifier = Notifier("http://localhost:8080")
            mock_session_cls.assert_called_once()
            notifier.shutdown()


class TestNotify:
    def test_returns_future(self):
        mock_session = MagicMock(spec=requests.Session)
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        with Notifier("http://localhost:8080", session=mock_session) as notifier:
            future = notifier.notify("hello")
            result = future.result(timeout=5)
            assert result is mock_response

    def test_sends_post_to_configured_url(self):
        mock_session = MagicMock(spec=requests.Session)
        mock_response = MagicMock(spec=requests.Response)
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        with Notifier("http://example.com/notify", session=mock_session) as notifier:
            future = notifier.notify("test message")
            future.result(timeout=5)

        mock_session.post.assert_called_with(
            "http://example.com/notify",
            json={"message": "test message"},
            timeout=30,
        )

    def test_sends_with_configured_timeout(self):
        mock_session = MagicMock(spec=requests.Session)
        mock_response = MagicMock(spec=requests.Response)
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        with Notifier(
            url="http://localhost:8080",
            timeout=5,
            session=mock_session,
        ) as notifier:
            future = notifier.notify("msg")
            future.result(timeout=5)

        mock_session.post.assert_called_with(
            "http://localhost:8080",
            json={"message": "msg"},
            timeout=5,
        )

    def test_multiple_messages_all_delivered(self):
        mock_session = MagicMock(spec=requests.Session)
        mock_response = MagicMock(spec=requests.Response)
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        with Notifier(
            "http://localhost:8080",
            session=mock_session,
        ) as notifier:
            futures = [notifier.notify(f"msg-{i}") for i in range(20)]
            results = [f.result(timeout=5) for f in futures]

        assert len(results) == 20
        assert mock_session.post.call_count == 20

    def test_is_non_blocking(self):
        mock_session = MagicMock(spec=requests.Session)
        mock_response = MagicMock(spec=requests.Response)
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        notifier = Notifier(
            "http://localhost:8080",
            max_queue_size=100,
            session=mock_session,
        )
        futures = []
        for i in range(50):
            future = notifier.notify(f"msg-{i}")
            futures.append(future)

        assert len(futures) == 50
        notifier.shutdown()


class TestQueueFull:
    def test_raises_queue_full_error_when_queue_is_full(self):
        worker_blocked = threading.Event()
        release_worker = threading.Event()
        mock_session = MagicMock(spec=requests.Session)

        def slow_post(*_args, **_kwargs):
            worker_blocked.set()
            release_worker.wait()

        mock_session.post.side_effect = slow_post

        notifier = Notifier(
            "http://localhost:8080",
            max_workers=1,
            max_queue_size=1,
            session=mock_session,
        )
        notifier.notify("first")
        worker_blocked.wait(timeout=5)
        notifier.notify("fills queue")

        with pytest.raises(QueueFullError, match="max size: 1"):
            notifier.notify("overflows")

        release_worker.set()
        notifier.shutdown(timeout=2)


class TestErrorHandling:
    def test_http_error_sets_exception_on_future(self):
        mock_session = MagicMock(spec=requests.Session)
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            response=mock_response
        )
        mock_session.post.return_value = mock_response

        with Notifier("http://localhost:8080", session=mock_session) as notifier:
            future = notifier.notify("will fail")
            with pytest.raises(requests.HTTPError):
                future.result(timeout=5)

    def test_connection_error_sets_exception_on_future(self):
        mock_session = MagicMock(spec=requests.Session)
        mock_session.post.side_effect = requests.ConnectionError("refused")

        with Notifier("http://localhost:8080", session=mock_session) as notifier:
            future = notifier.notify("will fail")
            with pytest.raises(requests.ConnectionError):
                future.result(timeout=5)

    def test_timeout_error_sets_exception_on_future(self):
        mock_session = MagicMock(spec=requests.Session)
        mock_session.post.side_effect = requests.Timeout("timed out")

        with Notifier("http://localhost:8080", session=mock_session) as notifier:
            future = notifier.notify("will fail")
            with pytest.raises(requests.Timeout):
                future.result(timeout=5)

    def test_failed_message_does_not_stop_worker(self):
        mock_session = MagicMock(spec=requests.Session)
        fail_response = MagicMock(spec=requests.Response)
        fail_response.status_code = 500
        fail_response.raise_for_status.side_effect = requests.HTTPError(
            response=fail_response
        )
        ok_response = MagicMock(spec=requests.Response)
        ok_response.status_code = 200
        ok_response.raise_for_status = MagicMock()

        mock_session.post.side_effect = [fail_response, ok_response]

        with Notifier("http://localhost:8080", max_workers=1, session=mock_session) as notifier:
            future_fail = notifier.notify("bad")
            future_ok = notifier.notify("good")

            with pytest.raises(requests.HTTPError):
                future_fail.result(timeout=5)
            result = future_ok.result(timeout=5)
            assert result is ok_response


class TestShutdown:
    def test_shutdown_drains_queue(self):
        mock_session = MagicMock(spec=requests.Session)
        mock_response = MagicMock(spec=requests.Response)
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        notifier = Notifier("http://localhost:8080", session=mock_session)
        futures = [notifier.notify(f"msg-{i}") for i in range(10)]
        notifier.shutdown(timeout=5)

        for f in futures:
            assert f.done()
            assert f.result() is mock_response

    def test_notify_after_shutdown_raises(self):
        mock_session = MagicMock(spec=requests.Session)
        notifier = Notifier("http://localhost:8080", session=mock_session)
        notifier.shutdown()

        with pytest.raises(RuntimeError, match="shut down"):
            notifier.notify("too late")

    def test_shutdown_closes_session(self):
        mock_session = MagicMock(spec=requests.Session)
        notifier = Notifier("http://localhost:8080", session=mock_session)
        notifier.shutdown()
        mock_session.close.assert_called_once()

    def test_all_workers_stopped_after_shutdown(self):
        mock_session = MagicMock(spec=requests.Session)
        notifier = Notifier(
            "http://localhost:8080",
            max_workers=5,
            session=mock_session,
        )
        notifier.shutdown(timeout=5)
        for worker in notifier._workers:
            assert not worker.is_alive()


class TestContextManager:
    def test_context_manager_shuts_down(self):
        mock_session = MagicMock(spec=requests.Session)
        mock_response = MagicMock(spec=requests.Response)
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        with Notifier("http://localhost:8080", session=mock_session) as notifier:
            notifier.notify("hello")

        assert notifier._shutdown is True
        mock_session.close.assert_called_once()

    def test_context_manager_returns_notifier(self):
        mock_session = MagicMock(spec=requests.Session)
        with Notifier("http://localhost:8080", session=mock_session) as notifier:
            assert isinstance(notifier, Notifier)
