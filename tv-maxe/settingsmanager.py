from PyQt5.QtCore import QSettings

class SettingsManager(QSettings):
    def __init__(self):
        super().__init__()

