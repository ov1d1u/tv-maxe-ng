import mpv
import logging
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import QApplication, QWidget, QSizePolicy
from PyQt5.QtGui import QKeyEvent, QCursor
from urllib.parse import urlparse
from enum import Enum, auto

from models.channel import Channel
from fullscreentoolbar import FullscreenToolbar

log = logging.getLogger(__name__)

class VideoPlayerState(Enum):
    PLAYER_UNKNOWN = auto()
    PLAYER_IDLE = auto()
    PLAYER_LOADING = auto()
    PLAYER_PLAYING = auto()
    PLAYER_PAUSED = auto()

class VideoPlayer(QWidget):
    playback_started = pyqtSignal('PyQt_PyObject')
    playback_paused = pyqtSignal('PyQt_PyObject')
    playback_stopped = pyqtSignal('PyQt_PyObject')
    playback_error = pyqtSignal('PyQt_PyObject')
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
        log.debug('Playing channel {0}'.format(channel.id))
        self.channel = channel
        app = QApplication.instance()
        url = self.channel.streamurls[0]
        log.debug('Selected url: {0}'.format(url))
        url_components = urlparse(url)
        if app.protocol_plugins.get(url_components.scheme, None):
            protocol_class = app.protocol_plugins[url_components.scheme]
            log.debug('Using {0} to process {1}'.format(protocol_class, url))
            self.protocol = protocol_class()
            self.protocol.protocol_ready.connect(self.protocol_ready)
            self.protocol.protocol_error.connect(self.protocol_error)
            self.protocol.protocol_finished.connect(self.protocol_finished)
            self.protocol.load_url(url)
        else:
            log.error('No suitable protocol found for {0}'.format(url))

    def protocol_ready(self, url):
        self.player.observe_property('core-idle', self.idle_observer)
        self.player.register_message_handler('commands', self.command_received)
        self.player.register_event_callback(self.event_observer)
        log.debug('Ready to play {0} via {1}'.format(self.channel.id, url))
        self.player.play(url)

    def command_received(self, args):
        print (args)

    def protocol_error(self, url, error_message):
        log.debug('Protocol returned error, stopping playback')
        self.unregister_observers()
        self.player.command('stop')
        self.protocol.stop()

    def protocol_finished(self):
        self.protocol = None

    def pause(self):
        log.debug('pause')
        self.player.pause = True

    def unpause(self):
        log.debug('resume')
        self.player.pause = False

    def stop(self):
        log.debug('stop')
        self.unregister_observers()
        self.player.play('')
        self.exit_fullscreen()
        if self.protocol:
            self.protocol.stop()
        self.playback_stopped.emit(self.channel)

    def set_volume(self, volume):
        log.debug('set_volume: {0}'.format(volume))
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
        log.debug('Switched to fullscreen')

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
        log.debug('Returned from fullscreen')

    def event_observer(self, event):
        event_id = event.get('event_id', None)
        log.debug('Received event id: {0} data: {1}'.format(event_id, event))
        if event_id == mpv.MpvEventID.END_FILE:  # end-file
            reason = event['event']['reason']
            log.debug('- Reason: {0}'.format(reason))
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

    def idle_observer(self, name, value):
        log.debug('idle_observer: {0} {1}'.format(name, value))
        if value == False:
            log.debug('Started playback')
            self.playback_started.emit(self.channel)
        else:
            if self.player.cache_used:
                # This is also called when playback was paused because the network cache is empty.
                # Emit `playback_paused` only if the user paused the playback
                cache_used = None
                try:
                    cache_used = int(self.player.cache_used)
                except:
                    pass

                if cache_used != 0:
                    log.debug('Paused playback')
                    self.playback_paused.emit(self.channel)

    def unregister_observers(self):
        try:
            self.player.unregister_event_callback(self.event_observer)
        except ValueError:
            log.warn("Failed to unregister from mpv events")
        try:
            self.player.unobserve_property('core-idle', self.idle_observer)
        except ValueError:
            log.warn("Failed to unregister as a mpv observer")

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