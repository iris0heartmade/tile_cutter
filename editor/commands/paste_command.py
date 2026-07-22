from PyQt5.QtGui import QImage
from editor.commands.base_command import Command


class PasteCommand(Command):
    """Paste a source QImage onto the project canvas at image-space (x, y).

    Captures the pixels that will be overwritten so that `undo()` restores the
    canvas exactly. Pixels outside the canvas bounds are clipped (their old
    values are never recorded because nothing changed).
    """

    def __init__(self, project, image: QImage, x: int, y: int):
        self.project = project
        self.image = QImage(image)  # defensive copy
        self.x = int(x)
        self.y = int(y)
        self.old_pixels: dict = {}

    def do(self):
        self.old_pixels = {}
        img_w = self.image.width()
        img_h = self.image.height()
        for dy in range(img_h):
            for dx in range(img_w):
                px = self.x + dx
                py = self.y + dy
                if not (0 <= px < self.project.width and 0 <= py < self.project.height):
                    continue
                self.old_pixels[(px, py)] = self.project.image.pixel(px, py)
                self.project.image.setPixel(px, py, self.image.pixel(dx, dy))

    def undo(self):
        for (px, py), rgba in self.old_pixels.items():
            self.project.image.setPixel(px, py, rgba)