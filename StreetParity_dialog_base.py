# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'StreetParity_dialog_base.ui'
#
# Created by: PyQt5 UI code generator 5.15.6
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_StreetParityDialog(object):
    def setupUi(self, StreetParityDialog):
        StreetParityDialog.setObjectName("StreetParityDialog")
        StreetParityDialog.resize(445, 335)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(StreetParityDialog.sizePolicy().hasHeightForWidth())
        StreetParityDialog.setSizePolicy(sizePolicy)
        self.buttonBox = QtWidgets.QDialogButtonBox(StreetParityDialog)
        self.buttonBox.setGeometry(QtCore.QRect(140, 280, 171, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.StreetLayerComboBox = QtWidgets.QComboBox(StreetParityDialog)
        self.StreetLayerComboBox.setGeometry(QtCore.QRect(160, 30, 221, 25))
        self.StreetLayerComboBox.setObjectName("StreetLayerComboBox")
        self.StreetLayerStreetFieldComboBox = QtWidgets.QComboBox(StreetParityDialog)
        self.StreetLayerStreetFieldComboBox.setGeometry(QtCore.QRect(240, 80, 141, 25))
        self.StreetLayerStreetFieldComboBox.setObjectName("StreetLayerStreetFieldComboBox")
        self.label = QtWidgets.QLabel(StreetParityDialog)
        self.label.setGeometry(QtCore.QRect(70, 30, 91, 17))
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(StreetParityDialog)
        self.label_2.setGeometry(QtCore.QRect(140, 80, 81, 20))
        self.label_2.setObjectName("label_2")
        self.AddressLayerStreetFieldComboBox = QtWidgets.QComboBox(StreetParityDialog)
        self.AddressLayerStreetFieldComboBox.setGeometry(QtCore.QRect(240, 190, 141, 25))
        self.AddressLayerStreetFieldComboBox.setObjectName("AddressLayerStreetFieldComboBox")
        self.AddressLayerComboBox = QtWidgets.QComboBox(StreetParityDialog)
        self.AddressLayerComboBox.setGeometry(QtCore.QRect(160, 140, 221, 25))
        self.AddressLayerComboBox.setObjectName("AddressLayerComboBox")
        self.label_3 = QtWidgets.QLabel(StreetParityDialog)
        self.label_3.setGeometry(QtCore.QRect(140, 190, 101, 20))
        self.label_3.setObjectName("label_3")
        self.label_4 = QtWidgets.QLabel(StreetParityDialog)
        self.label_4.setGeometry(QtCore.QRect(50, 140, 101, 17))
        self.label_4.setObjectName("label_4")
        self.AddressLayerAddressNumberFieldComboBox = QtWidgets.QComboBox(StreetParityDialog)
        self.AddressLayerAddressNumberFieldComboBox.setGeometry(QtCore.QRect(240, 230, 141, 25))
        self.AddressLayerAddressNumberFieldComboBox.setObjectName("AddressLayerAddressNumberFieldComboBox")
        self.label_5 = QtWidgets.QLabel(StreetParityDialog)
        self.label_5.setGeometry(QtCore.QRect(70, 230, 161, 20))
        self.label_5.setObjectName("label_5")

        self.retranslateUi(StreetParityDialog)
        self.buttonBox.accepted.connect(StreetParityDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(StreetParityDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(StreetParityDialog)

    def retranslateUi(self, StreetParityDialog):
        _translate = QtCore.QCoreApplication.translate
        StreetParityDialog.setWindowTitle(_translate("StreetParityDialog", "Dialog"))
        self.label.setText(_translate("StreetParityDialog", "Street Layer"))
        self.label_2.setText(_translate("StreetParityDialog", "Street Field"))
        self.label_3.setText(_translate("StreetParityDialog", "Street Field"))
        self.label_4.setText(_translate("StreetParityDialog", "Address Layer"))
        self.label_5.setText(_translate("StreetParityDialog", "Address Number Field"))
