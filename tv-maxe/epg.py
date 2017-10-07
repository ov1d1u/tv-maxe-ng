import datetime
import logging
import json
import os
import sqlite3
import itertools
from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QAbstractItemView, QMessageBox
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt5.QtGui import QImage, QPixmap, QStandardItemModel, QStandardItem
from PyQt5.QtCore import QUrl, Qt, QObject, QItemSelectionModel, pyqtSignal

import paths
from util import toLocalTime
from channellistmanager import ChannelListManager

log = logging.getLogger(__name__)

class EPGDialog(QDialog):
    def __init__(self, channel, parent=None):
        super(QDialog, self).__init__(parent)
        uic.loadUi('ui/epg.ui', self)

        self.channel = channel

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

        start_date = datetime.datetime.today()
        for day in (start_date + datetime.timedelta(n) for n in range(7)):
            combobox_model.appendRow(
                [QStandardItem(day.strftime("%Y-%m-%d")), QStandardItem(day.strftime("%A, %x").capitalize())]
            )

        self.access_manager = None
        self.day_activated(0)

    def day_activated(self, index):
        self.progress_bar.show()
        self.epg_treeview.setHeaderHidden(True)
        self.epg_treeview.model().clear()

        self.epg_retriever = EPGRetriever(self.channel, self.days_combobox.model().item(index, 0).text())
        self.epg_retriever.epg_data_available.connect(self.display_epg)
        self.epg_retriever.epg_data_error.connect(self.epg_data_error)
        self.epg_retriever.retrieve_epg()

    def display_epg(self, epg_list):
        self.progress_bar.hide()
        hours = [toLocalTime(x[0]) for x in epg_list]
        now = datetime.datetime.strptime(datetime.datetime.now().strftime("%H:%M"), "%H:%M")
        current = [x for x in itertools.takewhile(lambda t: now >= datetime.datetime.strptime(t, "%H:%M"), hours)][-1]

        for idx, epg_line in enumerate(epg_list):
            row = [
                QStandardItem(toLocalTime(epg_line[0])), QStandardItem(epg_line[1])
            ]
            self.epg_treeview.model().appendRow(row)
            if toLocalTime(epg_line[0]) == current and \
              self.days_combobox.model().item(self.days_combobox.currentIndex(), 0).text() == datetime.datetime.now().strftime("%Y-%m-%d"):
                selection = self.epg_treeview.selectionModel()
                selection.select(self.epg_treeview.model().index(idx, 0), QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)

        self.epg_treeview.model().setHorizontalHeaderLabels(['Time', 'Show'])
        self.epg_treeview.setHeaderHidden(False)
        self.epg_treeview.resizeColumnToContents(0)

    def epg_data_error(self, error_msg):
        self.progress_bar.hide()
        QMessageBox.critical(
            self,
            self.tr("EPG Error"),
            error_msg
        )


class EPGRetriever(QObject):
    epg_data_available = pyqtSignal(list)
    epg_data_error = pyqtSignal(str)

    def __init__(self, channel, date_str, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.channel = channel
        self.date_str = date_str

        self.origin_chlist = None
        for chlist in ChannelListManager.channellists:
            if chlist.origin_url == channel.origin:
                self.origin_chlist = chlist
                break

        self.access_manager = QNetworkAccessManager(self)
        self.access_manager.finished.connect(self.handle_response)

    def retrieve_epg(self):
        if self.origin_chlist:
            url = "{0}?action=getGuide&channel={1}&date={2}".format(
                self.origin_chlist.epg_url,
                self.channel.id,
                self.date_str
            )            

            cached_json = self.epg_from_cache(self.channel.id, self.date_str)
            if cached_json:
                log.debug("Found EPG in cache for {0}".format(self.date_str))
                self.process_data(cached_json)
            else:
                log.debug('Retrieving EPG data from {0}'.format(url))
                request = QNetworkRequest(QUrl(url))
                self.access_manager.get(request)

    def handle_response(self, response):
        if response.error() == QNetworkReply.NoError:
            log.debug('Retrieved EPG for {0}'.format(self.channel.name))
            json_data = bytes(response.readAll())
            self.cache_epg(self.channel.id, self.date_str, json_data)
            self.process_data(json_data)
        elif response.error() == QNetworkReply.ContentNotFoundError:
            self.epg_data_error.emit("EPG data is not available for this channel.")
        else:
            self.epg_data_error.emit(response.errorString())

    def process_data(self, json_data):
        try:
            epg_list = json.loads(json_data.decode("utf-8"))
        except json.decoder.JSONDecodeError:
            log.error("Error while decoding JSON data")
            self.epg_data_error.emit("EPG data format is invalid.")
            return

        self.epg_data_available.emit(epg_list)

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
