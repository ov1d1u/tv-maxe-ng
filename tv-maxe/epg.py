import datetime
import logging
import json
import os
import sqlite3
from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QAbstractItemView, QMessageBox
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt5.QtGui import QImage, QPixmap, QStandardItemModel, QStandardItem
from PyQt5.QtCore import QUrl, Qt

import paths
from util import toLocalTime
from channellistmanager import ChannelListManager

log = logging.getLogger(__name__)

class EPGDialog(QDialog):
    def __init__(self, channel, parent=None):
        super(QDialog, self).__init__(parent)
        uic.loadUi('ui/epg.ui', self)

        self.setWindowTitle(self.tr("TV Guide for {0}").format(channel.name))
        self.channel_name_label.setText(channel.name)
        image = QImage()
        image.loadFromData(channel.icon)
        self.icon_label.setPixmap(
            QPixmap.fromImage(image).scaled(
                self.icon_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        )

        combobox_model = QStandardItemModel(0, 2)
        self.days_combobox.setModel(combobox_model)
        self.days_combobox.setModelColumn(1)
        self.days_combobox.activated.connect(self.day_activated)

        self.epg_treeview.setSelectionMode(QAbstractItemView.NoSelection)
        self.epg_treeview.setUniformRowHeights(True)
        treeview_model = QStandardItemModel(0, 2)
        self.epg_treeview.setModel(treeview_model)
        self.epg_treeview.setColumnWidth(0, 80)

        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)
        self.progress_bar.hide()

        self.channel = channel
        self.origin_chlist = None
        for chlist in ChannelListManager.channellists:
            if chlist.origin_url == channel.origin:
                self.origin_chlist = chlist

        start_date = datetime.datetime.today()
        for day in (start_date + datetime.timedelta(n) for n in range(7)):
            combobox_model.appendRow(
                [QStandardItem(day.strftime("%Y-%m-%d")), QStandardItem(day.strftime("%A, %x").capitalize())]
            )

        self.access_manager = None
        self.day_activated(0)

    def day_activated(self, index):
        self.epg_treeview.setHeaderHidden(True)
        self.epg_treeview.model().clear()
        if self.origin_chlist:
            datestring = self.days_combobox.model().item(index, 0).text()
            url = "{0}?action=getGuide&channel={1}&date={2}".format(
                self.origin_chlist.epg_url,
                self.channel.id,
                datestring
            )            

            cached_json = self.epg_from_cache(self.channel.id, datestring)
            if cached_json:
                log.debug("Found EPG in cache for {0}".format(datestring))
                self.process_data(cached_json)
            else:
                log.debug('Retrieving EPG data from {0}'.format(url))

                if self.access_manager:
                    self.access_manager.finished.disconnect()
                    self.access_manager = None

                request = QNetworkRequest(QUrl(url))
                self.access_manager = QNetworkAccessManager()
                self.access_manager.finished.connect(self.handle_response)
                self.access_manager.get(request)
                self.progress_bar.show()

    def handle_response(self, response):
        self.progress_bar.hide()
        if response.error() == QNetworkReply.NoError:
            log.debug('Retrieved EPG for {0}'.format(self.channel.name))
            json_data = bytes(response.readAll())
            self.cache_epg(self.channel.id, self.days_combobox.model().item(self.days_combobox.currentIndex(), 0).text(), json_data)
            self.process_data(json_data)
        elif response.error() == QNetworkReply.ContentNotFoundError:
            QMessageBox.critical(
                self,
                self.tr("Could not load EPG data"),
                self.tr("EPG data is not available for this channel.")
            )
    
    def process_data(self, json_data):
        try:
            epg_list = json.loads(json_data)
        except json.decoder.JSONDecodeError:
            log.error("Error while decoding JSON data")
            QMessageBox.critical(
                self,
                self.tr("Could not load EPG data"),
                self.tr("EPG data format is invalid.")
            )
            return

        for epg_line in epg_list:
            row = [
                QStandardItem(toLocalTime(epg_line[0])), QStandardItem(epg_line[1])
            ]
            self.epg_treeview.model().appendRow(row)

        self.epg_treeview.model().setHorizontalHeaderLabels(['Time', 'Show'])
        self.epg_treeview.setHeaderHidden(False)
        self.epg_treeview.resizeColumnToContents(0)

    def cache_epg(self, channel_id, date_str, json_data):
        if not os.path.exists(paths.EPG_CACHE):
            conn = sqlite3.connect(paths.EPG_CACHE)
            c = conn.cursor()
            c.execute("CREATE TABLE epg_cache (channel_id text, date_str text, json_data blob)")
            conn.commit()
            conn.close()

        conn = sqlite3.connect(paths.EPG_CACHE)
        c = conn.cursor()
        c.execute(
            "INSERT INTO epg_cache (channel_id, date_str, json_data) VALUES (:channel_id, :date_str, :json_data)",
            {
                "channel_id": channel_id,
                "date_str": date_str,
                "json_data": json_data
            }
        )
        conn.commit()
        conn.close()

    def epg_from_cache(self, channel_id, date_str):
        if not os.path.exists(paths.EPG_CACHE):
            return None

        conn = sqlite3.connect(paths.EPG_CACHE)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM epg_cache WHERE channel_id=? AND date_str=?", (channel_id, date_str))
        row = c.fetchone()
        conn.close()
        if row:
            return row['json_data']
        return None