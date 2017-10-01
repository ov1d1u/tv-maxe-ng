from urllib.parse import urlparse
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QAbstractItemView
from PyQt5.QtGui import QImage, QPixmap, QStandardItemModel, QStandardItem

from channellistmanager import ChannelListManager

class ChannelInfoDialog(QDialog):
    def __init__(self, channel, parent=None):
        super(QDialog, self).__init__(parent)
        uic.loadUi('ui/channelInfo.ui', self)

        self.setWindowTitle(self.tr("Channel Info: {0}").format(channel.name))

        self.streams_treeview.setSelectionMode(QAbstractItemView.NoSelection)
        self.streams_treeview.setUniformRowHeights(True)
        model = QStandardItemModel(0, 2)
        model.setHorizontalHeaderLabels(['Protocol', 'Address'])
        self.streams_treeview.setModel(model)
        self.streams_treeview.setColumnWidth(0, 80)

        image = QImage()
        image.loadFromData(channel.icon)
        self.icon_label.setPixmap(
            QPixmap.fromImage(image).scaled(
                self.icon_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        )
        self.channel_name_label.setText(channel.name)

        origin_chlist = None
        for chlist in ChannelListManager.channellists:
            if chlist.origin_url == channel.origin:
                origin_chlist = chlist
        self.channel_list_label.setText(origin_chlist.name)
        self.channel_list_url.setText("({0})".format(channel.origin))

        for streamurl in channel.streamurls:
            parse_result = urlparse(streamurl)
            schema_name = parse_result.scheme.upper()
            if parse_result.scheme == 'sop':
                schema_name = "SopCast"
            protocol_item = QStandardItem(schema_name)
            address_item = QStandardItem(streamurl)
            self.streams_treeview.model().appendRow([protocol_item, address_item])