#!/usr/bin/env python3
import sys
import os
import logger
import logging
import argparse
from os.path import isfile, join, splitext
from importlib import import_module
from PyQt5 import QtCore, QtWidgets, uic
from PyQt5.QtGui import QIcon, QPixmap

from settingsmanager import SettingsManager
from mainwindow import TVMaxeMainWindow

log = logging.getLogger(__name__)

class TVMaxe(QtWidgets.QApplication):
    protocol_plugins = {}

    def __init__(self, argv):
        super(QtWidgets.QApplication, self).__init__(argv)

        self.setApplicationName("TV-Maxe")
        self.setApplicationVersion("0.1a")
        self.setOrganizationDomain("org.tv-maxe.app")
        self.setOrganizationName("TV-Maxe")

        log.info('{0} {1}'.format(self.applicationName(), self.applicationVersion()))

        self.settings_manager = SettingsManager()

        self.init_plugins()

        log.debug('Current localization: {0}'.format(QtCore.QLocale.system().name()))
        translator = QtCore.QTranslator()
        translator.load("i18n/{0}.qm".format(QtCore.QLocale.system().name()))
        self.installTranslator(translator)
        self.mainw = TVMaxeMainWindow(None)
        self.mainw.show()

    def init_plugins(self):
        log.debug('Initializing plugins:')
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
                log.debug('- Plugin found: {0} {1} ({2})'.format(
                    protocol_module.__classname__.name,
                    protocol_module.__classname__.version, 
                    protocol_module.__classname__)
                )
                for protocol in protocol_class.protocols:
                    self.protocol_plugins[protocol] = protocol_class


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--log-level",
        help="Sets the logger verbosity",
        choices=["debug", "warn", "info"]
    )
    args = parser.parse_args()

    if args.log_level:
        if args.log_level == 'debug':
            logger.set_logging_level(logging.DEBUG)
        elif args.log_level == 'warn':
            logger.set_logging_level(logging.WARNING)
        else:
            logger.set_logging_level(logging.INFO)
    else:
        logger.set_logging_level(logging.INFO)

if __name__ == '__main__':
    parse_args()
    if getattr(sys, 'frozen', False):
        os.chdir(sys._MEIPASS)
    else:
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
    log.debug('Current working directory: {0}'.format(os.getcwd()))
    app = TVMaxe(sys.argv)
    sys.exit(app.exec_())
    log.debug('Exiting app...')