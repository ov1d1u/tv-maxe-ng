from urllib.parse import urlparse
from PyQt5.QtWidgets import QApplication, QListWidgetItem
from PyQt5.QtGui import QIcon, QImage, QPixmap

class ChannelItem(QListWidgetItem):
    __channel = None

    @property
    def channel(self):
        return self.__channel

    @channel.setter
    def channel(self, channel):
        self.__channel = channel
        image = QImage()
        image.loadFromData(channel.icon)
        self.setText(channel.name)
        self.setIcon(QIcon(QPixmap.fromImage(image)))

        protocol_plugins = QApplication.instance().protocol_plugins
        for idx, streamurl in enumerate(channel.streamurls):
            url_comps = urlparse(streamurl)
            schema = url_comps.scheme
            if not protocol_plugins.get(schema, None):
                channel.streamurls.pop(idx)
