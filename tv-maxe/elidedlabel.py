from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QPainter, QFontMetrics
from PyQt5.QtCore import Qt

class ElidedLabel(QLabel):
    _text = None
    _settingElidedText = False

    def resizeEvent(self, event):
        if not self._text:
            self._text = self.text()
        metrics = QFontMetrics(self.font())
        elidedText = metrics.elidedText(self._text, Qt.ElideRight, self.width())
        self.setElidedText(elidedText)

    def setText(self, text):
        if not self._settingElidedText:
            self._text = text
        super().setText(text)

    def setElidedText(self, elidedText):
        self._settingElidedText = True
        self.setText(elidedText)
        self._settingElidedText = False

    def minimumSizeHint(self):
        sizeHint = super().sizeHint()
        sizeHint.setWidth(100)
        return sizeHint