from PyQt5.QtWidgets import QDialog, QMessageBox, QProgressDialog
from .Fishbone_dialog_base import Ui_FishboneDialog
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsCoordinateTransform,
)
from PyQt5.QtCore import Qt
from qgis.PyQt.QtCore import QVariant
import os
from PyQt5.QtGui import QIcon


class FishboneDialog(QDialog):

    def load_fields(self, layer, combo_box):
        combo_box.addItem("Select Field")
        for field in layer.fields():
            combo_box.addItem(field.name())

    def __init__(self,parent=None):
        super().__init__(parent)
        self.ui = Ui_FishboneDialog()
        self.ui.setupUi(self)
        self.setWindowModality(Qt.NonModal)
        self.plugin_dir = os.path.dirname(__file__)
        layers = QgsProject.instance().layerTreeRoot().children()
        refresh_button_icon = os.path.join(self.plugin_dir, "icons", "recycle.png")
        self.ui.StreetRefreshButton.setIcon(QIcon(refresh_button_icon))
        refresh_button_icon = os.path.join(self.plugin_dir, "icons", "recycle.png")
        self.ui.AddressRefreshButton.setIcon(QIcon(refresh_button_icon))
        self.refreshing = False
        #connect the refresh button to the refresh method
        self.ui.StreetRefreshButton.clicked.connect(self.refreshstreet)
        self.ui.AddressRefreshButton.clicked.connect(self.refreshaddress)

        self.ui.AddressComboBox.addItem("Select Address Layer")
        self.ui.StreetComboBox.addItem("Select Street Layer")

        if layers:
            for layer in layers:
                if layer.layer().type() == QgsVectorLayer.VectorLayer:

                    self.ui.StreetComboBox.addItem(layer.name())
                    self.ui.AddressComboBox.addItem(layer.name())
        else:
            QMessageBox.warning(self, "No Layers", "No layers are currently loaded in the project.")

        self.ui.buttonBox.accepted.connect(self.run)
        self.ui.buttonBox.rejected.connect(self.reject)
        # when the street layer is changed, update the street field combo box
        self.ui.StreetComboBox.currentIndexChanged.connect(self.street_layer_changed)
        self.ui.AddressComboBox.currentIndexChanged.connect(self.address_layer_changed)

    def refreshstreet(self):
        self.refreshing = True
        self.ui.StreetComboBox.clear()
        self.ui.StreetComboBox.addItem("Select Street Layer")
        layers = QgsProject.instance().layerTreeRoot().children()
        if layers:
            for layer in layers:
                if layer.layer().type() == QgsVectorLayer.VectorLayer:
                    self.ui.StreetComboBox.addItem(layer.name())


        self.refreshing = False

    def refreshaddress(self):
        self.refreshing = True
        print('refresh')
        self.ui.AddressComboBox.clear()
        self.ui.AddressComboBox.addItem("Select Address Layer")
        layers = QgsProject.instance().layerTreeRoot().children()
        if layers:
            for layer in layers:
                if layer.layer().type() == QgsVectorLayer.VectorLayer:
                    self.ui.AddressComboBox.addItem(layer.name())

        self.refreshing = False

    def street_layer_changed(self):
        if self.refreshing:
            return


        print("Street Layer Changed")


        street_layer_name = self.ui.StreetComboBox.currentText()
        if street_layer_name == "Select Street Layer":
            return
        self.ui.StreetStreetComboBox.clear()

        #only string fields are allowed for street names
        street_layer = QgsProject.instance().mapLayersByName(street_layer_name)[0]

        self.load_fields(street_layer, self.ui.StreetStreetComboBox)

    def address_layer_changed(self):
        if self.refreshing:
            return
        print("Address Layer Changed")
        address_layer_name = self.ui.AddressComboBox.currentText()
        if address_layer_name == "Select Address Layer":
            return
        self.ui.AddressStreetComboBox.clear()
        #only INT fields are allowed for street names
        address_layer = QgsProject.instance().mapLayersByName(address_layer_name)[0]

        self.load_fields(address_layer, self.ui.AddressStreetComboBox)

    def _point_from_geometry(self, geom):
        """Return a single representative QgsPointXY for a point geometry.

        Handles both single-part points and multipoints (taking the first
        vertex, matching the old shapely ``Point(x[0])`` behaviour). Returns
        None for empty/invalid geometry.
        """
        if geom is None or geom.isEmpty():
            return None
        if geom.isMultipart():
            pts = geom.asMultiPoint()
            return pts[0] if pts else None
        return geom.asPoint()

    def run(self):

        street_layer_name = self.ui.StreetComboBox.currentText()
        address_layer_name = self.ui.AddressComboBox.currentText()
        # check if the user has selected both a street layer and an address layer

        if street_layer_name == "Select Street Layer" or address_layer_name == "Select Address Layer":
            QMessageBox.warning(self, "Selection Error", "Please select both an address layer and a street layer.")
            return

        address_street_field = self.ui.AddressStreetComboBox.currentText()
        street_street_field = self.ui.StreetStreetComboBox.currentText()
        if address_street_field in ("", "Select Field") or street_street_field in ("", "Select Field"):
            QMessageBox.warning(self, "Selection Error", "Please select the street-name field for both layers.")
            return

        address_layer = QgsProject.instance().mapLayersByName(address_layer_name)[0]
        street_layer = QgsProject.instance().mapLayersByName(street_layer_name)[0]

        # Work in the street layer's CRS and transform address points into it
        # (replaces geopandas' to_crs reprojection).
        street_crs = street_layer.crs()
        same_crs = address_layer.crs() == street_crs
        transform = QgsCoordinateTransform(address_layer.crs(), street_crs,
                                           QgsProject.instance())

        # Group street segment geometries by street name for quick lookup.
        streets_by_name = {}
        for sf in street_layer.getFeatures():
            geom = sf.geometry()
            if geom is None or geom.isEmpty():
                continue
            streets_by_name.setdefault(sf[street_street_field], []).append(geom)

        # Build an in-memory line layer to hold the fishbone lines.
        out_layer = QgsVectorLayer("LineString?crs=" + street_crs.authid(),
                                   "fishbone", "memory")
        provider = out_layer.dataProvider()
        provider.addAttributes([QgsField("STR_NAME", QVariant.String)])
        out_layer.updateFields()

        address_features = list(address_layer.getFeatures())
        progress_dialog = QProgressDialog("Building Fishbone...", "Cancel", 0,
                                          len(address_features), self)
        progress_dialog.setWindowTitle("Fishbone Generation")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.show()

        out_features = []
        for i, address in enumerate(address_features):
            if progress_dialog.wasCanceled():
                break
            progress_dialog.setValue(i + 1)

            point = self._point_from_geometry(address.geometry())
            if point is None:
                continue
            if not same_crs:
                point = transform.transform(point)

            street_name = address[address_street_field]
            candidates = streets_by_name.get(street_name, [])

            # Find the nearest matching street segment and the closest point on
            # it. closestSegmentWithContext returns the squared distance and the
            # projected point in one call (replaces shapely project/interpolate).
            best_sqr_dist = float("inf")
            nearest_point = None
            for segment_geom in candidates:
                sqr_dist, min_dist_point, _after, _left = \
                    segment_geom.closestSegmentWithContext(point)
                if sqr_dist < best_sqr_dist:
                    best_sqr_dist = sqr_dist
                    nearest_point = min_dist_point
            if nearest_point is None:
                continue

            feature = QgsFeature(out_layer.fields())
            feature.setGeometry(QgsGeometry.fromPolylineXY([point, nearest_point]))
            feature.setAttribute("STR_NAME", street_name)
            out_features.append(feature)

        provider.addFeatures(out_features)
        out_layer.updateExtents()
        QgsProject.instance().addMapLayer(out_layer)

        self.accept()
