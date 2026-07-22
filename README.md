# TileCutter

A desktop tileset editor for Godot, built with Python and PyQt5.

## Features

- Import multiple source tileset images.
- Grid-based tile selection and copy/paste.
- Pixel-level editing: brush, eraser, eyedropper.
- Rectangle and magic-wand selection.
- Color-to-transparent background removal.
- Undo/redo.
- Export PNG + Godot 4 TileSet `.tres` resource.

## Run

```bash
python main.py
```

## Test

```bash
pytest tests/ -v
```

## Project Structure

See `docs/superpowers/specs/2026-07-22-tilecutter-design.md`.
