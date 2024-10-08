import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QProgressBar, QLabel, QDialog
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import time




class ProgressPopup(QDialog):
    def __init__(self, parent, prompt):
        super().__init__(parent)
        self.setWindowTitle("Progress")
        self.layout = QVBoxLayout()

        self.counter = 0
        self.max = 100
        
        self.label = QLabel(prompt)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(self.counter, self.max)

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.progress_bar)

        self.setLayout(self.layout)


    def update_progress(self):
        """Update the progress bar based on the counter value."""
        self.counter += 1
        print(self.counter)
        self.progress_bar.setValue(self.counter)  # Update progress bar value

        if self.counter >= self.max:  # Stop the timer when progress reaches 100
            self.close()

    def set_max(self, max):
        """Update the progress bar maximum value"""
        print(max)
        self.max = max

    def set_counter(self, counter):
        """Update the progress bar to specific"""
        if counter < self.max:
            self.counter = counter
            self.progress_bar.setValue(self.counter)
        else:
            self.close()