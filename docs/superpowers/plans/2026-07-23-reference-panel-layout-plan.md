# 参考图区域布局调整 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 TileCutter 启动后的窗口与左右布局调整为接近 `合适大小截图.jpg` 的整体比例和参考图区域比例。

**Architecture:** 只调整 `MainWindow` 的窗口初始尺寸、水平分隔器的初始尺寸/伸缩策略和最小宽度；保留 `SourceLibraryWidget` 的参考图缩放、滚动、拖拽、选区及编辑业务逻辑。通过主窗口测试验证布局参数，使用完整测试套件确认行为无回归。

**Tech Stack:** Python 3、PyQt5、pytest、现有 `QMainWindow`/`QSplitter` UI 架构。

## Global Constraints

- 默认瓦片尺寸仍为 `48×48`。
- 参考图默认缩放仍为 `4x`。
- 不改变复制、粘贴、画布编辑和导出行为。
- 用户仍可拖动水平分隔条调整左右区域。
- 目标视觉基准约为 `2200×1266`，左侧约 `800 px`、右侧约 `1400 px`。

---

### Task 1: 增加布局回归测试

**Files:**
- Modify: `tests/test_main_window.py`

**Interfaces:**
- Consumes: `MainWindow` 的窗口尺寸、主分隔器对象及其子控件。
- Produces: 对默认窗口和左右区域初始比例的可执行验收标准。

- [ ] **Step 1: 写默认窗口与分隔器测试**

在 `tests/test_main_window.py` 增加：

```python
def test_default_layout_matches_reference_screenshot(app):
    window = MainWindow()
    assert window.size().width() == 2200
    assert window.size().height() == 1266
    assert window.main_splitter.sizes() == [800, 1400]
    assert window.source_library.minimumWidth() >= 700
```

测试通过公开/稳定的 `main_splitter` 属性读取布局，不依赖 Qt 内部子控件查找。

- [ ] **Step 2: 运行测试确认当前实现失败**

运行：

```bash
pytest tests/test_main_window.py::test_default_layout_matches_reference_screenshot -v
```

预期：FAIL，当前窗口仍为 `1400×1000`，且分隔器尺寸仍为 `[467, 933]`。

- [ ] **Step 3: 提交测试变更**

```bash
git add tests/test_main_window.py
git commit -m "test: 增加参考图布局验收测试"
```

### Task 2: 实现主窗口布局调整

**Files:**
- Modify: `editor/main_window.py:33-91`

**Interfaces:**
- Consumes: Task 1 中测试要求的 `main_splitter` 属性。
- Produces: 启动时 `2200×1266` 窗口、`[800, 1400]` 初始分隔器尺寸及参考区最小宽度。

- [ ] **Step 1: 调整默认窗口尺寸**

将 `MainWindow.__init__` 中的：

```python
self.resize(1400, 1000)
```

改为：

```python
self.resize(2200, 1266)
```

- [ ] **Step 2: 保存主分隔器并设置目标布局**

在 `_setup_widgets` 中，将局部变量 `splitter` 改为实例属性，并设置目标比例：

```python
self.main_splitter = QSplitter(Qt.Horizontal)
self.main_splitter.addWidget(self.source_library)

self.canvas_scroll = QScrollArea()
self.canvas_scroll.setWidget(self.canvas)
self.canvas_scroll.setWidgetResizable(False)
self.main_splitter.addWidget(self.canvas_scroll)
self.main_splitter.setStretchFactor(0, 1)
self.main_splitter.setStretchFactor(1, 1)
self.main_splitter.setSizes([800, 1400])
```

随后将：

```python
layout.addWidget(splitter, 1)
```

改为：

```python
layout.addWidget(self.main_splitter, 1)
```

- [ ] **Step 3: 设置参考区最低可用宽度**

在添加到分隔器后设置：

```python
self.source_library.setMinimumWidth(700)
self.canvas_scroll.setMinimumWidth(700)
```

这两个值避免窗口缩小时任一侧完全失去操作空间，同时不影响正常拖动分隔条。

- [ ] **Step 4: 运行布局测试确认通过**

运行：

```bash
pytest tests/test_main_window.py::test_default_layout_matches_reference_screenshot -v
```

预期：PASS。

- [ ] **Step 5: 提交实现**

```bash
git add editor/main_window.py tests/test_main_window.py
git commit -m "feat: 调整参考图区域默认布局"
```

### Task 3: 更新开发记录并执行完整验证

**Files:**
- Create: `changelog.txt`（当前仓库不存在该文件）

**Interfaces:**
- Consumes: Task 2 完成的布局实现。
- Produces: 中文开发记录和完整测试验证结果。

- [ ] **Step 1: 更新 changelog**

在顶部追加：

```text
2026-07-23
- 调整默认窗口与左右分隔布局，使参考图区域初始大小接近目标截图。
- 默认窗口调整为 2200×1266，参考区与工作区初始尺寸约为 800:1400。
- 保留 4x 参考图缩放、滚动、拖拽分隔条及现有编辑逻辑。
```

- [ ] **Step 2: 运行相关测试**

```bash
pytest tests/test_main_window.py tests/test_source_library_widget.py -v
```

预期：全部 PASS。

- [ ] **Step 3: 运行完整测试套件**

```bash
pytest tests/ -v
```

预期：全部测试 PASS，无新增失败。

- [ ] **Step 4: 检查最终变更**

```bash
git diff HEAD~2..HEAD --stat
git status --short
```

预期：只包含布局实现、测试、changelog 及相关提交记录；不修改用户提供的截图和 `raw_source/` 未跟踪文件。

- [ ] **Step 5: 提交开发记录**

```bash
git add changelog.txt
git commit -m "docs: 记录参考图布局调整"
```
