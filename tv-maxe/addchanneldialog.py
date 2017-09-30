import os
import uuid
import json
from io import BytesIO
from PyQt5 import uic
from PyQt5.QtWidgets import QWidget, QDialog, QApplication, QAbstractItemView, QFileDialog, QMessageBox
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QModelIndex, QBuffer, QByteArray, QIODevice

from models.channel import Channel

class AddChannelDialog(QDialog):
    channel_saved = pyqtSignal(Channel)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        uic.loadUi('ui/addChannel.ui', self)

        self.description_label.setText("{0}{1}. ".format(
            self.description_label.text(),
            ", ".join(list(QApplication.instance().protocol_plugins.keys()))
        ))

        self.params_treeview.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.params_treeview.setUniformRowHeights(True)
        model = QStandardItemModel(0, 2)
        model.setHorizontalHeaderLabels(['key', 'value'])
        self.params_treeview.setModel(model)
        self.params_treeview.itemDelegate().closeEditor.connect(self.close_editor)

    @pyqtSlot()
    def addParameter(self):
        row = [QStandardItem(), QStandardItem()]
        self.params_treeview.model().appendRow(row)
        self.params_treeview.setCurrentIndex(self.params_treeview.model().indexFromItem(row[0]))
        self.params_treeview.edit(self.params_treeview.model().indexFromItem(row[0]))

    @pyqtSlot()
    def removeParameter(self):
        self.params_treeview.model().removeRow(self.params_treeview.currentIndex().row())

    @pyqtSlot(QModelIndex)
    def selectionChanged(self, index):
        self.remove_param_button.setEnabled(True)

    @pyqtSlot()
    def chooseChannelIcon(self):
        filename = QFileDialog.getOpenFileName(
            self,
            self.tr("Select icon file..."),
            os.path.expanduser("~"),
            self.tr("Images (*.png *.gif *.svg)")
        )
        if filename[0]:
            icon = QIcon(filename[0])
            self.select_icon_button.setIcon(icon)

    def close_editor(self, editor, hint):
        if editor.text():
            current_index = self.params_treeview.currentIndex()
            if current_index.column() == 1:
                self.remove_param_button.setEnabled(True)
                return
            next_index = self.params_treeview.model().index(current_index.row(), 1)
            self.params_treeview.setCurrentIndex(next_index)
            self.params_treeview.edit(next_index)
        else:
            self.params_treeview.model().removeRow(self.params_treeview.currentIndex().row())

    @pyqtSlot()
    def accept(self):
        channel_name = self.channel_name_lineedit.text()
        channel_type = 'tv' if self.channel_type_buttongroup.checkedButton() == self.tv_radiobutton else 'radio'
        stream_url = self.stream_url_lineedit.text()

        if len(channel_name.strip()) == 0:
            QMessageBox.critical(
                self,
                self.tr("Could not save channel"),
                self.tr("Channel name cannot be empty."))
            return

        if len(stream_url.strip()) == 0:
            QMessageBox.critical(
                self,
                self.tr("Could not save channel"),
                self.tr("Stream address cannot be empty."))
            return

        schema_supported = False
        for schema in list(QApplication.instance().protocol_plugins.keys()):
            if stream_url.startswith(schema):
                schema_supported = True
                break

        if not schema_supported:
            QMessageBox.critical(
                self,
                self.tr("Could not save channel"),
                self.tr("This protocol is not supported by TV-Maxe or your system."))
            return

        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.WriteOnly)
        self.select_icon_button.icon().pixmap(256, 256).save(buffer, 'PNG')
        string_io = BytesIO(byte_array)
        string_io.seek(0)
        icon_data = string_io.read()

        params_dict = {}
        for i in range(self.params_treeview.model().rowCount()):
            key = self.params_treeview.model().item(i, 0).text()
            value = self.params_treeview.model().item(i, 1).text()
            params_dict[key] = value

        channel_dict = {
            "id": uuid.uuid4().hex,
            "icon": icon_data,
            "name": channel_name,
            "streamurls": json.dumps([stream_url]),
            "params": json.dumps({stream_url: params_dict})
        }

        channel = Channel(channel_dict, channel_type)
        self.channel_saved.emit(channel)
        self.close()
        self.deleteLater()