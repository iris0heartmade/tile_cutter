from PyQt5.QtGui import QColor
from editor.tools.brush_tool import BrushTool


class EraserTool(BrushTool):
    """BrushTool that makes pixels transparent instead of painting color."""

    name = 'Eraser'

    def __init__(self, size: int = 1, opacity: int = 255):
        # Eraser has no color; pass a fully-transparent default to BrushTool.
        super().__init__(color=QColor(0, 0, 0, 0), size=size, opacity=opacity)

    def _compute_pixel_color(self, project, px: int, py: int) -> QColor:
        old = project.image.pixelColor(px, py)
        new_alpha = max(0, old.alpha() - self.opacity)
        result = QColor(old)
        result.setAlpha(new_alpha)
        return result