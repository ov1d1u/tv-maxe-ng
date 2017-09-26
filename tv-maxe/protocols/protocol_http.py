from protocols import Protocol

class HTTP(Protocol):
    name = "HTTP Protocol"
    desc = "HTTP Protocol Backend for TV-Maxe"
    version = "0.01"
    protocols = ["http", "https"]

    def __init__(self):
        super().__init__()

    def load_url(self, url):
        self.protocol_ready.emit(url)

    def stop(self):
        pass


__classname__ = HTTP