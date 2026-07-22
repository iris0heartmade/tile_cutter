from abc import ABC, abstractmethod
from PyQt5.QtGui import QMouseEvent


class Tool(ABC):
    """Abstract base class for canvas tools."""

    name: str = 'Tool'

    @abstractmethod
    def on_mouse_press(self, event: QMouseEvent, canvas) -> None:
        raise NotImplementedError

    @abstractmethod
    def on_mouse_move(self, event: QMouseEvent, canvas) -> None:
        raise NotImplementedError

    @abstractmethod
    def on_mouse_release(self, event: QMouseEvent, canvas) -> None:
        raise NotImplementedError

    def get_options(self) -> dict:
        return {}