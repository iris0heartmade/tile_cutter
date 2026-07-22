from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QSpinBox, QCheckBox, QPushButton,
    QColorDialog,
)


class OptionsBar(QWidget):
    """Photoshop-style options bar showing the active tool's properties.

    `set_tool(tool)` rebuilds the option widgets from `tool.get_options()`:
    int values become QSpinBoxes, bools become QCheckBoxes and QColor values
    become color-picker buttons. Edits write straight back onto the tool
    instance via setattr, so tools always read the current values.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(6, 2, 6, 2)
        self.tool_label = QLabel('Tool: -')
        self._layout.addWidget(self.tool_label)
        self._layout.addStretch(1)
        self._tool = None
        self._option_widgets = []

    def set_tool(self, tool):
        self._tool = tool
        self._clear_options()
        if tool is None:
            self.tool_label.setText('Tool: -')
            return
        self.tool_label.setText(f'Tool: {tool.name}')
        for key, value in tool.get_options().items():
            self._add_option(tool, key, value)

    def _clear_options(self):
        for widget in self._option_widgets:
            self._layout.removeWidget(widget)
            widget.deleteLater()
        self._option_widgets = []

    def _add_widget(self, widget):
        # Keep the trailing stretch at the end of the layout.
        self._layout.insertWidget(self._layout.count() - 1, widget)
        self._option_widgets.append(widget)

    def _add_option(self, tool, key: str, value):
        label = QLabel(f'{key.capitalize()}:')
        self._add_widget(label)
        if isinstance(value, bool):
            box = QCheckBox()
            box.setChecked(value)
            box.toggled.connect(lambda checked, k=key: setattr(tool, k, checked))
            self._add_widget(box)
        elif isinstance(value, int):
            spin = QSpinBox()
            spin.setRange(0, 255)
            spin.setValue(value)
            spin.valueChanged.connect(lambda v, k=key: setattr(tool, k, v))
            self._add_widget(spin)
        elif isinstance(value, QColor):
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.setStyleSheet(f'background-color: {value.name()};')
            btn.clicked.connect(lambda _, k=key, b=btn: self._pick_color(tool, k, b))
            self._add_widget(btn)
        else:
            label.setText(f'{key.capitalize()}: {value}')

    def _pick_color(self, tool, key: str, button: QPushButton):
        current = getattr(tool, key)
        color = QColorDialog.getColor(current, self, f'Pick {key}')
        if color.isValid():
            setattr(tool, key, color)
            button.setStyleSheet(f'background-color: {color.name()};')
