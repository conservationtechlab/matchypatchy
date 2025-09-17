from PyQt6.QtWidgets import QFrame, QSizePolicy, QPushButton

class VerticalSeparator(QFrame):
    def __init__(self, linewidth=1):
        super().__init__()
        self.setFrameShape(QFrame.Shape.VLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)
        self.setLineWidth(linewidth)

class HorizontalSeparator(QFrame):
    def __init__(self, linewidth=1):
        super().__init__()
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)
        self.setLineWidth(linewidth)

class StandardButton(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        #self.setFixedHeight(30)
        self.setFixedWidth(100)
        #self.setStyleSheet("font-size: 14px; padding: 5px 15px;")