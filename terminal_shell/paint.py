from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPainter, QPixmap
from PyQt5.QtSvg import QSvgRenderer


PHOSPHOR_STYLESHEET = """
QMainWindow {
    background: #040704;
}

QWidget {
    color: #b8f7b8;
    font-family: "Lucida Console", "Courier New", monospace;
    font-size: 12px;
}

QMenuBar {
    background: #0a0f0a;
    color: #b8f7b8;
    border: 1px solid #365236;
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

QFrame#TopBar {
    background: #091109;
    border: 1px solid #3d633d;
}

QFrame#Panel,
QFrame#StatusStrip {
    background: #060b06;
    border: 1px solid #365236;
}

QLabel#HeroTitle {
    font-size: 20px;
    font-weight: 700;
    color: #d9ffd9;
}

QLabel#HeroSubtitle {
    font-size: 11px;
    color: #82c882;
}

QLabel#SectionTitle {
    font-size: 13px;
    font-weight: 700;
    color: #d9ffd9;
}

QLabel#SectionHint,
QLabel#StatusBarText,
QLabel#LayoutMode {
    color: #82c882;
}

QLabel#InlineLabel {
    font-size: 11px;
    font-weight: 700;
    color: #98d898;
}

QLabel#StatusText {
    font-size: 12px;
    color: #d9ffd9;
    font-weight: 600;
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

QPushButton {
    padding: 6px 16px;
    font-weight: 700;
    background: #091109;
    color: #c6ffc6;
    border: 1px solid #365236;
    min-height: 28px;
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

QCheckBox {
    spacing: 8px;
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

QGroupBox {
    border: 1px solid #365236;
    margin-top: 10px;
    padding: 12px;
    background: #060b06;
    font-weight: 700;
}

QGroupBox::title {
    left: 10px;
    padding: 0 4px;
    color: #b8f7b8;
}

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

QPlainTextEdit {
    background: #020502;
    color: #d9ffd9;
    border: 1px solid #365236;
    font-family: "Consolas";
}

QScrollArea {
    border: none;
    background: transparent;
}

QSplitter::handle {
    background: #193019;
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