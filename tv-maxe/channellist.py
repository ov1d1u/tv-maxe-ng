from PyQt5 import QtWidgets
from channelitem import ChannelItem

class ChannelList(QtWidgets.QListWidget):
    def addChannel(self, channel):
        channel_item = ChannelItem()
        channel_item.channel = channel
        self.addItem(channel_item)

        if len(channel_item.channel.streamurls) == 0:
            channel_item.setHidden(True)