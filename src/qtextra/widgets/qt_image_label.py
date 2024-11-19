"""Image label."""

from qtpy.QtCore import Qt
from qtpy.QtGui import QPainter, QPixmap, QResizeEvent, QWheelEvent
from qtpy.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QLabel,
)


class QImageLabel(QLabel):
    """Image label."""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.pixmap_width: int = 1
        self.pixmap_height: int = 1

    def setPixmap(self, pm) -> None:
        self.pixmap_width = pm.width()
        self.pixmap_height = pm.height()
        self.update_margins()
        super().setPixmap(pm)

    def resizeEvent(self, a0) -> None:
        self.update_margins()
        super().resizeEvent(a0)

    def update_margins(self):
        if self.pixmap() is None:
            return
        pixmapWidth = self.pixmap().width()
        pixmap_height = self.pixmap().height()
        if pixmapWidth <= 0 or pixmap_height <= 0:
            return
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return

        if w * pixmap_height > h * pixmapWidth:
            m = int((w - (pixmapWidth * h / pixmap_height)) / 2)
            self.setContentsMargins(m, 0, m, 0)
        else:
            m = int((h - (pixmap_height * w / pixmapWidth)) / 2)
            self.setContentsMargins(0, m, 0, m)


class ImageViewer(QGraphicsView):
    """Simple image viewer widget."""

    def __init__(self, image_path=None, parent=None):
        super().__init__(parent)

        # Set up the scene
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # Add a pixmap item
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)

        # Enable panning
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

        # Track zoom level and adjust zoom factor dynamically
        self.zoom_level = 0
        self.base_zoom_factor = 1.1  # Base zoom factor, will be adjusted dynamically

        # Set up smooth transformation for better quality zoom
        self.setRenderHints(
            self.renderHints() | QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing
        )

        # Load the initial image if provided
        if image_path:
            self.set_image(image_path)

    def set_image(self, image_path: str):
        """Set or change the image displayed in the viewer."""
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            print(f"Error: Could not load image from {image_path}")
            return

        # Update the pixmap in the scene
        self.pixmap_item.setPixmap(pixmap)

        # Reset zoom and fit the view to the new image
        self.reset_zoom()
        self.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event: QWheelEvent):
        """
        Handle zoom in/out with mouse wheel.
        """
        # Determine the mouse position relative to the scene
        mouse_scene_pos = self.mapToScene(event.position().toPoint())

        # Determine zoom in or out
        zoom_in = event.angleDelta().y() > 0

        if zoom_in:
            self.zoom(1, mouse_scene_pos)
        else:
            self.zoom(-1, mouse_scene_pos)

    def mouseDoubleClickEvent(self, event):
        """Reset zoom level on double-click."""
        self.zoom_level = 0
        self.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def zoom(self, direction, center_point):
        """
        Adjust zoom level and apply scaling centered around a point.
        """
        if direction > 0:
            factor = self.base_zoom_factor
            self.zoom_level += 1
        elif direction < 0 and self.zoom_level > 0:
            factor = 1 / self.base_zoom_factor
            self.zoom_level -= 1
        else:
            return  # Prevent over-zooming

        # Center the zoom on the mouse pointer
        self.setTransformationAnchor(QGraphicsView.NoAnchor)
        self.setResizeAnchor(QGraphicsView.NoAnchor)

        old_center = self.mapToScene(self.viewport().rect().center())
        self.scale(factor, factor)
        new_center = center_point
        offset = new_center - old_center
        self.centerOn(self.mapToScene(self.viewport().rect().center()) + offset)

    def reset_zoom(self):
        """
        Reset the zoom to its original state and fit the image to the view.
        """
        self.resetTransform()
        self.zoom_level = 0
        self.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)


class PixmapLabel(QLabel):
    """Label for displaying images."""

    _path = None
    _pixmap = None

    def __init__(self):
        super().__init__()

    def set_image(self, path: str) -> None:
        """Set image from path."""
        if self._path == str(path):
            return
        self._path = str(path)
        self.set_pixmap(QPixmap(str(path)))

    def set_pixmap(self, pm: QPixmap) -> None:
        """Set Pixmap."""
        self._pixmap = pm
        self.setPixmap(pm)

    def setPixmap(self, pm: QPixmap) -> None:
        """Set Pixmap."""
        super().setPixmap(self._resize_pixmap())

    def resizeEvent(self, a0: QResizeEvent) -> None:
        """Resize event."""
        pixmap = self._resize_pixmap()
        if pixmap:
            self.setPixmap(pixmap)
        super().resizeEvent(a0)

    def _resize_pixmap(self):
        if self._pixmap is None or self.pixmap() is None:
            return

        width = self.width()
        height = self.height()
        pixmap = self._pixmap.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatio)
        return pixmap
