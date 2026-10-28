"""
Image toolbar for the compare view: brightness, contrast, sharpness, edit, open, favorite

Floats over the bottom-left corner of the image it belongs to, so the images
keep the room a row of sliders and buttons used to take. The sliders open from
the Adjust button.
"""
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QVBoxLayout, QLabel, QSlider, QPushButton,
                             QMenu, QWidgetAction, QWidget)
from PyQt6.QtCore import Qt, QEvent, QSize, QPoint

from matchypatchy.gui.widgets.styles import icon, set_variant, FAVORITE


class ImageAdjustBar(QFrame):
    """Toolbar over a MediaWidget for adjusting and acting on the shown image."""

    FAVORITE_STYLE = f""" QPushButton {{ color: {FAVORITE}; }}"""
    MARGIN = 10

    def __init__(self, display, mediawidget, side):
        super().__init__(mediawidget)
        # display_compare
        self.display = display
        # media widget object it connects to
        self.mediawidget = mediawidget
        self.side = side  # query or match
        self.brightness_factor = 1.0
        self.contrast_factor = 1.0
        self.sharpness_factor = 1.0
        self.setStyleSheet("ImageAdjustBar { background: rgba(20, 23, 21, 215); border-radius: 8px; }")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # Adjust: the three sliders in a dropdown
        self.button_adjust = self._tool("contrast", "Brightness, contrast and sharpness")
        self.adjust_menu = QMenu(self)
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(12, 10, 12, 10)
        self.slider_brightness = self._slider(panel_layout, "Brightness", self.adjust_brightness)
        self.slider_contrast = self._slider(panel_layout, "Contrast", self.adjust_contrast)
        self.slider_sharpness = self._slider(panel_layout, "Sharpness", self.adjust_sharpness)
        button_reset = QPushButton("Reset")
        button_reset.clicked.connect(self.reset)
        panel_layout.addWidget(button_reset, 0, Qt.AlignmentFlag.AlignRight)
        action = QWidgetAction(self.adjust_menu)
        action.setDefaultWidget(panel)
        self.adjust_menu.addAction(action)
        self.button_adjust.clicked.connect(
            lambda: self.adjust_menu.popup(self.button_adjust.mapToGlobal(self.button_adjust.rect().topLeft())
                                           - self._menu_offset()))
        layout.addWidget(self.button_adjust)
        # Edit Image
        button_edit = self._tool("edit", "Edit ROI and metadata")
        button_edit.clicked.connect(self.edit_image)
        layout.addWidget(button_edit)
        # Open Image
        button_open = self._tool("open", "Open the original file")
        button_open.clicked.connect(self.open_image)
        layout.addWidget(button_open)
        # favorite
        self.button_favorite = self._tool("heart", "Favorite")
        self.button_favorite.setCheckable(True)
        self.button_favorite.clicked.connect(self.press_favorite)
        layout.addWidget(self.button_favorite)

        self.adjustSize()
        # follow the image's size
        mediawidget.installEventFilter(self)
        self._place()

    def _tool(self, icon_name, tooltip):
        button = QPushButton()
        button.setIcon(icon(icon_name, "#E9ECE9"))
        button.setIconSize(QSize(18, 18))
        button.setFixedSize(34, 34)
        button.setToolTip(tooltip)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        set_variant(button, "overlay")
        return button

    def _slider(self, layout, name, slot):
        layout.addWidget(QLabel(name))
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(25, 75)
        slider.setValue(50)
        slider.setMinimumWidth(200)
        slider.valueChanged.connect(slot)
        layout.addWidget(slider)
        return slider

    def _menu_offset(self):
        """Open the sliders above the toolbar, it sits at the bottom of the image"""
        return QPoint(0, self.adjust_menu.sizeHint().height() + 6)

    def eventFilter(self, obj, event):
        if obj is self.mediawidget and event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self._place()
        return super().eventFilter(obj, event)

    def _place(self):
        """Keep the toolbar in the image's bottom-left corner, above the video controls"""
        self.adjustSize()
        bottom = self.mediawidget.height() - self.height() - self.MARGIN
        bar = getattr(self.mediawidget, "playbackbar", None)
        if bar is not None and bar.isVisible():
            bottom -= bar.height()
        self.move(self.MARGIN, max(0, bottom))
        self.raise_()

    def adjust_brightness(self, value):
        """
        QImage needs to be reconverted each time
        """
        self.brightness_factor = value / 50
        self.mediawidget.image_widget.adjust(brightness=self.brightness_factor,
                                             contrast=self.contrast_factor,
                                             sharpness=self.sharpness_factor)

    def adjust_contrast(self, value):
        """
        QImage needs to be reconverted each time
        """
        self.contrast_factor = value / 50
        self.mediawidget.image_widget.adjust(brightness=self.brightness_factor,
                                             contrast=self.contrast_factor,
                                             sharpness=self.sharpness_factor)

    def adjust_sharpness(self, value):
        """
        QImage needs to be reconverted each time
        """
        self.sharpness_factor = value / 50
        self.mediawidget.image_widget.adjust(brightness=self.brightness_factor,
                                             contrast=self.contrast_factor,
                                             sharpness=self.sharpness_factor)

    def reset(self):
        """Reset sliders and image adjustments"""
        for slider in (self.slider_brightness, self.slider_contrast, self.slider_sharpness):
            slider.blockSignals(True)
            slider.setValue(50)
            slider.blockSignals(False)
        self.brightness_factor = 1.0
        self.contrast_factor = 1.0
        self.sharpness_factor = 1.0
        self.mediawidget.image_widget.reset()

    def press_favorite(self):
        """Press favorite button, connect to Compare View"""
        current_rid = self.display.get_rid(self.side)
        self.display.press_favorite_button(current_rid)

    def set_favorite(self, state):
        """Show a filled red heart when the shown roi is a favorite"""
        self.button_favorite.setChecked(bool(state))
        if state:
            self.button_favorite.setIcon(icon("heart", FAVORITE, fill=FAVORITE))
        else:
            self.button_favorite.setIcon(icon("heart", "#E9ECE9"))

    def edit_image(self):
        """Edit image button, connect to Compare View"""
        current_rid = self.display.get_rid(self.side)
        self.display.edit_image(current_rid)

    def open_image(self):
        """Open image button, connect to Compare View"""
        current_rid = self.display.get_rid(self.side)
        self.display.open_image(current_rid)
