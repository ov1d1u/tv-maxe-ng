import os
import threading
import sqlite3
from urllib.parse import urlparse
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt5.QtCore import pyqtSignal, QUrl, QObject

import paths
from models.channel import Channel

class ChannelListManager(QObject):
    channel_added = pyqtSignal(Channel)
    channel_removed = pyqtSignal(Channel)

    def download_chlists(self, urls):
        urls = [QUrl(url) for url in urls]
        self.access_manager = QNetworkAccessManager()
        self.access_manager.finished.connect(self.handle_response)

        for url in urls:
            request = QNetworkRequest()
            request.setUrl(url)
            self.access_manager.get(request)

    def handle_response(self, response):
        url = response.url().toString()

        if response.error() == QNetworkReply.NoError:
            data = response.readAll()
            parsed_url = urlparse(url)
            database = self.save_chlist(data, os.path.basename(parsed_url.path))
            self.load_chlist(database)

    def save_chlist(self, data, filename):
        path = os.path.join(paths.cache_dir, filename)
        fh = open(path, 'wb')
        fh.write(data)
        fh.close()
        return path

    def load_chlist(self, path):
        tv_channels = []
        radio_channels = []

        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("SELECT * FROM tv_channels")
        for row in c.fetchall():
            channel = Channel(row, 'tv')
            tv_channels.append(channel)
            self.channel_added.emit(channel)

        c.execute("SELECT * from radio_channels")
        for row in c.fetchall():
            channel = Channel(row, 'radio')
            radio_channels.append(row)
            self.channel_added.emit(channel)
