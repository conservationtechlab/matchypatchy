"""
Sidebar navigation for the main window

Shows the app name, the open project and active survey, and buttons for each
page. On the overview it is full width; on the working pages (media, match,
process) it collapses to an icon rail so the content gets the room.
"""
from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QButtonGroup, QSizePolicy, QMenu)
from PyQt6.QtCore import Qt, pyqtSignal, QSize

from matchypatchy import __version__
from matchypatchy.gui.widgets.styles import icon, paw_pixmap, label, SIDEBAR_BADGE

FULL_WIDTH = 240
COLLAPSED_WIDTH = 64

# key, label, icon, whether it is a page (checkable) or opens a dialog
NAV_ITEMS = [("overview", "Overview", "overview", True),
             ("media", "Media", "media", True),
             ("match", "Match", "match", True),
             ("individuals", "Individuals", "individuals", False),
             ("process", "Process && models", "process", True),
             ("surveys", "Surveys && stations", "surveys", False)]

FOOTER_ITEMS = [("settings", "Settings", "settings"),
                ("manual", "User manual", "help")]


class NavButton(QPushButton):
    """Sidebar button with an icon, a label and an optional count badge on the right"""
    def __init__(self, text, icon_name, checkable=True):
        super().__init__(text)
        self.full_text = text
        self.setIcon(icon(icon_name))
        self.setIconSize(QSize(18, 18))
        self.setCheckable(checkable)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(text.replace("&&", "&"))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 10, 0)
        layout.addStretch()
        self.badge = QLabel("")
        self.badge.setStyleSheet(f"background: {SIDEBAR_BADGE}; color: #E9ECE9; border-radius: 9px;"
                                 "padding: 1px 8px; font-size: 12px;")
        self.badge.setFixedHeight(20)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge.setVisible(False)
        layout.addWidget(self.badge, 0, Qt.AlignmentFlag.AlignVCenter)

    def set_badge(self, text):
        """Show text in the badge, hide it for empty text or zero"""
        self.badge.setText(str(text))
        self._badge_wanted = bool(text) and str(text) != "0"
        self.badge.setVisible(self._badge_wanted and bool(self.text()))

    def set_collapsed(self, collapsed):
        """Icon only when collapsed, the label is kept in the tooltip"""
        self.setText("" if collapsed else self.full_text)
        self.badge.setVisible(getattr(self, "_badge_wanted", False) and not collapsed)


class Sidebar(QFrame):
    """Dark navigation column on the left of the main window"""
    navigate = pyqtSignal(str)  # key of the clicked item

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(FULL_WIDTH)
        self.collapsed = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(14)

        # BRAND
        brand = QHBoxLayout()
        brand.setSpacing(10)
        self.logo = QLabel()
        self.logo.setPixmap(paw_pixmap(28))
        self.logo.setFixedSize(28, 28)
        brand.addWidget(self.logo)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        self.brand_name = QLabel("MatchyPatchy")
        self.brand_name.setStyleSheet("font-weight: 700; font-size: 15px;")
        self.brand_version = label(f"v{__version__}", "muted")
        self.brand_version.setStyleSheet("font-size: 11px;")
        brand_text.addWidget(self.brand_name)
        brand_text.addWidget(self.brand_version)
        brand.addLayout(brand_text)
        brand.addStretch()
        layout.addLayout(brand)

        # PROJECT AND SURVEY
        self.card = QFrame()
        self.card.setObjectName("SidebarCard")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(12, 10, 12, 12)
        card_layout.setSpacing(4)
        card_layout.addWidget(label("PROJECT", "muted"))
        self.project_name = QLabel("")
        self.project_name.setStyleSheet("font-weight: 600;")
        card_layout.addWidget(self.project_name)
        self.project_path = label("", "muted")
        self.project_path.setStyleSheet("font-size: 11px;")
        card_layout.addWidget(self.project_path)
        card_layout.addSpacing(8)
        card_layout.addWidget(label("ACTIVE SURVEY", "muted"))
        self.survey_slot = QVBoxLayout()
        self.survey_slot.setContentsMargins(0, 0, 0, 0)
        card_layout.addLayout(self.survey_slot)
        layout.addWidget(self.card)

        # NAVIGATION
        self.buttons = {}
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        nav = QVBoxLayout()
        nav.setSpacing(2)
        for key, text, icon_name, is_page in NAV_ITEMS:
            button = NavButton(text, icon_name, checkable=is_page)
            button.clicked.connect(lambda _checked=False, k=key: self._clicked(k))
            if is_page:
                self.group.addButton(button)
            self.buttons[key] = button
            nav.addWidget(button)
        layout.addLayout(nav)

        # surveys and stations open from a small menu
        self.surveys_menu = QMenu(self)
        self.surveys_menu.addAction("Manage surveys…", lambda: self.navigate.emit("manage_surveys"))
        self.surveys_menu.addAction("Manage stations…", lambda: self.navigate.emit("manage_stations"))

        layout.addStretch()

        # FOOTER
        self.footer = QFrame()
        self.footer.setStyleSheet("QFrame { border-top: 1px solid #333A35; }")
        footer_layout = QVBoxLayout(self.footer)
        footer_layout.setContentsMargins(0, 8, 0, 0)
        footer_layout.setSpacing(2)
        for key, text, icon_name in FOOTER_ITEMS:
            button = NavButton(text, icon_name, checkable=False)
            button.clicked.connect(lambda _checked=False, k=key: self._clicked(k))
            self.buttons[key] = button
            footer_layout.addWidget(button)
        layout.addWidget(self.footer)

    def _clicked(self, key):
        if key == "surveys":
            button = self.buttons[key]
            self.surveys_menu.popup(button.mapToGlobal(button.rect().topRight()))
            return
        self.navigate.emit(key)

    def set_survey_widget(self, widget):
        """Place the survey selector (owned by the overview page) in the project card"""
        self.survey_slot.addWidget(widget)

    def set_project(self, home_dir):
        """Show the open project's folder name and path"""
        self.project_name.setText(home_dir.name if home_dir else "")
        path = str(home_dir) if home_dir else ""
        self.project_path.setToolTip(path)
        metrics = self.project_path.fontMetrics()
        self.project_path.setText(metrics.elidedText(path, Qt.TextElideMode.ElideMiddle, FULL_WIDTH - 50))

    def set_current(self, key):
        """Check the button for the page being shown"""
        button = self.buttons.get(key)
        if button is not None and button.isCheckable():
            button.setChecked(True)

    def set_badge(self, key, value):
        """Show a count beside a nav item, nothing for zero"""
        if key in self.buttons:
            self.buttons[key].set_badge(f"{value:,}" if isinstance(value, int) else value)

    def set_collapsed(self, collapsed):
        """Icon rail on working pages, full width on the overview"""
        if collapsed == self.collapsed:
            return
        self.collapsed = collapsed
        self.setProperty("collapsed", "true" if collapsed else "false")
        self.setFixedWidth(COLLAPSED_WIDTH if collapsed else FULL_WIDTH)
        self.layout().setContentsMargins(8 if collapsed else 12, 16, 8 if collapsed else 12, 12)
        for widget in (self.brand_name, self.brand_version, self.card):
            widget.setVisible(not collapsed)
        for button in self.buttons.values():
            button.set_collapsed(collapsed)
        self.style().unpolish(self)
        self.style().polish(self)
        for button in self.buttons.values():
            button.style().unpolish(button)
            button.style().polish(button)
