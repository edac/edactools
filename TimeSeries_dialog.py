from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QDateEdit,
                             QDialog, QFileDialog, QHeaderView, QMessageBox,
                             QProgressDialog, QSpinBox, QTableWidgetItem)
from qgis.core import QgsGeometry, QgsMapLayer, QgsProject, QgsWkbTypes
from qgis.utils import iface
import csv
import os

from .TimeSeries_dialog_base import Ui_TimeSeriesDialog
from .band_dates import INTERVAL_UNITS, date_for_band
from .timeseries_chart import MAX_SERIES, Series, TimeSeriesChart
from .timeseries_extract import ExtractError, extract_series
from .timeseries_maptools import PointTool, PolygonTool, RectangleTool

COL_PLOT, COL_NAME, COL_START, COL_STEP, COL_UNIT = range(5)


class TimeSeriesDialog(QDialog):
    """Plots how one or more 3D rasters change over time at a point or an area."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_TimeSeriesDialog()
        self.ui.setupUi(self)
        self.setWindowModality(Qt.NonModal)
        self.plugin_dir = os.path.dirname(__file__)
        self.canvas = iface.mapCanvas()

        # The chart is added here rather than promoted in the .ui file: pyuic5
        # would emit a top-level import for it, which does not resolve from
        # inside the plugin package.
        self.chart = TimeSeriesChart(self)
        self.ui.chart_layout.addWidget(self.chart)

        self._series = []
        # Per-layer start/step survive a refresh, keyed by layer id, so reloading
        # the list does not throw away dates the user typed in.
        self._settings = {}

        refresh_icon = os.path.join(self.plugin_dir, "icons", "recycle.png")
        self.ui.refreshButton.setIcon(QIcon(refresh_icon))

        self._init_table()

        self._tools = {
            "point": PointTool(self.canvas),
            "rect": RectangleTool(self.canvas),
            "polygon": PolygonTool(self.canvas),
        }
        self._mode_buttons = {
            "point": self.ui.point_button,
            "rect": self.ui.rect_button,
            "polygon": self.ui.polygon_button,
        }
        for key, tool in self._tools.items():
            tool.geometry_ready.connect(self._on_geometry)
            tool.deactivated.connect(lambda k=key: self._on_tool_deactivated(k))
        for key, button in self._mode_buttons.items():
            button.toggled.connect(lambda checked, k=key: self._set_mode(k, checked))

        self.ui.refreshButton.clicked.connect(self.refresh)
        self.ui.selection_button.clicked.connect(self.use_selection)
        self.ui.clear_button.clicked.connect(self.clear)
        self.ui.export_csv_button.clicked.connect(self.export_csv)
        self.ui.save_png_button.clicked.connect(self.save_png)

        self.refresh()
        self._update_export_buttons()

    # ---------------------------------------------------------------- layers

    def _init_table(self):
        table = self.ui.layer_table
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Plot", "Raster", "Start date", "Step", "Unit"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        header = table.horizontalHeader()
        header.setSectionResizeMode(COL_PLOT, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(COL_NAME, QHeaderView.Stretch)
        header.setSectionResizeMode(COL_START, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(COL_STEP, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(COL_UNIT, QHeaderView.ResizeToContents)

    def _remember(self):
        """Snapshot the per-layer settings currently shown in the table."""
        for row in range(self.ui.layer_table.rowCount()):
            layer_id = self.ui.layer_table.item(row, COL_NAME).data(Qt.UserRole)
            self._settings[layer_id] = self._row_settings(row)

    def _row_settings(self, row):
        table = self.ui.layer_table
        return {
            "checked": table.item(row, COL_PLOT).checkState() == Qt.Checked,
            "start": table.cellWidget(row, COL_START).date(),
            "step": table.cellWidget(row, COL_STEP).value(),
            "unit": table.cellWidget(row, COL_UNIT).currentText(),
        }

    def refresh(self):
        """Reload the raster list from the project, keeping existing settings."""
        self._remember()
        table = self.ui.layer_table
        table.setRowCount(0)
        for tree_layer in QgsProject.instance().layerTreeRoot().children():
            layer = tree_layer.layer()
            if layer is None or layer.type() != QgsMapLayer.RasterLayer:
                continue
            self._add_row(layer)

    def _add_row(self, layer):
        table = self.ui.layer_table
        row = table.rowCount()
        table.insertRow(row)
        saved = self._settings.get(layer.id(), {})

        check = QTableWidgetItem()
        check.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        check.setCheckState(Qt.Checked if saved.get("checked") else Qt.Unchecked)
        table.setItem(row, COL_PLOT, check)

        name = QTableWidgetItem(layer.name())
        name.setData(Qt.UserRole, layer.id())
        name.setToolTip("%s — %d bands" % (layer.name(), layer.bandCount()))
        table.setItem(row, COL_NAME, name)

        start = QDateEdit()
        start.setCalendarPopup(True)
        start.setDisplayFormat("yyyy-MM-dd")
        start.setDate(saved.get("start") or QDate.currentDate())
        table.setCellWidget(row, COL_START, start)

        step = QSpinBox()
        step.setRange(1, 10000)
        step.setValue(saved.get("step", 1))
        table.setCellWidget(row, COL_STEP, step)

        unit = QComboBox()
        unit.addItems(INTERVAL_UNITS)
        unit.setCurrentText(saved.get("unit", INTERVAL_UNITS[0]))
        table.setCellWidget(row, COL_UNIT, unit)

    def _checked_layers(self):
        """(layer, settings) for every ticked row that still resolves."""
        out = []
        for row in range(self.ui.layer_table.rowCount()):
            settings = self._row_settings(row)
            if not settings["checked"]:
                continue
            layer_id = self.ui.layer_table.item(row, COL_NAME).data(Qt.UserRole)
            layer = QgsProject.instance().mapLayer(layer_id)
            if layer is not None:
                out.append((layer, settings))
        return out

    # ----------------------------------------------------------- map tools

    def _set_mode(self, key, checked):
        for other, button in self._mode_buttons.items():
            if other != key and button.isChecked():
                button.blockSignals(True)
                button.setChecked(False)
                button.blockSignals(False)
        if checked:
            self.canvas.setMapTool(self._tools[key])
            self._status({
                "point": "Click a spot on the map to plot the pixel under it.",
                "rect": "Drag a box on the map to plot the average inside it.",
                "polygon": "Click vertices on the map, then right-click to close the shape.",
            }[key])
        elif self.canvas.mapTool() is self._tools[key]:
            self.canvas.unsetMapTool(self._tools[key])

    def _on_tool_deactivated(self, key):
        """Untick the mode button when QGIS switches to some other tool."""
        button = self._mode_buttons[key]
        button.blockSignals(True)
        button.setChecked(False)
        button.blockSignals(False)

    def _on_geometry(self, geometry):
        self.plot(geometry, self.canvas.mapSettings().destinationCrs())

    def use_selection(self):
        layer = iface.activeLayer()
        if layer is None or layer.type() != QgsMapLayer.VectorLayer:
            QMessageBox.warning(self, "No vector layer",
                                "Select a polygon layer in the Layers panel first.")
            return
        if layer.geometryType() != QgsWkbTypes.PolygonGeometry:
            QMessageBox.warning(self, "Not a polygon layer",
                                "'%s' is not a polygon layer, so it cannot outline an "
                                "area to average." % layer.name())
            return
        geometries = [f.geometry() for f in layer.selectedFeatures() if not f.geometry().isEmpty()]
        if not geometries:
            QMessageBox.warning(self, "Nothing selected",
                                "Select one or more polygons in '%s' first." % layer.name())
            return
        # Several selected polygons are averaged as one area, not one series each.
        combined = QgsGeometry.unaryUnion(geometries) if len(geometries) > 1 else geometries[0]
        self.plot(combined, layer.crs())

    # -------------------------------------------------------------- plotting

    def _status(self, text):
        self.ui.status_label.setText(text)

    def _describe(self, geometry):
        if geometry.type() == QgsWkbTypes.PointGeometry:
            point = geometry.asPoint()
            return "Point %.2f, %.2f" % (point.x(), point.y())
        return "Area of %s map units" % format(geometry.area(), ".4g")

    def plot(self, geometry, crs):
        layers = self._checked_layers()
        if not layers:
            self._status("Tick at least one raster in the table, then click the map again.")
            return

        capped = layers[:MAX_SERIES]
        progress = QProgressDialog("Reading rasters…", "Cancel", 0, len(capped), self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(400)

        series, failed = [], []
        cancelled = False
        for index, (layer, settings) in enumerate(capped):
            progress.setValue(index)
            progress.setLabelText("Reading %s…" % layer.name())
            if progress.wasCanceled():
                cancelled = True
                break

            def tick(done, total, dialog=progress):
                # Keep Cancel responsive on a long stack, but only pump the event
                # loop every so often: processEvents forces the live canvas to
                # re-render, so calling it on every one of hundreds of bands is
                # what makes a big read crawl.
                if done % 25 == 0 or done == total:
                    QApplication.processEvents()
                return not dialog.wasCanceled()

            try:
                values = extract_series(layer, geometry, crs, tick)
            except ExtractError as error:
                failed.append(str(error))
                continue
            except Exception as error:  # a broken file should not take the dialog down
                failed.append("%s: %s" % (layer.name(), error))
                continue
            if values is None:
                cancelled = True
                break
            dates = [date_for_band(settings["start"], band, settings["step"], settings["unit"])
                     for band in range(1, len(values) + 1)]
            series.append(Series(layer.name(), dates, values))
        progress.setValue(len(capped))

        if cancelled:
            self._status("Cancelled.")
            return

        self._series = series
        self.chart.set_series(series)
        self._fill_results(series)
        self._update_export_buttons()
        self._report(geometry, series, layers, failed)

    def _report(self, geometry, series, layers, failed):
        if not series:
            self.chart.clear("No values here — the spot may be outside every raster.")
            self._status("%s — nothing to plot." % self._describe(geometry))
        else:
            plotted = sum(1 for s in series if any(v is not None for v in s.values))
            self._status("%s — %d raster%s, %d dates." % (
                self._describe(geometry), plotted, "" if plotted == 1 else "s",
                max(len(s.dates) for s in series)))
        if len(layers) > MAX_SERIES:
            QMessageBox.information(
                self, "Too many rasters",
                "The chart uses %d colours that stay distinct for colour-blind readers, "
                "so only the first %d ticked rasters were plotted. Untick some to see "
                "the rest." % (MAX_SERIES, MAX_SERIES))
        if failed:
            QMessageBox.warning(self, "Some rasters were skipped", "\n\n".join(failed))

    def _fill_results(self, series):
        """Mirror the chart into the Table tab.

        This is also what keeps the chart readable for anyone the colours fail:
        three of the light-mode hues sit below 3:1 against the chart surface, so
        the numbers have to be available as text somewhere.
        """
        table = self.ui.results_table
        table.clear()
        if not series:
            table.setRowCount(0)
            table.setColumnCount(0)
            return
        dates = sorted({date for s in series for date in s.dates})
        table.setColumnCount(1 + len(series))
        table.setHorizontalHeaderLabels(["Date"] + [s.name for s in series])
        table.setRowCount(len(dates))
        lookup = [dict(zip(s.dates, s.values)) for s in series]
        for row, date in enumerate(dates):
            table.setItem(row, 0, QTableWidgetItem(date.toString("yyyy-MM-dd")))
            for column, values in enumerate(lookup, start=1):
                value = values.get(date)
                table.setItem(row, column,
                              QTableWidgetItem("" if value is None else "%.6g" % value))
        table.resizeColumnsToContents()

    def clear(self):
        self._series = []
        self.chart.clear("Pick a point or draw an area on the map to plot values.")
        self._fill_results([])
        self._update_export_buttons()
        for tool in self._tools.values():
            tool_reset = getattr(tool, "reset", None)
            if tool_reset:
                tool_reset()
        self._status("Cleared. Pick a sampling mode, then click or draw on the map.")

    # --------------------------------------------------------------- export

    def _update_export_buttons(self):
        has_data = bool(self._series)
        self.ui.export_csv_button.setEnabled(has_data)
        self.ui.save_png_button.setEnabled(has_data)

    def export_csv(self):
        if not self._series:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export time series", "timeseries.csv",
                                              "CSV files (*.csv)")
        if not path:
            return
        dates = sorted({date for s in self._series for date in s.dates})
        lookup = [dict(zip(s.dates, s.values)) for s in self._series]
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["date"] + [s.name for s in self._series])
                for date in dates:
                    row = [date.toString("yyyy-MM-dd")]
                    for values in lookup:
                        value = values.get(date)
                        row.append("" if value is None else "%.6g" % value)
                    writer.writerow(row)
        except OSError as error:
            QMessageBox.warning(self, "Could not write CSV", str(error))
            return
        self._status("Exported %d rows to %s" % (len(dates), path))

    def save_png(self):
        if not self._series:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save chart", "timeseries.png",
                                              "PNG images (*.png)")
        if not path:
            return
        if self.chart.save_png(path):
            self._status("Saved chart to %s" % path)
        else:
            QMessageBox.warning(self, "Could not save chart",
                                "Could not write the image to %s" % path)

    # --------------------------------------------------------------- closing

    def closeEvent(self, event):
        # Leave the canvas as we found it rather than stranding the user on one
        # of our tools after the dialog is gone.
        for tool in self._tools.values():
            if self.canvas.mapTool() is tool:
                self.canvas.unsetMapTool(tool)
        super().closeEvent(event)
