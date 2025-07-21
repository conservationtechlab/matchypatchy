"""
View README

"""
from matchypatchy import config

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit


class AboutPopup(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setMinimumSize(800, 400)
        self.setWindowTitle('View README')

        layout = QVBoxLayout()
        self.text_edit = QTextEdit()
        layout.addWidget(self.text_edit)
        self.setLayout(layout)
        self.display_readme()

    def display_readme(self):
        about_path = config.resource_path("ABOUT.md")
        try:
            with open(about_path, "r") as file:
                readme_text = file.read()
                self.text_edit.setMarkdown(readme_text)
        except FileNotFoundError:
            self.text_edit.setText("ABOUT.md not found.")
        self.text_edit.setReadOnly(True)


class READMEPopup(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setMinimumSize(800, 400)
        self.setWindowTitle('View README')

        layout = QVBoxLayout()
        self.text_edit = QTextEdit()
        layout.addWidget(self.text_edit)
        self.setLayout(layout)
        self.display_readme()

    def display_readme(self):
        readme_path = config.resource_path("README.md")
        try:
            with open(readme_path, "r") as file:
                readme_text = file.read()
                self.text_edit.setMarkdown(readme_text)
        except FileNotFoundError:
            self.text_edit.setText("README.md not found.")
        self.text_edit.setReadOnly(True)


class LicensePopup(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setMinimumSize(800, 400)
        self.setWindowTitle('View License')

        layout = QVBoxLayout()
        self.text_edit = QTextEdit()
        layout.addWidget(self.text_edit)
        self.setLayout(layout)
        self.display_readme()

    def display_readme(self):
        license_path = config.resource_path("LICENSE")
        try:
            with open(license_path, "r") as file:
                readme_text = file.read()
                self.text_edit.setMarkdown(readme_text)
        except FileNotFoundError:
            self.text_edit.setText("LICENSE not found.")
        self.text_edit.setReadOnly(True)
