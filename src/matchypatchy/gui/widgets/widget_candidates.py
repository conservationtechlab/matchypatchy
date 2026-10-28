"""
Strip of ranked match candidates for the compare view

One tile per candidate roi of the current query, in the order the query
container ranks them, with the roi thumbnail, the individual and the
similarity. Clicking a tile shows that candidate, like the match arrows do.
"""
from PyQt6.QtWidgets import (QScrollArea, QWidget, QHBoxLayout, QToolButton, QButtonGroup, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QIcon

from matchypatchy.gui.widgets.styles import ACCENT

TILE_WIDTH = 116
THUMB_HEIGHT = 64
# more tiles than this are reached with the arrows, building hundreds is slow
MAX_TILES = 40


class CandidateStrip(QScrollArea):
    """Horizontally scrolling row of candidate tiles"""
    candidate_clicked = pyqtSignal(int)  # position in the match list

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFixedHeight(THUMB_HEIGHT + 62)
        self.inner = QWidget()
        self.row = QHBoxLayout(self.inner)
        self.row.setContentsMargins(0, 0, 0, 0)
        self.row.setSpacing(6)
        self.row.addStretch()
        self.setWidget(self.inner)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.tiles = []
        self.setStyleSheet(f"""
            QToolButton {{ border: 2px solid palette(midlight); border-radius: 8px; background: palette(base);
                          padding: 3px; font-size: 12px; }}
            QToolButton:checked {{ border: 2px solid {ACCENT}; }}
            QToolButton:hover {{ background: palette(alternate-base); }}""")

    def set_candidates(self, candidates):
        """
        Replace the tiles

        candidates: list of (thumbnail path or None, label, similarity text)
        """
        for tile in self.tiles:
            self.group.removeButton(tile)
            # out of the row now, deleteLater alone leaves it shown until the event loop runs
            self.row.removeWidget(tile)
            tile.hide()
            tile.deleteLater()
        self.tiles = []
        for i, (thumbnail, name, similarity) in enumerate(candidates[:MAX_TILES]):
            tile = QToolButton()
            tile.setCheckable(True)
            tile.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            tile.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            tile.setFixedWidth(TILE_WIDTH)
            tile.setIconSize(QSize(TILE_WIDTH - 12, THUMB_HEIGHT))
            pixmap = QPixmap(thumbnail) if thumbnail else QPixmap()
            if not pixmap.isNull():
                tile.setIcon(QIcon(pixmap.scaled(TILE_WIDTH - 12, THUMB_HEIGHT,
                                                 Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                                 Qt.TransformationMode.SmoothTransformation)))
            tile.setText(f"{name or 'Unnamed'}   {similarity}".strip())
            tile.setToolTip(f"Candidate {i + 1}: {name or 'Unnamed'} {similarity}")
            tile.clicked.connect(lambda _c=False, i=i: self.candidate_clicked.emit(i))
            self.group.addButton(tile)
            self.row.insertWidget(self.row.count() - 1, tile)
            self.tiles.append(tile)

    def set_current(self, index):
        """Check the tile of the shown candidate and scroll it into view"""
        if 0 <= index < len(self.tiles):
            self.tiles[index].setChecked(True)
            self.ensureWidgetVisible(self.tiles[index], 20, 0)
        else:
            checked = self.group.checkedButton()
            if checked is not None:
                self.group.setExclusive(False)
                checked.setChecked(False)
                self.group.setExclusive(True)
