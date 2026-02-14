from abc import ABC, abstractmethod
from typing import Any


class MessageFormatter(ABC):
    @abstractmethod
    def format_message(self, message: str) -> dict[str, Any]:
        pass
