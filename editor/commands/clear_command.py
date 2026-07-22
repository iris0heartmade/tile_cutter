from editor.commands.base_command import Command


class ClearCommand(Command):
    """Clear selected pixels to transparent (0) with full undo support."""

    def __init__(self, project, pixels):
        self.project = project
        self.pixels = set(pixels)
        self.old_values = {}

    def do(self):
        self.old_values = {}
        for x, y in self.pixels:
            if 0 <= x < self.project.width and 0 <= y < self.project.height:
                self.old_values[(x, y)] = self.project.image.pixel(x, y)
                self.project.image.setPixel(x, y, 0)

    def undo(self):
        for (x, y), rgba in self.old_values.items():
            self.project.image.setPixel(x, y, rgba)