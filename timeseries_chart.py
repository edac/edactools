"""A time-series line chart drawn with QPainter.

The plugin only depends on what ships with QGIS, and neither PyQtChart nor
pyqtgraph is part of that set (matplotlib usually is, but not on every Linux
install), so the chart is drawn by hand here. It is deliberately small: axes,
gridlines, one polyline per raster, a legend, and a hover crosshair.

Colours come from a categorical palette validated for colour-vision deficiency
in both light and dark modes; the two columns are the same eight hues stepped
for their surface, and the slot order is what keeps adjacent hues separable, so
neither the values nor their order should be shuffled. Series are assigned slots
in order and never cycled -- past eight series the caller must drop some rather
than reuse a hue, which is why MAX_SERIES is exported.
"""

import math

from PyQt5.QtCore import QDate, QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QFontMetrics, QPainter, QPainterPath, QPalette, QPen
from PyQt5.QtWidgets import QSizePolicy, QWidget

SERIES_LIGHT = ("#2a78d6", "#008300", "#e87ba4", "#eda100",
                "#1baf7a", "#eb6834", "#4a3aa7", "#e34948")
SERIES_DARK = ("#3987e5", "#008300", "#d55181", "#c98500",
               "#199e70", "#d95926", "#9085e9", "#e66767")

MAX_SERIES = len(SERIES_LIGHT)

# Chart chrome, per mode: surface, primary ink, secondary ink, muted, grid, axis.
_CHROME_LIGHT = dict(surface="#fcfcfb", primary="#0b0b0b", secondary="#52514e",
                     muted="#898781", grid="#e1e0d9", axis="#c3c2b7")
_CHROME_DARK = dict(surface="#1a1a19", primary="#ffffff", secondary="#c3c2b7",
                    muted="#898781", grid="#2c2c2a", axis="#383835")


class Series:
    """One raster's values over time. ``values`` may hold None for nodata."""

    def __init__(self, name, dates, values):
        self.name = name
        self.dates = dates
        self.values = values

    def points(self):
        """Yield (julian_day, value) for the points that actually have data."""
        for date, value in zip(self.dates, self.values):
            if value is not None and math.isfinite(value):
                yield date.toJulianDay(), value


def _nice_ticks(lo, hi, target=5):
    """Return round-numbered tick values covering [lo, hi]."""
    if not (math.isfinite(lo) and math.isfinite(hi)) or hi <= lo:
        return [lo], 1.0
    raw = (hi - lo) / target
    mag = 10.0 ** math.floor(math.log10(raw))
    for mult in (1, 2, 2.5, 5, 10):
        step = mult * mag
        if raw <= step:
            break
    ticks = []
    value = math.ceil(lo / step) * step
    while value <= hi + step * 1e-9:
        ticks.append(value)
        value += step
    return ticks, step


def _format_value(value, step):
    """Format an axis label with just enough decimals to tell ticks apart."""
    if step >= 1:
        decimals = 0
    else:
        decimals = min(6, int(math.ceil(-math.log10(step))))
    return "%.*f" % (decimals, value)


