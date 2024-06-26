from PyQt5.QtWidgets import QDialog, QMessageBox, QComboBox, QPushButton, QVBoxLayout, QLabel, QDoubleSpinBox
from PyQt5.QtCore import QTimer
from .Flipper_dialog_base import Ui_FlipperDialog
from qgis.core import QgsProject, QgsMapLayer, QgsRasterLayer, QgsSingleBandGrayRenderer, QgsContrastEnhancement
from PyQt5.QtGui import QIcon
import os
class FlipperDialog(QDialog):

    def __init__(self):
        super().__init__()
        self.ui = Ui_FlipperDialog()
        self.ui.setupUi(self)
        self.plugin_dir = os.path.dirname(__file__)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_band)
        #add icons to the buttons
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

        if layers:
            for layer in layers:
                if layer.layer().type() == QgsMapLayer.RasterLayer:
                    self.ui.FlipperRastercomboBox.addItem(layer.name())
        
        self.ui.FlipperRastercomboBox.currentIndexChanged.connect(self.layer_changed)
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
        self.timer.start(100)  # Adjust the interval as needed

    def stop(self):
        self.timer.stop()

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
