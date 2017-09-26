import mpv
from PyQt5.QtCore import Qt, QMessageLogger, QTimer, pyqtSignal
from PyQt5.QtWidgets import QApplication, QWidget, QSizePolicy
from PyQt5.QtGui import QKeyEvent, QCursor
from urllib.parse import urlparse
from enum import Enum, auto

from models.channel import Channel
from fullscreentoolbar import FullscreenToolbar

class VideoPlayerState(Enum):
    PLAYER_UNKNOWN = auto()
    PLAYER_IDLE = auto()
    PLAYER_LOADING = auto()
    PLAYER_PLAYING = auto()
    PLAYER_PAUSED = auto()

class VideoPlayer(QWidget):
    playback_started = pyqtSignal(Channel)
    playback_paused = pyqtSignal(Channel)
    playback_stopped = pyqtSignal(Channel)
    playback_error = pyqtSignal(Channel)
    volume_changed = pyqtSignal(int)
    fullscreen_changed = pyqtSignal(bool)

    def __init__(self, parent=None, flags=Qt.Widget):
        super().__init__(parent, flags)
        self.channel = None
        self.player = mpv.MPV()
        self.player.wid = int(self.winId())
        self.player.input_cursor = False
        self.player.cursor_autohide = False
        self.protocol = None
        self.mousehide_timer = QTimer()
        self.mousehide_timer.setSingleShot(True)
        self.mousehide_timer.timeout.connect(self._hide_mouse)
        self.fullscreen_toolbar = FullscreenToolbar(self)
        self.setMouseTracking(True)

    def get_state(self):
        if self.player.idle_active == True:
            return VideoPlayerState.PLAYER_IDLE
        elif self.player.core_idle == True:
            return VideoPlayerState.PLAYER_PAUSED
        elif self.player.core_idle == False:
            return VideoPlayerState.PLAYER_PLAYING
        return VideoPlayerState.PLAYER_UNKNOWN

    def play_channel(self, channel):
        self.channel = channel
        app = QApplication.instance()
        url = self.channel.streamurls[0]
        url_components = urlparse(url)
        if app.protocol_plugins.get(url_components.scheme, None):
            protocol_class = app.protocol_plugins[url_components.scheme]
            self.protocol = protocol_class()
            self.protocol.protocol_ready.connect(self.protocol_ready)
            self.protocol.protocol_error.connect(self.protocol_error)
            self.protocol.load_url(url)

    def protocol_ready(self, url):
        self.player.observe_property('core-idle', self.idle_observer)
        self.player.register_message_handler('commands', self.command_received)
        self.player.register_event_callback(self.event_observer)
        self.player.play(url)

    def command_received(self, args):
        print (args)

    def protocol_error(self, url, error_message):
        self.unregister_observers()
        self.player.stop()
        self.protocol.stop()
        self.protocol = None

    def pause(self):
        self.player.pause = True

    def unpause(self):
        self.player.pause = False

    def stop(self):
        self.unregister_observers()
        self.player.command('stop')
        self.exit_fullscreen()
        if self.protocol:
            self.protocol.stop()
            self.protocol = None
        if self.channel:
            self.playback_stopped.emit(self.channel)

    def set_volume(self, volume):
        self.player.volume = volume
        self.volume_changed.emit(volume)

    def switch_fullscreen(self):
        if self.isFullScreen():
            self.exit_fullscreen()
        else:
            self.enter_fullscreen()

    def enter_fullscreen(self):
        if self.isFullScreen():
            return

        self.setProperty('old-window', self.window())
        # self.setProperty('old-windowflags', self.windowFlags())
        # self.overrideWindowFlags(Qt.FramelessWindowHint)
        self.window().hide()
        self.setWindowTitle(' ')
        self.setParent(None)
        self.showFullScreen()
        self.setFocusPolicy(Qt.StrongFocus)
        self.fullscreen_changed.emit(True)

    def exit_fullscreen(self):
        if self.window().findChild(VideoPlayer, "video_player"):
            return  # guard check to be sure this code isn't called twice

        if not self.isFullScreen():
            return

        self.fullscreen_toolbar.hide()
        self.property('old-window').video_player_layout.addWidget(self)
        self.property('old-window').showNormal()
        # self.overrideWindowFlags(Qt.WindowFlags(self.property('old-windowflags')))
        self.fullscreen_changed.emit(False)

    def event_observer(self, event):
        event_id = event.get('event_id', None)
        if event_id == 6:
            self.playback_started.emit(self.channel)
        elif event_id == 7:  # end-file
            reason = event['event']['reason']
            if reason == 0:  # EOF
                self.stop()
            elif reason == 2:  # Playback was stopped by an external action (e.g. playlist controls).
                self.playback_stopped.emit(self.channel)
            elif reason == 3:  # quit
                self.playback_stopped.emit(self.channel)
            elif reason == 4:
                self.playback_error.emit(self.channel)
                self.unregister_observers()
                if self.protocol:
                    self.protocol.stop()
                    self.protocol = None


    def idle_observer(self, name, value):
        if value == False:
            self.playback_started.emit(self.channel)
        else:
            self.playback_paused.emit(self.channel)

    def unregister_observers(self):
        try:
            self.player.unregister_event_callback(self.event_observer)
        except ValueError:
            QMessageLogger().debug("Failed to unregister from mpv events")
        try:
            self.player.unobserve_property('core-idle', self.idle_observer)
        except ValueError:
            QMessageLogger().debug("Failed to unregister as a mpv observer")

    def _hide_mouse(self):
        if self.fullscreen_toolbar.isHidden():
            QApplication.instance().setOverrideCursor(QCursor(Qt.BlankCursor))

    def _show_mouse(self):
        QApplication.instance().setOverrideCursor(QCursor(Qt.ArrowCursor))

    # Qt Events

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        if type(event) == QKeyEvent:
            if event.key() == Qt.Key_Escape and self.isFullScreen():
                QTimer().singleShot(0, self.exit_fullscreen)
                event.accept()
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self.isFullScreen():
            if event.pos().y() > self.height() - 150:
                self.fullscreen_toolbar.move(
                    self.width()/2 - self.fullscreen_toolbar.width()/2,
                    self.height() - self.fullscreen_toolbar.height()
                )
                self.fullscreen_toolbar.show()
            else:
                self.fullscreen_toolbar.hide()

        self._show_mouse()
        self.mousehide_timer.start(2000)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.mousehide_timer.stop()