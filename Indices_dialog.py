from PyQt5.QtWidgets import QDialog, QMessageBox, QProgressDialog
from .Ndvi_dialog_base import Ui_NdviDialog
from .Ndwi_dialog_base import Ui_NdwiDialog
from .Evi_dialog_base import Ui_EviDialog
from .Evi2_dialog_base import Ui_Evi2Dialog
from qgis.core import QgsProject,QgsMapLayer, QgsRasterLayer, QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY, QgsSingleBandGrayRenderer
from PyQt5.QtCore import Qt
import geopandas as gpd
from shapely.geometry import Point, LineString, MultiPoint
import json
from shapely.ops import nearest_points
import json
from osgeo import gdal
import tempfile
import os
from PyQt5.QtGui import QIcon


class NDVIDialog(QDialog):



    def __init__(self,parent=None):
        super().__init__(parent)
        self.plugin_dir = os.path.dirname(__file__)
        self.ui = Ui_NdviDialog()
        self.ui.setupUi(self)
        self.setWindowModality(Qt.NonModal)
        self.ui.RastercomboBox.addItem("Select Raster")
        layers = QgsProject.instance().layerTreeRoot().children()
        if layers:
            for layer in layers:
                if layer.layer().type() == QgsMapLayer.RasterLayer:
                    self.ui.RastercomboBox.addItem(layer.name())
        self.ui.RastercomboBox.currentIndexChanged.connect(self.layer_changed)

        #connect the radio buttons
        self.ui.RGBradioButton.toggled.connect(self.rgb_toggled)
        self.ui.BGRradioButton.toggled.connect(self.bgr_toggled)
        #set refeshButton icon
        refresh_button_icon = os.path.join(self.plugin_dir, "icons", "recycle.png")
        self.ui.refreshButton.setIcon(QIcon(refresh_button_icon))
        self.refresing = False
        #connect the buttons
        self.ui.refreshButton.clicked.connect(self.refresh_raster_combobox)
        self.ui.buttonBox.accepted.connect(self.run)
        self.ui.buttonBox.rejected.connect(self.reject)
        self.raster_layer = None
        self.bands = 0

    def refresh_raster_combobox(self):
        self.refresing = True
        self.ui.RastercomboBox.clear()
        self.ui.RastercomboBox.addItem("Select Raster")
        layers = QgsProject.instance().layerTreeRoot().children()
        if layers:
            for layer in layers:
                if layer.layer().type() == QgsMapLayer.RasterLayer:
                    self.ui.RastercomboBox.addItem(layer.name())
        self.refresing = False

    def layer_changed(self):
        if self.refresing:
            return
        #get the bands of the layers
        layer_name = self.ui.RastercomboBox.currentText()
        if layer_name == "Select Raster":
            return
        layer = QgsProject.instance().mapLayersByName(layer_name)[0]
        self.bands = layer.bandCount()
        self.ui.RedcomboBox.clear()
        self.ui.NIRcomboBox.clear()
        for band in range(1, self.bands+1):
            self.ui.RedcomboBox.addItem(str(band))
            self.ui.NIRcomboBox.addItem(str(band))
        self.rgb_toggled()

    def rgb_toggled(self):
        #set the red and nir bands to the correct values
        if self.bands >= 4:
            self.ui.RedcomboBox.setCurrentText("1")
            self.ui.NIRcomboBox.setCurrentText("4")

    def bgr_toggled(self):
        #set the red and nir bands to the correct values
        self.ui.RedcomboBox.setCurrentText("3")
        self.ui.NIRcomboBox.setCurrentText("4")

    


    def run(self):
        #get the bands
        red_band = self.ui.RedcomboBox.currentText()
        nir_band = self.ui.NIRcomboBox.currentText()
        #get the raster layer
        layer_name = self.ui.RastercomboBox.currentText()
        layers = QgsProject.instance().mapLayersByName(layer_name)
        if layers:
            self.raster_layer = layers[0]
        else:
            QMessageBox.warning(self, "No Layer", "No layer selected")
            return
        #get the extent of the raster layer
        extent = self.raster_layer.extent()

        #using gdal open and read the raster layer
        ds = gdal.Open(self.raster_layer.source())
        #get the red and nir bands
        red_band_array = ds.GetRasterBand(int(red_band)).ReadAsArray()
        nir_band_array = ds.GetRasterBand(int(nir_band)).ReadAsArray()
        #get the transformation
        transform = ds.GetGeoTransform()
        #we also need the projection
        proj = ds.GetProjection()
        #calculate the NDVI
        ndvi = (nir_band_array - red_band_array) / (nir_band_array + red_band_array)
        #set any value greater than 1 to nan and any value less than -1 to nan
        ndvi[ndvi > 1] = float('nan')
        ndvi[ndvi < -1] = float('nan')
        #create a new raster layer
        driver = gdal.GetDriverByName("GTiff")
        #we need to get the tmp directory regardless of the operating system
        os_temp_dir = tempfile.gettempdir()
        out_path = os.path.join(os_temp_dir, "ndvi.tif")
        out_ds = driver.Create(out_path, self.raster_layer.width(), self.raster_layer.height(), 1, gdal.GDT_Float32)
        out_ds.SetGeoTransform(transform)
        out_ds.SetProjection(proj)
        out_band = out_ds.GetRasterBand(1)
        out_band.WriteArray(ndvi)
        out_band.FlushCache()
        out_ds = None
        #add the raster layer to the map
        ndvi_layer = QgsRasterLayer(out_path, "NDVI")
        QgsProject.instance().addMapLayer(ndvi_layer)
        self.accept()


class NDWIDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.plugin_dir = os.path.dirname(__file__)
        self.ui = Ui_NdwiDialog()
        self.ui.setupUi(self)
        self.setWindowModality(Qt.NonModal)
        self.ui.RastercomboBox.addItem("Select Raster")
        layers = QgsProject.instance().layerTreeRoot().children()
        if layers:
            for layer in layers:
                if layer.layer().type() == QgsMapLayer.RasterLayer:
                    self.ui.RastercomboBox.addItem(layer.name())
        self.ui.RastercomboBox.currentIndexChanged.connect(self.layer_changed)
        #set refeshButton icon
        refresh_button_icon = os.path.join(self.plugin_dir, "icons", "recycle.png")
        self.ui.refreshButton.setIcon(QIcon(refresh_button_icon))
        self.refresing = False
        #connect the radio buttons
        self.ui.refreshButton.clicked.connect(self.refresh_raster_combobox)
        self.ui.GradioButton.toggled.connect(self.g_toggled)
        self.ui.RGBradioButton.toggled.connect(self.rgb_toggled)

        #connect the buttons
        self.ui.buttonBox.accepted.connect(self.run)
        self.ui.buttonBox.rejected.connect(self.reject)
        self.raster_layer = None
        self.bands = 0
    
    def refresh_raster_combobox(self):
        self.refresing = True
        self.ui.RastercomboBox.clear()
        self.ui.RastercomboBox.addItem("Select Raster")
        layers = QgsProject.instance().layerTreeRoot().children()
        if layers:
            for layer in layers:
                if layer.layer().type() == QgsMapLayer.RasterLayer:
                    self.ui.RastercomboBox.addItem(layer.name())
        self.refresing = False
    

    def layer_changed(self):
        if self.refresing:
            return
        #get the bands of the layers
        layer_name = self.ui.RastercomboBox.currentText()
        if layer_name == "Select Raster":
            return
        layer = QgsProject.instance().mapLayersByName(layer_name)[0]
        self.bands = layer.bandCount()
        self.ui.GreencomboBox.clear()
        self.ui.NIRcomboBox.clear()
        for band in range(1, self.bands+1):
            self.ui.GreencomboBox.addItem(str(band))
            self.ui.NIRcomboBox.addItem(str(band))
        self.rgb_toggled()

    def rgb_toggled(self):
        #if there are at least 4 bands, set the green and nir bands to the correct values
        if self.bands >= 4:
        #set the green and nir bands to the correct values
            self.ui.GreencomboBox.setCurrentText("2")
            self.ui.NIRcomboBox.setCurrentText("4")

    def g_toggled(self):
        #set the Green and nir bands to the correct values
        self.ui.GreencomboBox.setCurrentText("1")
        self.ui.NIRcomboBox.setCurrentText("2")

    


    def run(self):
        #get the bands
        green_band = self.ui.GreencomboBox.currentText()
        nir_band = self.ui.NIRcomboBox.currentText()
        #get the raster layer
        layer_name = self.ui.RastercomboBox.currentText()
        layers = QgsProject.instance().mapLayersByName(layer_name)
        if layers:
            self.raster_layer = layers[0]
        else:
            QMessageBox.warning(self, "No Layer", "No layer selected")
            return
        #get the extent of the raster layer
        extent = self.raster_layer.extent()
        #using gdal open and read the raster layer
        ds = gdal.Open(self.raster_layer.source())
        #get the green and nir bands
        green_band_array = ds.GetRasterBand(int(green_band)).ReadAsArray()
        nir_band_array = ds.GetRasterBand(int(nir_band)).ReadAsArray()
        #get the transformation
        transform = ds.GetGeoTransform()
        #we also need the projection
        proj = ds.GetProjection()
        #calculate the NDVI
        ndwi = (green_band_array-nir_band_array) / (green_band_array+nir_band_array)
        #set any value greater than 1 to nan and any value less than -1 to nan
        ndwi[ndwi > 1] = float('nan')
        ndwi[ndwi < -1] = float('nan')
        #create a new raster layer
        driver = gdal.GetDriverByName("GTiff")
        #we need to get the tmp directory regardless of the operating system
        os_temp_dir = tempfile.gettempdir()
        out_path = os.path.join(os_temp_dir, "ndwi.tif")
        out_ds = driver.Create(out_path, self.raster_layer.width(), self.raster_layer.height(), 1, gdal.GDT_Float32)
        out_ds.SetGeoTransform(transform)
        out_ds.SetProjection(proj)
        out_band = out_ds.GetRasterBand(1)
        out_band.WriteArray(ndwi)
        out_band.FlushCache()
        out_ds = None
        #add the raster layer to the map
        ndwi_layer = QgsRasterLayer(out_path, "NDWI")
        QgsProject.instance().addMapLayer(ndwi_layer)
        self.accept()

  

class EVIDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.plugin_dir = os.path.dirname(__file__)
        self.ui = Ui_EviDialog()
        self.ui.setupUi(self)
        self.setWindowModality(Qt.NonModal)
        self.ui.RastercomboBox.addItem("Select Raster")
        layers = QgsProject.instance().layerTreeRoot().children()
        if layers:
            for layer in layers:
                if layer.layer().type() == QgsMapLayer.RasterLayer:
                    self.ui.RastercomboBox.addItem(layer.name())
        self.ui.RastercomboBox.currentIndexChanged.connect(self.layer_changed)
        self.ui.buttonBox.accepted.connect(self.run)
        self.ui.buttonBox.rejected.connect(self.reject)
        #set refeshButton icon
        refresh_button_icon = os.path.join(self.plugin_dir, "icons", "recycle.png")
        self.ui.refreshButton.setIcon(QIcon(refresh_button_icon))
        self.refresing = False
        
        #connect the refresh button
        self.ui.refreshButton.clicked.connect(self.refresh_raster_combobox)
        #connect the radio buttons
        #connect the radio buttons
        self.ui.RGBradioButton.toggled.connect(self.rgb_toggled)
        self.ui.BGRradioButton.toggled.connect(self.bgr_toggled)

        self.bands=0

    def refresh_raster_combobox(self):
        self.refresing = True
        self.ui.RastercomboBox.clear()
        self.ui.RastercomboBox.addItem("Select Raster")
        layers = QgsProject.instance().layerTreeRoot().children()
        if layers:
            for layer in layers:
                if layer.layer().type() == QgsMapLayer.RasterLayer:
                    self.ui.RastercomboBox.addItem(layer.name())
        self.refresing = False

    def layer_changed(self):
        if self.refresing:
            print("Refreshing")
            return
        #get the bands of the layers
        layer_name = self.ui.RastercomboBox.currentText()
        print("layer changed")
        if layer_name == "Select Raster":
            return
        else:
            layer = QgsProject.instance().mapLayersByName(layer_name)[0]
            self.bands = layer.bandCount()
            self.ui.RedcomboBox.clear()
            self.ui.NIRcomboBox.clear()
            self.ui.BluecomboBox.clear()
            for band in range(1, self.bands+1):
                self.ui.RedcomboBox.addItem(str(band))
                self.ui.NIRcomboBox.addItem(str(band))
                self.ui.BluecomboBox.addItem(str(band))
            self.rgb_toggled()
    def bgr_toggled(self):
        #set the red, nir and blue bands to the correct values
        self.ui.RedcomboBox.setCurrentText("3")
        self.ui.BluecomboBox.setCurrentText("1")
        self.ui.NIRcomboBox.setCurrentText("4")

    def rgb_toggled(self):
        #set the red, nir and blue bands to the correct values
        if self.bands >= 4:
            self.ui.RedcomboBox.setCurrentText("1")
            self.ui.BluecomboBox.setCurrentText("3")
            self.ui.NIRcomboBox.setCurrentText("4")
        

    def run(self):
        #get the bands
        red_band = self.ui.RedcomboBox.currentText()
        nir_band = self.ui.NIRcomboBox.currentText()
        blue_band = self.ui.BluecomboBox.currentText()
        #get the raster layer
        layer_name = self.ui.RastercomboBox.currentText()
        layers = QgsProject.instance().mapLayersByName(layer_name)
        if layers:
            self.raster_layer = layers[0]
        else:
            QMessageBox.warning(self, "No Layer", "No layer selected")
            return
        #show a message that the process is running
        #there are no steps to show so it will NOT be a progress dialog
        #we will use a message box that can be closed later

        
        #get the extent of the raster layer
        extent = self.raster_layer.extent()
        #using gdal open and read the raster layer
        ds = gdal.Open(self.raster_layer.source())
        #get the red, nir and blue bands
        red_band_array = ds.GetRasterBand(int(red_band)).ReadAsArray()
        nir_band_array = ds.GetRasterBand(int(nir_band)).ReadAsArray()
        blue_band_array = ds.GetRasterBand(int(blue_band)).ReadAsArray()
        Gval = self.ui.GValue.value()
        C1val = self.ui.C1Value.value()
        C2val = self.ui.C2Value.value()
        L = self.ui.LValue.value()

        #get the transformation
        transform = ds.GetGeoTransform()
        #we also need the projection
        proj = ds.GetProjection()
        #calculate the NDVI
        evi = Gval * ((nir_band_array - red_band_array) / (nir_band_array + C1val * red_band_array - C2val * blue_band_array + L))
        #set any value greater than 1 to nan and any value less than -1 to nan
        # evi[evi > 1] = float('nan')
        # evi[evi < -1] = float('nan')
        #set 0 to nan
        evi[evi == 0] = float('nan')
        #create a new raster layer
        driver = gdal.GetDriverByName("GTiff")
        #we need to get the tmp directory regardless of the operating system
        os_temp_dir = tempfile.gettempdir()
        out_path = os.path.join(os_temp_dir, "evi.tif")
        out_ds = driver.Create(out_path, self.raster_layer.width(), self.raster_layer.height(), 1, gdal.GDT_Float32)
        out_ds.SetGeoTransform(transform)
        out_ds.SetProjection(proj)
        out_band = out_ds.GetRasterBand(1)
        out_band.WriteArray(evi)
        out_band.FlushCache()
        out_ds = None
        #add the raster layer to the map
        evi_layer = QgsRasterLayer(out_path, "EVI")
        if evi_layer.isValid():
            # Get the raster renderer
            renderer = evi_layer.renderer()
            
            if isinstance(renderer, QgsSingleBandGrayRenderer):
                # Set the min and max values for the color gradient
                    contrast_enhancement = renderer.contrastEnhancement()
                    contrast_enhancement.setMinimumValue(-2)
                    contrast_enhancement.setMaximumValue(2)
            
            # Refresh the layer to apply changes
            evi_layer.triggerRepaint()
            
            # Add the layer to the map
            QgsProject.instance().addMapLayer(evi_layer)
        else:
            print("Layer failed to load!")


    
        self.accept()



