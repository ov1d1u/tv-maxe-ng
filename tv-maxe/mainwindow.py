import logging
import platform
from PyQt5 import uic
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QSizeGrip

from channellistmanager import ChannelListManager
from settings import SettingsDialog
from txicon import TXIcon

log = logging.getLogger(__name__)

class TVMaxeMainWindow(QMainWindow):
    def __init__(self, parent):
        super(QMainWindow, self).__init__(parent)
        uic.loadUi('ui/mainWindow.ui', self)

        self.chlist_manager = ChannelListManager()
        self.chlist_manager.channel_added.connect(self.channel_added)

        self.play_btn.clicked.connect(self.play_btn_clicked)
        self.stop_btn.clicked.connect(self.stop_btn_clicked)
        self.fullscreen_btn.clicked.connect(self.switch_fullscreen_mode)
        self.volume_slider.sliderMoved.connect(self.volume_changed)
        self.tv_channel_list.itemActivated.connect(self.activated_channel_item)
        self.radio_channel_list.itemActivated.connect(self.activated_channel_item)
        
        self.video_player.playback_started.connect(self.video_playback_started)
        self.video_player.playback_paused.connect(self.video_playback_paused)
        self.video_player.playback_stopped.connect(self.video_playback_stopped)
        self.video_player.playback_error.connect(self.video_playback_error)
        self.video_player.volume_changed.connect(self.video_volume_changed)

        self.statusbar.addPermanentWidget(self.bottom_bar, 1)
        self.bottom_layout.addWidget(QSizeGrip(self))
        self.splitter.setStretchFactor(1, 1)
        self.progress_bar.hide()
        self.progress_label.setText(self.tr("Idle"))
        self.video_player.set_volume(self.volume_slider.value())

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

    def activated_channel_item(self, channelitem):
        self.play_channel(channelitem.channel)

    def channel_added(self, channel):
        if channel.type == 'tv':
            self.tv_channel_list.addChannel(channel)
        elif channel.type == 'radio':
            self.radio_channel_list.addChannel(channel)

    def play_channel(self, channel):
        self.video_player.stop()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)
        self.progress_bar.show()
        self.progress_label.setText(self.tr("Now loading: {0} ({1})".format(channel.name, channel.streamurls[0])))
        self.video_player.play_channel(channel)

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
        self.play_btn.setIcon(TXIcon('icons/play-button.svg'))
        self.progress_label.setText(self.tr("Channel not available: {0}".format(channel.name)))
        self.progress_bar.hide()
        self.progress_bar.setMaximum(1)

    def video_volume_changed(self, value):
        self.volume_slider.setValue(int(value))

    @pyqtSlot()
    def openSettings(self):
        settings_dialog = SettingsDialog(self)
        settings_dialog.exec()

    # Qt Events

    def closeEvent(self, event):
        self.video_player.stop()

        app = QApplication.instance()
        settings = app.settings_manager
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.setValue("splitterSizes", self.splitter.sizes())
        settings.setValue("player/volume", self.volume_slider.value())
