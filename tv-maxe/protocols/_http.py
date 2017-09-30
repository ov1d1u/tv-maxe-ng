from protocols import Protocol
import logging

log = logging.getLogger(__name__)

class HTTP(Protocol):
    name = "HTTP Protocol"
    desc = "HTTP Protocol Backend for TV-Maxe"
    version = "0.01"
    protocols = ["http", "https"]

    def __init__(self, parent=None):
        super().__init__(parent)

    def load_url(self, url, args=None):
        self.protocol_ready.emit(url)

    def stop(self):
        self.deleteLater()


__classname__ = HTTP