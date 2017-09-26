import os
import subprocess
import threading
import shutil
import time
import requests
from PyQt5.QtWidgets import QApplication

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

    def _waitConnection(self):
        progress = 0.0
        protocol_ready_emited = False
        while self.spc:
            if not protocol_ready_emited:
                try:
                    r = requests.head('http://127.0.0.1:{0}'.format(self.outport))
                    if r.status_code != 200:
                        raise ValueError('HTTP Server Not Ready')
                    self.protocol_ready.emit(
                        "http://127.0.0.1:{0}".format(self.outport))
                    protocol_ready_emited = True
                except Exception as e:
                    time.sleep(1)
                    continue

            errorlevel = self.spc.poll()
            if  errorlevel:
                if errorlevel != -9:
                    self.protocol_error.emit("Stream not available.")
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
            threading.Thread(target=self._waitConnection).start()
        except Exception as e:
            print(e)
            self.protocol_error.emit(url, "Cannot start SopCast executable.")
            self.spc = None
            self.url = None

    def stop(self):
        self.url = None
        if self.spc:
            os.kill(self.spc.pid, 9)
            self.spc = None


__classname__ = SopCast