from PyQt5.QtWidgets import QListWidget, QMenu, QApplication
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor
from channelitem import ChannelItem

from models.channel import Channel
from channellistmanager import ChannelListManager
from channelinfo import ChannelInfoDialog
from epg import EPGDialog
from txicon import TXIcon

class ChannelListWidget(QListWidget):
    deleted_channels = QApplication.instance().settings_manager.value("channels/deleted", []) or []  # https://riverbankcomputing.com/pipermail/pyqt/2011-September/030480.html
    _show_deleted = False
    _chlist_filter = None
    channelActivated = pyqtSignal(Channel, int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        QApplication.instance().aboutToQuit.connect(self.aboutToQuit)
        self.itemActivated.connect(self.channelItemActivated)

    @property
    def show_deleted(self):
        return self._show_deleted

    @show_deleted.setter
    def show_deleted(self, show_deleted):
        self._show_deleted = show_deleted
        self.refresh()
    
    def refresh(self):
        for item in self.iterAllItems():
            self.setChannelItemVisibility(item)

    def addChannel(self, channel):
        if len(channel.streamurls) != 0:
            existing_item = self.channelItemForChannel(channel)
            if not existing_item:
                channel_item = ChannelItem(channel)
                self.addItem(channel_item)
                self.setChannelItemVisibility(channel_item)
            else:
                existing_item.channel = channel
                
    def showChannelList(self, chlist):
        self._chlist_filter = chlist
        self.refresh()

    def showAllChannelLists(self):
        self._chlist_filter = None
        self.refresh()

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
        ChannelListWidget.deleted_channels.append(channel.id)
        self.setChannelItemVisibility(self.channelItemForChannel(channel))

    def undeleteChannel(self, channel):
        ChannelListWidget.deleted_channels.remove(channel.id)
        channel_item = self.channelItemForChannel(channel)
        brush = ChannelItem(None).foreground()
        channel_item.setForeground(brush)
        channel_item.setHidden(False)
        self.setChannelItemVisibility(self.channelItemForChannel(channel))

    def showChannelInfo(self, channel):
        channel_info_dialog = ChannelInfoDialog(channel, self.window())
        channel_info_dialog.exec()

    def showChannelEPG(self, channel):
        channel_epg_dialog = EPGDialog(channel, self.window())
        channel_epg_dialog.exec()

    def setChannelItemVisibility(self, channel_item):
        if channel_item.channel.id in ChannelListWidget.deleted_channels:
            if self.show_deleted:
                if self._chlist_filter:
                    channel_item.setHidden(channel_item.channel.origin != self._chlist_filter.origin_url)
                else:
                    channel_item.setHidden(False)
                brush = channel_item.foreground()
                color = brush.color()
                color.setRed(255)
                brush.setColor(color)
                channel_item.setForeground(brush)
            else:
                channel_item.setHidden(True)
        else:
            if self._chlist_filter:
                channel_item.setHidden(channel_item.channel.origin != self._chlist_filter.origin_url)
            else:
                channel_item.setHidden(False)

    def channelItemActivated(self, channel_item):
        self.channelActivated.emit(channel_item.channel, 0)

    def aboutToQuit(self):
        QApplication.instance().settings_manager.setValue("channels/deleted", ChannelListWidget.deleted_channels)
        QApplication.instance().settings_manager.sync()

    # Events
    def contextMenuEvent(self, event):
        current_item = self.currentItem()
        play_menu_actions = []

        menu = QMenu(self)
        play_action = menu.addAction(TXIcon('icons/play-button.svg'), self.tr("Play"))
        if len(current_item.channel.streamurls) > 1:
            play_action.setVisible(False)
            play_menu = menu.addMenu(TXIcon('icons/play-button.svg'), self.tr("Play"))
            for streamurl in current_item.channel.streamurls:
                play_menu_actions.append(play_menu.addAction(streamurl))
        record_action = menu.addAction(TXIcon('icons/record-button.svg'), self.tr("Record"))
        menu.addSeparator()
        info_action = menu.addAction(TXIcon('icons/information.svg'), self.tr("Channel info"))
        epg_action = menu.addAction(TXIcon('icons/calendar-icon.svg'), self.tr("EPG"))
        menu.addSeparator()
        delete_action = menu.addAction(TXIcon('icons/trash.svg'), self.tr("Delete channel"))
        undelete_action = menu.addAction(TXIcon('icons/untrash.svg'), self.tr("Undelete channel"))
        if current_item.channel.id not in self.deleted_channels:
            undelete_action.setVisible(False)
        else:
            delete_action.setVisible(False)
        action = menu.exec_(self.mapToGlobal(event.pos()))

        if action in play_menu_actions:
            self.channelActivated.emit(current_item.channel, play_menu_actions.index(action))
        elif action == play_action:
            self.channelActivated.emit(current_item.channel, 0)
        elif action == delete_action:
            self.deleteChannel(current_item.channel)
        elif action == undelete_action:
            self.undeleteChannel(current_item.channel)
        elif action == info_action:
            self.showChannelInfo(current_item.channel)
        elif action == epg_action:
            self.showChannelEPG(current_item.channel)
