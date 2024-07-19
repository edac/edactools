# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Flipper_dialog_base.ui'
#
# Created by: PyQt5 UI code generator 5.15.6
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_FlipperDialog(object):
    def setupUi(self, FlipperDialog):
        FlipperDialog.setObjectName("FlipperDialog")
        FlipperDialog.resize(454, 232)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(FlipperDialog.sizePolicy().hasHeightForWidth())
        FlipperDialog.setSizePolicy(sizePolicy)
        self.tabWidget = QtWidgets.QTabWidget(FlipperDialog)
        self.tabWidget.setGeometry(QtCore.QRect(10, 10, 431, 211))
        self.tabWidget.setObjectName("tabWidget")
        self.Tool = QtWidgets.QWidget()
        self.Tool.setObjectName("Tool")
        self.band_slider = QtWidgets.QSlider(self.Tool)
        self.band_slider.setGeometry(QtCore.QRect(30, 140, 371, 20))
        self.band_slider.setOrientation(QtCore.Qt.Horizontal)
        self.band_slider.setObjectName("band_slider")
        self.FlipperRastercomboBox = QtWidgets.QComboBox(self.Tool)
        self.FlipperRastercomboBox.setGeometry(QtCore.QRect(2, 10, 421, 25))
        self.FlipperRastercomboBox.setObjectName("FlipperRastercomboBox")
        self.next_button = QtWidgets.QPushButton(self.Tool)
        self.next_button.setGeometry(QtCore.QRect(320, 100, 89, 25))
        self.next_button.setText("")
        self.next_button.setObjectName("next_button")
        self.max_spinbox = QtWidgets.QDoubleSpinBox(self.Tool)
        self.max_spinbox.setGeometry(QtCore.QRect(244, 60, 101, 26))
        self.max_spinbox.setProperty("value", 1.0)
        self.max_spinbox.setObjectName("max_spinbox")
        self.play_button = QtWidgets.QPushButton(self.Tool)
        self.play_button.setGeometry(QtCore.QRect(120, 100, 89, 25))
        self.play_button.setText("")
        self.play_button.setObjectName("play_button")
        self.band_label = QtWidgets.QLabel(self.Tool)
        self.band_label.setGeometry(QtCore.QRect(181, 40, 71, 16))
        self.band_label.setObjectName("band_label")
        self.min_spinbox = QtWidgets.QDoubleSpinBox(self.Tool)
        self.min_spinbox.setGeometry(QtCore.QRect(70, 60, 101, 26))
        self.min_spinbox.setObjectName("min_spinbox")
        self.min_spinbox.setMinimum(-99.99)
        self.prev_button = QtWidgets.QPushButton(self.Tool)
        self.prev_button.setGeometry(QtCore.QRect(20, 100, 89, 25))
        self.prev_button.setText("")
        self.prev_button.setObjectName("prev_button")
        self.stop_button = QtWidgets.QPushButton(self.Tool)
        self.stop_button.setGeometry(QtCore.QRect(220, 100, 89, 25))
        self.stop_button.setText("")
        self.stop_button.setObjectName("stop_button")
        self.band_slider.raise_()
        self.next_button.raise_()
        self.max_spinbox.raise_()
        self.play_button.raise_()
        self.band_label.raise_()
        self.min_spinbox.raise_()
        self.prev_button.raise_()
        self.stop_button.raise_()
        self.FlipperRastercomboBox.raise_()
        self.tabWidget.addTab(self.Tool, "")
        self.Help = QtWidgets.QWidget()
        self.Help.setObjectName("Help")
        self.label = QtWidgets.QLabel(self.Help)
        self.label.setGeometry(QtCore.QRect(10, 10, 411, 111))
        self.label.setWordWrap(True)
        self.label.setObjectName("label")
        self.tabWidget.addTab(self.Help, "")

        self.retranslateUi(FlipperDialog)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(FlipperDialog)

    def retranslateUi(self, FlipperDialog):
        _translate = QtCore.QCoreApplication.translate
        FlipperDialog.setWindowTitle(_translate("FlipperDialog", "Dialog"))
        self.max_spinbox.setPrefix(_translate("FlipperDialog", "Max: "))
        self.band_label.setText(_translate("FlipperDialog", "Band: 1"))
        self.min_spinbox.setPrefix(_translate("FlipperDialog", "Min: "))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.Tool), _translate("FlipperDialog", "Tool"))
        self.label.setText(_translate("FlipperDialog", "The FlipperDialog tool is a QGIS plugin that enables users to cycle through and visualize different bands of a 3D raster layer. Users can manually navigate bands, automate cycling with play/stop controls, and adjust contrast settings for optimal viewing. This tool simplifies the analysis of multi-band raster datasets directly within QGIS."))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.Help), _translate("FlipperDialog", "Help"))
