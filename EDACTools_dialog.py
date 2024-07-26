from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QTreeWidgetItem, QMessageBox
from PyQt5.QtGui import QIcon
from .EDACTools_dialog_base import Ui_EDACToolsDialog
from .Fishbone_dialog import FishboneDialog
from .StreetParity_dialog import StreetParityDialog
from .Flipper_dialog import FlipperDialog
from .Indices_dialog import NDVIDialog, NDWIDialog, EVI2Dialog, EVIDialog

import os

class EDACToolsDialog(QDialog):
    """ 
    This class creates the main dialog for the EDACTools plugin
    """
    def __init__(self, parent=None):
        """
        Initialize the dialog
        """
        super().__init__(parent)
        
        if self.CheckDependencies():
            self.ui = Ui_EDACToolsDialog()
            self.ui.setupUi(self)
            self.plugin_dir = os.path.dirname(__file__)
            self.fishbone_dialog = None  # Keep a reference to the Fishbone dialog instance
            self.street_parity_dialog = None  # Keep a reference to the Street Parity dialog instance
            self.flipper_dialog = None  # Keep a reference to the Flipper dialog instance
            self.ndvi_dialog = None
            self.ndwi_dialog = None
            self.evi_dialog = None
            self.evi2_dialog = None
            self.init_tree()
        else:
            self.reject()

    def CheckDependencies(self):
        # Check if the required plugins geopandas and shapley are installed
        try:
            import geopandas
            import shapely
            return True
        except ImportError:
            QMessageBox.critical(None, "Error", "The EDACTools plugin requires the geopandas and shapely libraries. Please install them and restart QGIS.")
            return False

    def init_tree(self):
        """
        Initialize the tree widget with the tools available in the plugin
        """
        self.ui.treeWidget.clear()

        # Create a parent item for Vector Tools
        vector_tools_item = QTreeWidgetItem(self.ui.treeWidget)
        vector_tools_item.setText(0, "Vector Tools")

        # Add child items under Vector Tools
        fishbone_item = QTreeWidgetItem(vector_tools_item)
        fishbone_item.setText(0, "Fishbone")
        #set the icon for the fishbone item
        fishbone_icon_path = os.path.join(self.plugin_dir, "icons", "fishbone.png")
        fishbone_item.setIcon(0, QIcon(fishbone_icon_path))

        street_parity_item = QTreeWidgetItem(vector_tools_item)
        street_parity_item.setText(0, "Street Parity")
        street_parity_icon_path = os.path.join(self.plugin_dir, "icons", "parity.png")
        street_parity_item.setIcon(0, QIcon(street_parity_icon_path))

        # Create a parent item for Raster Tools
        raster_tools_item = QTreeWidgetItem(self.ui.treeWidget)
        raster_tools_item.setText(0, "Raster Tools")

        # Add child items under Raster Tools
        flipper_item = QTreeWidgetItem(raster_tools_item)
        flipper_item.setText(0, "Flipper")
        flipper_icon_path = os.path.join(self.plugin_dir, "icons", "flipper.png")
        flipper_item.setIcon(0, QIcon(flipper_icon_path))

        #indices sub menu
        indices_item = QTreeWidgetItem(raster_tools_item)
        indices_item.setText(0, "Quick Index")
        #add item under indices
        ndvi_item = QTreeWidgetItem(indices_item)
        ndvi_item.setText(0, "NDVI")
        #add icon to the ndvi item
        ndvi_icon_path = os.path.join(self.plugin_dir, "icons", "index.png")
        ndvi_item.setIcon(0, QIcon(ndvi_icon_path))

        ndwi_item = QTreeWidgetItem(indices_item)
        ndwi_item.setText(0, "NDWI")
        ndwi_icon_path = os.path.join(self.plugin_dir, "icons", "index.png")
        ndwi_item.setIcon(0, QIcon(ndwi_icon_path))

        evi_item = QTreeWidgetItem(indices_item)
        evi_item.setText(0, "EVI")
        evi_icon_path = os.path.join(self.plugin_dir, "icons", "index.png")
        evi_item.setIcon(0, QIcon(evi_icon_path))

        evi2_item = QTreeWidgetItem(indices_item)
        evi2_item.setText(0, "EVI2")
        evi2_icon_path = os.path.join(self.plugin_dir, "icons", "index.png")
        evi2_item.setIcon(0, QIcon(evi2_icon_path))






        self.ui.treeWidget.itemDoubleClicked.connect(self.open_tool)

    def open_tool(self, item, column):
        if item.text(0) == "Fishbone":
            if not self.fishbone_dialog:
                self.fishbone_dialog = FishboneDialog(self)
                self.fishbone_dialog.setWindowFlags(self.fishbone_dialog.windowFlags() | Qt.WindowStaysOnTopHint)
            self.fishbone_dialog.show()  # Use show() to make the dialog modeless
        elif item.text(0) == "Street Parity":
            if not self.street_parity_dialog:
                self.street_parity_dialog = StreetParityDialog(self)
                self.street_parity_dialog.setWindowFlags(self.street_parity_dialog.windowFlags() | Qt.WindowStaysOnTopHint)
            self.street_parity_dialog.show()  # Use show() to make the dialog modeless
        elif item.text(0) == "Flipper":
            if not self.flipper_dialog:
                self.flipper_dialog = FlipperDialog(self)
                self.flipper_dialog.setWindowFlags(self.flipper_dialog.windowFlags() | Qt.WindowStaysOnTopHint)
            self.flipper_dialog.show()  # Use show() to make the dialog modeless
        elif item.text(0) == "NDVI":
            if not self.ndvi_dialog:
                self.ndvi_dialog = NDVIDialog(self)
                self.ndvi_dialog.setWindowFlags(self.ndvi_dialog.windowFlags() | Qt.WindowStaysOnTopHint)
            self.ndvi_dialog.show()
        elif item.text(0) == "NDWI":
            if not self.ndwi_dialog:
                self.ndwi_dialog = NDWIDialog(self)
                self.ndwi_dialog.setWindowFlags(self.ndwi_dialog.windowFlags() | Qt.WindowStaysOnTopHint)
            self.ndwi_dialog.show()
        elif item.text(0) == "EVI":
            if not self.evi_dialog:
                self.evi_dialog = EVIDialog(self)
                self.evi_dialog.setWindowFlags(self.evi_dialog.windowFlags() | Qt.WindowStaysOnTopHint)
            self.evi_dialog.show()
        elif item.text(0) == "EVI2":
            if not self.evi2_dialog:
                self.evi2_dialog = EVI2Dialog(self)
                self.evi2_dialog.setWindowFlags(self.evi2_dialog.windowFlags() | Qt.WindowStaysOnTopHint)
            self.evi2_dialog.show()