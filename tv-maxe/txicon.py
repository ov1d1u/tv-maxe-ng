from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon, QPixmap, QPalette
from PyQt5.QtCore import Qt

class TXIcon(QIcon):
    def __init__(self, filename="", tint_color=None):
        palette = QApplication.instance().palette()

        px = QPixmap(filename)
        pxr = QPixmap(px.size())
        if not tint_color:
            pxr.fill(palette.color(QPalette.ButtonText))
        else:
            pxr.fill(tint_color)
        pxr.setMask(px.createMaskFromColor((Qt.transparent)))
        super().__init__(pxr)