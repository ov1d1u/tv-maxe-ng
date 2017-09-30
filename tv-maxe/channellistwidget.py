from PyQt5 import QtWidgets
from channelitem import ChannelItem

class ChannelListWidget(QtWidgets.QListWidget):
    def addChannel(self, channel):
        channel_item = ChannelItem()
        channel_item.channel = channel
        if len(channel_item.channel.streamurls) != 0:
            self.addItem(channel_item)

    def showChannelList(self, chlist):
        for channel_item in self.iterAllItems():
            if channel_item.channel.origin == chlist.origin_url:
                channel_item.setHidden(False)
            else:
                channel_item.setHidden(True)

    def showAllChannelLists(self):
        for channel_item in self.iterAllItems():
            channel_item.setHidden(False)

    def iterAllItems(self):
        for i in range(self.count()):
            yield self.item(i)