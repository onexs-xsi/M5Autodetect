"""Reusable Qt widget classes for the M5Autodetect CBuilder GUI."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QStyledItemDelegate, QStyle, QSpinBox, QComboBox, QLineEdit,
    QStackedLayout, QGraphicsDropShadowEffect,
)
from PyQt6.QtGui import QFont, QPixmap, QColor, QPainter, QPen
from PyQt6.QtCore import Qt, QSize, QRect, QCoreApplication


class DeviceItemDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        if option.state & QStyle.StateFlag.State_Selected:
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen = QPen(QColor("#007ACC"), 3)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(option.rect.adjusted(2, 2, -2, -2), 10, 10)
            painter.restore()
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(option.rect, option.palette.light())

        icon = index.data(Qt.ItemDataRole.DecorationRole)
        name = index.data(Qt.ItemDataRole.DisplayRole)
        sku = index.data(Qt.ItemDataRole.UserRole).get('sku', '')
        eol_status = index.data(Qt.ItemDataRole.UserRole).get('eol', '')

        rect = option.rect

        icon_size = 100
        icon_rect = QRect(rect.left() + (rect.width() - icon_size) // 2, rect.top() + 10, icon_size, icon_size)
        if icon:
            icon.paint(painter, icon_rect)

        painter.save()
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        name_rect = QRect(rect.left(), icon_rect.bottom() + 5, rect.width(), 20)
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignCenter, name)
        painter.restore()

        if sku:
            painter.save()
            painter.setFont(QFont("Arial", 8))
            if eol_status == 'EOL':
                painter.setPen(QColor("#555555"))
            elif eol_status == 'SALE':
                painter.setPen(QColor("#00008B"))
            else:
                painter.setPen(QColor("#007ACC"))
            sku_rect = QRect(rect.left(), name_rect.bottom(), rect.width(), 15)
            painter.drawText(sku_rect, Qt.AlignmentFlag.AlignCenter, sku)
            painter.restore()

        if eol_status == 'EOL':
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            painter.setPen(QColor("#2F495E"))
            painter.translate(rect.right() - 25, rect.top() + 25)
            painter.rotate(45)
            eol_text = QCoreApplication.translate("DeviceItemDelegate", "EOL")
            painter.drawText(QRect(-30, -15, 60, 30), Qt.AlignmentFlag.AlignCenter, eol_text)
            painter.restore()

    def sizeHint(self, option, index):
        return QSize(140, 160)


class DictTranslator:
    """Minimal translator that maps source text directly to translations.

    Note: intentionally does NOT inherit QTranslator so that it can be used
    as a plain callable ``catalog.get(text, text)`` by manager classes.
    The main GUI still wraps it in a real QTranslator when needed.
    """

    def __init__(self, catalog):
        self._catalog = catalog or {}

    def translate(self, context, sourceText, disambiguation=None, n=-1):
        if not sourceText:
            return ""
        return self._catalog.get(sourceText, sourceText)


class NoScrollSpinBox(QSpinBox):
    """SpinBox that ignores mouse wheel to avoid accidental changes."""

    def wheelEvent(self, event):
        event.ignore()


class NoScrollComboBox(QComboBox):
    """ComboBox that ignores mouse wheel to avoid accidental changes."""

    def wheelEvent(self, event):
        event.ignore()


class PinValueEditor(QWidget):
    """Pin editor that defaults to numeric spin control but can fall back to free text."""

    def __init__(self, value=None, parent=None):
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)

        stack_host = QWidget(self)
        self._stack = QStackedLayout(stack_host)

        self._spin = NoScrollSpinBox()
        self._spin.setRange(-1, 255)
        self._spin.setSpecialValueText("NC")
        self._spin.setValue(-1)

        self._text = QLineEdit()
        self._text.setPlaceholderText("GPIO_NUM_NC / 表达式")

        spin_container = QWidget(stack_host)
        spin_layout = QVBoxLayout(spin_container)
        spin_layout.setContentsMargins(0, 0, 0, 0)
        spin_layout.addWidget(self._spin)

        text_container = QWidget(stack_host)
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.addWidget(self._text)

        self._stack.addWidget(spin_container)
        self._stack.addWidget(text_container)

        self._layout.addWidget(stack_host, 1)

        self._mode_button = QPushButton("123")
        self._mode_button.setCheckable(True)
        self._mode_button.setFixedWidth(44)
        self._mode_button.setToolTip("切换为文本模式")
        self._mode_button.toggled.connect(self._on_mode_toggled)
        self._layout.addWidget(self._mode_button)

        self.setValue(value)

    def _on_mode_toggled(self, checked):
        self._stack.setCurrentIndex(1 if checked else 0)
        self._mode_button.setText("TXT" if checked else "123")

    def setValue(self, value):
        if isinstance(value, str):
            stripped = value.strip()
            parsed = self._parse_numeric(stripped)
            if stripped and parsed is None:
                self._mode_button.setChecked(True)
                self._text.setText(stripped)
                return
            value = parsed

        if value is None:
            value = -1

        self._mode_button.setChecked(False)
        self._spin.setValue(int(value))
        self._text.clear()

    def value(self):
        if self._mode_button.isChecked():
            raw = self._text.text().strip()
            return raw or None
        val = self._spin.value()
        return None if val < 0 else val

    @staticmethod
    def _parse_numeric(value):
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            try:
                if text.lower().startswith('0x'):
                    return int(text, 16)
                return int(text)
            except ValueError:
                return None
        return None


class FloatingButtonWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.content_layout = QVBoxLayout(self)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        self.btn_apply = QPushButton(self.tr("💾 保存修改"), self)
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 12px 24px;
                border-radius: 25px;
                font-size: 14px;
                border: 2px solid #1976D2;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #42A5F5;
            }
            QPushButton:pressed {
                background-color: #1E88E5;
            }
        """)
        self.btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 5)
        self.btn_apply.setGraphicsEffect(shadow)

        self.btn_apply.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        margin_right = 40
        margin_bottom = 40
        btn_w = 140
        btn_h = 50

        self.btn_apply.setGeometry(
            self.width() - btn_w - margin_right,
            self.height() - btn_h - margin_bottom,
            btn_w, btn_h
        )
        self.btn_apply.raise_()
