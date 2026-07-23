from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QSplitter, QScrollArea,
    QToolBar, QAction, QActionGroup, QSpinBox, QLabel,
    QFileDialog, QMessageBox, QInputDialog,
)

from editor.models.project_model import ProjectModel
from editor.models.source_image import SourceImage
from editor.commands.base_command import CommandStack
from editor.commands.clear_command import ClearCommand
from editor.commands.resize_canvas_command import ResizeCanvasCommand
from editor.exporters.godot_exporter import GodotExporter
from editor.widgets.canvas_widget import CanvasWidget
from editor.widgets.source_library_widget import SourceLibraryWidget
from editor.widgets.options_bar import OptionsBar
from editor.widgets.status_bar import StatusBar
from editor.tools.brush_tool import BrushTool
from editor.tools.eraser_tool import EraserTool
from editor.tools.eyedropper_tool import EyedropperTool
from editor.tools.rect_select_tool import RectSelectTool
from editor.tools.magic_wand_tool import MagicWandTool
from editor.tools.color_to_transparent_tool import ColorToTransparentTool


class MainWindow(QMainWindow):
    """TileCutter main window: menus, tool bar, options bar, source library
    (left), canvas (center, scrollable) and status bar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('TileCutter')
        self.resize(1400, 1000)

        self.project = ProjectModel(48, 48, 8, 8)
        self.command_stack = CommandStack()

        # Set True whenever an undoable change is made; drives the
        # close-with-unsaved-changes confirmation (spec §12).
        self.dirty = False

        self.tools = {
            '画笔': BrushTool(),
            '橡皮擦': EraserTool(),
            '吸管': EyedropperTool(),
            '矩形选择': RectSelectTool(),
            '魔棒': MagicWandTool(tolerance=30),
            '颜色转透明': ColorToTransparentTool(tolerance=30),
        }

        self._setup_widgets()
        self._setup_menu()
        self._setup_toolbar()
        self._connect_signals()

        # Default tool.
        self._set_tool(self.tools['画笔'], '画笔')
        self.tool_actions['画笔'].setChecked(True)
        self.status_bar.set_zoom(self.canvas.zoom())
        self.status_bar.set_canvas_size(self.project.cols, self.project.rows)

    # --- UI construction ----------------------------------------------------

    def _setup_widgets(self):
        self.canvas = CanvasWidget(self.project, self.command_stack)
        self.source_library = SourceLibraryWidget(self.project)
        self.options_bar = OptionsBar()
        self.status_bar = StatusBar()
        self.setStatusBar(self.status_bar)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.options_bar)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.source_library)

        self.canvas_scroll = QScrollArea()
        self.canvas_scroll.setWidget(self.canvas)
        self.canvas_scroll.setWidgetResizable(False)
        splitter.addWidget(self.canvas_scroll)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([467, 933])

        layout.addWidget(splitter, 1)
        self.setCentralWidget(central)

    def _setup_menu(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu('&文件')
        new_action = QAction('&新建', self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self._on_new)
        file_menu.addAction(new_action)

        open_action = QAction('&打开源图...', self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self._on_open_source)
        file_menu.addAction(open_action)

        export_action = QAction('&导出...', self)
        export_action.setShortcut(QKeySequence('Ctrl+E'))
        export_action.triggered.connect(self._on_export)
        file_menu.addAction(export_action)

        edit_menu = menu_bar.addMenu('&编辑')
        self.undo_action = QAction('&撤销', self)
        self.undo_action.setShortcut(QKeySequence.Undo)
        self.undo_action.setEnabled(False)
        self.undo_action.triggered.connect(self._on_undo)
        edit_menu.addAction(self.undo_action)

        self.redo_action = QAction('&重做', self)
        self.redo_action.setShortcut(QKeySequence.Redo)
        self.redo_action.setEnabled(False)
        self.redo_action.triggered.connect(self._on_redo)
        edit_menu.addAction(self.redo_action)

        clear_action = QAction('&清除选区', self)
        clear_action.setShortcut(QKeySequence.Delete)
        clear_action.triggered.connect(self._on_clear_selection)
        edit_menu.addAction(clear_action)

    def _setup_toolbar(self):
        toolbar = QToolBar('工具', self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.tool_actions = {}
        group = QActionGroup(self)
        group.setExclusive(True)
        for name, tool in self.tools.items():
            action = QAction(name, self)
            action.setCheckable(True)
            action.triggered.connect(
                lambda _, t=tool, n=name: self._set_tool(t, n))
            group.addAction(action)
            toolbar.addAction(action)
            self.tool_actions[name] = action

        toolbar.addSeparator()

        zoom_in = QAction('放大 +', self)
        zoom_in.setShortcut(QKeySequence.ZoomIn)
        zoom_in.triggered.connect(lambda: self._change_zoom(2.0))
        toolbar.addAction(zoom_in)

        zoom_out = QAction('缩小 -', self)
        zoom_out.setShortcut(QKeySequence.ZoomOut)
        zoom_out.triggered.connect(lambda: self._change_zoom(0.5))
        toolbar.addAction(zoom_out)

        toolbar.addWidget(QLabel(' 缩放: '))
        self.zoom_spin = QSpinBox()
        self.zoom_spin.setRange(25, 800)
        self.zoom_spin.setSingleStep(25)
        self.zoom_spin.setSuffix('%')
        self.zoom_spin.setValue(int(self.canvas.zoom() * 100))
        self.zoom_spin.valueChanged.connect(self._on_zoom_spin_changed)
        toolbar.addWidget(self.zoom_spin)

        toolbar.addSeparator()

        toolbar.addWidget(QLabel(' 列数: '))
        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 256)
        self.cols_spin.setValue(self.project.cols)
        self.cols_spin.valueChanged.connect(self._on_canvas_size_changed)
        toolbar.addWidget(self.cols_spin)

        toolbar.addWidget(QLabel(' 行数: '))
        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 256)
        self.rows_spin.setValue(self.project.rows)
        self.rows_spin.valueChanged.connect(self._on_canvas_size_changed)
        toolbar.addWidget(self.rows_spin)

    def _connect_signals(self):
        self.source_library.tile_copied.connect(self.canvas.set_paste_image)
        self.source_library.tile_size_changed.connect(self._on_tile_size_changed)
        self.canvas.mouse_moved.connect(self._on_canvas_mouse_moved)
        self.command_stack.can_undo_changed.connect(self.undo_action.setEnabled)
        self.command_stack.can_redo_changed.connect(self.redo_action.setEnabled)
        self.command_stack.can_undo_changed.connect(self._mark_dirty)

    def _mark_dirty(self, *args):
        """Any mutation of the command stack marks the project unsaved."""
        self.dirty = True

    # --- Tool / zoom --------------------------------------------------------

    def _set_tool(self, tool, name: str):
        self.canvas.set_tool(tool)
        self.options_bar.set_tool(tool)
        self.status_bar.showMessage(f'Tool: {name}', 2000)

    def _change_zoom(self, factor: float):
        new_zoom = self.canvas.zoom() * factor
        self._apply_zoom(new_zoom)

    def _on_zoom_spin_changed(self, value: int):
        new_zoom = value / 100.0
        self._apply_zoom(new_zoom)

    def _apply_zoom(self, zoom: float):
        self.canvas.set_zoom(zoom)
        self.status_bar.set_zoom(self.canvas.zoom())
        # Sync the spinbox without re-triggering valueChanged.
        self.zoom_spin.blockSignals(True)
        self.zoom_spin.setValue(int(self.canvas.zoom() * 100))
        self.zoom_spin.blockSignals(False)

    # --- Canvas size --------------------------------------------------------

    def _on_canvas_size_changed(self):
        delta_cols = self.cols_spin.value() - self.project.cols
        delta_rows = self.rows_spin.value() - self.project.rows
        if delta_cols == 0 and delta_rows == 0:
            return
        cmd = ResizeCanvasCommand(self.project, delta_cols, delta_rows,
                                  anchor='bottom-right')
        self.command_stack.push(cmd)
        self._sync_size_spinboxes()
        self._refresh_canvas()

    def _sync_size_spinboxes(self):
        """Push project.cols/rows into the spinboxes without re-triggering
        _on_canvas_size_changed."""
        for spin, value in ((self.cols_spin, self.project.cols),
                            (self.rows_spin, self.project.rows)):
            spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(False)
        self.status_bar.set_canvas_size(self.project.cols, self.project.rows)

    def _refresh_canvas(self):
        self.canvas.updateGeometry()
        self.canvas.resize(self.canvas.sizeHint())
        self.canvas.update()

    def _on_tile_size_changed(self, tile_w: int, tile_h: int):
        self.project.set_tile_size(tile_w, tile_h)
        self._refresh_canvas()

    # --- Undo / redo --------------------------------------------------------

    def _on_undo(self):
        self.command_stack.undo()
        self._sync_size_spinboxes()
        self._refresh_canvas()

    def _on_redo(self):
        self.command_stack.redo()
        self._sync_size_spinboxes()
        self._refresh_canvas()

    # --- File actions -------------------------------------------------------

    def _on_new(self):
        self.project = ProjectModel(48, 48, 8, 8)
        self.canvas.project = self.project
        self.source_library.project = self.project
        # Fresh undo history for the fresh project.
        self.command_stack = CommandStack()
        self.canvas.command_stack = self.command_stack
        self.command_stack.can_undo_changed.connect(self.undo_action.setEnabled)
        self.command_stack.can_redo_changed.connect(self.redo_action.setEnabled)
        self.command_stack.can_undo_changed.connect(self._mark_dirty)
        self.undo_action.setEnabled(False)
        self.redo_action.setEnabled(False)
        self._sync_size_spinboxes()
        self._refresh_canvas()
        # A brand-new project starts clean.
        self.dirty = False

    def _on_open_source(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, '打开源图片', '', 'PNG图片 (*.png)')
        if not paths:
            return
        for path in paths:
            try:
                source = SourceImage(Path(path),
                                     self.project.tile_width,
                                     self.project.tile_height)
            except (FileNotFoundError, ValueError) as exc:
                QMessageBox.warning(self, '打开失败', str(exc))
                continue
            self.source_library.add_source(source)
        # Loading a fresh source library is treated as a clean state.
        self.dirty = False

    def _on_export(self):
        path_str, _ = QFileDialog.getSaveFileName(
            self, '导出瓦片集', '', 'PNG图片 (*.png)')
        if not path_str:
            return
        png_path = Path(path_str)
        if png_path.suffix.lower() != '.png':
            png_path = png_path.with_suffix('.png')
        tres_path = png_path.with_suffix('.tres')

        default_res = f'res://{png_path.name}'
        res_path, accepted = QInputDialog.getText(
            self, 'Godot资源路径',
            'Godot项目中的纹理路径:', text=default_res)
        godot_texture_path = res_path if (accepted and res_path) else default_res

        try:
            GodotExporter.export(self.project, png_path, tres_path,
                                 godot_texture_path)
        except OSError as exc:
            QMessageBox.critical(self, '导出失败', str(exc))
            return
        self.dirty = False
        QMessageBox.information(
            self, '导出完成',
            f'已导出:\n{png_path}\n{tres_path}')

    # --- Close handling -----------------------------------------------------

    def closeEvent(self, event):
        """Confirm before discarding unsaved changes (spec §12)."""
        if not self.dirty:
            event.accept()
            return
        reply = QMessageBox.question(
            self, '未保存的更改',
            '您有未保存的更改。关闭前保存？',
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            self._on_export()
            event.accept()
        elif reply == QMessageBox.No:
            event.accept()
        else:
            event.ignore()

    # --- Edit actions -------------------------------------------------------

    def _on_clear_selection(self):
        if not self.project.selection:
            return
        cmd = ClearCommand(self.project, self.project.selection)
        self.command_stack.push(cmd)
        self.canvas.update()

    # --- Status bar ---------------------------------------------------------

    def _on_canvas_mouse_moved(self, col: int, row: int):
        if col >= 0:
            self.status_bar.set_coords(col, row)
            self.status_bar.set_zoom(self.canvas.zoom())
            self.status_bar.set_canvas_size(self.project.cols,
                                            self.project.rows)
