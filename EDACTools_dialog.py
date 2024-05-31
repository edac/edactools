from PyQt5.QtWidgets import QDialog, QTreeWidgetItem, QMessageBox
from PyQt5.QtGui import QIcon
from .EDACTools_dialog_base import Ui_EDACToolsDialog
from .Fishbone_dialog import FishboneDialog
from .StreetParity_dialog import StreetParityDialog
from .Flipper_dialog import FlipperDialog

import os

class EDACToolsDialog(QDialog):
    """ 
    This class creates the main dialog for the EDACTools plugin
    """
    def __init__(self):
        """
        Initialize the dialog
        """
        
        super().__init__()
        if self.CheckDependencies():
            self.ui = Ui_EDACToolsDialog()
            self.ui.setupUi(self)
            self.plugin_dir = os.path.dirname(__file__)
            self.fishbone_dialog = None  # Keep a reference to the Fishbone dialog instance
            self.street_parity_dialog = None  # Keep a reference to the Street Parity dialog instance
            self.flipper_dialog = None  # Keep a reference to the Flipper dialog instance
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

        self.ui.treeWidget.itemDoubleClicked.connect(self.open_tool)

    def open_tool(self, item, column):
        if item.text(0) == "Fishbone":
            if not self.fishbone_dialog:
                self.fishbone_dialog = FishboneDialog()
            self.fishbone_dialog.show()  # Use show() to make the dialog modeless
        elif item.text(0) == "Street Parity":
            if not self.street_parity_dialog:
                self.street_parity_dialog = StreetParityDialog()
            self.street_parity_dialog.show()  # Use show() to make the dialog modeless
        elif item.text(0) == "Flipper":
            if not self.flipper_dialog:
                self.flipper_dialog = FlipperDialog()
            self.flipper_dialog.show()  # Use show() to make the dialog modeless
