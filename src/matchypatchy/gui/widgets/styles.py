"""
Shared look for the GUI: colors, the application stylesheet and line icons

The stylesheet uses palette() roles for surfaces and text, so it follows the
Light/Dark/System theme chosen in the configuration. Only the accent colors and
the sidebar, which is dark in both themes, are fixed.

Widgets opt into a variant with set_variant(widget, "primary"), which sets the
"variant" property the stylesheet selects on.
"""
from PyQt6.QtCore import Qt, QByteArray, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter
from PyQt6.QtWidgets import QLabel

# accents, the same in both themes
ACCENT = "#2E7031"          # match green, the app's existing Match button color
ACCENT_HOVER = "#265E29"
ACCENT_SOFT = "#E4EFE4"
ACCENT_INK = "#1F5222"
WARN_SOFT = "#FBF0DC"
WARN_INK = "#7A4700"
DANGER = "#B51B32"
FAVORITE = "#D6334B"

# sidebar, dark in both themes
SIDEBAR_BG = "#1B1E1C"
SIDEBAR_CARD = "#262B28"
SIDEBAR_ACTIVE = "#2F3A31"
SIDEBAR_TEXT = "#E9ECE9"
SIDEBAR_MUTED = "#B9BFBA"
SIDEBAR_BADGE = "#3A413C"

# image wells behind photos
IMAGE_WELL = "#2A2F2B"

STYLESHEET = f"""
QPushButton {{
    padding: 6px 14px;
    border: 1px solid palette(mid);
    border-radius: 8px;
    background: palette(base);
    color: palette(text);
}}
QPushButton:hover {{ background: palette(alternate-base); }}
QPushButton:pressed, QPushButton:checked {{ background: palette(midlight); }}
QPushButton:disabled {{ color: palette(placeholder-text); border-color: palette(midlight); }}
QPushButton[variant="primary"] {{
    background: {ACCENT}; color: white; border: 1px solid {ACCENT}; font-weight: 600;
}}
QPushButton[variant="primary"]:hover {{ background: {ACCENT_HOVER}; }}
QPushButton[variant="primary"]:disabled {{ background: palette(midlight); border-color: palette(midlight); color: palette(placeholder-text); }}
QPushButton[variant="danger"] {{ background: {DANGER}; color: white; border: 1px solid {DANGER}; font-weight: 600; }}
QPushButton[variant="chip"] {{ border-radius: 13px; padding: 3px 12px; }}
QPushButton[variant="segment"] {{ border-radius: 0px; padding: 6px 14px; }}
QPushButton[variant="segment"]:checked {{ background: palette(window-text); color: palette(window); font-weight: 600; }}
QPushButton[variant="segment-first"] {{ border-top-right-radius: 0px; border-bottom-right-radius: 0px; }}
QPushButton[variant="segment-first"]:checked, QPushButton[variant="segment-last"]:checked {{
    background: palette(window-text); color: palette(window); font-weight: 600;
}}
QPushButton[variant="segment-last"] {{ border-top-left-radius: 0px; border-bottom-left-radius: 0px; }}
QPushButton[variant="overlay"] {{
    background: rgba(20, 23, 21, 215); color: #E9ECE9; border: 0px; border-radius: 6px; padding: 6px;
}}
QPushButton[variant="overlay"]:hover {{ background: rgba(60, 66, 62, 230); }}
QPushButton[variant="overlay"]:checked {{ color: #FF6B81; }}
QPushButton[variant="selbar"] {{ background: transparent; color: white; border: 1px solid #3A413C; border-radius: 6px; padding: 4px 12px; }}
QPushButton[variant="selbar"]:hover {{ background: #2F3632; }}

QComboBox, QLineEdit {{
    padding: 4px 8px;
    border: 1px solid palette(mid);
    border-radius: 8px;
    background: palette(base);
    color: palette(text);
    min-height: 22px;
}}

QFrame#Card {{ background: palette(base); border: 1px solid palette(mid); border-radius: 14px; }}
QLabel[role="muted"] {{ color: palette(placeholder-text); }}
QLabel[role="eyebrow"] {{ color: palette(placeholder-text); font-size: 11px; font-weight: 600; letter-spacing: 1px; }}
QLabel[role="title"] {{ font-size: 26px; font-weight: 600; }}
QLabel[role="pill-ok"] {{ background: {ACCENT_SOFT}; color: {ACCENT_INK}; border-radius: 9px; padding: 2px 9px; font-weight: 600; }}
QLabel[role="pill-warn"] {{ background: {WARN_SOFT}; color: {WARN_INK}; border-radius: 9px; padding: 2px 9px; font-weight: 600; }}
QLabel[role="pill-muted"] {{ color: palette(placeholder-text); padding: 2px 9px; }}

QFrame#Sidebar {{ background: {SIDEBAR_BG}; }}
QFrame#Sidebar QLabel {{ color: {SIDEBAR_TEXT}; }}
QFrame#Sidebar QLabel[role="muted"] {{ color: {SIDEBAR_MUTED}; }}
QFrame#SidebarCard {{ background: {SIDEBAR_CARD}; border-radius: 10px; }}
QFrame#Sidebar QComboBox {{ background: {SIDEBAR_BG}; color: {SIDEBAR_TEXT}; border: 1px solid #3A413C; }}
QFrame#Sidebar QComboBox QAbstractItemView {{ background: {SIDEBAR_CARD}; color: {SIDEBAR_TEXT}; selection-background-color: {SIDEBAR_ACTIVE}; }}
QFrame#Sidebar QPushButton {{
    background: transparent; border: 0px; border-radius: 8px; color: #D5DAD6;
    padding: 0px 12px; min-height: 40px; text-align: left;
}}
QFrame#Sidebar QPushButton:hover {{ background: #262B28; }}
QFrame#Sidebar QPushButton:checked {{ background: {SIDEBAR_ACTIVE}; color: white; font-weight: 600; }}
QFrame#Sidebar[collapsed="true"] QPushButton {{ padding: 0px; text-align: center; }}

QFrame#SelectionBar {{ background: {SIDEBAR_BG}; }}
QFrame#SelectionBar QLabel {{ color: white; font-weight: 600; }}
QFrame#DecisionBar, QFrame#TopBar {{ background: palette(base); border: 0px; }}
QLabel#UnsavedNotice {{ background: {WARN_SOFT}; color: {WARN_INK}; border-radius: 8px; padding: 4px 10px; font-weight: 600; }}
QLabel#Kbd {{ border: 1px solid palette(mid); border-radius: 4px; padding: 0px 5px; background: palette(window); }}
"""


