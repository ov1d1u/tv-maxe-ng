import os
import sys
import subprocess
import shutil
import time
import requests
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QThread, QObject, QTimer, QMetaObject, pyqtSignal

from protocols import Protocol, ProtocolException
from util import get_open_port

log = logging.getLogger(__name__)

class Worker(QObject):
    do_work = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._do_work)

    def startTimer(self):
        self.timer.start()

    def stopTimer(self):
        self.timer.stop()

    def _do_work(self):
        self.do_work.emit()


class SopCast(Protocol):
    name = "SopCast Protocol"
    desc = "SopCast Protocol Backend for TV-Maxe"
    version = "0.01"
    protocols = ["sop"]

    def __init__(self, parent=None):
        super().__init__(parent)

        self.protocol_ready_emited = False
        self.monitor_thread = None
        self.worker = None
        self.spc = None

        self.spsc = None
        for spsc in ["sp-sc", "sp-sc-auth", "sop"]:
            if getattr(sys, 'frozen', False):
                self.spsc = os.path.join(sys._MEIPASS, 'sp-sc')
            else:
                self.spsc = shutil.which(spsc) or shutil.which(spsc, '.')
            if self.spsc:
                log.debug('Found SopCast executable at {0}'.format(self.spsc))
                break

        if not self.spsc:
            log.error("SopCast executable not found")
            raise ProtocolException("SopCast executable not found")

        settings = QApplication.instance().settings_manager
        if settings.value("sopcast/staticports", False):
            self.inport = settings.value("sopcast/inport", get_open_port())
            self.outport = settings.value("sopcast/outport", get_open_port())
        else:
            self.inport = get_open_port()
            self.outport = get_open_port()

        log.debug('inport: {0}'.format(self.inport))
        log.debug('outport: {0}'.format(self.outport))

    def _monitor_connection(self):
        if not self.spc:
            self.worker.stopTimer()
            return

        if not self.protocol_ready_emited:
            try:
                r = requests.head('http://127.0.0.1:{0}'.format(self.outport))
            except requests.exceptions.ConnectionError as e:
                return

            if r.status_code != 200:
                return

            log.debug('Ready to play, emitting signal')
            self.protocol_ready.emit(
                "http://127.0.0.1:{0}".format(self.outport))
            self.protocol_ready_emited = True

        errorlevel = self.spc.poll()
        if  errorlevel:
            if errorlevel != -9:
                self.protocol_error.emit(self.url, "Stream not available.")
                self.spc = None
                self.url = None

    def load_url(self, url, args=None):
        self.protocol_ready_emited = False
        self.monitor_thread = QThread(self)
        self.worker = Worker()
        self.worker.do_work.connect(self._monitor_connection)
        self.monitor_thread.started.connect(self.worker.startTimer)
        self.worker.moveToThread(self.monitor_thread)

        log.debug('Loading url: {0}'.format(url))
        self.url = url
        try:
            self.spc = subprocess.Popen(
                [
                    self.spsc,
                    self.url,
                    str(self.inport),
                    str(self.outport)
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL)
            self.monitor_thread.start()
        except Exception as e:
            log.debug(str(e))
            self.protocol_error.emit(url, "Cannot start SopCast executable.")
            self.spc = None
            self.url = None

    def stop(self):
        log.debug('Stopping')
        self.url = None
        self.protocol_ready_emited = None
        if self.spc:
            try:
                os.kill(self.spc.pid, 9)
            except ProcessLookupError as e:
                log.debug('SopCast cannot be killed because it is already killed')
                log.debug('What is dead may never die')
            self.spc = None
        self.worker.stopTimer()
        self.monitor_thread.quit()
        self.deleteLater()


__classname__ = SopCast