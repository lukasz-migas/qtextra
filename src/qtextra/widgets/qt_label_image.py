"""Image label."""

from __future__ import annotations

from qtpy.QtCore import QRectF, QSize, Qt, Signal
from qtpy.QtGui import QColor, QImage, QImageReader, QMovie, QPainter, QPainterPath, QPixmap, QResizeEvent, QWheelEvent
from qtpy.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsView, QLabel, QWidget

from qtextra.config import THEMES


class QPixmapLabel(QLabel):
    """Image label."""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.pixmap_width: int = 1
        self.pixmap_height: int = 1

    def setImage(self, image: str | QPixmap | QImage | None = None):
        """Set the image of label."""
        self.image = image or QImage()

        if isinstance(image, str):
            reader = QImageReader(image)
            if reader.supportsAnimation():
                self.setMovie(QMovie(image))
            else:
                self.image = reader.read()
        elif isinstance(image, QPixmap):
            self.image = image.toImage()

        self.setFixedSize(self.image.size())
        self.update()

    def setPixmap(self, pm) -> None:
        """Set Pixmap."""
        self.pixmap_width = pm.width()
        self.pixmap_height = pm.height()
        self.update_margins()
        super().setPixmap(pm)

    def resizeEvent(self, a0) -> None:
        """Resize event."""
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
        """Handle zoom in/out with mouse wheel."""
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
        """Adjust zoom level and apply scaling centered around a point."""
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
        """Reset the zoom to its original state and fit the image to the view."""
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


