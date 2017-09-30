from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QPainter, QFontMetrics
from PyQt5.QtCore import Qt

class ElidedLabel(QLabel):
    def resizeEvent(self, event):
        metrics = QFontMetrics(self.font())
        elidedText = metrics.elidedText(self.text(), Qt.ElideRight, self.width())
        self.setText(elidedText)