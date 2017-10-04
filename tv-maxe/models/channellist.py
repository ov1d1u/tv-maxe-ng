import os
import logging
import sqlite3
import getpass
from functools import reduce

import paths
from models.channel import Channel

log = logging.getLogger(__name__)

class ChannelList:
    def __init__(self, data, origin_url=None):
        self.data = data
        self.origin_url = origin_url
        if origin_url:
            self.cached_path = ChannelList.local_filename_for_url(origin_url)

            log.debug('Caching channel list "{0}" to: {1}'.format(origin_url, self.cached_path))
            fh = open(self.cached_path, 'wb')
            fh.write(self.data)
            fh.close()
        else:
            self.cached_path = self.origin_url = paths.LOCAL_CHANNEL_DB

    @staticmethod
    def local_filename_for_url(origin_url):
        return os.path.join(
            paths.CACHE_DIR,
            "{0}.db".format(str(reduce(lambda x,y:x+y, map(ord, origin_url))))
        )

    @staticmethod
    def create_user_db():
        conn = sqlite3.connect(paths.LOCAL_CHANNEL_DB)
        c = conn.cursor()
        c.execute("CREATE TABLE info (name text, version text, author text, url text, epgurl text)")
        c.execute("CREATE TABLE radio_channels (id text, icon blob, name text, streamurls text, params text, deleted bool)")
        c.execute("CREATE TABLE tv_channels (id text, icon blob, name text, streamurls text, params text, guide text, audiochannels text, deleted bool)")

        c.execute(
            "INSERT INTO info (name, version, author, url, epgurl) VALUES (?, ?, ?, ?, ?)",
            ("Local", "1.0", getpass.getuser(), "", "")
        )

        conn.commit()
        conn.close()

        fh = open(paths.LOCAL_CHANNEL_DB, 'rb')
        data = fh.read()
        fh.close()
        return ChannelList(data)

    @property
    def name(self):
        conn = sqlite3.connect(self.cached_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("SELECT * FROM info")
        row = c.fetchone()
        conn.close()
        return row['name']

    @property
    def epg_url(self):
        conn = sqlite3.connect(self.cached_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("SELECT * FROM info")
        row = c.fetchone()
        conn.close()
        return row['epgurl']

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

    def save_channel(self, channel):
        conn = sqlite3.connect(self.cached_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        if channel.type == 'tv':
            c.execute("""INSERT INTO tv_channels (id, icon, name, streamurls, params, guide, audiochannels, deleted)
                            VALUES (:id, :icon, :name, :streamurls, :params, :guide, :audiochannels, :deleted)""",
                            channel.to_dict()
            )
        else:
            c.execute("""INSERT INTO radio_channels (id, icon, name, streamurls, params, deleted)
                            VALUES (:id, :icon, :name, :streamurls, :params, :deleted)""",
                            channel.to_dict()
            )
        conn.commit()
        conn.close()

    def remove_channel(self, channel):
        conn = sqlite3.connect(self.cached_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        if channel.type == 'tv':
            c.execute("DELETE FROM tv_channels WHERE id=?", (channel.id, ))
        else:
            c.execute("DELETE FROM radio_channels WHERE id=?", (channel.id, ))
        conn.commit()
        conn.close()

    def __eq__(self, obj):
        if isinstance(obj, ChannelList):
            return obj.origin_url == self.origin_url
        return False

    def __hash__(self):
        return hash(self.origin_url)