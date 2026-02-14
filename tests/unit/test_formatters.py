import pytest

from notifee import MessageFormatter, DefaultFormatter


class TestDefaultFormatter:
    def test_formats_message_as_dict(self):
        formatter = DefaultFormatter()
        result = formatter.format_message("hello world")
        assert result == {"message": "hello world"}

    def test_formats_empty_string(self):
        formatter = DefaultFormatter()
        result = formatter.format_message("")
        assert result == {"message": ""}

    def test_is_instance_of_message_formatter(self):
        formatter = DefaultFormatter()
        assert isinstance(formatter, MessageFormatter)


class TestMessageFormatterAbstract:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            MessageFormatter()

    def test_subclass_must_implement_format_message(self):
        class IncompleteFormatter(MessageFormatter):
            pass

        with pytest.raises(TypeError):
            IncompleteFormatter()


class TestCustomFormatter:
    def test_custom_formatter_produces_expected_payload(self):
        class WebhookFormatter(MessageFormatter):
            def format_message(self, message: str) -> dict:
                return {
                    "event": "notification",
                    "data": {"content": message},
                    "version": 1,
                }

        formatter = WebhookFormatter()
        result = formatter.format_message("alert")
        assert result == {
            "event": "notification",
            "data": {"content": "alert"},
            "version": 1,
        }
