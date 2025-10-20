"""
Custom assets for the GUI, such as buttons and separators.

"""
from PyQt6.QtWidgets import (QFrame, QSizePolicy, QPushButton, QComboBox, QWidget,
                             QSlider, QLabel, QHBoxLayout, QVBoxLayout,
                             QSpacerItem)
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import Qt, pyqtSignal


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


class ComboBoxSeparator(QComboBox):
    def __init__(self):
        super().__init__()
        self.setModel(QStandardItemModel())

    def add_separator(self, label="────────"):
        separator = QStandardItem(label)
        separator.setFlags(Qt.ItemFlag.NoItemFlags)  # Non-selectable, disabled
        self.model().appendRow(separator)


class FilterBox(QComboBox):
    def __init__(self, initial_list, width):
        super().__init__()
        self.setModel(QStandardItemModel())
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedWidth(width)
        self.addItems([el[1] for el in initial_list])


class ThreePointSlider(QWidget):
    state_changed = pyqtSignal(int)  # emits 0,1,2

    def __init__(self, labels=None, initial: int = 0, parent=None):
        super().__init__(parent)

        self.labels = labels

        # Slider setup: discrete range 0..2
        self.slider = ClickableSlider(Qt.Orientation.Horizontal, self)
        self.slider.setFixedWidth(50)
        self.slider.setRange(0, 2)
        self.slider.setSingleStep(1)
        self.slider.setPageStep(1)
        self.slider.setTickInterval(1)
        self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider.setTracking(True)
        self.slider.setStyleSheet("""
                QSlider::groove:horizontal { height: 3px; background: #5e5e5e; border-radius: 3px; }
                QSlider::sub-page:horizontal { background: transparent; }
                QSlider::add-page:horizontal { background: transparent; }
                QSlider::handle:horizontal { background: #444; height: 15px; width: 12px; margin: -6px 0; border-radius: 8px; }
                """)

        initial = max(0, min(2, int(initial)))
        self.slider.setValue(initial)

        # Labels row under slider
        if self.labels is not None:
            labels_layout = QHBoxLayout()
            labels_layout.setContentsMargins(6, 0, 6, 0)
            labels_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

            for txt in self.labels:
                lbl = QLabel(txt, self)
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                labels_layout.addWidget(lbl)

            labels_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # Main layout
        v = QHBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        self.left_button = QPushButton("Left")
        self.left_button.setFixedWidth(50)
        self.left_button.pressed.connect(self.press_left)
        self.right_button = QPushButton("Right")
        self.right_button.setFixedWidth(50)
        self.right_button.pressed.connect(self.press_right)
        v.addWidget(self.left_button)
        v.addWidget(self.slider)
        v.addWidget(self.right_button)
        if self.labels is not None:
            v.addLayout(labels_layout)

        # Signals
        self.slider.valueChanged.connect(self._on_value_changed)
        self.slider.sliderReleased.connect(self._snap_to_tick)

        # Ensure initial state is emitted
        self._on_value_changed(self.slider.value())

    def _snap_to_tick(self):
        """Snap to nearest integer (defensive)."""
        val = self.slider.value()
        snapped = int(round(val))
        if snapped != val:
            # setting value will trigger valueChanged
            self.slider.setValue(snapped)
        # explicitly emit current index
        self.state_changed.emit(self.slider.value())

    def _on_value_changed(self, val: int):
        """Keep visual label and emit integer index."""
        idx = int(round(val))
        # Force integer if anything weird happens
        if idx != val:
            self.slider.blockSignals(True)
            self.slider.setValue(idx)
            self.slider.blockSignals(False)
        self.state_changed.emit(idx)

    def set_index(self, idx: int):
        idx = max(0, min(2, int(idx)))
        self.slider.setValue(idx)

    def index(self) -> int:
        return int(self.slider.value())
    
    def press_left(self):
        self.set_index(0)

    def press_right(self):
        self.set_index(2)

class ClickableSlider(QSlider):
    """QSlider that jumps to the position that was clicked on the groove."""
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # event.position() returns a QPointF in Qt6, fallback to event.pos()
            x = event.position().x() if hasattr(event, "position") else event.pos().x()
            w = self.width()

            # Compute an approximate value from x. This is sufficient for our discrete 3-point slider.
            # For more exact behavior with custom handle sizes, use QStyle metrics.
            min_v, max_v = self.minimum(), self.maximum()
            if w > 0:
                ratio = x / w
                val = round(min_v + ratio * (max_v - min_v))
            else:
                val = min_v

            # clamp and set value
            val = max(min_v, min(max_v, int(val)))
            self.setValue(val)

            # Accept and don't call base behavior that implements page-step jumps.
            event.accept()
        else:
            super().mousePressEvent(event)