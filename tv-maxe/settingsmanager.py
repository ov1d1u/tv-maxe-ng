from PyQt5.QtCore import QSettings

DEFAULT_SUBSCRIPTIONS = [
    [True, "http://tv-maxe.org/subscriptions/v2/Romania.db"],
    [True, "http://tv-maxe.org/subscriptions/v2/International.db"]
]

class SettingsManager(QSettings):
    def __init__(self):
        super().__init__()

    def get_subscriptions(self):
        return self.value("subscriptions", DEFAULT_SUBSCRIPTIONS)