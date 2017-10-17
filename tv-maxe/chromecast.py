import pychromecast
import logging
import socket
import threading
import subprocess
import signal
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs, quote_plus
from PyQt5.QtCore import Qt, QObject, QMetaObject, QThread, pyqtSignal, pyqtSlot, Q_ARG
from pychromecast.controllers.media import *

from util import get_open_port

log = logging.getLogger(__name__)
BUF_SIZE = 64 * 1024

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.end_headers()

        if self.path == '/splash.jpg':
            fh = open('images/open-source.jpg', 'rb')
            data = fh.read()
            fh.close()
            self.wfile.write(data)
            return
        elif self.path.startswith('/broadcast'):
            query_dict = parse_qs(urlparse(self.path).query)
            url = query_dict['url'][0]

            cmd = ["ffmpeg", "-i", url, "-preset", "ultrafast", "-frag_duration", "3000", "-max_muxing_queue_size", "9999", "-nostats", "-loglevel", "0", "-f", "mp4", "-"]
            log.debug("Executing {0}".format(" ".join(cmd)))
            self.server.ffmpeg_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL
            )

            while self.server.ffmpeg_process and self.server.ffmpeg_process.poll() is None:
                stdout_data = self.server.ffmpeg_process.stdout.read(BUF_SIZE)
                self.wfile.write(stdout_data)

            log.debug("FFMPEG is dead, closing server...")
            self.server.ffmpeg_process = None
            self.server.socket.close()
            return


class CastServer(QObject):
    def start_server(self):
        log.debug('Configuring Chromecast server')
        self.httpd = HTTPServer(self.server_address, RequestHandler)
        self.httpd.ffmpeg_process = None
        threading.Thread(target=self.httpd.serve_forever).start()
        log.debug("Started Chromecast server at {0}".format(self.server_address))

    @pyqtSlot()
    def stop_server(self):
        log.debug("Stopping Chromecast server...")
        if self.httpd.ffmpeg_process:
            self.httpd.ffmpeg_process.send_signal(signal.SIGINT)
            self.httpd.ffmpeg_process.wait()
            self.httpd.ffmpeg_process = None

class CastManager(QObject):
    devices_found = pyqtSignal(list)
    device_connected = pyqtSignal('PyQt_PyObject')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device = None
        self.cast_server = None

    @pyqtSlot()
    def search_devices(self):
        log.debug("Looking for Chromecast devices...")
        devices = pychromecast.get_chromecasts()
        self.devices_found.emit(devices)

    @pyqtSlot('PyQt_PyObject')
    def connect_to_device(self, device):
        self.device = device

        server_thread = QThread(self)
        self.cast_server = CastServer()
        self.cast_server.server_address = ('0.0.0.0', get_open_port())
        self.cast_server.moveToThread(server_thread)
        server_thread.started.connect(self.cast_server.start_server)
        server_thread.start()

        self.device_connected.emit(device)

    @pyqtSlot(str, str)
    def play_media_path(self, path, content_type):
        media_url = 'http://{0}:{1}{2}'.format(
            socket.gethostbyname(socket.getfqdn()),
            self.cast_server.server_address[1],
            path)
        self.device.media_controller.play_media(media_url, content_type)

    @pyqtSlot()
    def pause_media_playback(self):
        self.device.media_controller.pause()

    @pyqtSlot()
    def resume_media_playback(self):
        self.device.media_controller.play()

    @pyqtSlot(int)
    def set_media_volume(self, volume):
        self.device.set_volume(volume / 100.0)

    @pyqtSlot()
    def stop_media_playback(self):
        self.device.media_controller.stop()
        QMetaObject.invokeMethod(
            self.cast_server,
            'stop_server', 
            Qt.AutoConnection
        )

class Chromecast(QObject):
    devices_found = pyqtSignal(list)
    device_connected = pyqtSignal('PyQt_PyObject')
    device_playback_started = pyqtSignal()
    device_playback_paused = pyqtSignal()
    device_playback_buffering = pyqtSignal()
    device_playback_stopped = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.current_device = None

        self.cast_manager = CastManager()
        self.cast_manager.devices_found.connect(self.devices_found_)
        self.cast_manager.device_connected.connect(self.device_connected_)
        worker_thread = QThread(self)
        self.cast_manager.moveToThread(worker_thread)
        worker_thread.started.connect(self.cast_manager.search_devices)
        worker_thread.start()

    def new_media_status(self, status):
        if status.player_state == MEDIA_PLAYER_STATE_PLAYING:
            self.device_playback_started.emit()
        elif status.player_state == MEDIA_PLAYER_STATE_BUFFERING:
            self.device_playback_buffering.emit()
        elif status.player_state == MEDIA_PLAYER_STATE_PAUSED:
            self.device_playback_paused.emit()
        elif status.player_state == MEDIA_PLAYER_STATE_IDLE:
            if status.idle_reason and status.idle_reason != 'INTERRUPTED':
                self.device_playback_stopped.emit()

    def devices_found_(self, devices):
        self.devices_found.emit(devices)

    def select_device(self, device):
        QMetaObject.invokeMethod(
            self.cast_manager,
            'connect_to_device', 
            Qt.AutoConnection,
            Q_ARG('PyQt_PyObject', device)
        )
        self.current_device = device
        self.current_device.wait()
        self.current_device.media_controller.register_status_listener(self)

    def device_connected_(self, device):
        self.show_splashscreen()
        self.device_connected.emit(device)

    def play_url(self, url, content_type='video/mp4'):
        path = '/broadcast?url={0}'.format(quote_plus(url))
        QMetaObject.invokeMethod(
            self.cast_manager,
            'play_media_path', 
            Qt.AutoConnection,
            Q_ARG('QString', path),
            Q_ARG('QString', content_type)
        )

    def show_splashscreen(self):
        QMetaObject.invokeMethod(
            self.cast_manager,
            'play_media_path', 
            Qt.AutoConnection,
            Q_ARG('QString', '/splash.jpg'),
            Q_ARG('QString', 'image/jpeg')
        )

    def stop(self):
        QMetaObject.invokeMethod(
            self.cast_manager,
            'stop_media_playback', 
            Qt.AutoConnection
        )

    def pause(self):
        QMetaObject.invokeMethod(
            self.cast_manager,
            'pause_media_playback', 
            Qt.AutoConnection
        )

    def play(self):
        QMetaObject.invokeMethod(
            self.cast_manager,
            'resume_media_playback', 
            Qt.AutoConnection
        )

    def set_volume(self, volume):
        QMetaObject.invokeMethod(
            self.cast_manager,
            'set_media_volume',
            Qt.AutoConnection,
            Q_ARG(int, volume)
        )

    def disconnect(self):
        if self.current_device:
            self.current_device.quit_app()
            self.current_device = None
