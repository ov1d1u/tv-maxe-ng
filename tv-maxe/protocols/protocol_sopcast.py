import os
import subprocess
import shutil
import time
import requests
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread, QTimer

from protocols import Protocol

class SopCast(Protocol):
    name = "SopCast Protocol"
    desc = "SopCast Protocol Backend for TV-Maxe"
    version = "0.01"
    protocols = ["sop"]

    def __init__(self):
        super().__init__()

        self.spsc = None
        for spsc in ["sp-sc", "sp-sc-auth", "sop"]:
            self.spsc = shutil.which(spsc)
            if self.spsc:
                break

        self.protocol_ready_emited = False
        self.monitor_thread = QThread(self)
        self.monitor_timer = QTimer()
        self.monitor_timer.setInterval(500);
        self.monitor_timer.moveToThread(self.monitor_thread)
        self.monitor_timer.timeout.connect(self._monitor_connection)
        self.monitor_thread.started.connect(self.monitor_timer.start);

        if not self.spsc:
            raise OSError(42, "SopCast executable not found")

        settings = QApplication.instance().settings_manager
        if (settings.value("sopcast/inport")):
            self.inport = int(settings.value("sopcast/inport"))
        else:
            self.inport = self._get_open_port()

        if (settings.value("sopcast/outport")):
            self.outport = int(settings.value("sopcast/outport"))
        else:
            self.outport = self._get_open_port()

    def _get_open_port(self):
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("",0))
        s.listen(1)
        port = s.getsockname()[1]
        s.close()
        return port

    def _monitor_connection(self):
        if not self.protocol_ready_emited:
            try:
                r = requests.head('http://127.0.0.1:{0}'.format(self.outport))
                if r.status_code != 200:
                    raise ValueError('HTTP Server Not Ready')
                self.protocol_ready.emit(
                    "http://127.0.0.1:{0}".format(self.outport))
                self.protocol_ready_emited = True
            except Exception as e:
                return

        errorlevel = self.spc.poll()
        if  errorlevel:
            if errorlevel != -9:
                self.protocol_error.emit(self.url, "Stream not available.")
                self.spc = None
                self.url = None

    def load_url(self, url):
        self.url = url
        try:
            self.spc = subprocess.Popen(
                [
                    self.spsc,
                    self.url,
                    str(self.inport),
                    str(self.outport)
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE)
            self.monitor_thread.start()
        except Exception as e:
            print(e)
            self.protocol_error.emit(url, "Cannot start SopCast executable.")
            self.spc = None
            self.url = None

    def stop(self):
        self.url = None
        self.protocol_ready_emited = None
        self.monitor_thread.terminate()
        if self.spc:
            try:
                os.kill(self.spc.pid, 9)
            except ProcessLookupError as e:
                print('SopCast is already ded :(')
            self.spc = None


__classname__ = SopCast