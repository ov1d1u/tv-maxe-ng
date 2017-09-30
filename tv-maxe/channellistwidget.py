from PyQt5.QtWidgets import QListWidget, QMenu
from PyQt5.QtCore import Qt, pyqtSignal
from channelitem import ChannelItem

from txicon import TXIcon

class ChannelListWidget(QListWidget):
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

    # Events

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        play_action = menu.addAction(TXIcon('icons/play-button.svg'), self.tr("Play"))
        record_action = menu.addAction(TXIcon('icons/record-button.svg'), self.tr("Record"))
        menu.addSeparator()
        info_action = menu.addAction(TXIcon('icons/information.svg'), self.tr("Channel info"))
        epg_action = menu.addAction(TXIcon('icons/calendar-icon.svg'), self.tr("EPG"))
        menu.addSeparator()
        delete_action = menu.addAction(TXIcon('icons/empty-container.svg'), self.tr("Remove channel"))
        action = menu.exec_(self.mapToGlobal(event.pos()))
        if action == play_action:
            self.itemActivated.emit(self.currentItem())
