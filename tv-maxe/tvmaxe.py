#!/usr/bin/env python3
import sys
import os
from os.path import isfile, join, splitext
from importlib import import_module
from PyQt5 import QtCore, QtWidgets, uic
from PyQt5.QtGui import QIcon, QPixmap

from settingsmanager import SettingsManager
from mainwindow import TVMaxeMainWindow

class TVMaxe(QtWidgets.QApplication):
    protocol_plugins = {}

    def __init__(self, argv):
        super(QtWidgets.QApplication, self).__init__(argv)

        self.setApplicationName("TV-Maxe")
        self.setOrganizationName("Ovidiu Nitan")

        self.settings_manager = SettingsManager(self.organizationName(), self.applicationName())

        self.init_plugins()

        translator = QtCore.QTranslator()
        translator.load("i18n/{0}.qm".format(QtCore.QLocale.system().name()))
        self.installTranslator(translator)
        self.mainw = TVMaxeMainWindow(None)
        self.mainw.show()

    def init_plugins(self):
        protocols_dir = 'protocols'
        sys.path.insert(0, 'protocols/')

        protocol_modules = [f for f in os.listdir(protocols_dir) if isfile(join(protocols_dir, f))]
        for filename in protocol_modules:
            if filename == '__init__.py' or filename == '__init__.pyc':
                continue
            file, extension = splitext(filename)
            if extension == '.py':
                protocol_module = import_module(file)
                protocol_class = protocol_module.__classname__
                for protocol in protocol_class.protocols:
                    self.protocol_plugins[protocol] = protocol_class

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    app = TVMaxe(sys.argv)
    sys.exit(app.exec_())