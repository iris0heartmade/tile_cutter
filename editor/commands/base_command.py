from abc import ABC, abstractmethod
from typing import List
from PyQt5.QtCore import QObject, pyqtSignal


class Command(ABC):
    @abstractmethod
    def do(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def undo(self) -> None:
        raise NotImplementedError


class CommandStack(QObject):
    can_undo_changed = pyqtSignal(bool)
    can_redo_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._undo_stack: List[Command] = []
        self._redo_stack: List[Command] = []
        # Emit initial state so listeners can sync right after construction.
        self._emit_signals()

    def push(self, command: Command):
        command.do()
        self._undo_stack.append(command)
        self._redo_stack.clear()
        self._emit_signals()

    def undo(self):
        if not self._undo_stack:
            return
        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)
        self._emit_signals()

    def redo(self):
        if not self._redo_stack:
            return
        command = self._redo_stack.pop()
        command.do()
        self._undo_stack.append(command)
        self._emit_signals()

    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    def _emit_signals(self):
        self.can_undo_changed.emit(self.can_undo())
        self.can_redo_changed.emit(self.can_redo())
