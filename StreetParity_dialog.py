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
    QgsFeature,
    QgsRuleBasedRenderer,
    QgsSymbol
)
from PyQt5.QtGui import QColor  
from qgis.PyQt.QtCore import QVariant
import geopandas as gpd
from shapely.geometry import Point, LineString, MultiLineString, MultiPoint
from shapely.ops import nearest_points
import numpy as np

class StreetParityDialog(QDialog):

    def load_fields(self, layer, combo_box):
        combo_box.addItem("Select Field")
        for field in layer.fields():
            combo_box.addItem(field.name())

    def load_layers(self):
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

    def __init__(self):
        super().__init__()
        self.ui = Ui_StreetParityDialog()
        self.ui.setupUi(self)

        self.load_layers()
            
        self.ui.buttonBox.accepted.connect(self.run)
        self.ui.buttonBox.rejected.connect(self.reject)
        # when the street layer is changed, update the street field combo box
        self.ui.StreetLayerComboBox.currentIndexChanged.connect(lambda: self.load_fields(QgsProject.instance().mapLayersByName(self.ui.StreetLayerComboBox.currentText())[0], self.ui.StreetLayerStreetFieldComboBox))
        # when the address layer is changed, update the address field combo box
        self.ui.AddressLayerComboBox.currentIndexChanged.connect(lambda: self.load_fields(QgsProject.instance().mapLayersByName(self.ui.AddressLayerComboBox.currentText())[0], self.ui.AddressLayerStreetFieldComboBox))
        self.ui.AddressLayerComboBox.currentIndexChanged.connect(lambda: self.load_fields(QgsProject.instance().mapLayersByName(self.ui.AddressLayerComboBox.currentText())[0], self.ui.AddressLayerAddressNumberFieldComboBox))

    

    def nearest_segment_to_point(self, point, segments):
        """Find the nearest segment to a point from a GeoDataFrame of segments."""
        if segments.empty:
            return None
        
        distances = segments.geometry.apply(lambda segment: point.distance(segment))
        
        if distances.empty:
            return None
        
        min_distance_index = distances.idxmin()
        
        if min_distance_index not in segments.index:
            return None
        
        return segments.loc[min_distance_index]

    def nearest_inner_line(self, point, line):
        """Find the nearest inner line to a point from a LineString or MultiLineString."""
        if isinstance(line, LineString):
            return list(line.coords)
        
        elif isinstance(line, MultiLineString):
            nearest_segment_coords = None
            min_distance = float('inf')

            for single_line in line.geoms:
                for i in range(len(single_line.coords) - 1):
                    segment = LineString([single_line.coords[i], single_line.coords[i + 1]])
                    distance = point.distance(segment)
                    if distance < min_distance:
                        min_distance = distance
                        nearest_segment_coords = (single_line.coords[i], single_line.coords[i + 1])

            return nearest_segment_coords
        
        else:
            raise ValueError("The line should be either LineString or MultiLineString.")

    def get_orientation_and_direction(self, points):
        """Determine the orientation and direction of a line from a list of points."""
        minx, miny = float('inf'), float('inf')
        maxx, maxy = -float('inf'), -float('inf')

        for x, y in points:
            minx, maxx = min(minx, x), max(maxx, x)
            miny, maxy = min(miny, y), max(maxy, y)

        orientation = 'x' if maxx - minx > maxy - miny else 'y'

        if orientation == 'x':
            direction = 'increasing' if points[0][0] < points[1][0] else 'decreasing'
        else:
            direction = 'increasing' if points[0][1] < points[1][1] else 'decreasing'
        
        return orientation, direction

    def calculate_parity(self, addresses):
        if all(num % 2 == 0 for num in addresses):
            return 'even'
        elif all(num % 2 != 0 for num in addresses):
            return 'odd'
        else:
            return 'both'


    def calculate_angle_from_north(self, line):
        """Calculate the angle from the north of a line."""
        if isinstance(line, LineString):
            line = [line.coords[0], line.coords[1]]
        elif isinstance(line, MultiLineString):
            line = [line.geoms[0].coords[0], line.geoms[0].coords[1]]
        else:
            raise ValueError("The line should be either LineString or MultiLineString.")

        x1, y1 = line[0]
        x2, y2 = line[1]

        angle = np.arctan2(x2 - x1, y2 - y1) * 180 / np.pi
        return angle

    def determine_position(self, fish_bone_line, last_two_points):
        # Extract coordinates from lines as numpy arrays
        p1 = np.array(fish_bone_line.coords[0])
        p2 = np.array(fish_bone_line.coords[1])
        p3 = np.array(last_two_points.coords[0])
        p4 = np.array(last_two_points.coords[1])

        # Convert to 3D vectors by adding a zero z-component
        p1_3d = np.array([p1[0], p1[1], 0])
        p2_3d = np.array([p2[0], p2[1], 0])
        p3_3d = np.array([p3[0], p3[1], 0])
        p4_3d = np.array([p4[0], p4[1], 0])

        # Direction vectors
        v1 = p2_3d - p1_3d
        v2 = p4_3d - p3_3d

        # Cross product of v1 and v2
        cross_product = np.cross(v1, v2)

        # Check the z-component of the cross product
        z_component = cross_product[2]

        if z_component > 0:
            return "left"
        elif z_component < 0:
            return "right"
        else:
            return "collinear"

    def parity(self, addresses, streets, street_street_field='STR_NAME', address_street_field='STR_NAME', address_number_field='ADD_NUMBER'):
        """Determine the parity of the addresses on the left and right sides of the streets."""
        if isinstance(addresses['geometry'].iloc[0], MultiPoint):
            addresses['geometry'] = addresses['geometry'].apply(lambda x: Point(x[0]))

        street_addresses_by_side = {}
        address_count = len(addresses)
        progress_dialog = QProgressDialog("Computing Parity...", "Cancel", 0, address_count, self)
        progress_dialog.setWindowTitle("Parity Analysis")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.show()

        for i, address in enumerate(addresses.itertuples(), start=1):
            if progress_dialog.wasCanceled():
                break

            street_name = getattr(address, address_street_field)
            street_segments = streets[streets[street_street_field] == street_name]
            point = address.geometry
            nearest_segment = self.nearest_segment_to_point(point, street_segments)
            angle = self.calculate_angle_from_north(nearest_segment.geometry)
         
            if nearest_segment is None:
                continue

            if nearest_segment.unique_id not in street_addresses_by_side:
                street_addresses_by_side[nearest_segment.unique_id] = {"left_addresses": [], "right_addresses": []}

            nearest_point = nearest_points(nearest_segment.geometry, point)[0]
            inner_line_coords = self.nearest_inner_line(nearest_point, nearest_segment.geometry)
            #last point of the inner line
            last_point =Point(nearest_segment.geometry.geoms[-1].coords[-1])
            #last two points of the inner line as a line
            last_two_points = LineString(nearest_segment.geometry.geoms[-1].coords[-2:])



            if nearest_point==last_point:
                

                fish_bone_line = LineString([point,nearest_point])

                position = self.determine_position(fish_bone_line, last_two_points)
                if position == "left":
                    street_addresses_by_side[nearest_segment.unique_id]["left_addresses"].append(getattr(address, address_number_field))
                elif position == "right":
                    street_addresses_by_side[nearest_segment.unique_id]["right_addresses"].append(getattr(address, address_number_field))
                progress_dialog.setValue(i)
            else:


                orientation, direction = self.get_orientation_and_direction(inner_line_coords)

                attributes = {address_number_field: getattr(address, address_number_field), address_street_field: getattr(address, address_street_field)}
                if orientation == 'x':
                    attributes["SIDE"] = "left" if (direction == 'increasing' and point.y > nearest_point.y) or (direction == 'decreasing' and point.y < nearest_point.y) else "right"
                else:
                    attributes["SIDE"] = "left" if (direction == 'increasing' and point.x < nearest_point.x) or (direction == 'decreasing' and point.x > nearest_point.x) else "right"

                address_direction = attributes["SIDE"]
                street_addresses_by_side[nearest_segment.unique_id][f"{address_direction}_addresses"].append(getattr(address, address_number_field))
                progress_dialog.setValue(i)

        street_parity = {}
        for id, sides in street_addresses_by_side.items():
            left_addresses, right_addresses = sides['left_addresses'], sides['right_addresses']
            street_parity[id] = {
                "PARITY_L": self.calculate_parity(left_addresses),
                "PARITY_R": self.calculate_parity(right_addresses)
            }

        return street_parity

    def update_parities(self, streets, parity_result):
        """Update the parity values of the streets GeoDataFrame."""
        streets['PARITY_L'] = None
        streets['PARITY_R'] = None

        for id, parities in parity_result.items():
            streets.loc[streets['unique_id'] == id, 'PARITY_L'] = parities['PARITY_L']
            streets.loc[streets['unique_id'] == id, 'PARITY_R'] = parities['PARITY_R']

        return streets

    def create_new_layer(self, updated_gdf, original_layer):
        """Create a new QGIS layer with the updated GeoDataFrame."""
        # Define the fields for the new layer
        fields = QgsFields()
        for field in original_layer.fields():
            fields.append(field)
        fields.append(QgsField('PARITY_L', QVariant.String))
        fields.append(QgsField('PARITY_R', QVariant.String))

        # Create a new vector layer
        crs = original_layer.crs().toWkt()
        new_layer = QgsVectorLayer(f'LineString?crs={crs}', 'Updated Streets', 'memory')
        new_layer_data = new_layer.dataProvider()
        new_layer_data.addAttributes(fields)
        new_layer.updateFields()

        # Add the updated features to the new layer
        for idx, row in updated_gdf.iterrows():
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromWkt(row['geometry'].wkt))
            feature.setAttributes(list(row[original_layer.fields().names()]) + [row['PARITY_L'], row['PARITY_R']])
            new_layer_data.addFeature(feature)

        # Apply rule-based styling
        self.apply_rule_based_style(new_layer)

        # Add the new layer to the project
        QgsProject.instance().addMapLayer(new_layer)

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

    def run(self):
        street_layer_name = self.ui.StreetLayerComboBox.currentText()
        address_layer_name = self.ui.AddressLayerComboBox.currentText()
        # Check if the user has selected both a street layer and an address layer
        if street_layer_name == "Select Street Layer" or address_layer_name == "Select Address Layer":
            QMessageBox.warning(self, "Selection Error", "Please select both an address layer and a street layer.")
            return

        address_layer = QgsProject.instance().mapLayersByName(address_layer_name)[0]
        street_layer = QgsProject.instance().mapLayersByName(street_layer_name)[0]
        address_street_field = self.ui.AddressLayerStreetFieldComboBox.currentText()
        address_number_field = self.ui.AddressLayerAddressNumberFieldComboBox.currentText()
        street_street_field = self.ui.StreetLayerStreetFieldComboBox.currentText()

        address_gdf = gpd.GeoDataFrame.from_features([feature for feature in address_layer.getFeatures()])
        street_gdf = gpd.GeoDataFrame.from_features([feature for feature in street_layer.getFeatures()])

        # Add a unique identifier
        address_gdf['unique_id'] = np.arange(len(address_gdf))
        street_gdf['unique_id'] = np.arange(len(street_gdf))

        # Adding empty parity columns to the GeoDataFrame
        street_gdf['PARITY_L'] = None
        street_gdf['PARITY_R'] = None

        parity_result = self.parity(address_gdf, street_gdf, street_street_field, address_street_field, address_number_field)
        updated_streets = self.update_parities(street_gdf, parity_result)

        self.create_new_layer(updated_streets, street_layer)

        print(f"Selected Street Layer: {street_layer_name}, Selected Address Layer: {address_layer_name}")
        self.accept()