from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSlider, QPushButton
from PyQt6.QtCore import Qt


class ImageAdjustBar(QWidget):
    FAVORITE_STYLE = """ QPushButton { background-color: #b51b32; color: white; }"""

    def __init__(self, display, mediawidget, side):
        super().__init__()
        # display_compare
        self.display = display
        # media widget object it connects to
        self.mediawidget = mediawidget
        self.side = side # query or match
        self.brightness_factor = 1.0
        self.contrast_factor = 1.0
        self.sharpness_factor = 1.0

        # Layout ---------------------------------------------------------------   
        query_image_buttons = QHBoxLayout()
        # Brightness
        query_image_buttons.addWidget(QLabel("Brightness:"), 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.slider_brightness = QSlider(Qt.Orientation.Horizontal)
        self.slider_brightness.setRange(25, 75)  # Set range from 1 to 100
        self.slider_brightness.setValue(50)  # Set initial value
        self.slider_brightness.valueChanged.connect(self.adjust_brightness)
        query_image_buttons.addWidget(self.slider_brightness, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # Contrast
        query_image_buttons.addWidget(QLabel("Contrast:"), 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.slider_contrast = QSlider(Qt.Orientation.Horizontal)
        self.slider_contrast.setRange(25, 75)  # Set range from 1 to 100
        self.slider_contrast.setValue(50)  # Set initial value
        self.slider_contrast.valueChanged.connect(self.adjust_contrast)
        query_image_buttons.addWidget(self.slider_contrast, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # Sharpness
        query_image_buttons.addWidget(QLabel("Sharpness:"), 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.slider_sharpness = QSlider(Qt.Orientation.Horizontal)
        self.slider_sharpness.setRange(25, 75)  # Set range from 1 to 100
        self.slider_sharpness.setValue(50)  # Set initial value
        self.slider_sharpness.valueChanged.connect(self.adjust_sharpness)
        query_image_buttons.addWidget(self.slider_sharpness, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # Reset
        button_query_image_reset = QPushButton("Reset")
        button_query_image_reset.clicked.connect(self.reset)
        query_image_buttons.addWidget(button_query_image_reset, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # View Image
        button_query_image_edit = QPushButton("Edit Image")
        button_query_image_edit.clicked.connect(self.edit_image)
        query_image_buttons.addWidget(button_query_image_edit, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # Open Image
        button_query_image_open = QPushButton("Open Image")
        button_query_image_open.clicked.connect(self.open_image)
        query_image_buttons.addWidget(button_query_image_open, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        # favorite
        self.button_favorite = QPushButton("♥")
        self.button_favorite.setFixedWidth(30)
        self.button_favorite.clicked.connect(self.press_favorite)
        query_image_buttons.addWidget(self.button_favorite)
        self.button_favorite.setCheckable(True)

        query_image_buttons.addStretch()
        self.setLayout(query_image_buttons)

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
        self.slider_brightness.setValue(50)
        self.slider_contrast.setValue(50)
        self.slider_sharpness.setValue(50)
        self.brightness_factor = 1.0
        self.contrast_factor = 1.0
        self.sharpness_factor = 1.0
        self.mediawidget.image_widget.reset()
    
    def reset_sliders(self):
        self.slider_brightness.setValue(50)
        self.slider_contrast.setValue(50)
        self.slider_sharpness.setValue(50)

    def press_favorite(self):
        current_rid = self.display.get_rid(self.side)
        self.display.press_favorite_button(current_rid)

    def set_favorite(self, state):
        if state:
            self.button_favorite.setChecked(True)
            self.button_favorite.setStyleSheet(self.FAVORITE_STYLE)
        else:
            self.button_favorite.setChecked(False)
            self.button_favorite.setStyleSheet("")

    def edit_image(self):
        current_rid = self.display.get_rid(self.side)
        self.display.edit_image(current_rid)
    
    def open_image(self):
        current_rid = self.display.get_rid(self.side)
        self.display.open_image(current_rid)     