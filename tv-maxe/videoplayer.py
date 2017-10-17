import mpv
import logging
import platform
from urllib.parse import urlparse, quote_plus
from enum import Enum
from PyQt5.QtCore import Qt, QMetaObject, QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QSizePolicy, QMessageBox
from PyQt5.QtGui import QKeyEvent, QCursor, QPixmap

from protocols import ProtocolException
from models.channel import Channel
from chromecast import Chromecast
from fullscreentoolbar import FullscreenToolbar

log = logging.getLogger(__name__)

class VideoPlayerState(Enum):
    PLAYER_UNKNOWN = 0
    PLAYER_IDLE = 1
    PLAYER_LOADING = 2
    PLAYER_PLAYING = 3
    PLAYER_PAUSED = 4

class VideoPlayer(QWidget):
    playback_started = pyqtSignal('PyQt_PyObject')
    playback_paused = pyqtSignal('PyQt_PyObject')
    playback_stopped = pyqtSignal('PyQt_PyObject')
    playback_error = pyqtSignal('PyQt_PyObject')
    volume_changed = pyqtSignal(int)
    fullscreen_changed = pyqtSignal(bool)
    chromecast_available = pyqtSignal(list)
    chromecast_connected = pyqtSignal('PyQt_PyObject')
    chromecast_disconnected = pyqtSignal('PyQt_PyObject')

    def __init__(self, parent=None, flags=Qt.Widget):
        super().__init__(parent, flags)
        self.channel = None
        self.player = mpv.MPV()
        self.player.wid = int(self.winId())
        self.player.cursor_autohide = False
        self.protocol = None
        self.fullscreen_toolbar = FullscreenToolbar(self)

        self.player.register_key_binding('MOUSE_LEAVE', self.mouse_leave)
        self.player.register_key_binding('MOUSE_MOVE', self.mouse_move)
        self.player.register_key_binding('MOUSE_BTN0_DBL', self.mouse_dbclk)
        self.mousehide_timer = QTimer()
        self.mousehide_timer.setSingleShot(True)
        self.mousehide_timer.timeout.connect(self._hide_mouse)

        self.chromecast_manager = Chromecast(self)
        self.chromecast_manager.devices_found.connect(self.chromecast_devices_found)
        self.chromecast_manager.device_connected.connect(self.chromecast_device_connected)
        self.chromecast_manager.device_playback_started.connect(self.chromecast_playback_started)
        self.chromecast_manager.device_playback_stopped.connect(self.chromecast_playback_stopped)
        self.chromecast_manager.device_playback_paused.connect(self.chromecast_playback_paused)

    def get_state(self):
        if self.player.idle_active == True:
            return VideoPlayerState.PLAYER_IDLE
        elif self.player.core_idle == True:
            return VideoPlayerState.PLAYER_PAUSED
        elif self.player.core_idle == False:
            return VideoPlayerState.PLAYER_PLAYING
        return VideoPlayerState.PLAYER_UNKNOWN

    def play_channel(self, channel, play_index):
        log.debug('Playing channel: {0}'.format(channel.id))
        self.channel = Channel(channel.to_dict())
        self.channel.play_index = play_index
        url = self.channel.streamurls[play_index]
        log.debug('Selected url: {0}'.format(url))
        url_components = urlparse(url)
        app = QApplication.instance()
        if app.protocol_plugins.get(url_components.scheme, None):
            protocol_class = app.protocol_plugins[url_components.scheme]
            log.debug('Using {0} to process {1}'.format(protocol_class.name, url))
            try:
                self.protocol = protocol_class(self)
                self.protocol.protocol_ready.connect(self.protocol_ready)
                self.protocol.protocol_error.connect(self.protocol_error)
                self.protocol.load_url(url, channel.args(url))
            except ProtocolException as e:
                log.error(e.message)
                QMessageBox.critical(
                    self,
                    self.tr("Error playing channel"),
                    self.tr("Protocol crashed with error: {0}").format(e.message)
                )
                self.playback_error.emit(self.channel)
                self.channel = None
        else:
            log.error('No suitable protocol found for {0}'.format(url))

    def chromecast_devices_found(self, devices):
        self.chromecast_available.emit(devices)

    def chromecast_device_connected(self, device):
        px = QPixmap('icons/cast.svg')
        pxr = QPixmap(px.size())
        pxr.fill(Qt.lightGray)
        pxr.setMask(px.createMaskFromColor((Qt.transparent)))
        self.window().cast_label_pixmap.setPixmap(pxr)
        self.window().cast_label_pixmap.setScaledContents(True)
        self.window().cast_label.setText(self.tr("Connected to: {0}".format(device.device.friendly_name)))
        self.window().cast_label_pixmap.setHidden(False)
        self.window().cast_label.setHidden(False)
        self.chromecast_connected.emit(device)
        if self.player.path:
            self.chromecast_manager.play_url(self.player.path)

    def protocol_ready(self, url):
        self.player.observe_property('core-idle', self.idle_observer)
        self.player.register_event_callback(self.event_observer)
        log.debug('Ready to play {0} via {1}'.format(self.channel.id, url))
        if self.chromecast_manager.current_device:
            self.chromecast_manager.play_url(url)
        else:
            self.player.play(url)

    def protocol_error(self, url, error_message):
        log.debug('Protocol returned error, stopping playback')
        self.unregister_observers()
        self.deactivate_protocol()
        self.player.play('')
        self.exit_fullscreen()
        self.playback_error.emit(self.channel)

    def deactivate_protocol(self):
        self.protocol.protocol_ready.disconnect()
        self.protocol.protocol_error.disconnect()
        self.protocol.stop()
        self.protocol = None

    def switch_pause(self):
        if self.chromecast_manager.current_device:
            media_controller = self.chromecast_manager.current_device.media_controller
            if media_controller.status.player_is_playing:
                self.chromecast_manager.pause()
            else:
                self.chromecast_manager.play()
        else:
            if self.get_state() == VideoPlayerState.PLAYER_PAUSED:
                self.player.play()
            else:
                self.player.pause()

    def stop(self):
        log.debug('stop')
        self.unregister_observers()
        self.player.play('')
        self.exit_fullscreen()
        if self.protocol:
            self.deactivate_protocol()
        if self.chromecast_manager.current_device:
            self.chromecast_manager.stop()
        self.playback_stopped.emit(self.channel)
        self.channel = None

    def set_volume(self, volume):
        log.debug('set_volume: {0}'.format(volume))
        if self.chromecast_manager.current_device:
            self.chromecast_manager.set_volume(volume)
        else: 
            self.player.volume = volume
        self.volume_changed.emit(volume)

    def connect_chromecast(self, device):
        self.chromecast_manager.select_device(device)

    def disconnect_chromecast(self):
        self.stop()
        self.chromecast_manager.disconnect()
        self.window().cast_label_pixmap.setHidden(True)
        self.window().cast_label.setHidden(True)

    def chromecast_playback_started(self):
        # We don't have a self.channel if we're playing the splash screen
        if self.channel:
            self.playback_started.emit(self.channel)

            if self.player.path:
                # Stop the video player
                self.player.play('')

    def chromecast_playback_stopped(self):
        if self.channel:
            self.playback_stopped.emit(self.channel)

    def chromecast_playback_paused(self):
        if self.channel:
            self.playback_paused.emit(self.channel)

    @pyqtSlot()
    def switch_fullscreen(self):
        if self.isFullScreen():
            self.exit_fullscreen()
        else:
            self.enter_fullscreen()

    @pyqtSlot()
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

    @pyqtSlot()
    def exit_fullscreen(self):
        if self.window().findChild(VideoPlayer, "video_player"):
            return  # guard check to be sure this code isn't called twice

        if not self.isFullScreen():
            return

        self.fullscreen_toolbar.hide()
        if platform.system() == 'Darwin':
            self.property('old-window').video_player_layout.addWidget(self)
            self.property('old-window').showNormal()
        else:
            self.property('old-window').showNormal()
            self.property('old-window').video_player_layout.addWidget(self)
        # self.overrideWindowFlags(Qt.WindowFlags(self.property('old-windowflags')))
        self.fullscreen_changed.emit(False)
        log.debug('Returned from fullscreen')

    def event_observer(self, event):
        if self.chromecast_manager.current_device:
            return  # Ignore events if we're connected to a Chromecast

        event_id = event.get('event_id', None)
        if event_id == mpv.MpvEventID.END_FILE:  # end-file
            log.debug('Processing event id: {0} data: {1}'.format(event_id, event))
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
                    self.deactivate_protocol()

    def idle_observer(self, name, value):
        if self.chromecast_manager.current_device:
            return  # Ignore events if we're connected to a Chromecast

        log.debug('idle_observer: {0} {1}'.format(name, value))
        if value == False:
            log.debug('Started playback')
            self.playback_started.emit(self.channel)
        else:
            if not self.player.paused_for_cache:
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

    def mouse_leave(self, state, name):
        QMetaObject.invokeMethod(self, '_mouse_leave', Qt.AutoConnection)

    def mouse_move(self, state, name):
        QMetaObject.invokeMethod(self, '_mouse_move', Qt.AutoConnection)

    def mouse_dbclk(self, state, name):
        QMetaObject.invokeMethod(self, 'switch_fullscreen', Qt.AutoConnection)

    def quit(self):
        self.stop()
        if self.chromecast_manager.current_device:
            self.chromecast_manager.disconnect()

    @pyqtSlot()
    def _mouse_move(self):
        if self.isFullScreen():
            if QCursor.pos().y() > self.height() - 150:
                self.fullscreen_toolbar.move(
                    self.width()/2 - self.fullscreen_toolbar.width()/2,
                    self.height() - self.fullscreen_toolbar.height()
                )
                self.fullscreen_toolbar.show()
            else:
                self.fullscreen_toolbar.hide()

        self._show_mouse()
        self.mousehide_timer.start(2000)

    @pyqtSlot()
    def _mouse_leave(self):
        self.mousehide_timer.stop()

    def _hide_mouse(self):
        if self.get_state() != VideoPlayerState.PLAYER_IDLE and self.fullscreen_toolbar.isHidden():
            QApplication.instance().setOverrideCursor(QCursor(Qt.BlankCursor))

    def _show_mouse(self):
        QApplication.instance().setOverrideCursor(QCursor(Qt.ArrowCursor))

    # Qt Events

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        if type(event) == QKeyEvent:
            if event.key() == Qt.Key_Escape and self.isFullScreen():
                QMetaObject.invokeMethod(self, 'exit_fullscreen', Qt.AutoConnection)
                event.accept()
        else:
            event.ignore()
