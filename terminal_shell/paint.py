from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPainter, QPixmap
from PyQt5.QtSvg import QSvgRenderer


PHOSPHOR_STYLESHEET = """
QMainWindow, QWidget {
    background: #040704;
    color: #b8f7b8;
    font-family: "Lucida Console", "Courier New", monospace;
    font-size: 12px;
}

QMenuBar {
    background: #0a0f0a;
    color: #b8f7b8;
    border-bottom: 1px solid #365236;
}

QMenuBar::item {
    padding: 4px 10px;
    background: transparent;
}

QMenuBar::item:selected {
    background: #143114;
    color: #e8ffe8;
}

QMenu {
    background: #0a0f0a;
    border: 1px solid #365236;
    padding: 4px;
}

QMenu::item {
    padding: 6px 18px;
}

QMenu::item:selected {
    background: #143114;
    color: #e8ffe8;
}

/* ── Dialogs / message boxes ─────────────────────────────────────────────── */
QDialog,
QMessageBox {
    background: #060b06;
    border: 1px solid #365236;
}

QMessageBox QWidget,
QDialog QWidget {
    background: #060b06;
    color: #d9ffd9;
}

QMessageBox QLabel,
QDialog QLabel {
    background: transparent;
    color: #d9ffd9;
}

QMessageBox QTextEdit,
QMessageBox QPlainTextEdit {
    background: #020502;
    color: #d9ffd9;
    border: 1px solid #365236;
}

/* QMessageBox buttons use QPushButton, covered below */

/* ── Named frames ─────────────────────────────────────────────────────────── */
QFrame#TopBar {
    background: #091109;
    border: 1px solid #3d633d;
}

QFrame#Panel,
QFrame#StatusStrip {
    background: #060b06;
    border: 1px solid #365236;
}

/* ── Labels ───────────────────────────────────────────────────────────────── */
QLabel#HeroTitle {
    font-size: 20px;
    font-weight: 700;
    color: #d9ffd9;
    background: transparent;
}

QLabel#HeroSubtitle {
    font-size: 11px;
    color: #82c882;
    background: transparent;
}

QLabel#SectionTitle {
    font-size: 13px;
    font-weight: 700;
    color: #d9ffd9;
    background: transparent;
}

QLabel#SectionHint,
QLabel#StatusBarText,
QLabel#LayoutMode {
    color: #82c882;
    background: transparent;
}

QLabel#InlineLabel {
    font-size: 11px;
    font-weight: 700;
    color: #98d898;
    background: transparent;
}

QLabel#StatusText {
    font-size: 12px;
    color: #d9ffd9;
    font-weight: 600;
    background: transparent;
}

QLabel#StateBadge[state="idle"] {
    background: #060b06;
    color: #98d898;
    border: 1px solid #365236;
    padding: 4px 10px;
    font-weight: 700;
}

QLabel#StateBadge[state="active"] {
    background: #102010;
    color: #e8ffe8;
    border: 1px solid #6dac6d;
    padding: 4px 10px;
    font-weight: 700;
}

QLabel#StateBadge[state="success"] {
    background: #102010;
    color: #e8ffe8;
    border: 1px solid #7bcf7b;
    padding: 4px 10px;
    font-weight: 700;
}

QLabel#StateBadge[state="error"] {
    background: #0d130d;
    color: #c6ffc6;
    border: 1px solid #4e734e;
    padding: 4px 10px;
    font-weight: 700;
}

/* ── Input widgets ────────────────────────────────────────────────────────── */
QLineEdit,
QComboBox,
QPlainTextEdit {
    background: #020502;
    border: 1px solid #365236;
    padding: 5px 7px;
    color: #d9ffd9;
    selection-background-color: #1c451c;
    selection-color: #e8ffe8;
}

QLineEdit:focus,
QComboBox:focus,
QPlainTextEdit:focus {
    border: 1px solid #7bcf7b;
}

QComboBox QAbstractItemView {
    background: #060b06;
    color: #b8f7b8;
    border: 1px solid #365236;
    selection-background-color: #143114;
    selection-color: #e8ffe8;
    outline: 0;
}

QComboBox QAbstractItemView::item {
    min-height: 22px;
    padding: 4px 8px;
}

QComboBox QAbstractItemView::item:hover {
    background: #102010;
    color: #e8ffe8;
}

QComboBox QAbstractItemView::item:selected {
    background: #143114;
    color: #e8ffe8;
}

QLineEdit[readOnly="true"] {
    background: #070d07;
    color: #8cc88c;
}

QComboBox::drop-down {
    width: 22px;
    border-left: 1px solid #365236;
    background: #091109;
}

QComboBox::down-arrow {
    width: 10px;
    height: 10px;
}

/* ── Buttons ──────────────────────────────────────────────────────────────── */
QPushButton {
    padding: 6px 16px;
    font-weight: 700;
    background: #091109;
    color: #c6ffc6;
    border: 1px solid #365236;
    min-height: 28px;
    font-family: "Lucida Console", "Courier New", monospace;
    font-size: 12px;
}

QPushButton:hover {
    background: #102010;
}

QPushButton:pressed {
    background: #143114;
}

QPushButton:disabled {
    background: #070d07;
    color: #587958;
}

QPushButton#PrimaryButton {
    background: #143114;
    color: #e8ffe8;
    border: 1px solid #7bcf7b;
}

QPushButton#PrimaryButton:hover {
    background: #1d451d;
}

QPushButton#GhostButton {
    min-width: 90px;
}

/* ── Checkbox ─────────────────────────────────────────────────────────────── */
QCheckBox {
    spacing: 8px;
    background: transparent;
}

QCheckBox::indicator {
    width: 13px;
    height: 13px;
    border: 1px solid #365236;
    background: #020502;
}

QCheckBox::indicator:checked {
    background: #7bcf7b;
    border: 1px solid #7bcf7b;
}

/* ── Group box ────────────────────────────────────────────────────────────── */
QGroupBox {
    border: 1px solid #365236;
    margin-top: 10px;
    padding: 12px;
    background: #060b06;
    font-weight: 700;
    color: #b8f7b8;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 4px;
    color: #b8f7b8;
    background: #060b06;
}

/* ── Progress bar ─────────────────────────────────────────────────────────── */
QProgressBar {
    border: 1px solid #365236;
    background: #020502;
    text-align: center;
    min-height: 18px;
    font-weight: 700;
    color: #d9ffd9;
}

QProgressBar::chunk {
    background: #7bcf7b;
}

/* ── Log / text edit ──────────────────────────────────────────────────────── */
QPlainTextEdit {
    background: #020502;
    color: #d9ffd9;
    border: 1px solid #365236;
    font-family: "Consolas", "Courier New", monospace;
}

/* ── Scroll area ──────────────────────────────────────────────────────────── */
QScrollArea {
    border: none;
    background: transparent;
}

QScrollArea > QWidget > QWidget {
    background: transparent;
}

QAbstractScrollArea {
    background: #040704;
}

QAbstractScrollArea > QWidget {
    background: #040704;
}

/* ── Scrollbars ───────────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: #040704;
    width: 10px;
    margin: 0;
    border: none;
}

QScrollBar::handle:vertical {
    background: #2a4a2a;
    min-height: 24px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #3d663d;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: none;
    height: 0;
}

QScrollBar:horizontal {
    background: #040704;
    height: 10px;
    margin: 0;
    border: none;
}

QScrollBar::handle:horizontal {
    background: #2a4a2a;
    min-width: 24px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background: #3d663d;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: none;
    width: 0;
}

/* ── Splitter ─────────────────────────────────────────────────────────────── */
QSplitter {
    background: #040704;
}

QSplitter::handle {
    background: #193019;
}

QSplitter::handle:hover {
    background: #2a4a2a;
}

/* ── Tooltip ──────────────────────────────────────────────────────────────── */
QToolTip {
    background: #0a0f0a;
    color: #d9ffd9;
    border: 1px solid #365236;
    padding: 4px 8px;
    font-family: "Lucida Console", "Courier New", monospace;
    font-size: 11px;
}
"""


def svg_to_pixmap(svg_path, size):
    renderer = QSvgRenderer(svg_path)
    if not renderer.isValid():
        return QPixmap()

    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)

    painter = QPainter(image)
    renderer.render(painter)
    painter.end()

    return QPixmap.fromImage(image)