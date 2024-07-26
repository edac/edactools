from PyQt5.QtWidgets import QDialog, QMessageBox
from .Flipper_dialog_base import Ui_FlipperDialog
from qgis.core import QgsProject, QgsMapLayer, QgsSingleBandGrayRenderer, QgsContrastEnhancement
from PyQt5.QtGui import QIcon
import os
from qgis.utils import iface

class FlipperDialog(QDialog):

    def __init__(self,parent=None):
        self.playing = False
        super().__init__(parent)
        self.ui = Ui_FlipperDialog()
        self.ui.setupUi(self)
        self.setWindowModality(Qt.NonModal) 
        self.plugin_dir = os.path.dirname(__file__)
        #add icons to the buttons
        refresh_button_icon = os.path.join(self.plugin_dir, "icons", "recycle.png")
        self.ui.refreshButton.setIcon(QIcon(refresh_button_icon))
        #connect the refresh button to the refresh method
        self.ui.refreshButton.clicked.connect(self.refresh)
        next_button_icon = os.path.join(self.plugin_dir, "icons", "next_button.png")
        self.ui.next_button.setIcon(QIcon(next_button_icon))
        prev_button_icon = os.path.join(self.plugin_dir, "icons", "prev_button.png")
        self.ui.prev_button.setIcon(QIcon(prev_button_icon))
        play_button_icon = os.path.join(self.plugin_dir, "icons", "play_button.png")
        self.ui.play_button.setIcon(QIcon(play_button_icon))
        stop_button_icon = os.path.join(self.plugin_dir, "icons", "stop_button.png")
        self.ui.stop_button.setIcon(QIcon(stop_button_icon))

        # Add UI elements
        self.ui.FlipperRastercomboBox.addItem("Select 3D Raster")
        self.ui.next_button.clicked.connect(self.next_band)
        self.ui.prev_button.clicked.connect(self.prev_band)
        self.ui.play_button.clicked.connect(self.play)
        self.ui.stop_button.clicked.connect(self.stop)
        self.ui.min_spinbox.valueChanged.connect(self.update_band)
        self.ui.max_spinbox.valueChanged.connect(self.update_band)
        self.ui.band_slider.valueChanged.connect(self.slider_changed)
        layers = QgsProject.instance().layerTreeRoot().children()
        self.raster_layer = None
        self.current_band = 1
        self.canvas = iface.mapCanvas()
        self.connect_signals()

        if layers:
            for layer in layers:
                if layer.layer().type() == QgsMapLayer.RasterLayer:
                    self.ui.FlipperRastercomboBox.addItem(layer.name())
        self.ui.FlipperRastercomboBox.currentIndexChanged.connect(self.layer_changed)
    def refresh(self):
        print('refresh')
        self.ui.FlipperRastercomboBox.clear()
        self.ui.FlipperRastercomboBox.addItem("Select 3D Raster")
        layers = QgsProject.instance().layerTreeRoot().children()
        if layers:
            for layer in layers:
                if layer.layer().type() == QgsMapLayer.RasterLayer:
                    self.ui.FlipperRastercomboBox.addItem(layer.name())
      
    def connect_signals(self): 
        # Connect to map canvas signal
        self.canvas.renderComplete.connect(self.on_render_complete)

    def on_render_complete(self):
        if self.playing:
            self.next_band()
        
    def slider_changed(self):
        self.current_band = self.ui.band_slider.value()
        self.update_band()


    def layer_changed(self):
        raster_layer_name = self.ui.FlipperRastercomboBox.currentText()
        if raster_layer_name != "Select 3D Raster":
            layers = QgsProject.instance().mapLayersByName(raster_layer_name)
            if layers:
                self.raster_layer = layers[0]
                self.current_band = 1
                self.ui.band_slider.setMinimum(1)
                self.ui.band_slider.setMaximum(self.raster_layer.bandCount())
                self.update_band()

    def next_band(self):
        if self.raster_layer:
            self.current_band += 1
            if self.current_band > self.raster_layer.bandCount():
                self.current_band = 1
            #update the slider
            self.ui.band_slider.setValue(self.current_band)
            self.update_band()

    def prev_band(self):
        if self.raster_layer:
            self.current_band -= 1
            if self.current_band < 1:
                self.current_band = self.raster_layer.bandCount()
            self.update_band()

    def play(self):
        self.playing = True
        self.next_band()
     

    def stop(self):
        self.playing = False
       

    def update_band(self):
        if self.raster_layer:
            min_value = self.ui.min_spinbox.value()
            max_value = self.ui.max_spinbox.value()
            provider = self.raster_layer.dataProvider()
            renderer = QgsSingleBandGrayRenderer(provider, self.current_band)
            contrast_enhancement = QgsContrastEnhancement(renderer.dataType(1))
            contrast_enhancement.setMinimumValue(min_value)
            contrast_enhancement.setMaximumValue(max_value)
            contrast_enhancement.setContrastEnhancementAlgorithm(QgsContrastEnhancement.StretchToMinimumMaximum)
            renderer.setContrastEnhancement(contrast_enhancement)
            self.raster_layer.setRenderer(renderer)
            self.raster_layer.triggerRepaint()
            self.ui.band_label.setText(f"Band: {self.current_band}")

    def run(self):
        raster_layer_name = self.ui.FlipperRastercomboBox.currentText()
        if raster_layer_name == "Select 3D Raster":
            QMessageBox.warning(self, "No Raster Layer Selected", "Please select a raster layer.")
            return

        print(f"Raster Layer: {raster_layer_name}")
        self.accept()
