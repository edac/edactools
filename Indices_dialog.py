from PyQt5.QtWidgets import QDialog, QMessageBox, QProgressDialog
from .Ndvi_dialog_base import Ui_NdviDialog
from .Ndwi_dialog_base import Ui_NdwiDialog
from .Evi_dialog_base import Ui_EviDialog
from .Evi2_dialog_base import Ui_Evi2Dialog
from qgis.core import QgsProject,QgsMapLayer, QgsRasterLayer, QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY, QgsSingleBandGrayRenderer
from PyQt5.QtCore import Qt
from osgeo import gdal
import numpy as np
import tempfile
import os
from PyQt5.QtGui import QIcon


def _write_index_raster(raster_layer, band_indices, compute_fn, out_name, layer_name,
                        block_rows=512):
    """Compute a per-pixel raster index block-wise and write it to a temp GeoTIFF.

    Reading the whole raster into memory and doing float64 arithmetic on it is
    what previously exhausted RAM and threw ``std::bad_alloc`` (crashing QGIS).
    Here we stream the raster in horizontal strips of ``block_rows`` rows, cast
    each strip to float32, run ``compute_fn`` on it, and write the strip out, so
    peak memory is bounded by one strip regardless of the raster's total size.

    ``compute_fn`` receives the requested bands (as float32 numpy arrays, in the
    order given by ``band_indices``) and must return the index strip. Returns a
    QgsRasterLayer for the result. Raises on failure; the caller handles it.
    """
    ds = gdal.Open(raster_layer.source())
    if ds is None:
        raise RuntimeError("Could not open raster: %s" % raster_layer.source())
    try:
        xsize = ds.RasterXSize
        ysize = ds.RasterYSize
        transform = ds.GetGeoTransform()
        proj = ds.GetProjection()
        bands = [ds.GetRasterBand(i) for i in band_indices]

        out_path = os.path.join(tempfile.gettempdir(), out_name)
        driver = gdal.GetDriverByName("GTiff")
        out_ds = driver.Create(out_path, xsize, ysize, 1, gdal.GDT_Float32)
        if out_ds is None:
            raise RuntimeError("Could not create output raster: %s" % out_path)
        try:
            out_ds.SetGeoTransform(transform)
            out_ds.SetProjection(proj)
            out_band = out_ds.GetRasterBand(1)
            out_band.SetNoDataValue(float('nan'))

            for y in range(0, ysize, block_rows):
                rows = min(block_rows, ysize - y)
                strips = [b.ReadAsArray(0, y, xsize, rows).astype(np.float32)
                          for b in bands]
                # divide/invalid come from zero denominators; they yield nan/inf
                # which we treat as nodata, so silence the warnings.
                with np.errstate(divide='ignore', invalid='ignore'):
                    result = np.asarray(compute_fn(*strips), dtype=np.float32)
                out_band.WriteArray(result, 0, y)
            out_band.FlushCache()
        finally:
            out_ds = None
    finally:
        ds = None

    return QgsRasterLayer(out_path, layer_name)


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
        #calculate NDVI = (NIR - Red) / (NIR + Red), streamed block-wise
        def compute(nir, red):
            ndvi = (nir - red) / (nir + red)
            #anything outside the valid [-1, 1] range becomes nodata
            ndvi[ndvi > 1] = np.nan
            ndvi[ndvi < -1] = np.nan
            return ndvi
        try:
            ndvi_layer = _write_index_raster(
                self.raster_layer, [int(nir_band), int(red_band)],
                compute, "ndvi.tif", "NDVI")
        except Exception as e:
            QMessageBox.critical(self, "NDVI failed",
                                 "Could not compute NDVI:\n%s" % e)
            return
        #add the raster layer to the map
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
        #calculate NDWI = (Green - NIR) / (Green + NIR), streamed block-wise
        def compute(green, nir):
            ndwi = (green - nir) / (green + nir)
            #anything outside the valid [-1, 1] range becomes nodata
            ndwi[ndwi > 1] = np.nan
            ndwi[ndwi < -1] = np.nan
            return ndwi
        try:
            ndwi_layer = _write_index_raster(
                self.raster_layer, [int(green_band), int(nir_band)],
                compute, "ndwi.tif", "NDWI")
        except Exception as e:
            QMessageBox.critical(self, "NDWI failed",
                                 "Could not compute NDWI:\n%s" % e)
            return
        #add the raster layer to the map
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

        
        Gval = self.ui.GValue.value()
        C1val = self.ui.C1Value.value()
        C2val = self.ui.C2Value.value()
        L = self.ui.LValue.value()

        #calculate EVI = G * (NIR - Red) / (NIR + C1*Red - C2*Blue + L),
        #streamed block-wise to keep memory bounded
        def compute(nir, red, blue):
            evi = Gval * ((nir - red) / (nir + C1val * red - C2val * blue + L))
            #set 0 to nan
            evi[evi == 0] = np.nan
            return evi
        try:
            evi_layer = _write_index_raster(
                self.raster_layer,
                [int(nir_band), int(red_band), int(blue_band)],
                compute, "evi.tif", "EVI")
        except Exception as e:
            QMessageBox.critical(self, "EVI failed",
                                 "Could not compute EVI:\n%s" % e)
            return
        #add the raster layer to the map
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
 

        #get the G value
        Gval = self.ui.GValue.value()
        #get the RedRefValue
        RedRefValue = self.ui.RedRefValue.value()

        #calculate EVI2 = G * (NIR - Red) / (NIR + RedRef*Red + 1),
        #streamed block-wise to keep memory bounded
        def compute(nir, red):
            evi2 = Gval * ((nir - red) / (nir + RedRefValue * red + 1))
            #set 0 to nan
            evi2[evi2 == 0] = np.nan
            return evi2
        try:
            evi2_layer = _write_index_raster(
                self.raster_layer, [int(nir_band), int(red_band)],
                compute, "evi2.tif", "EVI2")
        except Exception as e:
            QMessageBox.critical(self, "EVI2 failed",
                                 "Could not compute EVI2:\n%s" % e)
            return
        #add the raster layer to the map
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
