from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import pyqtSignal, QObject

class Protocol(QObject):
    name = "Generic Protocol"
    desc = "Generic Protocol Backend for TV-Maxe"
    version = "0.01"
    protocols = [""]

    protocol_ready = pyqtSignal(str)
    protocol_error = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.app = QApplication.instance()

    def load_url(self, url, args=None):
        pass

    def stop(self):
        pass


__classname__ = Protocol