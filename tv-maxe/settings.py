import os
import shutil
import logging
import requests
from pathlib import Path
from PyQt5 import uic
from PyQt5.QtCore import Qt, QModelIndex, pyqtSlot
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import (QApplication, QDialog, QFileDialog, QLayout, QListWidgetItem,
    QAbstractItemView, QInputDialog, QLineEdit, QMessageBox)

from util import bytes2human

log = logging.getLogger(__name__)

class SubscriptionListItem(QListWidgetItem):
    __subscription = None

    @property
    def subscription(self):
        return self.__subscription

    @subscription.setter
    def subscription(self, subscription):
        __subscription = subscription


class SettingsDialog(QDialog):
    def __init__(self, parent):
        super(QDialog, self).__init__(parent)
        uic.loadUi('ui/settings.ui', self)

        self.settings_manager = QApplication.instance().settings_manager
        self.layout().setSizeConstraint(QLayout.SetFixedSize)
        self.subs_treeview.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.subs_treeview.setUniformRowHeights(True)
        model = QStandardItemModel(0, 2)
        model.setHorizontalHeaderLabels(['Enabled', 'URL'])
        self.subs_treeview.setModel(model)
        self.subs_treeview.setColumnWidth(0, 80)

        # General settings
        self.show_trayicon_checkbox.setChecked(
            self.settings_manager.value("trayicon", False, bool)
        )
        self.recording_path_lineedit.setText(
            self.settings_manager.value("recording/path", os.path.expanduser("~/Videos"), str)
        )

        # Sopcast Settings
        self.sopcast_static_ports.setChecked(
            self.settings_manager.value("sopcast/staticports", False, bool)
        )
        self.local_port_spinbox.setValue(
            self.settings_manager.value("sopcast/inport", 9000, int)
        )
        self.player_port_spinbox.setValue(
            self.settings_manager.value("sopcast/outport", 9001, int)
        )

        # Rest API settings
        self.rest_api_checkbox.setChecked(
            self.settings_manager.value("restapi/enabled", False, bool)
        )
        self.rest_api_spinbox.setValue(
            self.settings_manager.value("restapi/port", 8000, int)
        )

        # Subscriptions
        for idx, subscription in enumerate(self.settings_manager.get_subscriptions()):
            checkbox_item = QStandardItem()
            checkbox_item.setCheckable(True)
            checkbox_item.setCheckState(Qt.Unchecked if subscription[0] == False else Qt.Checked)
            model.setItem(idx, 0, checkbox_item)

            text_item = QStandardItem(subscription[1])
            model.setItem(idx, 1, text_item)

        self.show()

    def subscription_exists(self, sub_url):
        for i in range(0, self.subs_treeview.model().rowCount()):
            text_item = self.subs_treeview.model().item(i, 1)
            if sub_url == text_item.text():
                return True
        return False

    @pyqtSlot()
    def selectRecordingsDirectory(self):
        recording_path = QFileDialog.getExistingDirectory(
            self, 
            self.select_folder_button.text(),
            self.settings_manager.value("recording/path", os.path.expanduser("~/Videos")),
            QFileDialog.ShowDirsOnly
        )
        self.recording_path_lineedit.setText(recording_path)

    @pyqtSlot(str)
    def recordingPathChanged(self, text):
        free_disk = self.tr("Please provide a valid path")
        if text:
            path = Path(text)
            try:
                if path.is_dir():
                    free_disk = bytes2human(shutil.disk_usage(str(path)).free)
                else:
                    for parent in path.parents:
                        if parent.is_dir():
                            free_disk = bytes2human(shutil.disk_usage(str(parent)).free)
                            break
            except PermissionError:
                log.debug("Permission error: {0}".format(text))
        self.disk_space_label.setText(
            "Free disk space: {0}".format(
                free_disk
            )
        )

    @pyqtSlot(QModelIndex)
    def selectedSubscription(self, model_index):
        self.del_sub_button.setEnabled(True)

    @pyqtSlot()
    def addSubscription(self):
        sub_url, ok = QInputDialog.getText(
            self,
            self.tr("Add new subscription"),
            self.tr("Insert subscription URL:"),
            QLineEdit.Normal,
            "")
        if ok:
            try:
                r = requests.head(sub_url, allow_redirects=True)
                if r.status_code == 200:
                    if self.subscription_exists(sub_url):
                        QMessageBox.critical(
                            self,
                            self.tr("Add new subscription"),
                            self.tr("This subscription is already in your list."))
                        return

                    checkbox_item = QStandardItem()
                    checkbox_item.setCheckable(True)
                    checkbox_item.setCheckState(Qt.Checked)
                    text_item = QStandardItem(sub_url)

                    self.subs_treeview.model().appendRow([checkbox_item, text_item])
                    return
                else:
                    raise ConnectionError("HTTP error status: {0}".format(r.status_code))
            except:
                pass

            QMessageBox.critical(
                self,
                self.tr("Add new subscription"),
                self.tr("Failed to add subscription. Please check the URL and try again."))

    @pyqtSlot()
    def removeSubscription(self):
        current_index = self.subs_treeview.currentIndex().row()
        self.subs_treeview.model().takeRow(current_index)

    @pyqtSlot()
    def accept(self):
        # General settings
        self.settings_manager.setValue("trayicon", self.show_trayicon_checkbox.isChecked())
        self.settings_manager.setValue("recording/path", self.recording_path_lineedit.text())

        # Sopcast Settings
        self.settings_manager.setValue("sopcast/staticports", self.sopcast_static_ports.isChecked())
        self.settings_manager.setValue("sopcast/inport", self.local_port_spinbox.value())
        self.settings_manager.setValue("sopcast/outport", self.player_port_spinbox.value())

        # Rest API settings
        self.settings_manager.setValue("restapi/enabled", self.rest_api_checkbox.isChecked())
        self.settings_manager.setValue("restapi/port", self.rest_api_spinbox.value())

        # Subscriptions
        subscriptions = []
        for i in range(0, self.subs_treeview.model().rowCount()):
            checkbox_item = self.subs_treeview.model().item(i, 0)
            text_item = self.subs_treeview.model().item(i, 1)
            subscriptions.append(
                [True if checkbox_item.checkState() == Qt.Checked else False,
                text_item.text()]
            )
        self.settings_manager.setValue("subscriptions", subscriptions)

        self.close()
        self.deleteLater()

    @pyqtSlot()
    def reject(self):
        self.close()
        self.deleteLater()
