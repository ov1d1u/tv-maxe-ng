import logging
from PyQt5.QtCore import QSettings

DEFAULT_SUBSCRIPTIONS = [
    [True, "http://tv-maxe.org/subscriptions/v2/Romania.db"],
    [True, "http://tv-maxe.org/subscriptions/v2/International.db"]
]

log = logging.getLogger(__name__)

class SettingsManager(QSettings):
    def __init__(self):
        super().__init__()
        log.debug("Loaded configuration from {0}".format(self.fileName()))

    def get_subscriptions(self):
        return self.value("subscriptions", DEFAULT_SUBSCRIPTIONS)