import os
import threading
import logging
from urllib.parse import urlparse
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt5.QtCore import pyqtSignal, QUrl, QObject, qDebug

import paths
from models.channellist import ChannelList
from models.channel import Channel

log = logging.getLogger(__name__)

class ChannelListManager(QObject):
    channellist_available = pyqtSignal(ChannelList)
    channel_added = pyqtSignal(Channel)
    channel_removed = pyqtSignal(Channel)

    def download_chlists(self, subscriptions):
        urls = []
        for subscription in subscriptions:
            if subscription[0] == True:
                urls.append(QUrl(subscription[1]))
        self.access_manager = QNetworkAccessManager()
        self.access_manager.finished.connect(self.handle_response)

        for url in urls:
            request = QNetworkRequest()
            request.setUrl(url)
            self.access_manager.get(request)

    def handle_response(self, response):
        url = response.url().toString()

        if response.error() == QNetworkReply.NoError:
            log.debug('Downloaded channel list: {0}'.format(url))
            data = response.readAll()
            chlist = ChannelList(data, url)

            try:
                self.load_chlist(chlist)
                self.channellist_available.emit(chlist)
            except Exception as e:
                log.error('Failed to process `{0}` ({1}): {2}'.format(
                    os.path.basename(chlist.origin_url),
                    chlist.cached_path,
                    e
                ))
        else:
            log.error('Failed to download channel list: {0}'.format(url))

    def load_chlist(self, chlist):
        log.debug('Processing channel list: {0}'.format(chlist.origin_url))

        for channel in chlist.tv_channels + chlist.radio_channels:
            self.channel_added.emit(channel)