import datetime
import itertools
from PyQt5 import uic
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QWidget

from txicon import TXIcon
from epg import EPGRetriever
from util import toLocalTime

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

        self.timer = None
        self.epg = None
        self.epg_list = []

        # Set custom icons
        self.play_btn.setIcon(TXIcon('icons/play-button.svg', Qt.white))
        self.stop_btn.setIcon(TXIcon('icons/stop-button.svg', Qt.white))
        self.fullscreen_btn.setIcon(TXIcon('icons/unfullscreen.svg', Qt.white))

        self.show_progress.hide()

    def show(self):
        super().show()
        self.activateWindow()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(1000)

    def hide(self):
        super().hide()
        if self.timer:
            self.timer.stop()
            self.timer.deleteLater()
            self.timer = None

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

    def epg_data_available(self, epg_list):
        self.epg_list = epg_list

    # Signals

    def video_playback_started(self, channel):
        self.play_btn.setIcon(TXIcon('icons/pause-button.svg', Qt.white))
        self.osd_channel_name.setText(channel.name)
        self.epg = EPGRetriever(channel, datetime.datetime.now().strftime("%Y-%m-%d"))
        self.epg.epg_data_available.connect(self.epg_data_available)
        self.epg.retrieve_epg()

    def video_playback_paused(self, channel):
        self.play_btn.setIcon(TXIcon('icons/play-button.svg', Qt.white))

    def video_playback_stopped(self, channel):
        self.play_btn.setIcon(TXIcon('icons/play-button.svg', Qt.white))

    def video_playback_error(self, channel):
        self.play_btn.setIcon(TXIcon('icons/play-button.svg', Qt.white))

    def video_volume_changed(self, value):
        self.volume_slider.setValue(int(value))

    # Qt Events

    def paintEvent(self, event):
        super().paintEvent(event)
        now = datetime.datetime.now()
        self.clock_label.setText(now.strftime("%X"))

        if self.epg_list:
            hours = [toLocalTime(x[0]) for x in self.epg_list]
            now = datetime.datetime.strptime(datetime.datetime.now().strftime("%H:%M"), "%H:%M")
            current = [x for x in itertools.takewhile(lambda t: now >= datetime.datetime.strptime(t, "%H:%M"), hours)][-1]

            for idx, epg_line in enumerate(self.epg_list):
                if toLocalTime(epg_line[0]) == current:
                    self.show_name_label.setText(epg_line[1])

                    if len(self.epg_list) > idx + 1:
                        start_time = datetime.datetime.strptime(toLocalTime(epg_line[0]), "%H:%M")
                        end_time = datetime.datetime.strptime(toLocalTime(self.epg_list[idx + 1][0]), "%H:%M")
                        elapsed_time = datetime.datetime.strptime(datetime.datetime.now().strftime("%H:%M"), "%H:%M")
                        show_duration = end_time - start_time
                        elapsed_duration = elapsed_time - start_time
                        self.show_progress.setMinimum(0)
                        self.show_progress.setMaximum(show_duration.seconds)
                        self.show_progress.setValue(elapsed_duration.seconds)
                        self.show_progress.show()
                    return

        self.show_name_label.setText("")

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        self.parent().keyPressEvent(event)