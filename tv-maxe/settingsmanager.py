from PyQt5.QtCore import QSettings

class SettingsManager(QSettings):
    def __init__(self, organization, application='', parent=None):
        super().__init__(organization, application, parent)

