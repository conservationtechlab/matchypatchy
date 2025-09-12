from PyQt6.QtWidgets import QFrame, QSizePolicy

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
