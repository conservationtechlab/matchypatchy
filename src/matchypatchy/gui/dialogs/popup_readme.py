"""
View README popups

"""
from matchypatchy.config import resource_path

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit


class READMEPopup(QDialog):
    """
    Popup to view the README information
    """
    def __init__(self, parent, doc_type):
        super().__init__(parent)
        self.parent = parent
        self.doc_type = doc_type
        self.setMinimumSize(800, 400)
        self.setWindowTitle(f'View {self.doc_type}')

        layout = QVBoxLayout()
        self.text_edit = QTextEdit()
        layout.addWidget(self.text_edit)
        self.setLayout(layout)
        self.display_readme()

    def display_readme(self):
        """Display the README information"""
        readme_path = resource_path(f"{self.doc_type}.md")
        try:
            with open(readme_path, "r", encoding="utf-8") as file:
                readme_text = file.read()
                self.text_edit.setMarkdown(readme_text)
        except FileNotFoundError:
            self.text_edit.setText(f"{self.doc_type}.md not found.")
        self.text_edit.setReadOnly(True)
