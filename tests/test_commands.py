from editor.commands.base_command import Command, CommandStack


class AddCommand(Command):
    def __init__(self, target, value):
        self.target = target
        self.value = value

    def do(self):
        self.target['value'] += self.value

    def undo(self):
        self.target['value'] -= self.value


def test_command_stack_undo_redo():
    state = {'value': 0}
    stack = CommandStack()
    stack.push(AddCommand(state, 5))
    assert state['value'] == 5
    stack.undo()
    assert state['value'] == 0
    assert not stack.can_undo()
    stack.redo()
    assert state['value'] == 5


def test_command_stack_push_clears_redo():
    state = {'value': 0}
    stack = CommandStack()
    stack.push(AddCommand(state, 5))
    stack.undo()
    stack.push(AddCommand(state, 3))
    assert state['value'] == 3
    assert not stack.can_redo()


def test_command_stack_signals_emit_can_undo_and_can_redo():
    state = {'value': 0}
    stack = CommandStack()

    undo_history = []
    redo_history = []
    stack.can_undo_changed.connect(lambda v: undo_history.append(bool(v)))
    stack.can_redo_changed.connect(lambda v: redo_history.append(bool(v)))

    def last_undo() -> bool:
        assert undo_history, 'can_undo_changed was never emitted'
        return undo_history[-1]

    def last_redo() -> bool:
        assert redo_history, 'can_redo_changed was never emitted'
        return redo_history[-1]

    # Each operation below must emit BOTH signals, and the *final* emitted
    # value must reflect the new stack state. (The implementation emits
    # unconditionally, so we just check the terminal value.)
    baseline_undo = len(undo_history)
    baseline_redo = len(redo_history)

    stack.push(AddCommand(state, 5))
    assert len(undo_history) >= baseline_undo + 1
    assert len(redo_history) >= baseline_redo + 1
    assert last_undo() is True
    assert last_redo() is False

    stack.undo()
    assert last_undo() is False
    assert last_redo() is True

    stack.redo()
    assert last_undo() is True
    assert last_redo() is False

    stack.undo()
    # After undo, push clears the redo stack and emits the new terminal values.
    stack.push(AddCommand(state, 3))
    assert last_undo() is True
    assert last_redo() is False