class EVI2Dialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.plugin_dir = os.path.dirname(__file__)
        self.ui = Ui_Evi2Dialog()
        self.ui.setupUi(self)
        self.setWindowModality(Qt.NonModal) 
        layers = QgsProject.instance().layerTreeRoot().children()
        self.ui.RastercomboBox.addItem("Select Raster")
        if layers:
            for layer in layers:
                if layer.layer().type() == QgsMapLayer.RasterLayer:
                    self.ui.RastercomboBox.addItem(layer.name())
        self.ui.RastercomboBox.currentIndexChanged.connect(self.layer_changed)
        self.ui.buttonBox.accepted.connect(self.run)
        self.ui.buttonBox.rejected.connect(self.reject)
        #set refeshButton icon
        refresh_button_icon = os.path.join(self.plugin_dir, "icons", "recycle.png")
        self.ui.refreshButton.setIcon(QIcon(refresh_button_icon))
        self.refresing = False
        
        #connect the refresh button
        self.ui.refreshButton.clicked.connect(self.refresh_raster_combobox)
        self.ui.RGBradioButton.toggled.connect(self.rgb_toggled)
        self.ui.BGRradioButton.toggled.connect(self.bgr_toggled)
        self.bands=0

    def refresh_raster_combobox(self):
        self.refresing = True
        self.ui.RastercomboBox.clear()
        self.ui.RastercomboBox.addItem("Select Raster")
        layers = QgsProject.instance().layerTreeRoot().children()
        if layers:
            for layer in layers:
                if layer.layer().type() == QgsMapLayer.RasterLayer:
                    self.ui.RastercomboBox.addItem(layer.name())
        self.refresing = False

    def layer_changed(self):
        if self.refresing:
            return
        #get the bands of the layers
        layer_name = self.ui.RastercomboBox.currentText()
        if layer_name == "Select Raster":
            return
        layer = QgsProject.instance().mapLayersByName(layer_name)[0]
        self.bands = layer.bandCount()
        self.ui.RedcomboBox.clear()
        self.ui.NIRcomboBox.clear()
        for band in range(1, self.bands+1):
            self.ui.RedcomboBox.addItem(str(band))
            self.ui.NIRcomboBox.addItem(str(band))
        self.rgb_toggled()
    def bgr_toggled(self):
        #set the red and nir bands to the correct values
        self.ui.RedcomboBox.setCurrentText("3")
        self.ui.NIRcomboBox.setCurrentText("4")

    def rgb_toggled(self):
        #set the red and nir bands to the correct values
        if self.bands >= 4:
            self.ui.RedcomboBox.setCurrentText("1")
            self.ui.NIRcomboBox.setCurrentText("4")





    def run(self):
        #get the bands
        red_band = self.ui.RedcomboBox.currentText()
        nir_band = self.ui.NIRcomboBox.currentText()
        #get the raster layer
        layer_name = self.ui.RastercomboBox.currentText()
        layers = QgsProject.instance().mapLayersByName(layer_name)
        if layers:
            self.raster_layer = layers[0]
        else:
            QMessageBox.warning(self, "No Layer", "No layer selected")
            return
        #show a message that the process is running
        #there are no steps to show so it will NOT be a progress dialog
        #we will use a message box that can be closed later
 

        #get the extent of the raster layer
        extent = self.raster_layer.extent()
        #using gdal open and read the raster layer
        ds = gdal.Open(self.raster_layer.source())
        #get the red and nir bands
        red_band_array = ds.GetRasterBand(int(red_band)).ReadAsArray()
        nir_band_array = ds.GetRasterBand(int(nir_band)).ReadAsArray()
        #get the transformation
        transform = ds.GetGeoTransform()
        #we also need the projection
        proj = ds.GetProjection()
        #get the G value
        Gval = self.ui.GValue.value()
        #get the RedRefValue
        RedRefValue = self.ui.RedRefValue.value()

        #calculate the EVI2
        evi2 = Gval * ((nir_band_array - red_band_array) / (nir_band_array + RedRefValue * red_band_array+1))
        #set any value greater than 1 to nan and any value less than -1 to nan
        # evi2[evi2 > 1] = float('nan')
        # evi2[evi2 < -1] = float('nan')
        #set 0 to nan
        evi2[evi2 == 0] = float('nan')
        #create a new raster layer
        driver = gdal.GetDriverByName("GTiff")
        #we need to get the tmp directory regardless of the operating system
        os_temp_dir = tempfile.gettempdir()
        out_path = os.path.join(os_temp_dir, "evi2.tif")
        out_ds = driver.Create(out_path, self.raster_layer.width(), self.raster_layer.height(), 1, gdal.GDT_Float32)
        out_ds.SetGeoTransform(transform)
        out_ds.SetProjection(proj)
        out_band = out_ds.GetRasterBand(1)
        out_band.WriteArray(evi2)
        out_band.FlushCache()
        out_ds = None
        #add the raster layer to the map
        evi2_layer = QgsRasterLayer(out_path, "EVI2")
        if evi2_layer.isValid():
            # Get the raster renderer
            renderer = evi2_layer.renderer()
            
            if isinstance(renderer, QgsSingleBandGrayRenderer):
                # Set the min and max values for the color gradient
                    contrast_enhancement = renderer.contrastEnhancement()
                    contrast_enhancement.setMinimumValue(-2)
                    contrast_enhancement.setMaximumValue(2)
            
            # Refresh the layer to apply changes
            evi2_layer.triggerRepaint()
            
            # Add the layer to the map
            QgsProject.instance().addMapLayer(evi2_layer)
        else:
            print("Layer failed to load!")
        







        self.accept()
