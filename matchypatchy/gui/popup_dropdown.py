"""
Popup for Selection within a list, ie Survey selection
"""
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QComboBox, QPushButton, QLabel


class DropdownPopup(QDialog):
    def __init__(self, parent, table, column):
        super().__init__(parent)
        self.parent = parent
        self.table = table
        self.column = column
        self.selected_option = None

        self.setWindowTitle('Selection')
        layout = QVBoxLayout()

        self.label = QLabel(self.table.capitalize())

        # dropdown
        self.combo = QComboBox()
        self.combo.currentTextChanged.connect(self.select)

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)

        layout.addWidget(self.label)
        layout.addWidget(self.combo)
        layout.addWidget(self.ok_button)
        self.setLayout(layout)

        self.get_options()

    def select(self):
        try:
            self.selected_option = self.list[self.combo.currentIndex()]
            return True
        except IndexError:
            return False

    def get_options(self):
        options = self.parent.mpDB.select(self.table, columns=f"id, {self.column}")
        self.list = list(options)
        self.combo.addItems([el[1] for el in self.list])

    def get_selection(self):
        return self.selected_option
