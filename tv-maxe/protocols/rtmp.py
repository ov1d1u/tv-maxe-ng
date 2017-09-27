import librtmp
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from PyQt5.QtCore import Qt, QThread, QObject, QTimer, QMetaObject, pyqtSignal, pyqtSlot

from protocols import Protocol
from util import get_open_port

log = logging.getLogger(__name__)
BUF_SIZE = 64 * 1024

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()

        data = self.server.rtmp_stream.read(BUF_SIZE)
        while data:
            try:
                self.wfile.write(data)
            except BrokenPipeError as e:
                break
            data = self.server.rtmp_stream.read(BUF_SIZE)

        self.server.socket.close()
        log.debug('End of stream')
        # self.server.http_server_closed.emit()
        return


class RTMPWorker(QObject):
    stream_available = pyqtSignal(str)
    http_server_closed = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, url, args, parent=None):
        super().__init__(parent=None)
        self.conn = None
        self.httpd = None
        self.url = url
        self.args = args

    def play_url(self):
        self.conn = librtmp.RTMP(self.url, live=True)
        log.debug('Initializing RTMP connection with {0}'.format(self.url))
        try:
            log.debug('Connect...')
            self.conn.connect()
            log.debug('Connected')
        except Exception as e:
            log.debug('Failed to initiate RTMP connection: {0}'.format(e.message))
            self.error.emit(e.message)
            return

        log.debug('Configuring HTTP server')
        server_address = ('127.0.0.1', get_open_port())
        self.httpd = HTTPServer(server_address, RequestHandler)
        self.httpd.rtmp_stream = self.conn.create_stream()
        self.httpd.http_server_closed = self.http_server_closed
        log.debug('Starting HTTP Server')
        threading.Thread(target=self.httpd.serve_forever).start()
        self.stream_available.emit('http://{0}:{1}'.format(server_address[0], server_address[1]))

    def stop(self):
        if self.conn:
            self.httpd.shutdown()
            self.conn.close()
            log.debug('Closed RTMP connection')

class RTMP(Protocol):
    name = "RTMP Protocol"
    desc = "RTMP Protocol Backend for TV-Maxe"
    version = "0.01"
    protocols = ["rtmp", "rtmpe"]

    def __init__(self):
        super().__init__()
        log.debug('Using librtmp {0}'.format(librtmp.__version__))

    def load_url(self, url, args=None):
        log.debug('Playing {0}, args {1}'.format(url, args))
        self.worker_thread = QThread(self)
        self.worker = RTMPWorker(url, args)
        self.worker.stream_available.connect(self.stream_available)
        self.worker.http_server_closed.connect(self.http_server_closed)
        self.worker.error.connect(self.error)
        self.worker_thread.started.connect(self.worker.play_url)
        self.worker_thread.finished.connect(lambda: log.debug('Thread finished'))
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.start()

    def stream_available(self, cb_url):
        self.protocol_ready.emit(cb_url)

    def error(self, error_msg):
        self.protocol_error.emit(self.worker.url, error_msg)

    def stop(self):
        self.worker.stop()
        self.worker_thread.quit()

    def http_server_closed(self):
        self.protocol_finished.emit()


__classname__ = RTMP