def set_variant(widget, variant):
    """Give a widget a stylesheet variant, eg. 'primary', and restyle it"""
    widget.setProperty("variant", variant)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def set_role(label, role):
    """Give a label a stylesheet role, eg. 'muted', and restyle it"""
    label.setProperty("role", role)
    label.style().unpolish(label)
    label.style().polish(label)


def label(text="", role=None, parent=None):
    """QLabel with an optional stylesheet role"""
    lbl = QLabel(text, parent)
    if role:
        lbl.setProperty("role", role)
    return lbl


# 24x24 stroke icons, {color} is filled in by icon()
ICON_PATHS = {
    "overview": '<rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/>'
                '<rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/>',
    "media": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M9 4v16"/>',
    "match": '<rect x="2" y="5" width="9" height="14" rx="1"/><rect x="13" y="5" width="9" height="14" rx="1"/>',
    "individuals": '<circle cx="9" cy="8" r="4"/><path d="M2 21c0-4 3-6 7-6s7 2 7 6M17 4a4 4 0 0 1 0 8M22 21c0-3-1.5-5-4-5.6"/>',
    "process": '<path d="M12 2v4M12 18v4M4.9 4.9l2.8 2.8M16.3 16.3l2.8 2.8M2 12h4M18 12h4M4.9 19.1l2.8-2.8M16.3 7.7l2.8-2.8"/>',
    "surveys": '<path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
    "help": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 0 1 4.9.8c0 1.7-2.4 2.2-2.4 3.7M12 17h.01"/>',
    "zoom": '<circle cx="11" cy="11" r="7"/><path d="M21 21l-5-5M11 8v6M8 11h6"/>',
    "contrast": '<circle cx="12" cy="12" r="8"/><path d="M12 4v16"/>',
    "edit": '<path d="M4 20h4L19 9l-4-4L4 16z"/>',
    "open": '<path d="M14 3h7v7M21 3l-9 9M19 14v6H4V5h6"/>',
    "heart": '<path d="M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.5-7 10-7 10z"/>',
    "recalc": '<path d="M21 12a9 9 0 1 1-3-6.7M21 3v6h-6"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="M21 21l-5-5"/>',
    "reset": '<path d="M3 12a9 9 0 1 0 3-6.7M3 3v6h6"/>',
    "download": '<path d="M12 3v12M7 10l5 5 5-5M4 21h16"/>',
}

PAW_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 28 28" fill="{color}">'
           '<ellipse cx="9" cy="8" rx="3" ry="4"/><ellipse cx="19" cy="8" rx="3" ry="4"/>'
           '<ellipse cx="4.5" cy="15" rx="2.6" ry="3.4"/><ellipse cx="23.5" cy="15" rx="2.6" ry="3.4"/>'
           '<path d="M14 13c4 0 7 4.5 7 8 0 2.5-2 3.5-4 3-1.4-.4-2-.9-3-.9s-1.6.5-3 .9c-2 .5-4-.5-4-3 0-3.5 3-8 7-8z"/></svg>')


def _render_svg(svg, size):
    """Render an svg string to a pixmap of size x size at the screen's pixel ratio"""
    source = QPixmap()
    source.loadFromData(QByteArray(svg.encode()), "SVG")
    if source.isNull():
        return source
    return source.scaled(QSize(size, size), Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)


def icon(name, color="#D5DAD6", size=48, fill="none"):
    """Line icon from ICON_PATHS as a QIcon, an empty icon for unknown names"""
    paths = ICON_PATHS.get(name)
    if paths is None:
        return QIcon()
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" '
           f'fill="{fill}" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
           f'{paths}</svg>')
    return QIcon(_render_svg(svg, size))


def paw_pixmap(size, color="#E9ECE9"):
    """The paw mark used as the app logo in the sidebar and on the overview"""
    return _render_svg(PAW_SVG.format(color=color), size)
