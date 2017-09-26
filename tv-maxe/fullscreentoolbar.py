from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QWidget

from txicon import TXIcon


class FullscreenToolbar(QWidget):
    def __init__(self, parent=None, flags=0):
        super().__init__(parent)

        uic.loadUi('ui/fullscreenToolbar.ui', self)

        self.setWindowFlags(Qt.Tool|Qt.Widget|Qt.FramelessWindowHint);
        self.setAttribute(Qt.WA_NoSystemBackground, True);
        self.setAttribute(Qt.WA_TranslucentBackground, True); 

        app = QApplication.instance()
        settings = app.settings_manager

        if settings.value("player/volume"):
            self.volume_slider.setValue(int(settings.value("player/volume")))

        parent.playback_started.connect(self.video_playback_started)
        parent.playback_paused.connect(self.video_playback_paused)
        parent.playback_stopped.connect(self.video_playback_stopped)
        parent.playback_error.connect(self.video_playback_error)
        parent.volume_changed.connect(self.video_volume_changed)

        self.play_btn.clicked.connect(self.play_btn_clicked)
        self.stop_btn.clicked.connect(self.stop_btn_clicked)
        self.fullscreen_btn.clicked.connect(self.switch_fullscreen_mode)
        self.volume_slider.sliderMoved.connect(self.volume_changed)

        # Set custom icons
        self.play_btn.setIcon(TXIcon('icons/play-button.svg', Qt.white))
        self.stop_btn.setIcon(TXIcon('icons/stop-button.svg', Qt.white))
        self.fullscreen_btn.setIcon(TXIcon('icons/unfullscreen.svg', Qt.white))

    def play_btn_clicked(self, checked=False):
        from videoplayer import VideoPlayerState
        player_state = self.parent().get_state()
        if player_state is VideoPlayerState.PLAYER_PLAYING:
            self.parent().pause()
        else:
            self.parent().unpause()

    def stop_btn_clicked(self, checked=False):
        self.parent().stop()

    def volume_changed(self, level):
        self.parent().volume_changed.disconnect(self.video_volume_changed)
        self.parent().set_volume(level)
        self.parent().volume_changed.connect(self.video_volume_changed)

    def switch_fullscreen_mode(self, checked=False):
        self.parent().exit_fullscreen()

    # Signals

    def video_playback_started(self, channel):
        self.play_btn.setIcon(TXIcon('icons/pause-button.svg', Qt.white))
        self.osd_channel_name.setText(channel.name)

    def video_playback_paused(self, channel):
        self.play_btn.setIcon(TXIcon('icons/play-button.svg', Qt.white))

    def video_playback_stopped(self, channel):
        self.play_btn.setIcon(TXIcon('icons/play-button.svg', Qt.white))

    def video_playback_error(self, channel):
        self.play_btn.setIcon(TXIcon('icons/play-button.svg', Qt.white))

    def video_volume_changed(self, value):
        self.volume_slider.setValue(int(value))

    # Qt Events

    def keyPressEvent(self, event):
        self.parent().keyPressEvent(event)