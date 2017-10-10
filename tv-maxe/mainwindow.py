import logging
import platform
from PyQt5 import uic
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QAction, QActionGroup,
    QMenu)

from channellistmanager import ChannelListManager
from settings import SettingsDialog
from addchanneldialog import AddChannelDialog
from txicon import TXIcon

log = logging.getLogger(__name__)

class TVMaxeMainWindow(QMainWindow):
    def __init__(self, parent):
        super(QMainWindow, self).__init__(parent)
        uic.loadUi('ui/mainWindow.ui', self)

        self.play_btn.clicked.connect(self.play_btn_clicked)
        self.stop_btn.clicked.connect(self.stop_btn_clicked)
        self.fullscreen_btn.clicked.connect(self.switch_fullscreen_mode)
        self.volume_slider.sliderMoved.connect(self.volume_changed)
        self.tv_channel_list.channelActivated.connect(self.activated_channel)
        self.radio_channel_list.channelActivated.connect(self.activated_channel)
        
        self.video_player.playback_started.connect(self.video_playback_started)
        self.video_player.playback_paused.connect(self.video_playback_paused)
        self.video_player.playback_stopped.connect(self.video_playback_stopped)
        self.video_player.playback_error.connect(self.video_playback_error)
        self.video_player.volume_changed.connect(self.video_volume_changed)

        self.chlist_manager = ChannelListManager()
        self.chlist_manager.channel_added.connect(self.channel_added)
        self.chlist_manager.channellist_available.connect(self.channel_list_available)

        self.statusbar.addPermanentWidget(self.bottom_bar, 1)
        self.splitter.setStretchFactor(1, 1)
        self.progress_bar.hide()
        self.progress_label.setText(self.tr("Idle"))
        self.video_player.set_volume(self.volume_slider.value())

        self.channellist_show_actiongroup = QActionGroup(self)
        self.channellist_show_actiongroup.triggered.connect(self.show_channel_list)
        chlist_showall_action = QAction(self.tr("All"), self.menu_show_chlist)
        chlist_showall_action.setCheckable(True)
        chlist_showall_action.setChecked(True)
        chlist_showall_action.setActionGroup(self.channellist_show_actiongroup)
        self.menu_show_chlist.addAction(chlist_showall_action)

        os_type = platform.system()
        log.info('Detected OS type: {0}'.format(os_type))
        if os_type == 'Darwin':
            self.playlist_tab_widget.setDocumentMode(True)

        self.load_settings()

        # Set custom icons
        self.play_btn.setIcon(TXIcon('icons/play-button.svg'))
        self.stop_btn.setIcon(TXIcon('icons/stop-button.svg'))
        self.fullscreen_btn.setIcon(TXIcon('icons/fullscreen.svg'))

    def load_settings(self):
        log.debug('Loading settings...')
        app = QApplication.instance()
        settings = app.settings_manager
        try:
            self.restoreGeometry(settings.value("geometry"))
            self.restoreState(settings.value("windowState"))
        except TypeError:
            pass  # do nothing for now

        self.splitter.setSizes(settings.value("splitterSizes", [242, self.width()-242], int))
        self.video_player.set_volume(int(settings.value("player/volume", 50)))
        self.action_hide_channellist.setChecked(settings.value("hideChannelList", False, bool))

        self.chlist_manager.download_chlists(settings.get_subscriptions())

        log.debug('Settings loaded')

    def play_btn_clicked(self, checked=False):
        from videoplayer import VideoPlayerState
        player_state = self.video_player.get_state()
        if player_state is VideoPlayerState.PLAYER_PLAYING:
            self.video_player.pause()
        else:
            self.video_player.unpause()

    def stop_btn_clicked(self, checked=False):
        self.video_player.stop()

    def volume_changed(self, level):
        self.video_player.volume_changed.disconnect(self.video_volume_changed)
        self.video_player.set_volume(level)
        self.video_player.volume_changed.connect(self.video_volume_changed)

    def switch_fullscreen_mode(self, checked=False):
        self.video_player.switch_fullscreen()

    def activated_channel(self, channel, play_index):
        self.play_channel(channel, play_index)

    def channel_list_available(self, chlist):
        if len(self.menu_show_chlist.actions()) == 1:
            self.menu_show_chlist.addSeparator()

        for action in self.menu_show_chlist.actions():
            if isinstance(action, ChannelListShowAction):
                if action.channel_list == chlist:
                    return  # We already have this channel list in menu

        chlist_action = ChannelListShowAction(self.menu_show_chlist, chlist)
        chlist_action.setActionGroup(self.channellist_show_actiongroup)
        self.menu_show_chlist.addAction(chlist_action)

    def show_channel_list(self):
        action = self.channellist_show_actiongroup.checkedAction()
        if isinstance(action, ChannelListShowAction):
            self.tv_channel_list.showChannelList(action.channel_list)
            self.radio_channel_list.showChannelList(action.channel_list)
        else:
            self.tv_channel_list.showAllChannelLists()
            self.radio_channel_list.showAllChannelLists()

    def channel_added(self, channel):
        if channel.type == 'tv':
            self.tv_channel_list.addChannel(channel)
        elif channel.type == 'radio':
            self.radio_channel_list.addChannel(channel)

    def play_channel(self, channel, play_index=0):
        self.video_player.stop()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)
        self.progress_bar.show()
        self.progress_label.setText(
            self.tr("Now loading: {0} ({1})".format(channel.name, channel.streamurls[play_index]))
        )
        self.video_player.play_channel(channel, play_index)

    def video_playback_started(self, channel):
        self.play_btn.setIcon(TXIcon('icons/pause-button.svg'))
        self.progress_bar.hide()
        self.progress_bar.setMaximum(1)
        self.progress_label.setText(self.tr("Now playing: {0}".format(channel.name)))

    def video_playback_paused(self, channel):
        self.play_btn.setIcon(TXIcon('icons/play-button.svg'))

    def video_playback_stopped(self, channel):
        self.play_btn.setIcon(TXIcon('icons/play-button.svg'))
        self.progress_label.setText(self.tr("Idle"))
        self.progress_bar.hide()
        self.progress_bar.setMaximum(1)

    def video_playback_error(self, channel):
        if channel.play_index + 1 < len(channel.streamurls):
            self.progress_bar.setMinimum(0)
            self.progress_bar.setMaximum(0)
            self.progress_bar.show()
            self.progress_label.setText(
                self.tr("Retrying: {0} ({1})".format(
                    channel.name, channel.streamurls[channel.play_index + 1]
                    ))
            )
            self.video_player.play_channel(channel, channel.play_index + 1)
        else:
            self.play_btn.setIcon(TXIcon('icons/play-button.svg'))
            self.progress_label.setText(self.tr("Channel not available: {0}".format(channel.name)))
            self.progress_bar.hide()
            self.progress_bar.setMaximum(1)

    def video_volume_changed(self, value):
        self.volume_slider.setValue(int(value))

    @pyqtSlot()
    def reloadChannelList(self):
        self.tv_channel_list.clear()
        self.radio_channel_list.clear()
        subscriptions = QApplication.instance().settings_manager.get_subscriptions()
        self.chlist_manager.clear_cached_chlists(subscriptions)
        self.chlist_manager.download_chlists(subscriptions)

    @pyqtSlot()
    def showDeletedChannels(self):
        if self.action_show_deleted.isChecked():
            self.tv_channel_list.show_deleted = True
            self.radio_channel_list.show_deleted = True
        else:
            self.tv_channel_list.show_deleted = False
            self.radio_channel_list.show_deleted = False

    @pyqtSlot(bool)
    def hideShowChannelList(self, hide):
        if hide:
            self.playlist_tab_widget.hide()
        else:
            self.playlist_tab_widget.show()

    @pyqtSlot()
    def openSettings(self):
        settings_dialog = SettingsDialog(self)
        settings_dialog.exec()

    @pyqtSlot()
    def showAddChannelDialog(self):
        add_channel_dialog = AddChannelDialog(self)
        add_channel_dialog.channel_saved.connect(self.custom_channel_saved)
        add_channel_dialog.exec()

    def custom_channel_saved(self, channel):
        if channel.type == 'tv':
            self.tv_channel_list.addChannel(channel)
        else:
            self.radio_channel_list.addChannel(channel)
        self.chlist_manager.save_user_channel(channel)

    # Qt Events

    def closeEvent(self, event):
        self.video_player.stop()

        app = QApplication.instance()
        settings = app.settings_manager
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.setValue("hideChannelList", self.action_hide_channellist.isChecked())
        if not self.action_hide_channellist.isChecked():
            settings.setValue("splitterSizes", self.splitter.sizes())
        settings.setValue("player/volume", self.volume_slider.value())

        super().closeEvent(event)


class ChannelListShowAction(QAction):
    def __init__(self, parent=None, channel_list=None):
        super().__init__(parent)

        self.channel_list = channel_list
        self.setText(self.channel_list.name)
        self.setCheckable(True)