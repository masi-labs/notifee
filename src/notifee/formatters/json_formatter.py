from notifee.formatters.base import MessageFormatter


class DefaultFormatter(MessageFormatter):
    def format_message(self, message: str) -> dict[str, str]:
        return {"message": message}