class QImageLabel(QLabel):
    """Image label."""

    evt_clicked = Signal()

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.image = QImage()
        self.setBorderRadius(0, 0, 0, 0)
        self._postInit()

    def _postInit(self):
        pass

    def _onFrameChanged(self, index: int):
        self.image = self.movie().currentImage()
        self.update()

    def setBorderRadius(self, topLeft: int, topRight: int, bottomLeft: int, bottomRight: int):
        """Set the border radius of image."""
        self._topLeftRadius = topLeft
        self._topRightRadius = topRight
        self._bottomLeftRadius = bottomLeft
        self._bottomRightRadius = bottomRight
        self.update()

    def setImage(self, image: str | QPixmap | QImage | None = None):
        """Set the image of label."""
        self.image = image or QImage()

        if isinstance(image, str):
            reader = QImageReader(image)
            if reader.supportsAnimation():
                self.setMovie(QMovie(image))
            else:
                self.image = reader.read()
        elif isinstance(image, QPixmap):
            self.image = image.toImage()

        self.setFixedSize(self.image.size())
        self.update()

    def scaledToWidth(self, width: int):
        if self.isNull():
            return

        h = int(width / self.image.width() * self.image.height())
        self.setFixedSize(width, h)

        if self.movie():
            self.movie().setScaledSize(QSize(width, h))

    def scaledToHeight(self, height: int):
        """Scale the image to a specific height."""
        if self.isNull():
            return

        w = int(height / self.image.height() * self.image.width())
        self.setFixedSize(w, height)

        if self.movie():
            self.movie().setScaledSize(QSize(w, height))

    def setScaledSize(self, size: QSize):
        if self.isNull():
            return

        self.setFixedSize(size)

        if self.movie():
            self.movie().setScaledSize(size)

    def isNull(self):
        return self.image.isNull()

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        self.evt_clicked.emit()

    def setPixmap(self, pixmap: QPixmap):
        self.setImage(pixmap)

    def pixmap(self) -> QPixmap:
        return QPixmap.fromImage(self.image)

    def setMovie(self, movie: QMovie):
        super().setMovie(movie)
        self.movie().start()
        self.image = self.movie().currentImage()
        self.movie().frameChanged.connect(self._onFrameChanged)

    def paintEvent(self, e):
        if self.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        w, h = self.width(), self.height()

        # top line
        path.moveTo(self.topLeftRadius, 0)
        path.lineTo(w - self.topRightRadius, 0)

        # top right arc
        d = self.topRightRadius * 2
        path.arcTo(w - d, 0, d, d, 90, -90)

        # right line
        path.lineTo(w, h - self.bottomRightRadius)

        # bottom right arc
        d = self.bottomRightRadius * 2
        path.arcTo(w - d, h - d, d, d, 0, -90)

        # bottom line
        path.lineTo(self.bottomLeftRadius, h)

        # bottom left arc
        d = self.bottomLeftRadius * 2
        path.arcTo(0, h - d, d, d, -90, -90)

        # left line
        path.lineTo(0, self.topLeftRadius)

        # top left arc
        d = self.topLeftRadius * 2
        path.arcTo(0, 0, d, d, -180, -90)

        # draw image
        image = self.image.scaled(
            self.size() * self.devicePixelRatioF(),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setClipPath(path)
        painter.drawImage(self.rect(), image)

    @property
    def topLeftRadius(self):
        return self._topLeftRadius

    @topLeftRadius.setter
    def topLeftRadius(self, radius: int):
        self.setBorderRadius(radius, self.topRightRadius, self.bottomLeftRadius, self.bottomRightRadius)

    @property
    def topRightRadius(self):
        return self._topRightRadius

    @topRightRadius.setter
    def topRightRadius(self, radius: int):
        self.setBorderRadius(self.topLeftRadius, radius, self.bottomLeftRadius, self.bottomRightRadius)

    @property
    def bottomLeftRadius(self):
        return self._bottomLeftRadius

    @bottomLeftRadius.setter
    def bottomLeftRadius(self, radius: int):
        self.setBorderRadius(self.topLeftRadius, self.topRightRadius, radius, self.bottomRightRadius)

    @property
    def bottomRightRadius(self):
        return self._bottomRightRadius

    @bottomRightRadius.setter
    def bottomRightRadius(self, radius: int):
        self.setBorderRadius(self.topLeftRadius, self.topRightRadius, self.bottomLeftRadius, radius)


class AvatarWidget(QImageLabel):
    """Avatar widget."""

    def _postInit(self):
        self.setRadius(48)
        self.lightBackgroundColor = QColor(0, 0, 0, 50)
        self.darkBackgroundColor = QColor(255, 255, 255, 50)

    def getRadius(self):
        return self._radius

    def setRadius(self, radius: int):
        from qtextra.helpers import set_font

        self._radius = radius
        set_font(self, radius)
        self.setFixedSize(2 * radius, 2 * radius)
        self.update()

    def setBackgroundColor(self, light: QColor, dark: QColor):
        self.lightBackgroundColor = QColor(light)
        self.darkBackgroundColor = QColor(light)
        self.update()

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing)

        if not self.isNull():
            self._drawImageAvatar(painter)
        else:
            self._drawTextAvatar(painter)

    def _drawImageAvatar(self, painter: QPainter):
        # center crop image
        image = self.image.scaled(
            self.size() * self.devicePixelRatioF(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )  # type: QImage

        iw, ih = image.width(), image.height()
        d = self.getRadius() * 2 * self.devicePixelRatioF()
        x, y = (iw - d) / 2, (ih - d) / 2
        image = image.copy(int(x), int(y), int(d), int(d))

        # draw image
        path = QPainterPath()
        path.addEllipse(QRectF(self.rect()))

        painter.setPen(Qt.NoPen)
        painter.setClipPath(path)
        painter.drawImage(self.rect(), image)

    def _drawTextAvatar(self, painter: QPainter):
        if not self.text():
            return

        painter.setBrush(self.darkBackgroundColor if THEMES.is_dark else self.lightBackgroundColor)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(self.rect()))

        painter.setFont(self.font())
        painter.setPen(Qt.white if THEMES.is_dark else Qt.black)
        painter.drawText(self.rect(), Qt.AlignCenter, self.text()[0].upper())

    radius = property(int, getRadius, setRadius)
