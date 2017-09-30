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
            except (BrokenPipeError, ConnectionResetError) as e:
                break
            data = self.server.rtmp_stream.read(BUF_SIZE)

        self.server.socket.close()
        log.debug('End of stream')
        return


class RTMPWorker(QObject):
    stream_available = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, url, args, parent=None):
        super().__init__(parent=None)
        self.conn = None
        self.rtmp_stream = None
        self.httpd = None
        self.url = url
        self.args = args

    def play_url(self):
        self.conn = librtmp.RTMP(self.url, live=True)
        log.debug('Initializing RTMP connection with {0}'.format(self.url))
        try:
            self.conn.connect()
        except Exception as e:
            log.debug('Failed to initiate RTMP connection: {0}'.format(e))
            self.error.emit(str(e))
            return

        log.debug('Creating RTMP connection stream')
        try:
            self.rtmp_stream = self.conn.create_stream()
        except librtmp.exceptions.RTMPError as e:
            log.debug('Failed to create RTMP connection stream')
            self.error.emit(str(e))
            return

        log.debug('Configuring HTTP server')
        server_address = ('127.0.0.1', get_open_port())
        self.httpd = HTTPServer(server_address, RequestHandler)
        self.httpd.rtmp_stream = self.rtmp_stream
        log.debug('Starting HTTP Server')
        threading.Thread(target=self.httpd.serve_forever).start()
        self.stream_available.emit('http://{0}:{1}'.format(server_address[0], server_address[1]))

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            log.debug('Shut down HTTP server')
        if self.rtmp_stream:
            self.rtmp_stream.close()
            log.debug('Closed RTMP connection stream')
        if self.conn:
            self.conn.close()
            log.debug('Closed RTMP connection')

class RTMP(Protocol):
    name = "RTMP Protocol"
    desc = "RTMP Protocol Backend for TV-Maxe"
    version = "0.01"
    protocols = ["rtmp", "rtmpe"]

    def __init__(self, parent=None):
        super().__init__(parent)
        log.debug('Using librtmp {0}'.format(librtmp.__version__))

    def load_url(self, url, args=None):
        log.debug('Playing {0}, args {1}'.format(url, args))
        self.worker_thread = QThread(self)
        self.worker = RTMPWorker(url, args)
        self.worker.stream_available.connect(self.stream_available)
        self.worker.error.connect(self.error)
        self.worker_thread.finished.connect(self.worker_thread_finished)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.play_url)
        self.worker_thread.start()

    def stream_available(self, cb_url):
        self.protocol_ready.emit(cb_url)

    def error(self, error_msg):
        self.protocol_error.emit(self.worker.url, error_msg)

    def stop(self):
        self.worker.stop()
        self.worker_thread.quit()

    def worker_thread_finished(self):
        log.debug('Worker thread finished')
        self.deleteLater()


__classname__ = RTMP