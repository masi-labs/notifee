from typing import Any

from notifee.formatters.base import MessageFormatter


class DefaultFormatter(MessageFormatter):
    def format_message(self, message: str) -> dict[str, Any]:
        return {"message": message}
