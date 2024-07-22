from PyQt5.QtCore import QObject
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QMessageBox
from qgis.core import QgsProject
from qgis.gui import QgsMessageBar
import os
from .EDACTools_dialog import EDACToolsDialog

class EDACTools:
    def __init__(self, iface):
        self.iface = iface  # Save reference to the QGIS interface
        self.plugin_dir = os.path.dirname(__file__)  # Set the path to the plugin directory
        self.action = None  # Initialize the action variable
        self.menu_added = False  # Initialize a flag to track if the menu is added
        self.dialog = None  # Keep a reference to the dialog instance
        self.initGui()  # Call the initGui method (below) to create the menu item and toolbar button

    def initGui(self):
        """
        Create the menu item and toolbar button
        """
        # Check if the action already exists to avoid duplication
        if not self.action:
            toolbox_icon_path = os.path.join(self.plugin_dir, "icons", "toolbox.png")  # Path to the plugin icon
            self.action = QAction(QIcon(toolbox_icon_path), "EDAC Tools", self.iface.mainWindow())  # Create the action
            self.action.triggered.connect(self.run)  # Connect the action to the run method (below)
        
        # Check if the menu has already been added to avoid duplication
        if not self.menu_added:
            self.iface.addPluginToMenu("&EDAC Tools", self.action)  # Add to the menu
            self.iface.addToolBarIcon(self.action)  # Add to the toolbar if desired
            self.menu_added = True  # Set the flag to True

    def run(self):
        """
        Run method that creates and shows the dialog
        """
        if not self.dialog:
            self.dialog = EDACToolsDialog(self.iface.mainWindow())
        self.dialog.show()  # Use show() to make the dialog modeless

    def unload(self):
        """
        Remove the menu item and toolbar button
        """
        if self.action:
            self.iface.removePluginMenu("&EDAC Tools", self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None  # Reset the action variable
            self.menu_added = False  # Reset the menu_added flag
        if self.dialog:
            self.dialog.close()  # Close the dialog if it's open
            self.dialog = None  # Reset the dialog reference
