from .StreetParity_dialog_base import Ui_StreetParityDialog
from PyQt5.QtWidgets import QDialog, QMessageBox, QProgressDialog
from PyQt5.QtCore import Qt
from qgis.core import (
    QgsFeature,
    QgsGeometry,
    QgsVectorLayer,
    QgsField,
    QgsProject,
    QgsFields,
    QgsRuleBasedRenderer,
    QgsSymbol,
    QgsWkbTypes,
    QgsCoordinateTransform,
)
from PyQt5.QtGui import QColor
from qgis.PyQt.QtCore import QVariant
import os
from PyQt5.QtGui import QIcon

class StreetParityDialog(QDialog):

    def load_fields(self, layer, combo_box):
        combo_box.addItem("Select Field")
        for field in layer.fields():
            combo_box.addItem(field.name())

    def refresh_address(self):
        self.refreshing = True
        self.ui.AddressLayerComboBox.clear()
        self.ui.AddressLayerComboBox.addItem("Select Address Layer")
        layers = QgsProject.instance().layerTreeRoot().children()
        if layers:
            for layer in layers:
                if layer.layer().type() == QgsVectorLayer.VectorLayer:
                    self.ui.AddressLayerComboBox.addItem(layer.name())

        self.refreshing = False

    def refresh_street(self):
        self.refreshing = True
        self.ui.StreetLayerComboBox.clear()
        self.ui.StreetLayerComboBox.addItem("Select Street Layer")
        layers = QgsProject.instance().layerTreeRoot().children()
        if layers:
            for layer in layers:
                if layer.layer().type() == QgsVectorLayer.VectorLayer:
                    self.ui.StreetLayerComboBox.addItem(layer.name())
        self.refreshing = False

    def load_layers(self):

        if self.refreshing:
            return
        print("load layers running")
        #clear the combo boxes
        self.ui.AddressLayerComboBox.clear()
        self.ui.StreetLayerComboBox.clear()
        self.ui.AddressLayerComboBox.addItem("Select Address Layer")
        self.ui.StreetLayerComboBox.addItem("Select Street Layer")
        layers = QgsProject.instance().layerTreeRoot().children()
        if layers:
            for layer in layers:
                self.ui.AddressLayerComboBox.addItem(layer.name())
                self.ui.StreetLayerComboBox.addItem(layer.name())
        else:
            QMessageBox.warning(self, "No Layers", "No layers are currently loaded in the project.")
        self.refreshing = False
    def update_street_fields(self):
        if self.refreshing:
            return
        street_layer_name = self.ui.StreetLayerComboBox.currentText()
        street_layer = QgsProject.instance().mapLayersByName(street_layer_name)[0]
        self.ui.StreetLayerStreetFieldComboBox.clear()
        self.load_fields(street_layer, self.ui.StreetLayerStreetFieldComboBox)

    def update_address_fields(self):
        if self.refreshing:
            return
        address_layer_name = self.ui.AddressLayerComboBox.currentText()
        address_layer = QgsProject.instance().mapLayersByName(address_layer_name)[0]
        self.ui.AddressLayerStreetFieldComboBox.clear()
        self.ui.AddressLayerAddressNumberFieldComboBox.clear()
        self.load_fields(address_layer, self.ui.AddressLayerStreetFieldComboBox)
        self.load_fields(address_layer, self.ui.AddressLayerAddressNumberFieldComboBox)

    def __init__(self,parent=None):
        super().__init__(parent)
        self.plugin_dir = os.path.dirname(__file__)
        self.ui = Ui_StreetParityDialog()
        self.ui.setupUi(self)
        self.setWindowModality(Qt.NonModal)
        self.refreshing = False
        self.load_layers()

        refresh_button_icon = os.path.join(self.plugin_dir, "icons", "recycle.png")
        self.ui.AddressRefreshButton.setIcon(QIcon(refresh_button_icon))
        self.ui.StreetRefreshButton.setIcon(QIcon(refresh_button_icon))
        #connect the refresh button to the refresh method
        self.ui.AddressRefreshButton.clicked.connect(self.refresh_address)
        self.ui.StreetRefreshButton.clicked.connect(self.refresh_street)


        self.ui.buttonBox.accepted.connect(self.run)
        self.ui.buttonBox.rejected.connect(self.reject)
        # when the street layer is changed, update the street field combo box
        self.ui.StreetLayerComboBox.currentIndexChanged.connect(self.update_street_fields)
        # when the address layer is changed, update the address field combo box
        self.ui.AddressLayerComboBox.currentIndexChanged.connect(self.update_address_fields)

    def _point_from_geometry(self, geom):
        """Return a single representative QgsPointXY for a point geometry.

        Handles single points and multipoints (first vertex), matching the old
        shapely ``Point(x[0])`` behaviour. Returns None for empty geometry.
        """
        if geom is None or geom.isEmpty():
            return None
        if geom.isMultipart():
            pts = geom.asMultiPoint()
            return pts[0] if pts else None
        return geom.asPoint()

    def calculate_parity(self, addresses):
        """Return 'even', 'odd' or 'both' for a list of address numbers.

        Non-numeric values are ignored. An empty list yields 'even', preserving
        the original behaviour (``all()`` over an empty sequence is True).
        """
        numbers = []
        for value in addresses:
            try:
                numbers.append(int(value))
            except (TypeError, ValueError):
                continue

        if all(num % 2 == 0 for num in numbers):
            return 'even'
        elif all(num % 2 != 0 for num in numbers):
            return 'odd'
        else:
            return 'both'

    def apply_rule_based_style(self, layer):
        """Apply rule-based style to the layer."""
        # Create rules
        symbol_red = QgsSymbol.defaultSymbol(layer.geometryType())
        symbol_red.setColor(QColor('red'))
        # Set thickness of the line
        symbol_red.setWidth(1)
        rule_red = QgsRuleBasedRenderer.Rule(symbol_red)
        rule_red.setLabel("Inconsistent Parity")
        rule_red.setFilterExpression('("PARITY_L" = \'both\') OR ("PARITY_R" = \'both\')')

        symbol_green = QgsSymbol.defaultSymbol(layer.geometryType())
        symbol_green.setColor(QColor('green'))
        symbol_green.setWidth(1)
        rule_green = QgsRuleBasedRenderer.Rule(symbol_green)
        rule_green.setLabel("Consistent Parity")
        rule_green.setFilterExpression('("PARITY_L" != \'both\') AND ("PARITY_R" != \'both\')')

        # Create root rule and append the rules
        root_rule = QgsRuleBasedRenderer.Rule(QgsSymbol.defaultSymbol(layer.geometryType()))
        root_rule.appendChild(rule_red)
        root_rule.appendChild(rule_green)

        # Apply the rule-based renderer to the layer
        renderer = QgsRuleBasedRenderer(root_rule)
        layer.setRenderer(renderer)
        layer.triggerRepaint()

    def build_output_layer(self, street_layer, street_features, sides, address_number_field):
        """Create a memory layer copying the street layer plus PARITY_L/PARITY_R."""
        fields = QgsFields()
        for field in street_layer.fields():
            fields.append(field)
        fields.append(QgsField('PARITY_L', QVariant.String))
        fields.append(QgsField('PARITY_R', QVariant.String))

        crs = street_layer.crs()
        crs_ref = crs.authid() if crs.authid() else crs.toWkt()
        geom_type = QgsWkbTypes.displayString(street_layer.wkbType())
        new_layer = QgsVectorLayer('%s?crs=%s' % (geom_type, crs_ref),
                                   'Updated Streets', 'memory')
        provider = new_layer.dataProvider()
        provider.addAttributes(fields)
        new_layer.updateFields()

        out_features = []
        for sf in street_features:
            parity = sides.get(sf.id())
            if parity is None:
                # No addresses matched this segment (matches the old behaviour
                # of leaving PARITY_L/PARITY_R as NULL).
                parity_l = None
                parity_r = None
            else:
                parity_l = self.calculate_parity(parity['left'])
                parity_r = self.calculate_parity(parity['right'])

            feature = QgsFeature(new_layer.fields())
            feature.setGeometry(sf.geometry())
            feature.setAttributes(sf.attributes() + [parity_l, parity_r])
            out_features.append(feature)

        provider.addFeatures(out_features)
        new_layer.updateExtents()

        self.apply_rule_based_style(new_layer)
        QgsProject.instance().addMapLayer(new_layer)

    def run(self):
        street_layer_name = self.ui.StreetLayerComboBox.currentText()
        address_layer_name = self.ui.AddressLayerComboBox.currentText()
        # Check if the user has selected both a street layer and an address layer
        if street_layer_name == "Select Street Layer" or address_layer_name == "Select Address Layer":
            QMessageBox.warning(self, "Selection Error", "Please select both an address layer and a street layer.")
            return

        address_street_field = self.ui.AddressLayerStreetFieldComboBox.currentText()
        address_number_field = self.ui.AddressLayerAddressNumberFieldComboBox.currentText()
        street_street_field = self.ui.StreetLayerStreetFieldComboBox.currentText()
        if (address_street_field in ("", "Select Field")
                or address_number_field in ("", "Select Field")
                or street_street_field in ("", "Select Field")):
            QMessageBox.warning(self, "Selection Error",
                                "Please select the street-name field for both layers and the address-number field.")
            return

        address_layer = QgsProject.instance().mapLayersByName(address_layer_name)[0]
        street_layer = QgsProject.instance().mapLayersByName(street_layer_name)[0]

        # Work in the street layer's CRS and transform address points into it.
        street_crs = street_layer.crs()
        same_crs = address_layer.crs() == street_crs
        transform = QgsCoordinateTransform(address_layer.crs(), street_crs,
                                           QgsProject.instance())

        # Group street features by street name for quick lookup.
        street_features = list(street_layer.getFeatures())
        streets_by_name = {}
        for sf in street_features:
            geom = sf.geometry()
            if geom is None or geom.isEmpty():
                continue
            streets_by_name.setdefault(sf[street_street_field], []).append(sf)

        # For each street feature, collect the address numbers falling on each
        # side of the segment. sides[feature_id] = {"left": [...], "right": [...]}
        sides = {}

        address_features = list(address_layer.getFeatures())
        progress_dialog = QProgressDialog("Computing Parity...", "Cancel", 0,
                                          len(address_features), self)
        progress_dialog.setWindowTitle("Parity Analysis")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.show()

        for i, address in enumerate(address_features, start=1):
            if progress_dialog.wasCanceled():
                break
            progress_dialog.setValue(i)

            point = self._point_from_geometry(address.geometry())
            if point is None:
                continue
            if not same_crs:
                point = transform.transform(point)

            street_name = address[address_street_field]
            number = address[address_number_field]
            candidates = streets_by_name.get(street_name, [])

            # Find the nearest matching street segment. closestSegmentWithContext
            # returns, in one call, the squared distance to the nearest segment
            # and whether the point lies left or right of it (leftOf < 0 => left).
            # This replaces the shapely nearest_points / cross-product logic.
            best_sqr_dist = float("inf")
            best_fid = None
            best_left_of = 0
            for sf in candidates:
                sqr_dist, _min_pt, _after, left_of = \
                    sf.geometry().closestSegmentWithContext(point)
                if sqr_dist < best_sqr_dist:
                    best_sqr_dist = sqr_dist
                    best_fid = sf.id()
                    best_left_of = left_of
            if best_fid is None:
                continue

            side = "left" if best_left_of < 0 else "right"
            sides.setdefault(best_fid, {"left": [], "right": []})[side].append(number)

        self.build_output_layer(street_layer, street_features, sides, address_number_field)

        self.accept()
