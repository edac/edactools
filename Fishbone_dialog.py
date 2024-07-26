from PyQt5.QtWidgets import QDialog, QMessageBox, QProgressDialog
from .Fishbone_dialog_base import Ui_FishboneDialog
from qgis.core import QgsProject, QgsVectorLayer
from PyQt5.QtCore import Qt
import geopandas as gpd
from shapely.geometry import Point, LineString, MultiPoint
import json
from shapely.ops import nearest_points
import json
import os
from PyQt5.QtGui import QIcon


class FishboneDialog(QDialog):

    def load_fields(self, layer, combo_box):
        combo_box.addItem("Select Field")
        for field in layer.fields():
            combo_box.addItem(field.name())

    def __init__(self):
        super().__init__()
        self.ui = Ui_FishboneDialog()
        self.ui.setupUi(self)
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

        
        

    def nearest_segment_to_point(self, point, segments):
        #initialize the minimum distance
        min_distance = float('inf')
        #initialize the nearest segment
        nearest_segment = None
        #for each segment
        for i, segment in segments.iterrows():
            #get the segment geometry
            segment_geometry = segment['geometry']
            #get the distance between the point and the segment
            distance = point.distance(segment_geometry)
            #if the distance is less than the minimum distance
            if distance < min_distance:
                #update the minimum distance
                min_distance = distance
                #update the nearest segment
                nearest_segment = segment
        #return the nearest segment
        return nearest_segment 
    
    def fishbone(self,addresses, streets, address_street_field, street_street_field):
        return_json={
        "type": "FeatureCollection",
        "name": "fishbone",
        "crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:EPSG::4326" } },
        "features": []
        }
        address_count = len(addresses)
        progress_dialog = QProgressDialog("Building Fishbone...", "Cancel", 0, address_count, self)
        progress_dialog.setWindowTitle("Fishbone Generation")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.show()
        #if the addresses dataframe is of type MultiPoint we need to convert it to a Point
        if isinstance(addresses['geometry'].iloc[0], MultiPoint):
            addresses['geometry'] = addresses['geometry'].apply(lambda x: Point(x[0]))
        #for each address find the nearest segment that has the same STR_NAME
        for i, address in addresses.iterrows():


            if progress_dialog.wasCanceled():
                break
            #get the street name of the address
            street_name = address[address_street_field]
            #get the street segments with the same name
            street_segments = streets[streets[street_street_field] == street_name]
            #get the point of the address
            point = address['geometry']
        

            #get the nearest segment
            nearest_segment = self.nearest_segment_to_point(point, street_segments)
            #
            if nearest_segment is None:
                continue
            #find the nearest point on the segment from the address
            nearest_point = nearest_segment['geometry'].interpolate(nearest_segment['geometry'].project(point))
            
            #create a line between the address and the nearest point

            line = LineString([point, nearest_point])
            #attributes of the address
            # attributes =  {"ADD_NUMBER": address['ADD_NUMBER'], "STR_NAME": address[address_street_field]}
            attributes =  { "STR_NAME": address[address_street_field]}
            #new we have the line and the attributes of the address let's create a GeoJSON feature
            feature = {
                "type": "Feature",
                "geometry": line.__geo_interface__,
                "properties": attributes
            }
            return_json['features'].append(feature)
            progress_dialog.setValue(i + 1)
        return return_json

    def run(self):

        street_layer_name = self.ui.StreetComboBox.currentText()
        address_layer_name = self.ui.AddressComboBox.currentText()
        # check if the user has selected both a street layer and an address layer

        if street_layer_name == "Select Street Layer" or address_layer_name == "Select Address Layer":
            QMessageBox.warning(self, "Selection Error", "Please select both an address layer and a street layer.")
            return

        address_layer = QgsProject.instance().mapLayersByName(address_layer_name)[0]
        street_layer = QgsProject.instance().mapLayersByName(street_layer_name)[0]
        address_layer_df = gpd.GeoDataFrame.from_features([feature for feature in address_layer.getFeatures()])
        street_layer_df = gpd.GeoDataFrame.from_features([feature for feature in street_layer.getFeatures()])

        # Ensure the CRS is set for both dataframes
        if address_layer_df.crs is None:
            address_layer_df.set_crs(address_layer.crs().authid(), inplace=True)

        if street_layer_df.crs is None:
            street_layer_df.set_crs(street_layer.crs().authid(), inplace=True)

        # Convert all geometries to the same CRS UTM 13N
        address_layer_df = address_layer_df.to_crs("EPSG:4326")
        street_layer_df = street_layer_df.to_crs("EPSG:4326")


        address_street_field = self.ui.AddressStreetComboBox.currentText()
        street_street_field = self.ui.StreetStreetComboBox.currentText()
        fb = self.fishbone(address_layer_df, street_layer_df, address_street_field, street_street_field)

        json_string = json.dumps(fb)
      
        fishbone_layer = QgsVectorLayer(json_string, "fishbone", "ogr")
        QgsProject.instance().addMapLayer(fishbone_layer)

        self.accept()

