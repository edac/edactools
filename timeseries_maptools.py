"""Canvas tools that let the user say *where* to sample a time series.

Each tool emits ``geometry_ready`` with a QgsGeometry in the canvas CRS -- a
point for the click tool, a polygon for the rectangle and freehand tools. The
dialog converts that to the raster's CRS itself, since each selected raster may
be in a different one.
"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from qgis.core import QgsGeometry, QgsPointXY, QgsRectangle, QgsWkbTypes
from qgis.gui import QgsMapTool, QgsRubberBand

# Orange, matching the "selection" feel of QGIS's own identify tools without
# reusing the red that means "error" elsewhere in this plugin.
_STROKE = QColor(235, 104, 52)
_FILL = QColor(235, 104, 52, 55)


def _make_band(canvas):
    band = QgsRubberBand(canvas, QgsWkbTypes.PolygonGeometry)
    band.setColor(_FILL)
    band.setStrokeColor(_STROKE)
    band.setWidth(2)
    return band


class PointTool(QgsMapTool):
    """Click once to sample the pixel under the cursor."""

    geometry_ready = pyqtSignal(object)

    def canvasReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        point = self.toMapCoordinates(event.pos())
        self.geometry_ready.emit(QgsGeometry.fromPointXY(QgsPointXY(point)))


class RectangleTool(QgsMapTool):
    """Drag a box; the pixels inside it are averaged."""

    geometry_ready = pyqtSignal(object)

    def __init__(self, canvas):
        super().__init__(canvas)
        self._canvas = canvas
        self._band = _make_band(canvas)
        self._origin = None

    def _show(self, corner):
        rect = QgsRectangle(self._origin, corner)
        self._band.setToGeometry(QgsGeometry.fromRect(rect), None)

    def canvasPressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        self._origin = self.toMapCoordinates(event.pos())

    def canvasMoveEvent(self, event):
        if self._origin is not None:
            self._show(self.toMapCoordinates(event.pos()))

    def canvasReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or self._origin is None:
            return
        corner = self.toMapCoordinates(event.pos())
        rect = QgsRectangle(self._origin, corner)
        self._origin = None
        self.reset()
        # A click with no drag is a mis-hit, not a zero-area request.
        if rect.width() <= 0 or rect.height() <= 0:
            return
        self.geometry_ready.emit(QgsGeometry.fromRect(rect))

    def reset(self):
        self._band.reset(QgsWkbTypes.PolygonGeometry)

    def deactivate(self):
        self._origin = None
        self.reset()
        super().deactivate()


class PolygonTool(QgsMapTool):
    """Click vertices, right-click to close the shape and sample it."""

    geometry_ready = pyqtSignal(object)

    def __init__(self, canvas):
        super().__init__(canvas)
        self._canvas = canvas
        self._band = _make_band(canvas)
        self._points = []

    def _redraw(self, hover=None):
        self._band.reset(QgsWkbTypes.PolygonGeometry)
        points = self._points + ([hover] if hover else [])
        if len(points) < 2:
            return
        self._band.setToGeometry(QgsGeometry.fromPolygonXY([[QgsPointXY(p) for p in points]]), None)

    def canvasMoveEvent(self, event):
        if self._points:
            self._redraw(self.toMapCoordinates(event.pos()))

    def canvasReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._points.append(self.toMapCoordinates(event.pos()))
            self._redraw()
            return
        if event.button() != Qt.RightButton:
            return
        points = self._points
        self.reset()
        # Fewer than three vertices cannot enclose any pixels.
        if len(points) < 3:
            return
        self.geometry_ready.emit(
            QgsGeometry.fromPolygonXY([[QgsPointXY(p) for p in points]]))

    def reset(self):
        self._points = []
        self._band.reset(QgsWkbTypes.PolygonGeometry)

    def deactivate(self):
        self.reset()
        super().deactivate()
