from PyQt5.QtWidgets import QListWidget, QMenu
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor
from channelitem import ChannelItem

from channellistmanager import ChannelListManager
from txicon import TXIcon

class ChannelListWidget(QListWidget):
    _show_deleted = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def show_deleted(self):
        return self._show_deleted

    @show_deleted.setter
    def show_deleted(self, show_deleted):
        self._show_deleted = show_deleted
        for item in self.iterAllItems():
            if item.channel.deleted:
                self.processDeletedChannelItem(item)

    def addChannel(self, channel):
        if len(channel.streamurls) != 0:
            existing_item = self.channelItemForChannel(channel)
            if not existing_item:
                channel_item = ChannelItem()
                channel_item.channel = channel
                self.addItem(channel_item)
                if channel.deleted:
                    self.processDeletedChannelItem(channel_item)
                
    def showChannelList(self, chlist):
        for channel_item in self.iterAllItems():
            if channel_item.channel.origin == chlist.origin_url:
                if channel_item.channel.deleted:
                    self.processDeletedChannelItem(channel_item)
                else:
                    channel_item.setHidden(False)
            else:
                channel_item.setHidden(True)

    def showAllChannelLists(self):
        for channel_item in self.iterAllItems():
            if not channel_item.channel.deleted:
                self.processDeletedChannelItem(channel_item)

    def channelItemForChannel(self, channel):
        for channel_item in self.iterAllItems():
            if channel_item.channel == channel:
                return channel_item
        return None

    def channelExists(self, channel):
        for channelitem in self.iterAllItems():
            if channelitem.channel == channel:
                return True
        return False

    def iterAllItems(self):
        for i in range(self.count()):
            yield self.item(i)

    def deleteChannel(self, channel):
        if not ChannelListManager.user_channellist:
            ChannelListManager().load_user_chlist()

        channel.deleted = True
        ChannelListManager.user_channellist.save_channel(channel)
        self.processDeletedChannelItem(self.channelItemForChannel(channel))

    def undeleteChannel(self, channel):
        if not ChannelListManager.user_channellist:
            ChannelListManager().load_user_chlist()

        # Don't worry, this just remove our copy of the channel from user db
        ChannelListManager.user_channellist.remove_channel(channel)
        channel.deleted = False
        self.processDeletedChannelItem(self.channelItemForChannel(channel))

    def processDeletedChannelItem(self, channel_item):
        if channel_item.channel.deleted:
            if self.show_deleted:
                channel_item.setHidden(False)
                brush = channel_item.foreground()
                color = brush.color()
                color.setRed(255)
                brush.setColor(color)
                channel_item.setForeground(brush)
            else:
                channel_item.setHidden(True)
        else:
            brush = ChannelItem().foreground()
            channel_item.setForeground(brush)

    # Events

    def contextMenuEvent(self, event):
        current_item = self.currentItem()

        menu = QMenu(self)
        play_action = menu.addAction(TXIcon('icons/play-button.svg'), self.tr("Play"))
        record_action = menu.addAction(TXIcon('icons/record-button.svg'), self.tr("Record"))
        menu.addSeparator()
        info_action = menu.addAction(TXIcon('icons/information.svg'), self.tr("Channel info"))
        epg_action = menu.addAction(TXIcon('icons/calendar-icon.svg'), self.tr("EPG"))
        menu.addSeparator()
        delete_action = undelete_action = None
        if current_item.channel.deleted:
            undelete_action = menu.addAction(TXIcon('icons/untrash.svg'), self.tr("Undelete channel"))
        else:
            delete_action = menu.addAction(TXIcon('icons/trash.svg'), self.tr("Delete channel"))
        action = menu.exec_(self.mapToGlobal(event.pos()))

        if action == play_action:
            self.itemActivated.emit(current_item)
        elif action == delete_action:
            self.deleteChannel(current_item.channel)
        elif action == undelete_action:
            self.undeleteChannel(current_item.channel)