class TimeSeriesChart(QWidget):
    """Plots one line per raster against a date axis."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._series = []
        self._placeholder = "Pick a point or draw an area on the map to plot values."
        self._hover_x = None
        self._hover_y = 0
        self._plot_rect = QRectF()
        self.setMouseTracking(True)
        self.setMinimumHeight(260)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_series(self, series):
        """Show ``series``; the caller is expected to pass at most MAX_SERIES."""
        self._series = list(series)[:MAX_SERIES]
        self._hover_x = None
        self.update()

    def clear(self, placeholder=None):
        self._series = []
        self._hover_x = None
        if placeholder:
            self._placeholder = placeholder
        self.update()

    def save_png(self, path):
        return self.grab().save(path)

    def color_for(self, index):
        """The palette slot for series ``index``, in the current mode."""
        table = SERIES_DARK if self._is_dark() else SERIES_LIGHT
        return QColor(table[index % len(table)])

    def _is_dark(self):
        return self.palette().color(QPalette.Window).lightness() < 128

    def _chrome(self):
        return _CHROME_DARK if self._is_dark() else _CHROME_LIGHT

    def _data_bounds(self):
        xs, ys = [], []
        for series in self._series:
            for x, y in series.points():
                xs.append(x)
                ys.append(y)
        if not xs:
            return None
        x_lo, x_hi = min(xs), max(xs)
        y_lo, y_hi = min(ys), max(ys)
        if x_hi == x_lo:  # a single date would collapse the x axis
            x_lo -= 1
            x_hi += 1
        if y_hi == y_lo:  # a flat series would collapse the y axis
            y_lo -= 0.5
            y_hi += 0.5
        else:
            pad = (y_hi - y_lo) * 0.08
            y_lo -= pad
            y_hi += pad
        return x_lo, x_hi, y_lo, y_hi

    def _date_format(self, span_days):
        if span_days <= 90:
            return "MMM d"
        if span_days <= 1200:
            return "MMM yyyy"
        return "yyyy"

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        chrome = self._chrome()
        painter.fillRect(self.rect(), QColor(chrome["surface"]))

        bounds = self._data_bounds()
        if bounds is None:
            painter.setPen(QColor(chrome["muted"]))
            painter.drawText(self.rect(), Qt.AlignCenter, self._placeholder)
            return

        metrics = QFontMetrics(self.font())
        legend_h = self._paint_legend(painter, chrome, metrics)
        self._paint_plot(painter, chrome, metrics, bounds, legend_h)

    def _paint_legend(self, painter, chrome, metrics):
        """Draw the legend row above the plot; returns the height it used.

        Identity is never carried by colour alone: every series gets a swatch
        plus its name here, and short series lists are direct-labelled at the
        line ends as well.
        """
        if len(self._series) < 2:
            return 6 if not self._series else metrics.height() + 8
        x = 8.0
        y = 6.0
        row_h = metrics.height() + 4
        for index, series in enumerate(self._series):
            label = series.name
            width = 14 + 4 + metrics.width(label) + 14
            if x + width > self.width() - 8 and x > 8.0:
                x = 8.0
                y += row_h
            painter.setPen(QPen(self.color_for(index), 2.4))
            painter.drawLine(QPointF(x, y + row_h / 2), QPointF(x + 14, y + row_h / 2))
            painter.setPen(QColor(chrome["secondary"]))
            painter.drawText(QRectF(x + 18, y, metrics.width(label) + 2, row_h),
                             Qt.AlignVCenter | Qt.AlignLeft, label)
            x += width
        return y + row_h + 4

    def _paint_plot(self, painter, chrome, metrics, bounds, legend_h):
        x_lo, x_hi, y_lo, y_hi = bounds
        y_ticks, y_step = _nice_ticks(y_lo, y_hi)
        label_w = max(metrics.width(_format_value(t, y_step)) for t in y_ticks)

        # Reserve room on the right for direct labels when the list is short
        # enough to stay legible; that plus the legend keeps the three
        # low-contrast light-mode hues from being the only cue.
        direct = len(self._series) <= 4
        right_pad = 12.0
        if direct:
            right_pad = 12.0 + max(metrics.width(s.name) for s in self._series) + 14

        left = 10.0 + label_w + 8
        top = legend_h + 6
        rect = QRectF(left, top,
                      max(10.0, self.width() - left - right_pad),
                      max(10.0, self.height() - top - (metrics.height() + 14)))
        self._plot_rect = rect

        def to_px(x, y):
            fx = (x - x_lo) / (x_hi - x_lo)
            fy = (y - y_lo) / (y_hi - y_lo)
            return QPointF(rect.left() + fx * rect.width(),
                           rect.bottom() - fy * rect.height())

        # Gridlines and y labels stay recessive so the data reads first.
        for tick in y_ticks:
            if not (y_lo <= tick <= y_hi):
                continue
            py = to_px(x_lo, tick).y()
            painter.setPen(QPen(QColor(chrome["grid"]), 1))
            painter.drawLine(QPointF(rect.left(), py), QPointF(rect.right(), py))
            painter.setPen(QColor(chrome["muted"]))
            painter.drawText(QRectF(0, py - metrics.height() / 2, left - 8, metrics.height()),
                             Qt.AlignVCenter | Qt.AlignRight, _format_value(tick, y_step))

        self._paint_date_axis(painter, chrome, metrics, rect, x_lo, x_hi, to_px, y_lo)

        painter.setPen(QPen(QColor(chrome["axis"]), 1))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        painter.drawLine(rect.topLeft(), rect.bottomLeft())

        painter.save()
        painter.setClipRect(rect.adjusted(-1, -1, 1, 1))
        for index, series in enumerate(self._series):
            self._paint_series(painter, series, index, to_px)
        painter.restore()

        if direct:
            self._paint_direct_labels(painter, chrome, metrics, rect, to_px)
        self._paint_hover(painter, chrome, metrics, rect, to_px, x_lo, x_hi)

    def _paint_date_axis(self, painter, chrome, metrics, rect, x_lo, x_hi, to_px, y_lo):
        span = x_hi - x_lo
        fmt = self._date_format(span)
        count = max(2, min(6, int(rect.width() // 90)))
        painter.setPen(QColor(chrome["muted"]))
        for i in range(count + 1):
            jd = x_lo + span * i / count
            label = QDate.fromJulianDay(int(round(jd))).toString(fmt)
            px = to_px(jd, y_lo).x()
            width = metrics.width(label) + 10
            # Keep the end labels inside the widget; the first and last ticks sit
            # on the plot edges and would otherwise be clipped.
            left = min(max(0.0, px - width / 2), self.width() - width)
            painter.drawText(QRectF(left, rect.bottom() + 4, width, metrics.height()),
                             Qt.AlignCenter, label)

    def _paint_series(self, painter, series, index, to_px):
        color = self.color_for(index)
        path = QPainterPath()
        pixels = []
        started = False
        # Nodata breaks the line rather than being bridged over, so a gap in the
        # stack reads as a gap instead of an invented straight segment.
        for date, value in zip(series.dates, series.values):
            if value is None or not math.isfinite(value):
                started = False
                continue
            point = to_px(date.toJulianDay(), value)
            pixels.append(point)
            if started:
                path.lineTo(point)
            else:
                path.moveTo(point)
                started = True
        painter.setPen(QPen(color, 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)
        # Markers only when they would not merge into a solid band.
        if 0 < len(pixels) <= 40:
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            for point in pixels:
                painter.drawEllipse(point, 4.0, 4.0)
            painter.setBrush(Qt.NoBrush)

    def _paint_direct_labels(self, painter, chrome, metrics, rect, to_px):
        """Label each line at its right end, so the low-contrast light-mode
        hues are not the only thing telling the series apart."""
        placed = []
        for index, series in enumerate(self._series):
            points = list(series.points())
            if not points:
                continue
            x, y = points[-1]
            at = to_px(x, y)
            top = at.y() - metrics.height() / 2
            # Nudge apart labels that would otherwise overlap each other.
            for other in placed:
                if abs(other - top) < metrics.height():
                    top = other + metrics.height()
            placed.append(top)
            painter.setBrush(self.color_for(index))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(rect.right() + 7, top + metrics.height() / 2), 3.5, 3.5)
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QColor(chrome["secondary"]))
            painter.drawText(QRectF(rect.right() + 14, top,
                                    self.width() - rect.right() - 14, metrics.height()),
                             Qt.AlignVCenter | Qt.AlignLeft, series.name)

    def _nearest_date(self, x_lo, x_hi):
        """Julian day of the point nearest the cursor, or None."""
        if self._hover_x is None or not self._plot_rect.width():
            return None
        frac = (self._hover_x - self._plot_rect.left()) / self._plot_rect.width()
        target = x_lo + frac * (x_hi - x_lo)
        best, best_gap = None, None
        for series in self._series:
            for x, _ in series.points():
                gap = abs(x - target)
                if best_gap is None or gap < best_gap:
                    best, best_gap = x, gap
        return best

    def _paint_hover(self, painter, chrome, metrics, rect, to_px, x_lo, x_hi):
        jd = self._nearest_date(x_lo, x_hi)
        if jd is None:
            return
        px = to_px(jd, 0).x()
        if not (rect.left() - 1 <= px <= rect.right() + 1):
            return
        pen = QPen(QColor(chrome["axis"]), 1, Qt.DashLine)
        painter.setPen(pen)
        painter.drawLine(QPointF(px, rect.top()), QPointF(px, rect.bottom()))

        rows = []
        for index, series in enumerate(self._series):
            hit = next((v for x, v in series.points() if x == jd), None)
            if hit is None:
                continue
            rows.append((index, series.name, hit))
            painter.setBrush(self.color_for(index))
            painter.setPen(QPen(QColor(chrome["surface"]), 2))
            painter.drawEllipse(to_px(jd, hit), 4.5, 4.5)
            painter.setBrush(Qt.NoBrush)
        if not rows:
            return

        title = QDate.fromJulianDay(int(jd)).toString("yyyy-MM-dd")
        lines = [(None, title)] + [(i, "%s  %.4g" % (n, v)) for i, n, v in rows]
        width = max(metrics.width(text) for _, text in lines) + 22
        height = len(lines) * (metrics.height() + 2) + 8
        left = px + 12
        if left + width > rect.right():
            left = px - 12 - width
        top = min(max(rect.top() + 4, self._hover_y - height / 2), rect.bottom() - height - 4)

        box = QRectF(left, top, width, height)
        painter.setBrush(QColor(chrome["surface"]))
        painter.setPen(QPen(QColor(chrome["axis"]), 1))
        painter.drawRoundedRect(box, 4, 4)
        painter.setBrush(Qt.NoBrush)
        y = top + 4
        for index, text in lines:
            if index is None:
                painter.setPen(QColor(chrome["primary"]))
                painter.drawText(QRectF(left + 8, y, width - 12, metrics.height() + 2),
                                 Qt.AlignVCenter | Qt.AlignLeft, text)
            else:
                painter.setBrush(self.color_for(index))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(QPointF(left + 11, y + metrics.height() / 2 + 1), 3.0, 3.0)
                painter.setBrush(Qt.NoBrush)
                painter.setPen(QColor(chrome["secondary"]))
                painter.drawText(QRectF(left + 19, y, width - 23, metrics.height() + 2),
                                 Qt.AlignVCenter | Qt.AlignLeft, text)
            y += metrics.height() + 2

    def mouseMoveEvent(self, event):
        self._hover_x = event.pos().x()
        self._hover_y = event.pos().y()
        self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hover_x = None
        self.update()
        super().leaveEvent(event)
