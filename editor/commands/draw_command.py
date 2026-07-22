from editor.commands.base_command import Command


class DrawCommand(Command):
    """Stroke undo: replays new_pixels on do(), restores old_pixels on undo()."""

    def __init__(self, project, old_pixels: dict, new_pixels: dict):
        self.project = project
        self.old_pixels = dict(old_pixels)
        self.new_pixels = dict(new_pixels)

    def do(self):
        for (x, y), rgba in self.new_pixels.items():
            self.project.image.setPixel(x, y, rgba)

    def undo(self):
        for (x, y), rgba in self.old_pixels.items():
            self.project.image.setPixel(x, y, rgba)