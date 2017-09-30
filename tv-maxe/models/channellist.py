import os
import logging
import sqlite3
from functools import reduce

import paths
from models.channel import Channel

log = logging.getLogger(__name__)

class ChannelList:
    def __init__(self, data, origin_url):
        self.data = data
        self.origin_url = origin_url
        self.cached_path = os.path.join(
            paths.cache_dir,
            str(reduce(lambda x,y:x+y, map(ord, self.origin_url)))
        )

        log.debug('Caching channel list "{0}" to: {1}'.format(origin_url, self.cached_path))
        fh = open(self.cached_path, 'wb')
        fh.write(self.data)
        fh.close()

    @property
    def name(self):
        conn = sqlite3.connect(self.cached_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("SELECT * FROM info")
        row = c.fetchone()
        c.close()
        return row['name']

    @property
    def tv_channels(self):
        channels = []

        conn = sqlite3.connect(self.cached_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("SELECT * FROM tv_channels")
        for row in c.fetchall():
            channel = Channel(row, 'tv', self.origin_url)
            channels.append(channel)
            log.debug('Found TV Channel: {0} with ID: {1}'.format(channel.name, channel.id))
        
        conn.close()

        return channels

    @property
    def radio_channels(self):
        channels = []

        conn = sqlite3.connect(self.cached_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("SELECT * FROM radio_channels")
        for row in c.fetchall():
            channel = Channel(row, 'radio', self.origin_url)
            channels.append(channel)
            log.debug('Found Radio Channel: {0} with ID: {1}'.format(channel.name, channel.id))
        
        conn.close()

        return channels

    def __eq__(self, obj):
        if isinstance(obj, ChannelList):
            return obj.origin_url == self.origin_url
        return False