print("Starting script...")
print(f"__name__ is {__name__}")
import sys
import os


def _configure_qt_dll_path():
    candidates = []

    for base in {sys.prefix, sys.base_prefix, os.path.dirname(sys.executable)}:
        if not base:
            continue
        candidates.append({
            'bin': os.path.join(base, 'Lib', 'site-packages', 'PyQt6', 'Qt6', 'bin'),
            'plugins': os.path.join(base, 'Lib', 'site-packages', 'PyQt6', 'Qt6', 'plugins'),
        })

    if not hasattr(os, 'add_dll_directory'):
        return

    for candidate in candidates:
        dll_dir = candidate['bin']
        plugins_dir = candidate['plugins']
        if os.path.isdir(dll_dir):
            os.add_dll_directory(dll_dir)
            if os.path.isdir(plugins_dir):
                os.environ.setdefault('QT_PLUGIN_PATH', plugins_dir)
                os.environ.setdefault('QT_QPA_PLATFORM_PLUGIN_PATH', os.path.join(plugins_dir, 'platforms'))
            break


_configure_qt_dll_path()

import copy
import html
import json
import yaml
import requests
import hashlib
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTextEdit, QLabel, QMessageBox,
                             QFileDialog, QTreeWidget, QTreeWidgetItem, QSplitter,
                             QFormLayout, QLineEdit, QComboBox, QSpinBox, QGroupBox,
                             QScrollArea, QStackedWidget, QListWidget, QListWidgetItem,
                             QStyledItemDelegate, QStyle, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QCheckBox, QStackedLayout, QGraphicsDropShadowEffect,
                             QGridLayout, QTabWidget, QSizePolicy)
from PyQt6.QtGui import QFont, QIcon, QPixmap, QColor, QPainter, QPen, QBrush, QPalette
from PyQt6.QtCore import Qt, QSize, QRect, QTimer, QTranslator, QLocale, QCoreApplication
from M5Autodetect_CBuilder_GenCode import M5HeaderGenerator

# Paths
BASE_DIR = os.path.dirname(__file__)
YAML_FILE = os.path.join(BASE_DIR, 'm5stack_dev_config.yaml')
OUTPUT_HEADER_FILE = os.path.join(BASE_DIR, '../src/data/M5Autodetect_DeviceData.h')
OUTPUT_SOURCE_FILE = os.path.join(BASE_DIR, '../src/data/M5Autodetect_DeviceData.cpp')
CACHE_DIR = os.path.join(BASE_DIR, '.cache')
LOCALES_DIR = os.path.join(BASE_DIR, 'locales')

class DeviceItemDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        # Draw background if selected or hovered
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

        # Get data
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        name = index.data(Qt.ItemDataRole.DisplayRole)
        sku = index.data(Qt.ItemDataRole.UserRole).get('sku', '')
        eol_status = index.data(Qt.ItemDataRole.UserRole).get('eol', '')

        rect = option.rect
        
        # Draw Icon
        icon_size = 100
        icon_rect = QRect(rect.left() + (rect.width() - icon_size) // 2, rect.top() + 10, icon_size, icon_size)
        if icon:
            icon.paint(painter, icon_rect)

        # Draw Name
        painter.save()
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        name_rect = QRect(rect.left(), icon_rect.bottom() + 5, rect.width(), 20)
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignCenter, name)
        painter.restore()

        # Draw SKU
        if sku:
            painter.save()
            painter.setFont(QFont("Arial", 8))
            
            # Determine color based on EOL status
            if eol_status == 'EOL':
                painter.setPen(QColor("#555555")) # Grey-black for EOL
            elif eol_status == 'SALE':
                painter.setPen(QColor("#00008B")) # Dark Blue for SALE
            else:
                painter.setPen(QColor("#007ACC")) # Default Blue
                
            sku_rect = QRect(rect.left(), name_rect.bottom(), rect.width(), 15)
            painter.drawText(sku_rect, Qt.AlignmentFlag.AlignCenter, sku)
            painter.restore()

        # Draw EOL Label
        if eol_status == 'EOL':
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            painter.setPen(QColor("#2F495E"))
            
            # Position at top-right corner
            painter.translate(rect.right() - 25, rect.top() + 25)
            painter.rotate(45)
            eol_text = QCoreApplication.translate("DeviceItemDelegate", "EOL")
            painter.drawText(QRect(-30, -15, 60, 30), Qt.AlignmentFlag.AlignCenter, eol_text)
            painter.restore()

    def sizeHint(self, option, index):
        return QSize(140, 160)


class DictTranslator(QTranslator):
    """Minimal translator that maps source text directly to translations."""

    def __init__(self, catalog):
        super().__init__()
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

class FloatingButtonWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Main layout for content
        self.content_layout = QVBoxLayout(self)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        
        # The floating button (child of self, not added to layout)
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
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 5)
        self.btn_apply.setGraphicsEffect(shadow)
        
        self.btn_apply.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Position button at bottom right with margin
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

class M5BuilderGUI(QMainWindow):
    HIGHLIGHT_STYLE = "background-color: #DFF7E0;"
    VARIANT_OVERRIDE_STYLE = "background-color: #EAF4FF; color: #24476B; border: 1px solid #C8DDF4;"
    def __init__(self):
        super().__init__()
        self.setWindowTitle("M5Autodetect CBuilder GUI - byonexs.")
        self.resize(1200, 700)
        
        # Ensure cache directory exists
        os.makedirs(CACHE_DIR, exist_ok=True)
        os.makedirs(LOCALES_DIR, exist_ok=True)
        
        self.current_yaml_data = None
        self.base_yaml_data = None
        self.current_device_original = None
        self._is_rebuilding_detail = False
        self.variant_editors = []
        self.translator = None
        self.current_language = None
        self.available_languages = [
            ("zh_CN", "中文"),
            ("ja_JP", "日本語"),
            ("en_US", "English"),
        ]
        
        # Central widget with splitter
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout(self.central_widget)
        
        # Create splitter for left navigation and right content
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - Navigation Tree
        self.tree_widget = QTreeWidget()
        self.tree_widget.setMinimumWidth(250)
        self.tree_widget.itemClicked.connect(self.on_tree_item_clicked)
        self.splitter.addWidget(self.tree_widget)
        
        # Right side - Detail view
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Header
        self.header_label = QLabel()
        self.header_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self._header_template = "设备仪表板"
        self._header_kwargs = {}
        self.header_bar = QHBoxLayout()
        self.header_bar.addWidget(self.header_label)
        self.header_bar.addStretch()
        self.lang_label = QLabel()
        self.language_selector = NoScrollComboBox()
        self.language_selector.setMinimumWidth(140)
        for code, label in self.available_languages:
            self.language_selector.addItem(label, code)
        self.language_selector.currentIndexChanged.connect(self._on_language_changed)
        self.header_bar.addWidget(self.lang_label)
        self.header_bar.addWidget(self.language_selector)
        right_layout.addLayout(self.header_bar)
        
        # Stacked Widget for different views
        self.stacked_widget = QStackedWidget()
        
        # View 1: Dashboard (Device Grid)
        self.dashboard_widget = QListWidget()
        self.dashboard_widget.setViewMode(QListWidget.ViewMode.IconMode)
        self.dashboard_widget.setMovement(QListWidget.Movement.Static)
        self.dashboard_widget.setIconSize(QSize(100, 100))
        self.dashboard_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.dashboard_widget.setSpacing(10)
        self.dashboard_widget.setItemDelegate(DeviceItemDelegate()) # Set custom delegate
        self.dashboard_widget.itemDoubleClicked.connect(self.on_dashboard_item_clicked)
        self.stacked_widget.addWidget(self.dashboard_widget)
        
        # View 2: Detail View (Container for dynamic content)
        self.detail_container = FloatingButtonWidget()
        self.detail_layout = self.detail_container.content_layout
        self.stacked_widget.addWidget(self.detail_container)
        self._floating_btn_template = "💾 保存修改"
        self._apply_floating_button_translation()
        
        # View 3: YAML Editor
        self.editor = QTextEdit()
        self.editor.setFont(QFont("Consolas", 10))
        self.stacked_widget.addWidget(self.editor)
        
        right_layout.addWidget(self.stacked_widget)
        
        # Buttons
        self.button_layout = QHBoxLayout()
        
        self.btn_home = QPushButton()
        self.btn_home.clicked.connect(self.show_dashboard)
        self.button_layout.addWidget(self.btn_home)
        
        self.btn_edit_yaml = QPushButton()
        self.btn_edit_yaml.clicked.connect(self.show_yaml_editor)
        self.button_layout.addWidget(self.btn_edit_yaml)
        
        self.btn_load = QPushButton()
        self.btn_load.clicked.connect(self.load_yaml)
        self.button_layout.addWidget(self.btn_load)
        
        self.btn_save = QPushButton()
        self.btn_save.clicked.connect(self.save_yaml)
        self.button_layout.addWidget(self.btn_save)
        
        self.btn_generate = QPushButton()
        self.btn_generate.clicked.connect(self.generate_device_data_files)
        self.btn_generate.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.button_layout.addWidget(self.btn_generate)
        
        right_layout.addLayout(self.button_layout)
        
        self.splitter.addWidget(right_widget)
        self.splitter.setSizes([300, 900])
        
        main_layout.addWidget(self.splitter)

        # Apply initial translations
        default_lang = self._detect_default_language()
        default_index = self.language_selector.findData(default_lang)
        if default_index == -1:
            default_index = 0
        self.language_selector.blockSignals(True)
        self.language_selector.setCurrentIndex(default_index)
        self.language_selector.blockSignals(False)
        self.apply_language(self.language_selector.currentData())
        
        # Load initial data
        self.load_yaml()
        print("GUI Initialized successfully")

    def _register_change_highlight(self, widget, signal, getter, original_value):
        """Apply highlight style when widget value changes from original."""
        if widget is None or signal is None:
            return

        highlight_style = self.HIGHLIGHT_STYLE

        def update_highlight(*_):
            try:
                current = getter()
            except Exception:
                current = None
            widget.setStyleSheet(highlight_style if current != original_value else "")

        signal.connect(update_highlight)
        update_highlight()

    def _normalize_struct(self, value):
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            try:
                return yaml.dump(value, sort_keys=True, allow_unicode=True)
            except Exception:
                return str(value)
        return str(value).strip()

    def _compose_variant_display_name(self, base_name, variant_name):
        base = str(base_name or self.tr('Unknown Device'))
        suffix = str(variant_name or '').strip()
        return f"{base}_{suffix}" if suffix else base

    def _is_effective_variant_override(self, value):
        if value is None:
            return False
        if isinstance(value, str):
            return value.strip() != ''
        if isinstance(value, (list, dict)):
            return len(value) > 0
        return True

    def _variant_has_overrides(self, variant_data):
        if not isinstance(variant_data, dict):
            return False
        for key, value in variant_data.items():
            if key == 'name':
                continue
            if self._is_effective_variant_override(value):
                return True
        return False

    def _merge_variant_view_data(self, base_data, variant_data):
        merged = copy.deepcopy(base_data or {})
        variant = copy.deepcopy(variant_data or {})
        for key, value in variant.items():
            if key == 'name':
                continue
            if not self._is_effective_variant_override(value):
                continue
            merged[key] = value
        merged['name'] = self._compose_variant_display_name((base_data or {}).get('name'), variant.get('name'))
        return merged

    def _variant_text_brush(self, variant_data):
        return QBrush(QColor('#000000'))

    def _refresh_config_selector(self):
        base_name = str(self.device_data.get('name') or self.tr('Unknown Device'))
        variants = self.device_data.get('variants', [])
        if not isinstance(variants, list):
            variants = []

        self.combo_config.blockSignals(True)
        self.combo_config.clear()
        self.combo_config.addItem(self.tr("主设备: {name}").format(name=base_name), None)
        for i, variant in enumerate(variants):
            variant_name = self._compose_variant_display_name(base_name, variant.get('name', f'Variant {i+1}'))
            self.combo_config.addItem(self.tr("变体: {name}").format(name=variant_name), i)
        self.combo_config.blockSignals(False)

    def _extract_variant_override_data(self, base_data, edited_data, variant_name):
        overrides = {'name': str(variant_name or '').strip()}
        if not isinstance(edited_data, dict):
            return overrides

        for key, value in edited_data.items():
            if key == 'name':
                continue
            if not self._is_effective_variant_override(value):
                continue
            base_value = (base_data or {}).get(key)
            if self._normalize_struct(value) != self._normalize_struct(base_value):
                overrides[key] = copy.deepcopy(value)

        return overrides

    def _collect_device_changes(self, old_data, new_data):
        if not isinstance(old_data, dict):
            old_data = {}
        if not isinstance(new_data, dict):
            new_data = {}
        change_lines = []

        field_labels = {
            'name': self.tr('名称'),
            'description': self.tr('描述'),
            'sku': 'SKU',
            'eol': self.tr('EOL 状态'),
            'image': self.tr('图片链接'),
            'docs': self.tr('文档链接'),
            'mcu': 'MCU'
        }
        empty_placeholder = self.tr('[空]')

        for key, label in field_labels.items():
            old_val = str(old_data.get(key) or '').strip()
            new_val = str(new_data.get(key) or '').strip()
            if old_val != new_val:
                change_lines.append(
                    self.tr("{label}: {old} → {new}").format(
                        label=label,
                        old=old_val or empty_placeholder,
                        new=new_val or empty_placeholder
                    )
                )

        # Check PSRAM enabled (boolean field)
        old_psram = bool(old_data.get('psram_enabled', False))
        new_psram = bool(new_data.get('psram_enabled', False))
        if old_psram != new_psram:
            old_text = self.tr("启用") if old_psram else self.tr("禁用")
            new_text = self.tr("启用") if new_psram else self.tr("禁用")
            change_lines.append(
                self.tr("{label}: {old} → {new}").format(
                    label=self.tr("PSRAM 启用"),
                    old=old_text,
                    new=new_text
                )
            )

        # Check complex fields with detailed diff
        self._check_pins_changes(old_data, new_data, change_lines)
        self._check_i2c_changes(old_data, new_data, change_lines)
        self._check_display_changes(old_data, new_data, change_lines)
        self._check_touch_changes(old_data, new_data, change_lines)
        self._check_variants_changes(old_data, new_data, change_lines)
        self._check_additional_tests_changes(old_data, new_data, change_lines)

        return change_lines
    
    def _check_additional_tests_changes(self, old_data, new_data, change_lines):
        old_tests = old_data.get('additional_tests', [])
        new_tests = new_data.get('additional_tests', [])
        
        if self._normalize_struct(old_tests) != self._normalize_struct(new_tests):
            if isinstance(new_tests, list) and isinstance(old_tests, list):
                change_lines.append(
                    self.tr("额外测试数量: {old} → {new}").format(
                        old=len(old_tests),
                        new=len(new_tests)
                    )
                )
            else:
                change_lines.append(self.tr("额外测试配置已更新"))

        return change_lines
    
    def _check_identify_i2c_changes(self, old_data, new_data, change_lines):
        old_val = old_data.get('identify_i2c', [])
        new_val = new_data.get('identify_i2c', [])
        if self._normalize_struct(old_val) != self._normalize_struct(new_val):
            change_lines.append(self.tr("identify_i2c 配置已更新"))

    def _check_tests_changes(self, old_data, new_data, change_lines):
        old_tests = old_data.get('tests', [])
        new_tests = new_data.get('tests', [])
        if self._normalize_struct(old_tests) != self._normalize_struct(new_tests):
            if isinstance(new_tests, list) and isinstance(old_tests, list):
                change_lines.append(
                    self.tr("测试项数量: {old} → {new}").format(
                        old=len(old_tests),
                        new=len(new_tests)
                    )
                )
            else:
                change_lines.append(self.tr("测试项配置已更新"))

    def _check_variants_changes(self, old_data, new_data, change_lines):
        old_val = old_data.get('variants', [])
        new_val = new_data.get('variants', [])
        if self._normalize_struct(old_val) != self._normalize_struct(new_val):
            change_lines.append(
                self.tr("变体配置已更新: {old} → {new}").format(
                    old=len(old_val),
                    new=len(new_val)
                )
            )
    
    def _check_pins_changes(self, old_data, new_data, change_lines):
        old_pins = old_data.get('check_pins', {})
        new_pins = new_data.get('check_pins', {})
        
        # Check count
        old_count = old_data.get('check_pins_count')
        new_count = new_data.get('check_pins_count')
        if old_count != new_count:
            change_lines.append(
                self.tr("检测引脚通过数量: {old} → {new}").format(
                    old=old_count,
                    new=new_count
                )
            )

        if not isinstance(old_pins, dict):
            old_pins = {}
        if not isinstance(new_pins, dict):
            new_pins = {}
        
        # Helper to normalize keys
        def normalize_keys(d):
            new_d = {}
            for k, v in d.items():
                try:
                    key = int(k)
                except (ValueError, TypeError):
                    key = k
                new_d[key] = v
            return new_d

        old_pins_norm = normalize_keys(old_pins)
        new_pins_norm = normalize_keys(new_pins)
        
        all_keys = set(old_pins_norm.keys()) | set(new_pins_norm.keys())
        
        # Sort keys
        def sort_key(k):
            if isinstance(k, int):
                return k
            if isinstance(k, str) and k.isdigit():
                return int(k)
            return 0
            
        sorted_keys = sorted(list(all_keys), key=sort_key)
        
        for key in sorted_keys:
            old_pin = old_pins_norm.get(key)
            new_pin = new_pins_norm.get(key)
            
            if old_pin is not None and new_pin is not None:
                # Check for changes
                old_mode = old_pin.get('mode', 'input')
                old_expect = old_pin.get('expect', 0)
                new_mode = new_pin.get('mode', 'input')
                new_expect = new_pin.get('expect', 0)
                
                if old_mode != new_mode or old_expect != new_expect:
                    change_lines.append(
                        self.tr("检测引脚: GPIO{gpio}({old_mode}={old_expect}) → GPIO{gpio}({new_mode}={new_expect})").format(
                            gpio=key,
                            old_mode=old_mode,
                            old_expect=old_expect,
                            new_mode=new_mode,
                            new_expect=new_expect
                        )
                    )
            elif old_pin is not None:
                # Removed
                old_mode = old_pin.get('mode', 'input')
                old_expect = old_pin.get('expect', 0)
                change_lines.append(
                    self.tr("检测引脚: GPIO{gpio}({mode}={expect}) → [已删除]").format(
                        gpio=key,
                        mode=old_mode,
                        expect=old_expect
                    )
                )
            else:
                # Added
                new_mode = new_pin.get('mode', 'input')
                new_expect = new_pin.get('expect', 0)
                change_lines.append(
                    self.tr("检测引脚: [新增] → GPIO{gpio}({mode}={expect})").format(
                        gpio=key,
                        mode=new_mode,
                        expect=new_expect
                    )
                )
    
    def _check_i2c_changes(self, old_data, new_data, change_lines):
        old_i2c_list = old_data.get('i2c_internal', [])
        new_i2c_list = new_data.get('i2c_internal', [])
        
        if not isinstance(old_i2c_list, list):
            old_i2c_list = []
        if not isinstance(new_i2c_list, list):
            new_i2c_list = []

        # Helper to map by port
        def map_by_port(i2c_list):
            mapping = {}
            for item in i2c_list:
                if isinstance(item, dict):
                    port = item.get('port', 0)
                    mapping[port] = item
            return mapping

        old_map = map_by_port(old_i2c_list)
        new_map = map_by_port(new_i2c_list)
        
        all_ports = sorted(set(old_map.keys()) | set(new_map.keys()))
        
        for port in all_ports:
            old_bus = old_map.get(port)
            new_bus = new_map.get(port)
            
            if old_bus and new_bus:
                # Check bus config changes
                changes = []
                if old_bus.get('sda') != new_bus.get('sda'):
                    changes.append(
                        self.tr("SDA: {old}→{new}").format(
                            old=old_bus.get('sda'),
                            new=new_bus.get('sda')
                        )
                    )
                if old_bus.get('scl') != new_bus.get('scl'):
                    changes.append(
                        self.tr("SCL: {old}→{new}").format(
                            old=old_bus.get('scl'),
                            new=new_bus.get('scl')
                        )
                    )
                if old_bus.get('freq') != new_bus.get('freq'):
                    changes.append(
                        self.tr("频率: {old}→{new}").format(
                            old=old_bus.get('freq'),
                            new=new_bus.get('freq')
                        )
                    )
                if old_bus.get('internal_pullup', False) != new_bus.get('internal_pullup', False):
                    changes.append(
                        self.tr("内部上拉: {old}→{new}").format(
                            old=self.tr("是") if old_bus.get('internal_pullup', False) else self.tr("否"),
                            new=self.tr("是") if new_bus.get('internal_pullup', False) else self.tr("否")
                        )
                    )
                
                if changes:
                    change_lines.append(
                        self.tr("内部 I2C Port{port}: {changes}").format(
                            port=port,
                            changes=", ".join(changes)
                        )
                    )
                
                # Check detect count
                old_detect_count = old_bus.get('detect_count')
                new_detect_count = new_bus.get('detect_count')
                if old_detect_count != new_detect_count:
                    change_lines.append(
                        self.tr("内部 I2C Port{port} 检测通过数量: {old} → {new}").format(
                            port=port,
                            old=old_detect_count,
                            new=new_detect_count
                        )
                    )

                # Check detected devices
                old_detect = old_bus.get('detect', [])
                new_detect = new_bus.get('detect', [])
                
                # Map devices by address for better comparison
                def map_detects(detect_list):
                    d_map = {}
                    for d in detect_list:
                        if isinstance(d, dict):
                            addr = d.get('addr')
                            if addr is not None:
                                d_map[addr] = d
                    return d_map

                old_d_map = map_detects(old_detect)
                new_d_map = map_detects(new_detect)
                
                all_addrs = sorted(set(old_d_map.keys()) | set(new_d_map.keys()))
                
                for addr in all_addrs:
                    old_d = old_d_map.get(addr)
                    new_d = new_d_map.get(addr)
                    
                    addr_hex = f"0x{addr:02X}"
                    
                    if old_d and new_d:
                        if old_d.get('name') != new_d.get('name'):
                            change_lines.append(
                                self.tr("内部 I2C Port{port} 设备 {addr}: 名称 '{old}' → '{new}'").format(
                                    port=port,
                                    addr=addr_hex,
                                    old=old_d.get('name'),
                                    new=new_d.get('name')
                                )
                            )
                    elif old_d:
                        change_lines.append(
                            self.tr("内部 I2C Port{port} 设备: [删除] {addr} ({name})").format(
                                port=port,
                                addr=addr_hex,
                                name=old_d.get('name')
                            )
                        )
                    else:
                        change_lines.append(
                            self.tr("内部 I2C Port{port} 设备: [新增] {addr} ({name})").format(
                                port=port,
                                addr=addr_hex,
                                name=new_d.get('name')
                            )
                        )

            elif old_bus:
                # Bus removed
                change_lines.append(
                    self.tr("内部 I2C Port{port}: [已删除]").format(port=port)
                )
            else:
                # Bus added
                change_lines.append(
                    self.tr("内部 I2C Port{port}: [新增] (SDA:{sda} SCL:{scl})").format(
                        port=port,
                        sda=new_bus.get('sda'),
                        scl=new_bus.get('scl')
                    )
                )
    
    def _check_display_changes(self, old_data, new_data, change_lines):
        old_display = old_data.get('display', [])
        new_display = new_data.get('display', [])
        
        if self._normalize_struct(old_display) != self._normalize_struct(new_display):
            if isinstance(new_display, list) and isinstance(old_display, list):
                change_lines.append(
                    self.tr("显示屏配置项数量: {old} → {new}").format(
                        old=len(old_display),
                        new=len(new_display)
                    )
                )
            else:
                change_lines.append(self.tr("显示屏配置已更新"))
    
    def _check_touch_changes(self, old_data, new_data, change_lines):
        old_touch = old_data.get('touch', [])
        new_touch = new_data.get('touch', [])
        
        if self._normalize_struct(old_touch) != self._normalize_struct(new_touch):
            if isinstance(new_touch, list) and isinstance(old_touch, list):
                change_lines.append(
                    self.tr("触摸配置项数量: {old} → {new}").format(
                        old=len(old_touch),
                        new=len(new_touch)
                    )
                )
            else:
                change_lines.append(self.tr("触摸配置已更新"))

    def _build_changes_html(self, change_lines):
        if not change_lines:
            return ""
        rows = []
        for line in change_lines:
            rows.append(
                f"<li><span style='background-color:#FFCDD2;padding:4px 8px;border-radius:6px;display:block;margin-bottom:6px;'>{html.escape(line)}</span></li>"
            )
        header_html = self.tr("<p>以下字段将被保存：</p>")
        return header_html + "<ul>" + "".join(rows) + "</ul>"

    def _show_change_dialog(self, title, body_html):
        if not body_html:
            return True

        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setTextFormat(Qt.TextFormat.RichText)
        box.setText(body_html)
        box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        box.setDefaultButton(QMessageBox.StandardButton.Ok)
        return box.exec() == QMessageBox.StandardButton.Ok

    def _collect_all_changes(self, candidate_data=None):
        target_data = candidate_data or self.current_yaml_data
        if not target_data:
            return {}

        base_source = self.base_yaml_data or {}
        base_categories = base_source.get('mcu_categories', [])
        current_categories = target_data.get('mcu_categories', []) if isinstance(target_data, dict) else []
        summary = {}

        base_map = {cat.get('mcu'): cat for cat in base_categories if isinstance(cat, dict) and cat.get('mcu')}

        for current_cat in current_categories:
            if not isinstance(current_cat, dict):
                continue
            mcu_name = current_cat.get('mcu') or self.tr('Unknown MCU')
            base_cat = base_map.get(mcu_name, {})
            base_devices = base_cat.get('devices', []) if isinstance(base_cat, dict) else []
            current_devices = current_cat.get('devices', [])
            if not isinstance(current_devices, list):
                current_devices = []

            base_dev_map = {dev.get('name'): dev for dev in base_devices if isinstance(dev, dict) and dev.get('name')}

            for current_dev in current_devices:
                if not isinstance(current_dev, dict):
                    continue
                dev_key = current_dev.get('name')
                dev_name = dev_key or self.tr('Unknown Device')
                base_dev = base_dev_map.get(dev_key)
                changes = self._collect_device_changes(base_dev or {}, current_dev)
                if changes:
                    summary.setdefault(mcu_name, {})[dev_name] = changes

        return summary

    def _build_grouped_changes_html(self, summary):
        if not summary:
            return ""

        sections = []
        for mcu, devices in summary.items():
            device_rows = []
            for device_name, changes in devices.items():
                change_list = ''.join(
                    f"<li><span style='background-color:#FFCDD2;padding:3px 6px;border-radius:4px;display:block;margin-bottom:4px;'>{html.escape(c)}</span></li>"
                    for c in changes
                )
                device_rows.append(
                    f"<div style='margin-bottom:10px;'><strong>{html.escape(device_name)}</strong><ul style='margin-top:4px;'>" + change_list + "</ul></div>"
                )
            sections.append(
                f"<div style='margin-bottom:14px;'><h4 style='margin-bottom:6px;'>{html.escape(mcu)}</h4>" + "".join(device_rows) + "</div>"
            )
        
        header_html = self.tr("<p>以下设备将被修改：</p>")
        return header_html + "".join(sections)

    def _confirm_device_changes(self, old_data, new_data):
        change_lines = self._collect_device_changes(old_data, new_data)
        if not change_lines:
            QMessageBox.information(
                self,
                self.tr("无变更"),
                self.tr("当前没有任何修改，无需保存。")
            )
            return False

        body_html = self._build_changes_html(change_lines)
        return self._show_change_dialog(self.tr("保存前确认"), body_html)

    def _confirm_full_yaml_changes(self, candidate_data=None):
        summary = self._collect_all_changes(candidate_data)
        base_snapshot = self.base_yaml_data or {}
        candidate_snapshot = candidate_data or {}
        if not summary and base_snapshot != candidate_snapshot:
            summary = {
                self.tr('整体'): {
                    self.tr('YAML 配置'): [self.tr('整体结构发生变化')]
                }
            }
        if not summary:
            QMessageBox.information(
                self,
                self.tr("无变更"),
                self.tr("当前 YAML 没有任何改动。")
            )
            return False

        html_body = self._build_grouped_changes_html(summary)
        return self._show_change_dialog(self.tr("写入 YAML 前确认"), html_body)

    def get_cached_image(self, url):
        """Download image from URL and cache it locally, return QPixmap"""
        if not url:
            return None
            
        try:
            # Create cache filename from URL hash
            url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
            ext = os.path.splitext(url)[1]
            if not ext:
                ext = '.png' # Default extension
            
            cache_path = os.path.join(CACHE_DIR, f"{url_hash}{ext}")
            
            # Check if cached file exists
            if os.path.exists(cache_path):
                return QPixmap(cache_path)
            
            # Download image
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                with open(cache_path, 'wb') as f:
                    f.write(response.content)
                return QPixmap(cache_path)
                
        except Exception as e:
            print(f"Failed to load image {url}: {e}")
            
        return None

    def load_yaml(self):
        if os.path.exists(YAML_FILE):
            try:
                with open(YAML_FILE, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.editor.setPlainText(content)
                    self.current_yaml_data = yaml.safe_load(content)
                self.populate_tree()
                self.populate_dashboard()
                self.show_dashboard()
                self.statusBar().showMessage(
                    self.tr("已加载: {path}").format(path=YAML_FILE)
                )
                self.base_yaml_data = copy.deepcopy(self.current_yaml_data)
            except Exception as e:
                QMessageBox.critical(
                    self,
                    self.tr("错误"),
                    self.tr("加载 YAML 失败: {error}").format(error=str(e))
                )
        else:
            self.editor.setPlainText(self.tr("# 未找到 m5stack_dev_config.yaml。可创建一个新的配置。"))
            self.current_yaml_data = None
            self.base_yaml_data = None

    def _detect_default_language(self):
        system_name = QLocale.system().name()
        for code, _ in self.available_languages:
            if system_name == code:
                return code
        system_base = system_name.split('_')[0]
        for code, _ in self.available_languages:
            if code.startswith(system_base):
                return code
        return "zh_CN"

    def _on_language_changed(self, index):
        if index < 0:
            return
        lang_code = self.language_selector.itemData(index)
        if not lang_code or lang_code == self.current_language:
            return
        self.apply_language(lang_code)

    def _load_dict_translator(self, lang_code):
        json_path = os.path.join(LOCALES_DIR, f'm5builder_{lang_code}.json')
        if not os.path.exists(json_path):
            return None
        try:
            with open(json_path, 'r', encoding='utf-8') as fp:
                payload = json.load(fp)
            catalog = payload.get('strings') if isinstance(payload, dict) else None
            if catalog is None:
                catalog = payload
            if isinstance(catalog, dict):
                return DictTranslator(catalog)
        except Exception as exc:
            print(f"[i18n] Failed to load JSON translator {json_path}: {exc}")
        return None

    def apply_language(self, lang_code):
        app = QApplication.instance()
        if app is None:
            return

        if self.translator:
            app.removeTranslator(self.translator)
            self.translator = None

        # Default language falls back to source strings
        if lang_code == 'zh_CN':
            self.current_language = lang_code
            self.retranslate_ui()
            return

        translator_path = os.path.join(
            LOCALES_DIR,
            f'm5builder_{lang_code}.qm'
        )
        new_translator = QTranslator()
        if os.path.exists(translator_path) and new_translator.load(translator_path):
            app.installTranslator(new_translator)
            self.translator = new_translator
        else:
            dict_translator = self._load_dict_translator(lang_code)
            if dict_translator:
                app.installTranslator(dict_translator)
                self.translator = dict_translator
            else:
                print(f"[i18n] Translator catalog not found for {lang_code}: {translator_path}")
                # Fall back to default language if nothing available
                lang_code = 'zh_CN'

        self.current_language = lang_code
        self.retranslate_ui()

    def _refresh_header_text(self):
        template = getattr(self, '_header_template', None) or "设备仪表板"
        kwargs = getattr(self, '_header_kwargs', {})
        translated = self.tr(template)
        if kwargs:
            try:
                translated = translated.format(**kwargs)
            except Exception:
                pass
        self.header_label.setText(translated)

    def _set_header_text(self, template, **kwargs):
        self._header_template = template
        self._header_kwargs = kwargs
        self._refresh_header_text()

    def _apply_floating_button_translation(self):
        template = getattr(self, '_floating_btn_template', "💾 保存修改")
        self.detail_container.btn_apply.setText(self.tr(template))

    def _set_floating_button_text(self, template):
        self._floating_btn_template = template
        self._apply_floating_button_translation()

    def retranslate_ui(self):
        self.setWindowTitle(self.tr("M5Autodetect CBuilder GUI - byonexs."))
        self.tree_widget.setHeaderLabel(self.tr("MCU 类别与设备"))
        self.lang_label.setText(self.tr("语言:"))

        self.btn_home.setText(self.tr("🏠 仪表板"))
        self.btn_edit_yaml.setText(self.tr("📝 编辑 YAML"))
        self.btn_load.setText(self.tr("🔄 重新加载"))
        self.btn_save.setText(self.tr("💾 写入 YAML"))
        self.btn_generate.setText(self.tr("⚙️ 生成设备数据文件 (.h/.cpp)"))

        self._refresh_header_text()
        self._apply_floating_button_translation()

        # Refresh Detail View if active to apply new language
        if self.stacked_widget.currentWidget() == self.detail_container:
            if hasattr(self, 'current_edit_data') and self.current_edit_data:
                item_type = self.current_edit_data.get('type')
                if item_type == 'device':
                    # Try to save current edits to memory so we don't lose them
                    # If validation fails, we skip refresh to allow user to fix errors
                    if self.save_device_details(silent=True):
                        self.show_device_details(self.current_edit_data)
                elif item_type == 'variant':
                    if self.save_device_details(silent=True):
                        self.show_variant_details(self.current_edit_data)
                elif item_type == 'mcu':
                    self.show_mcu_details(self.current_edit_data)
                elif item_type == 'pin':
                    self.show_pin_details(self.current_edit_data)

            
    def populate_dashboard(self):
        """Populate the dashboard with device cards"""
        self.dashboard_widget.clear()
        
        if not self.current_yaml_data:
            return
            
        mcu_categories = self.current_yaml_data.get('mcu_categories', [])
        
        # Create a placeholder pixmap
        placeholder = QPixmap(100, 100)
        placeholder.fill(QColor("#E0E0E0"))
        
        for category_idx, category in enumerate(mcu_categories):
            devices = category.get('devices', [])
            for dev_idx, device in enumerate(devices):
                device_name = device.get('name') or self.tr('Unknown Device')
                image_url = device.get('image', '')
                sku = device.get('sku', '')
                eol = device.get('eol', '')
                
                # Try to load image
                pixmap = self.get_cached_image(image_url)
                if not pixmap:
                    pixmap = placeholder
                
                # Scale pixmap for icon
                icon_pixmap = pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                icon = QIcon(icon_pixmap)
                
                item = QListWidgetItem(icon, device_name)
                item.setData(Qt.ItemDataRole.UserRole, {
                    'type': 'device',
                    'mcu_index': category_idx,
                    'device_index': dev_idx,
                    'sku': sku,
                    'eol': eol,
                    'variants': device.get('variants', []),
                    'base_name': device_name,
                    'variant_name': '',
                    'variant_override': False,
                })
                self.dashboard_widget.addItem(item)

                variants = device.get('variants', [])
                if isinstance(variants, list):
                    for variant_idx, variant in enumerate(variants):
                        variant_display_name = self._compose_variant_display_name(device_name, variant.get('name', f'Variant {variant_idx+1}'))
                        variant_item = QListWidgetItem(icon, variant_display_name)
                        variant_item.setData(Qt.ItemDataRole.UserRole, {
                            'type': 'variant',
                            'mcu_index': category_idx,
                            'device_index': dev_idx,
                            'variant_index': variant_idx,
                            'sku': sku,
                            'eol': eol,
                            'base_name': device_name,
                            'variant_name': variant.get('name', f'Variant {variant_idx+1}'),
                            'variant_override': self._variant_has_overrides(variant),
                        })
                        self.dashboard_widget.addItem(variant_item)

    def on_dashboard_item_clicked(self, item):
        """Handle dashboard item click"""
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
            
        mcu_idx = data.get('mcu_index')
        dev_idx = data.get('device_index')
        variant_idx = data.get('variant_index')

        if mcu_idx < self.tree_widget.topLevelItemCount():
            mcu_item = self.tree_widget.topLevelItem(mcu_idx)
            for child_idx in range(mcu_item.childCount()):
                tree_item = mcu_item.child(child_idx)
                tree_data = tree_item.data(0, Qt.ItemDataRole.UserRole) or {}
                if tree_data.get('device_index') != dev_idx:
                    continue
                if variant_idx is None and tree_data.get('type') == 'device':
                    self.tree_widget.setCurrentItem(tree_item)
                    self.on_tree_item_clicked(tree_item, 0)
                    return
                if variant_idx is not None:
                    tree_item.setExpanded(True)
                    for variant_child_idx in range(tree_item.childCount()):
                        variant_item = tree_item.child(variant_child_idx)
                        variant_data = variant_item.data(0, Qt.ItemDataRole.UserRole) or {}
                        if variant_data.get('type') == 'variant' and variant_data.get('variant_index') == variant_idx:
                            self.tree_widget.setCurrentItem(variant_item)
                            self.on_tree_item_clicked(variant_item, 0)
                            return

    def show_dashboard(self):
        self.stacked_widget.setCurrentWidget(self.dashboard_widget)
        self._set_header_text("设备仪表板")
        self.tree_widget.clearSelection()

    def show_yaml_editor(self):
        self.stacked_widget.setCurrentWidget(self.editor)
        self._set_header_text("YAML 编辑器")
        
    def populate_tree(self):
        """Populate the navigation tree with MCU categories and devices"""
        self.tree_widget.clear()
        
        if not self.current_yaml_data:
            return
        
        mcu_categories = self.current_yaml_data.get('mcu_categories', [])
        
        for category_idx, category in enumerate(mcu_categories):
            mcu_name = category.get('mcu') or self.tr('Unknown MCU')
            
            # Create MCU category item
            mcu_item = QTreeWidgetItem(self.tree_widget)
            mcu_item.setText(0, self.tr("📦 {name}").format(name=mcu_name))
            mcu_item.setData(0, Qt.ItemDataRole.UserRole, {
                'type': 'mcu',
                'index': category_idx,
                'data': category
            })
            mcu_item.setExpanded(True)
            
            # Add devices under this MCU
            devices = category.get('devices', [])
            for dev_idx, device in enumerate(devices):
                device_name = device.get('name') or self.tr('Unknown Device')
                device_item = QTreeWidgetItem(mcu_item)
                device_item.setText(0, self.tr("🔧 {name}").format(name=device_name))
                device_item.setData(0, Qt.ItemDataRole.UserRole, {
                    'type': 'device',
                    'mcu_index': category_idx,
                    'device_index': dev_idx,
                    'data': device
                })
                device_item.setExpanded(False)

                variants = device.get('variants', [])
                if isinstance(variants, list):
                    for variant_idx, variant in enumerate(variants):
                        variant_name = self._compose_variant_display_name(device_name, variant.get('name', f'Variant {variant_idx+1}'))
                        variant_item = QTreeWidgetItem(device_item)
                        variant_item.setText(0, self.tr("↳ {name}").format(name=variant_name))
                        variant_item.setForeground(0, self._variant_text_brush(variant))
                        variant_item.setData(0, Qt.ItemDataRole.UserRole, {
                            'type': 'variant',
                            'mcu_index': category_idx,
                            'device_index': dev_idx,
                            'variant_index': variant_idx,
                            'data': variant,
                            'base_data': device,
                        })
    
    def on_tree_item_clicked(self, item, column):
        """Handle tree item selection"""
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if not item_data:
            return
        
        item_type = item_data.get('type')
        
        # Switch to detail view
        self.stacked_widget.setCurrentWidget(self.detail_container)
        
        if item_type == 'mcu':
            self.show_mcu_details(item_data)
        elif item_type == 'device':
            self.show_device_details(item_data)
        elif item_type == 'variant':
            self.show_variant_details(item_data)
    
    def _add_variant_tab(self, variant_data):
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)

        form_layout = QFormLayout()
        name_val = str(variant_data.get('name') or '')
        le_name = QLineEdit(name_val)
        form_layout.addRow(self.tr("变体名称:"), le_name)
        self._register_change_highlight(le_name, le_name.textChanged, le_name.text, name_val)
        layout.addLayout(form_layout)

        grp_id_i2c = QGroupBox(self.tr("识别 I2C (变体识别)"))
        layout_id_i2c = QVBoxLayout(grp_id_i2c)
        identify_i2c_editors = []
        for item in variant_data.get('identify_i2c', []) or []:
            self._add_identify_i2c_editor(layout_id_i2c, item, identify_i2c_editors)
        btn_add_id_i2c = QPushButton(self.tr("➕ 添加识别 I2C"))
        btn_add_id_i2c.clicked.connect(lambda: self._add_identify_i2c_editor(layout_id_i2c, {}, identify_i2c_editors))
        layout_id_i2c.addWidget(btn_add_id_i2c)
        layout.addWidget(grp_id_i2c)

        grp_touch = QGroupBox(self.tr("Step 5: Screen - 触摸"))
        layout_touch = QVBoxLayout(grp_touch)
        touch_editors = []
        for item in variant_data.get('touch', []) or []:
            self._add_touch_editor(layout_touch, item, touch_editors)
        btn_add_touch = QPushButton(self.tr("➕ 添加触摸"))
        btn_add_touch.clicked.connect(lambda: self._add_touch_editor(layout_touch, {}, touch_editors))
        layout_touch.addWidget(btn_add_touch)
        layout.addWidget(grp_touch)

        grp_display = QGroupBox(self.tr("Step 6: 显示屏"))
        layout_display = QVBoxLayout(grp_display)
        display_editors = []
        for item in variant_data.get('display', []) or []:
            self._add_display_editor_to_layout(layout_display, item, display_editors)
        btn_add_display = QPushButton(self.tr("➕ 添加显示屏"))
        btn_add_display.clicked.connect(lambda: self._add_display_editor_to_layout(layout_display, {}, display_editors))
        layout_display.addWidget(btn_add_display)
        layout.addWidget(grp_display)

        btn_del = QPushButton(self.tr("删除此变体"))
        btn_del.setStyleSheet("background-color: #FFCDD2; color: #B71C1C;")
        layout.addWidget(btn_del)

        editor_dict = {
            'widget': tab_widget,
            'name': le_name,
            'identify_i2c_editors': identify_i2c_editors,
            'touch_editors': touch_editors,
            'display_editors': display_editors,
        }

        self.variant_editors.append(editor_dict)

        if hasattr(self, 'tabs_variants'):
            default_tab_name = self.tr("新变体")
            self.tabs_variants.addTab(tab_widget, name_val or default_tab_name)
            le_name.textChanged.connect(
                lambda text, w=tab_widget: self.tabs_variants.setTabText(
                    self.tabs_variants.indexOf(w), text or default_tab_name
                )
            )

        btn_del.clicked.connect(lambda: self._delete_editor_from_list(tab_widget, editor_dict, self.variant_editors))
        return editor_dict

    def _add_identify_i2c_editor(self, parent_layout, id_i2c_data, editor_list):
        widget = QGroupBox()
        layout = QGridLayout(widget)
        
        # Port
        sb_port = NoScrollSpinBox()
        sb_port.setValue(int(id_i2c_data.get('port', 0)))
        layout.addWidget(QLabel(self.tr("Port:")), 0, 0)
        layout.addWidget(sb_port, 0, 1)
        
        # SDA
        sb_sda = NoScrollSpinBox()
        sb_sda.setRange(-1, 999)
        sb_sda.setValue(int(id_i2c_data.get('sda', -1)))
        layout.addWidget(QLabel(self.tr("SDA:")), 0, 2)
        layout.addWidget(sb_sda, 0, 3)
        
        # SCL
        sb_scl = NoScrollSpinBox()
        sb_scl.setRange(-1, 999)
        sb_scl.setValue(int(id_i2c_data.get('scl', -1)))
        layout.addWidget(QLabel(self.tr("SCL:")), 0, 4)
        layout.addWidget(sb_scl, 0, 5)
        
        # Freq
        sb_freq = NoScrollSpinBox()
        sb_freq.setRange(0, 1000000)
        sb_freq.setSingleStep(10000)
        sb_freq.setValue(int(id_i2c_data.get('freq', 400000)))
        layout.addWidget(QLabel(self.tr("Freq:")), 1, 0)
        layout.addWidget(sb_freq, 1, 1)
        
        # Addr
        le_addr = QLineEdit(self._int_to_hex_str(id_i2c_data.get('addr')))
        le_addr.setPlaceholderText("0x55")
        layout.addWidget(QLabel(self.tr("Addr:")), 1, 2)
        layout.addWidget(le_addr, 1, 3)
        
        # Delete
        btn_del = QPushButton(self.tr("删除"))
        btn_del.setStyleSheet("background-color: #FFCDD2; color: #B71C1C;")
        layout.addWidget(btn_del, 1, 4, 1, 2)
        
        parent_layout.addWidget(widget)
        
        editor_dict = {
            'widget': widget,
            'port': sb_port,
            'sda': sb_sda,
            'scl': sb_scl,
            'freq': sb_freq,
            'addr': le_addr
        }
        editor_list.append(editor_dict)
        
        btn_del.clicked.connect(lambda: self._delete_editor_from_list(widget, editor_dict, editor_list))

    def _add_display_editor_to_layout(self, parent_layout, display_data, editor_list):
        widget = QGroupBox()
        widget.setStyleSheet("QGroupBox { border: 1px solid #ccc; border-radius: 5px; margin-top: 10px; padding-top: 10px; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 3px; font-weight: bold; }")
        layout = QVBoxLayout(widget)
        
        # 1. Basic Info (Grid Layout)
        grid_basic = QGridLayout()
        
        # Bus Type
        combo_bus = NoScrollComboBox()
        combo_bus.addItems(['spi', 'i2c', 'parallel8', 'parallel16', 'rgb', 'dsi'])
        current_bus = display_data.get('bus_type', 'spi')
        combo_bus.setCurrentText(current_bus)
        grid_basic.addWidget(QLabel(self.tr("接口类型:")), 0, 0)
        grid_basic.addWidget(combo_bus, 0, 1)

        # Driver
        le_driver = QLineEdit(str(display_data.get('driver', '')))
        grid_basic.addWidget(QLabel(self.tr("驱动:")), 0, 2)
        grid_basic.addWidget(le_driver, 0, 3)
        
        # Width
        sb_width = NoScrollSpinBox()
        sb_width.setRange(0, 9999)
        sb_width.setValue(int(display_data.get('width', 0)))
        grid_basic.addWidget(QLabel(self.tr("宽度:")), 1, 0)
        grid_basic.addWidget(sb_width, 1, 1)
        
        # Height
        sb_height = NoScrollSpinBox()
        sb_height.setRange(0, 9999)
        sb_height.setValue(int(display_data.get('height', 0)))
        grid_basic.addWidget(QLabel(self.tr("高度:")), 1, 2)
        grid_basic.addWidget(sb_height, 1, 3)
        
        # Freq
        sb_freq = NoScrollSpinBox()
        sb_freq.setRange(0, 100000000)
        sb_freq.setSingleStep(1000000)
        sb_freq.setValue(int(display_data.get('freq', 0)))
        grid_basic.addWidget(QLabel(self.tr("频率:")), 2, 0)
        grid_basic.addWidget(sb_freq, 2, 1)
        
        layout.addLayout(grid_basic)
        
        # 2. Interface Configuration (Dynamic Layout)
        # Use a container widget with VBox layout instead of QStackedWidget
        # to allow automatic height adjustment based on visible content.
        container_config = QWidget()
        layout_config = QVBoxLayout(container_config)
        layout_config.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(container_config)
        
        # Helper to create pin table
        def create_pin_table(pins_list, data):
            grp = QGroupBox(self.tr("引脚配置"))
            l = QVBoxLayout(grp)
            t = QTableWidget()
            t.setColumnCount(2)
            t.setHorizontalHeaderLabels([self.tr("功能"), self.tr("引脚")])
            t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            t.setRowCount(len(pins_list))
            for i, p in enumerate(pins_list):
                item = QTableWidgetItem(p)
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                t.setItem(i, 0, item)
                val = data.get(p)
                if val is None: val = ""
                le = QLineEdit(str(val))
                t.setCellWidget(i, 1, le)
            self._adjust_table_height(t)
            l.addWidget(t)
            return grp, t

        pins_data = display_data.get('pins', {})
        
        # Store pages in a dict for easy access
        config_pages = {}

        # Page 0: SPI
        page_spi, table_spi = create_pin_table(['mosi', 'miso', 'sclk', 'cs', 'dc', 'rst', 'bl'], pins_data)
        config_pages['spi'] = page_spi
        layout_config.addWidget(page_spi)
        
        # Page 1: I2C
        page_i2c = QWidget()
        l_i2c = QVBoxLayout(page_i2c)
        l_i2c.setContentsMargins(0, 0, 0, 0)
        # Addr
        l_i2c_form = QFormLayout()
        le_i2c_addr = QLineEdit(self._int_to_hex_str(display_data.get('addr')))
        le_i2c_addr.setPlaceholderText("0x3C")
        l_i2c_form.addRow(self.tr("I2C 地址:"), le_i2c_addr)
        l_i2c.addLayout(l_i2c_form)
        # Pins
        grp_i2c_pins, table_i2c = create_pin_table(['sda', 'scl', 'rst', 'bl'], pins_data)
        l_i2c.addWidget(grp_i2c_pins)
        config_pages['i2c'] = page_i2c
        layout_config.addWidget(page_i2c)
        
        # Page 2: Parallel 8
        page_p8, table_p8 = create_pin_table(['d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7', 'wr', 'rd', 'rs', 'cs', 'rst', 'bl'], pins_data)
        config_pages['parallel8'] = page_p8
        layout_config.addWidget(page_p8)
        
        # Page 3: Parallel 16
        page_p16, table_p16 = create_pin_table([f'd{i}' for i in range(16)] + ['wr', 'rd', 'rs', 'cs', 'rst', 'bl'], pins_data)
        config_pages['parallel16'] = page_p16
        layout_config.addWidget(page_p16)
        
        # Page 4: RGB
        page_rgb, table_rgb = create_pin_table(['hsync', 'vsync', 'de', 'pclk', 'd0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7', 'd8', 'd9', 'd10', 'd11', 'd12', 'd13', 'd14', 'd15', 'disp_en', 'rst', 'bl'], pins_data)
        config_pages['rgb'] = page_rgb
        layout_config.addWidget(page_rgb)

        # Page 5: DSI
        page_dsi, table_dsi = create_pin_table(['te', 'rst', 'bl'], pins_data)
        config_pages['dsi'] = page_dsi
        layout_config.addWidget(page_dsi)

        # Connect combo to switch visibility
        def on_bus_changed(text):
            for bus_name, page in config_pages.items():
                if bus_name == text:
                    page.show()
                else:
                    page.hide()
        
        combo_bus.currentTextChanged.connect(on_bus_changed)
        on_bus_changed(current_bus) # Set initial visibility
        
        # 3. Identify (Form)
        grp_id = QGroupBox(self.tr("识别参数 (Identify)"))
        layout_id = QFormLayout(grp_id)
        
        id_data = display_data.get('identify', {})
        
        le_cmd = QLineEdit(self._int_to_hex_str(id_data.get('cmd')))
        le_cmd.setPlaceholderText(self.tr("例如: 0x04"))
        layout_id.addRow(self.tr("指令 (CMD):"), le_cmd)
        
        le_expect = QLineEdit(self._int_to_hex_str(id_data.get('expect')))
        le_expect.setPlaceholderText(self.tr("例如: 0x079100"))
        layout_id.addRow(self.tr("期望值 (Expect):"), le_expect)
        
        le_mask = QLineEdit(self._int_to_hex_str(id_data.get('mask')))
        le_mask.setPlaceholderText(self.tr("例如: 0xFFFFFF"))
        layout_id.addRow(self.tr("掩码 (Mask):"), le_mask)
        
        chk_rst = QCheckBox(self.tr("读取前复位 (RST Before)"))
        chk_rst.setChecked(bool(id_data.get('rst_before', False)))
        layout_id.addRow("", chk_rst)
        
        sb_wait = NoScrollSpinBox()
        sb_wait.setRange(0, 5000)
        sb_wait.setValue(int(id_data.get('rst_wait', 0)))
        sb_wait.setSuffix(" ms")
        layout_id.addRow(self.tr("复位等待 (Wait):"), sb_wait)
        
        layout.addWidget(grp_id)
        
        # Prerequisites
        prereq_entries = []
        grp_prereq = self._create_prerequisites_widget(display_data, prereq_entries)
        layout.addWidget(grp_prereq)

        # Delete Button
        btn_del = QPushButton(self.tr("删除此屏幕"))
        btn_del.setStyleSheet("background-color: #FFCDD2; color: #B71C1C;")
        layout.addWidget(btn_del)
        
        parent_layout.addWidget(widget)
        
        editor_dict = {
            'widget': widget,
            'bus_type': combo_bus,
            'driver': le_driver,
            'width': sb_width,
            'height': sb_height,
            'freq': sb_freq,
            'tables': {
                'spi': table_spi,
                'i2c': table_i2c,
                'parallel8': table_p8,
                'parallel16': table_p16,
                'rgb': table_rgb,
                'dsi': table_dsi
            },
            'i2c_addr': le_i2c_addr,
            'id_cmd': le_cmd,
            'id_expect': le_expect,
            'id_mask': le_mask,
            'id_rst': chk_rst,
            'id_wait': sb_wait,
            'prereq_entries': prereq_entries
        }
        editor_list.append(editor_dict)
        
        btn_del.clicked.connect(lambda: self._delete_editor_from_list(widget, editor_dict, editor_list))

    def _create_prerequisites_widget(self, data, entries_list):
        grp_prereq = QGroupBox(self.tr("前置条件 (Prerequisites)"))
        layout_prereq = QVBoxLayout(grp_prereq)
        
        # Container for rows
        prereq_container = QWidget()
        layout_prereq_rows = QVBoxLayout(prereq_container)
        layout_prereq_rows.setContentsMargins(0, 0, 0, 0)
        layout_prereq.addWidget(prereq_container)
        
        def add_prereq_row(p_type_val=None, p_params_val=None):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            
            cb_type = NoScrollComboBox()
            cb_type.addItems(['gpio', 'i2c_read', 'i2c_write', 'spi_read', 'spi_write'])
            if p_type_val:
                cb_type.setCurrentText(p_type_val)
            
            param_container = QWidget()
            param_layout = QHBoxLayout(param_container)
            param_layout.setContentsMargins(0, 0, 0, 0)
            
            # Helper to parse params string to dict
            def parse_params(val):
                if isinstance(val, dict):
                    return val
                if not val: return {}
                # Legacy string parsing
                res = {}
                parts = str(val).split(',')
                for part in parts:
                    if ':' in part:
                        k, v = part.split(':', 1)
                        res[k.strip()] = v.strip()
                return res

            current_params = parse_params(p_params_val)

            # Store widget references
            widgets = {}

            def create_label(text):
                lbl = QLabel(text)
                lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                lbl.setFixedWidth(40)
                return lbl

            def update_params_ui(type_text):
                # Clear existing
                while param_layout.count():
                    item = param_layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                widgets.clear()

                if type_text == 'gpio':
                    # GPIO: pin, level
                    sb_gpio = NoScrollSpinBox()
                    sb_gpio.setRange(-1, 999)
                    sb_gpio.setValue(int(current_params.get('gpio', -1)))
                    param_layout.addWidget(create_label("GPIO:"))
                    param_layout.addWidget(sb_gpio)
                    widgets['gpio'] = sb_gpio

                    cb_level = NoScrollComboBox()
                    cb_level.addItems(['0', '1'])
                    cb_level.setCurrentText(str(current_params.get('level', '0')))
                    param_layout.addWidget(create_label("Level:"))
                    param_layout.addWidget(cb_level)
                    widgets['level'] = cb_level
                    param_layout.addStretch()

                elif type_text.startswith('i2c'):
                    # I2C: addr, reg, [data/len]
                    # Addr (Hex)
                    addr_val = str(current_params.get('addr', ''))
                    try:
                        addr_int = int(addr_val, 16) if addr_val.strip().lower().startswith('0x') else int(addr_val)
                        addr_disp = f"0x{addr_int:02X}"
                    except:
                        addr_disp = addr_val
                    le_addr = QLineEdit(addr_disp)
                    le_addr.setPlaceholderText("0x00")
                    le_addr.setFixedWidth(60)
                    param_layout.addWidget(create_label("Addr:"))
                    param_layout.addWidget(le_addr)
                    widgets['addr'] = le_addr

                    # Reg (Hex)
                    reg_val = str(current_params.get('reg', ''))
                    try:
                        reg_int = int(reg_val, 16) if reg_val.strip().lower().startswith('0x') else int(reg_val)
                        reg_disp = f"0x{reg_int:02X}"
                    except:
                        reg_disp = reg_val
                    le_reg = QLineEdit(reg_disp)
                    le_reg.setPlaceholderText("0x00")
                    le_reg.setFixedWidth(60)
                    param_layout.addWidget(create_label("Reg:"))
                    param_layout.addWidget(le_reg)
                    widgets['reg'] = le_reg

                    if 'write' in type_text:
                        # Data field
                        val_str = str(current_params.get('data', '0'))
                        try:
                            val_int = int(val_str, 16) if val_str.strip().lower().startswith('0x') else int(val_str)
                        except:
                            val_int = 0
                        
                        le_data = QLineEdit(f"0x{val_int:02X}")
                        le_data.setPlaceholderText("0x00")
                        le_data.setFixedWidth(60)
                        param_layout.addWidget(create_label("Data:"))
                        param_layout.addWidget(le_data)
                        widgets['data'] = le_data

                        # Bit Editor
                        bit_container = QWidget()
                        bit_layout = QHBoxLayout(bit_container)
                        bit_layout.setContentsMargins(5, 0, 0, 0)
                        bit_layout.setSpacing(1)
                        
                        bit_btns = [] 

                        def on_bit_toggled():
                            new_val = 0
                            for b_idx, btn in bit_btns:
                                if btn.isChecked():
                                    new_val |= (1 << b_idx)
                            le_data.setText(f"0x{new_val:02X}")

                        for i in range(7, -1, -1):
                            btn = QPushButton(str(i))
                            btn.setCheckable(True)
                            btn.setFixedSize(20, 20)
                            def update_style(b=btn):
                                if b.isChecked():
                                    b.setStyleSheet("background-color: #4CAF50; color: white; border: none; font-size: 10px; font-weight: bold;")
                                else:
                                    b.setStyleSheet("background-color: #E0E0E0; color: #888888; border: none; font-size: 10px;")
                            
                            is_set = (val_int >> i) & 1
                            btn.setChecked(bool(is_set))
                            update_style(btn)
                            
                            btn.toggled.connect(lambda checked, b=btn: update_style(b))
                            btn.toggled.connect(on_bit_toggled)
                            
                            bit_layout.addWidget(btn)
                            bit_btns.append((i, btn))
                        
                        bit_layout.addStretch()
                        param_layout.addWidget(bit_container)

                        def on_text_changed(text):
                            try:
                                v = int(text, 16) if text.strip().lower().startswith('0x') else int(text)
                                for b_idx, btn in bit_btns:
                                    btn.blockSignals(True)
                                    should_check = bool((v >> b_idx) & 1)
                                    if btn.isChecked() != should_check:
                                        btn.setChecked(should_check)
                                        if should_check:
                                            btn.setStyleSheet("background-color: #4CAF50; color: white; border: none; font-size: 10px; font-weight: bold;")
                                        else:
                                            btn.setStyleSheet("background-color: #E0E0E0; color: #888888; border: none; font-size: 10px;")
                                    btn.blockSignals(False)
                            except:
                                pass
                        
                        le_data.textChanged.connect(on_text_changed)
                    else:
                        sb_len = NoScrollSpinBox()
                        sb_len.setValue(int(current_params.get('len', 1)))
                        param_layout.addWidget(create_label("Len:"))
                        param_layout.addWidget(sb_len)
                        widgets['len'] = sb_len
                    
                    param_layout.addStretch()

                elif type_text.startswith('spi'):
                    # SPI: cmd, [data/len]
                    le_cmd = QLineEdit(str(current_params.get('cmd', '')))
                    le_cmd.setPlaceholderText("0x00")
                    le_cmd.setFixedWidth(60)
                    param_layout.addWidget(create_label("Cmd:"))
                    param_layout.addWidget(le_cmd)
                    widgets['cmd'] = le_cmd

                    if 'write' in type_text:
                        # Data field
                        val_str = str(current_params.get('data', '0'))
                        try:
                            val_int = int(val_str, 16) if val_str.strip().lower().startswith('0x') else int(val_str)
                        except:
                            val_int = 0
                        
                        le_data = QLineEdit(f"0x{val_int:02X}")
                        le_data.setPlaceholderText("0x00")
                        le_data.setFixedWidth(60)
                        param_layout.addWidget(create_label("Data:"))
                        param_layout.addWidget(le_data)
                        widgets['data'] = le_data

                        # Bit Editor
                        bit_container = QWidget()
                        bit_layout = QHBoxLayout(bit_container)
                        bit_layout.setContentsMargins(5, 0, 0, 0)
                        bit_layout.setSpacing(1)
                        
                        bit_btns = [] 

                        def on_bit_toggled():
                            new_val = 0
                            for b_idx, btn in bit_btns:
                                if btn.isChecked():
                                    new_val |= (1 << b_idx)
                            le_data.setText(f"0x{new_val:02X}")

                        for i in range(7, -1, -1):
                            btn = QPushButton(str(i))
                            btn.setCheckable(True)
                            btn.setFixedSize(20, 20)
                            def update_style(b=btn):
                                if b.isChecked():
                                    b.setStyleSheet("background-color: #4CAF50; color: white; border: none; font-size: 10px; font-weight: bold;")
                                else:
                                    b.setStyleSheet("background-color: #E0E0E0; color: #888888; border: none; font-size: 10px;")
                            
                            is_set = (val_int >> i) & 1
                            btn.setChecked(bool(is_set))
                            update_style(btn)
                            
                            btn.toggled.connect(lambda checked, b=btn: update_style(b))
                            btn.toggled.connect(on_bit_toggled)
                            
                            bit_layout.addWidget(btn)
                            bit_btns.append((i, btn))
                        
                        bit_layout.addStretch()
                        param_layout.addWidget(bit_container)

                        def on_text_changed(text):
                            try:
                                v = int(text, 16) if text.strip().lower().startswith('0x') else int(text)
                                for b_idx, btn in bit_btns:
                                    btn.blockSignals(True)
                                    should_check = bool((v >> b_idx) & 1)
                                    if btn.isChecked() != should_check:
                                        btn.setChecked(should_check)
                                        if should_check:
                                            btn.setStyleSheet("background-color: #4CAF50; color: white; border: none; font-size: 10px; font-weight: bold;")
                                        else:
                                            btn.setStyleSheet("background-color: #E0E0E0; color: #888888; border: none; font-size: 10px;")
                                    btn.blockSignals(False)
                            except:
                                pass
                        
                        le_data.textChanged.connect(on_text_changed)
                    else:
                        sb_len = NoScrollSpinBox()
                        sb_len.setValue(int(current_params.get('len', 1)))
                        param_layout.addWidget(create_label("Len:"))
                        param_layout.addWidget(sb_len)
                        widgets['len'] = sb_len
                    
                    param_layout.addStretch()

            cb_type.currentTextChanged.connect(update_params_ui)
            update_params_ui(cb_type.currentText())

            btn_remove = QPushButton("X")
            btn_remove.setFixedWidth(30)
            btn_remove.setStyleSheet("color: red;")
            
            row_layout.addWidget(cb_type)
            row_layout.addWidget(param_container)
            row_layout.addStretch()
            row_layout.addWidget(btn_remove)
            
            layout_prereq_rows.addWidget(row_widget)
            
            # Function to get params dict
            def get_params_dict():
                res = {}
                for k, w in widgets.items():
                    val = None
                    if isinstance(w, QComboBox):
                        val = w.currentText()
                        # Try to convert int if possible (for level)
                        try:
                            val = int(val)
                        except ValueError:
                            pass
                    elif isinstance(w, QSpinBox):
                        val = w.value()
                    elif isinstance(w, QLineEdit):
                        val = w.text().strip()
                        # Try to convert hex/int
                        if val:
                            try:
                                if val.lower().startswith('0x'):
                                    val = int(val, 16)
                                else:
                                    val = int(val)
                            except ValueError:
                                pass # Keep as string if not int
                    
                    if val is not None and val != "":
                        res[k] = val
                return res

            entry = {'widget': row_widget, 'type': cb_type, 'get_params': get_params_dict}
            entries_list.append(entry)
            
            def remove_row():
                layout_prereq_rows.removeWidget(row_widget)
                row_widget.deleteLater()
                if entry in entries_list:
                    entries_list.remove(entry)
            
            btn_remove.clicked.connect(remove_row)

        # Load existing
        existing_prereqs = data.get('prerequisites', [])
        for p in existing_prereqs:
            # Handle both legacy 'params' string/dict and new flat structure
            params = p.get('params')
            if params is None:
                # If no 'params' key, assume flat structure (copy p and remove 'type')
                params = p.copy()
                if 'type' in params:
                    del params['type']
            
            add_prereq_row(p.get('type'), params)
            
        # Add button
        btn_add_prereq = QPushButton(self.tr("➕ 添加前置条件"))
        btn_add_prereq.setMinimumHeight(28)
        btn_add_prereq.setStyleSheet("text-align: left; padding-left: 10px;")
        btn_add_prereq.clicked.connect(lambda: add_prereq_row())
        layout_prereq.addWidget(btn_add_prereq)
        
        return grp_prereq

    def _add_touch_editor(self, parent_layout, touch_data, editor_list):
        widget = QGroupBox()
        layout = QVBoxLayout(widget)
        
        grid = QGridLayout()
        
        # Bus Type
        cb_bus_type = NoScrollComboBox()
        cb_bus_type.addItems(['i2c', 'spi'])
        bus_type_val = str(touch_data.get('bus_type', 'i2c'))
        cb_bus_type.setCurrentText(bus_type_val)
        grid.addWidget(QLabel(self.tr("总线类型:")), 0, 0)
        grid.addWidget(cb_bus_type, 0, 1)

        # Driver
        le_driver = QLineEdit(str(touch_data.get('driver', '')))
        grid.addWidget(QLabel(self.tr("驱动:")), 0, 2)
        grid.addWidget(le_driver, 0, 3)
        
        # Addr
        lbl_addr = QLabel(self.tr("地址:"))
        le_addr = QLineEdit(self._int_to_hex_str(touch_data.get('addr')))
        le_addr.setPlaceholderText("0x14")
        grid.addWidget(lbl_addr, 1, 0)
        grid.addWidget(le_addr, 1, 1)
        
        # Width/Height (Optional for touch but good to have)
        sb_width = NoScrollSpinBox()
        sb_width.setRange(0, 9999)
        sb_width.setValue(int(touch_data.get('width', 0)))
        grid.addWidget(QLabel(self.tr("宽度:")), 1, 2)
        grid.addWidget(sb_width, 1, 3)
        
        sb_height = NoScrollSpinBox()
        sb_height.setRange(0, 9999)
        sb_height.setValue(int(touch_data.get('height', 0)))
        grid.addWidget(QLabel(self.tr("高度:")), 2, 0)
        grid.addWidget(sb_height, 2, 1)

        sb_freq = NoScrollSpinBox()
        sb_freq.setRange(0, 10000000)
        sb_freq.setSingleStep(10000)
        sb_freq.setValue(int(touch_data.get('freq', 0)))
        grid.addWidget(QLabel(self.tr("频率:")), 2, 2)
        grid.addWidget(sb_freq, 2, 3)
        
        layout.addLayout(grid)
        
        # Pins
        grp_pins = QGroupBox(self.tr("引脚"))
        layout_pins = QGridLayout(grp_pins)
        
        pins_data = touch_data.get('pins', {})
        
        def get_pin_val(k):
            v = pins_data.get(k)
            return "" if v is None else str(v)
        
        # Common pins
        le_int = QLineEdit(get_pin_val('int'))
        le_rst = QLineEdit(get_pin_val('rst'))
        
        # I2C pins
        le_sda = QLineEdit(get_pin_val('sda'))
        le_scl = QLineEdit(get_pin_val('scl'))
        
        # SPI pins
        le_cs = QLineEdit(get_pin_val('cs'))
        le_mosi = QLineEdit(get_pin_val('mosi'))
        le_miso = QLineEdit(get_pin_val('miso'))
        le_sclk = QLineEdit(get_pin_val('sclk'))

        # Labels
        lbl_sda = QLabel("SDA:")
        lbl_scl = QLabel("SCL:")
        lbl_cs = QLabel("CS:")
        lbl_mosi = QLabel("MOSI:")
        lbl_miso = QLabel("MISO:")
        lbl_sclk = QLabel("SCLK:")
        lbl_int = QLabel("INT:")
        lbl_rst = QLabel("RST:")

        # Add all to layout
        # Row 0
        # Row 0 I2C
        layout_pins.addWidget(lbl_sda, 0, 0)
        layout_pins.addWidget(le_sda, 0, 1)
        layout_pins.addWidget(lbl_scl, 0, 2)
        layout_pins.addWidget(le_scl, 0, 3)
        
        # Row 1 SPI (part 1)
        layout_pins.addWidget(lbl_cs, 1, 0)
        layout_pins.addWidget(le_cs, 1, 1)
        layout_pins.addWidget(lbl_mosi, 1, 2)
        layout_pins.addWidget(le_mosi, 1, 3)
        
        # Row 2 SPI (part 2)
        layout_pins.addWidget(lbl_miso, 2, 0)
        layout_pins.addWidget(le_miso, 2, 1)
        layout_pins.addWidget(lbl_sclk, 2, 2)
        layout_pins.addWidget(le_sclk, 2, 3)
        
        # Row 3 (Common)
        layout_pins.addWidget(lbl_int, 3, 0)
        layout_pins.addWidget(le_int, 3, 1)
        layout_pins.addWidget(lbl_rst, 3, 2)
        layout_pins.addWidget(le_rst, 3, 3)

        layout.addWidget(grp_pins)
        
        def update_visibility(bus_type):
            is_i2c = (bus_type == 'i2c')
            
            # I2C specific
            lbl_sda.setVisible(is_i2c)
            le_sda.setVisible(is_i2c)
            lbl_scl.setVisible(is_i2c)
            le_scl.setVisible(is_i2c)
            lbl_addr.setVisible(is_i2c)
            le_addr.setVisible(is_i2c)
            
            # SPI specific
            lbl_cs.setVisible(not is_i2c)
            le_cs.setVisible(not is_i2c)
            lbl_mosi.setVisible(not is_i2c)
            le_mosi.setVisible(not is_i2c)
            lbl_miso.setVisible(not is_i2c)
            le_miso.setVisible(not is_i2c)
            lbl_sclk.setVisible(not is_i2c)
            le_sclk.setVisible(not is_i2c)

        cb_bus_type.currentTextChanged.connect(update_visibility)
        update_visibility(bus_type_val)

        # Prerequisites
        prereq_entries = []
        grp_prereq = self._create_prerequisites_widget(touch_data, prereq_entries)
        layout.addWidget(grp_prereq)
        
        # Delete
        btn_del = QPushButton(self.tr("删除此触摸"))
        btn_del.setStyleSheet("background-color: #FFCDD2; color: #B71C1C;")
        layout.addWidget(btn_del)
        
        parent_layout.addWidget(widget)
        
        editor_dict = {
            'widget': widget,
            'bus_type': cb_bus_type,
            'driver': le_driver,
            'addr': le_addr,
            'width': sb_width,
            'height': sb_height,
            'freq': sb_freq,
            'pin_sda': le_sda,
            'pin_scl': le_scl,
            'pin_cs': le_cs,
            'pin_mosi': le_mosi,
            'pin_miso': le_miso,
            'pin_sclk': le_sclk,
            'pin_int': le_int,
            'pin_rst': le_rst,
            'prereq_entries': prereq_entries
        }
        editor_list.append(editor_dict)
        
        btn_del.clicked.connect(lambda: self._delete_editor_from_list(widget, editor_dict, editor_list))

    def _add_display_editor(self, display_data):
        self._add_display_editor_to_layout(self.layout_display_items, display_data, self.display_editors)

    def _int_to_hex_str(self, val):
        if val is None: return ""
        if isinstance(val, int): return f"0x{val:X}"
        return str(val)

    def _parse_int_or_hex(self, val_str):
        val_str = val_str.strip()
        if not val_str: return None
        try:
            if val_str.lower().startswith('0x'):
                return int(val_str, 16)
            return int(val_str)
        except ValueError:
            return None

    def _delete_editor_from_list(self, widget, editor_dict, editor_list):
        widget.deleteLater()
        if editor_dict in editor_list:
            editor_list.remove(editor_dict)

    def _add_pin_row(self, pin_data):
        row = self.table_pins.rowCount()
        self.table_pins.insertRow(row)
        
        # GPIO
        sb_gpio = NoScrollSpinBox()
        sb_gpio.setRange(0, 999)
        gpio_val = pin_data.get('gpio', None)
        if gpio_val is not None and int(gpio_val) != -1:
            sb_gpio.setValue(int(gpio_val))
        original_gpio = int(gpio_val) if gpio_val is not None and int(gpio_val) != -1 else sb_gpio.value()
        self.table_pins.setCellWidget(row, 0, sb_gpio)
        self._register_change_highlight(sb_gpio, sb_gpio.valueChanged, sb_gpio.value, original_gpio)
        
        # Mode
        combo_mode = NoScrollComboBox()
        combo_mode.addItems(['input', 'input_pullup', 'input_pulldown'])
        original_mode = pin_data.get('mode', 'input')
        combo_mode.setCurrentText(original_mode)
        self.table_pins.setCellWidget(row, 1, combo_mode)
        self._register_change_highlight(combo_mode, combo_mode.currentTextChanged, combo_mode.currentText, original_mode)
        
        # Expect
        combo_expect = NoScrollComboBox()
        combo_expect.addItems(['LOW', 'HIGH'])
        expect_val = int(pin_data.get('expect', 0))
        combo_expect.setCurrentIndex(expect_val) # 0=LOW, 1=HIGH
        self.table_pins.setCellWidget(row, 2, combo_expect)
        self._register_change_highlight(combo_expect, combo_expect.currentIndexChanged, combo_expect.currentIndex, expect_val)

        # Adjust table height after adding row
        self._adjust_table_height(self.table_pins)

    def _delete_selected_pin(self):
        current_row = self.table_pins.currentRow()
        if current_row >= 0:
            self.table_pins.removeRow(current_row)
            self._adjust_table_height(self.table_pins) # Adjust height after deletion

    def _import_pins_from_json(self):
        """Import pins from SelfCheck JSON data"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QComboBox, QPushButton, QMessageBox
        
        # Create custom dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("批量导入引脚"))
        dialog.setMinimumSize(500, 400)
        layout = QVBoxLayout(dialog)
        
        # Instruction label
        label = QLabel(self.tr("请粘贴 SelfCheck JSON 数据 (GPIO):"))
        layout.addWidget(label)
        
        # Text input area
        text_edit = QTextEdit()
        text_edit.setPlaceholderText('{"chip_model":"...","pins":[...]}')
        layout.addWidget(text_edit)
        
        # Bottom row with filter and buttons
        bottom_layout = QHBoxLayout()
        
        # Level filter dropdown (left side)
        filter_label = QLabel(self.tr("GPIO 电平过滤:"))
        combo_filter = QComboBox()
        combo_filter.addItems([self.tr("全部电平"), self.tr("仅高电平"), self.tr("仅低电平")])
        bottom_layout.addWidget(filter_label)
        bottom_layout.addWidget(combo_filter)
        bottom_layout.addStretch()
        
        # Buttons (right side)
        btn_cancel = QPushButton(self.tr("取消"))
        btn_ok = QPushButton(self.tr("导入"))
        btn_ok.setDefault(True)
        bottom_layout.addWidget(btn_cancel)
        bottom_layout.addWidget(btn_ok)
        
        layout.addLayout(bottom_layout)
        
        # Connect buttons
        btn_cancel.clicked.connect(dialog.reject)
        btn_ok.clicked.connect(dialog.accept)
        
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
            
        text = text_edit.toPlainText()
        level_filter = combo_filter.currentIndex()  # 0=all, 1=high only, 2=low only
        
        if not text.strip():
            return
            
        try:
            import json
            data = json.loads(text.strip())
            
            # Check for GPIO data
            if 'pins' in data:
                self._import_pins_from_data(data, level_filter)
                return
                
            QMessageBox.warning(self, self.tr("导入失败"), self.tr("未识别的 JSON 格式 (未找到 'pins' 字段)"))
            
        except json.JSONDecodeError:
            QMessageBox.warning(self, self.tr("导入失败"), self.tr("无效的 JSON 格式"))
        except Exception as e:
            QMessageBox.warning(self, self.tr("导入失败"), str(e))

    def _import_i2c_from_json(self):
        """Import I2C devices from SelfCheck JSON data"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton, QMessageBox
        
        # Create custom dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("批量导入 I2C"))
        dialog.setMinimumSize(500, 400)
        layout = QVBoxLayout(dialog)
        
        # Instruction label
        label = QLabel(self.tr("请粘贴 SelfCheck JSON 数据 (I2C):"))
        layout.addWidget(label)
        
        # Text input area
        text_edit = QTextEdit()
        text_edit.setPlaceholderText('{"type":"I2C","devices":[...]}')
        layout.addWidget(text_edit)
        
        # Bottom row with buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        
        # Buttons (right side)
        btn_cancel = QPushButton(self.tr("取消"))
        btn_ok = QPushButton(self.tr("导入"))
        btn_ok.setDefault(True)
        bottom_layout.addWidget(btn_cancel)
        bottom_layout.addWidget(btn_ok)
        
        layout.addLayout(bottom_layout)
        
        # Connect buttons
        btn_cancel.clicked.connect(dialog.reject)
        btn_ok.clicked.connect(dialog.accept)
        
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
            
        text = text_edit.toPlainText()
        
        if not text.strip():
            return
            
        try:
            import json
            data = json.loads(text.strip())
            
            # Check for I2C data
            if 'type' in data and data['type'] == 'I2C' and 'devices' in data:
                self._import_i2c_from_data(data)
                return
                
            QMessageBox.warning(self, self.tr("导入失败"), self.tr("未识别的 JSON 格式 (未找到 I2C 数据)"))
            
        except json.JSONDecodeError:
            QMessageBox.warning(self, self.tr("导入失败"), self.tr("无效的 JSON 格式"))
        except Exception as e:
            QMessageBox.warning(self, self.tr("导入失败"), str(e))

    def _import_pins_from_data(self, data, level_filter):
        from PyQt6.QtWidgets import QMessageBox
        pins = data['pins']
        if not isinstance(pins, list):
            QMessageBox.warning(self, self.tr("导入失败"), self.tr("'pins' 字段必须是数组"))
            return
        
        # Filter pins by level
        if level_filter == 1:  # High only
            pins = [p for p in pins if p.get('level', 0) == 1]
        elif level_filter == 2:  # Low only
            pins = [p for p in pins if p.get('level', 0) == 0]
        
        if len(pins) == 0:
            QMessageBox.warning(self, self.tr("导入失败"), self.tr("没有符合过滤条件的引脚"))
            return
        
        # Ask user whether to replace or append
        reply = QMessageBox.question(
            self,
            self.tr("导入模式"),
            self.tr("是否清空现有引脚后导入？\n\n是 = 替换现有引脚\n否 = 追加到现有引脚"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )
        
        if reply == QMessageBox.StandardButton.Cancel:
            return
            
        if reply == QMessageBox.StandardButton.Yes:
            # Clear existing pins
            self.table_pins.setRowCount(0)
        
        # Import pins
        imported_count = 0
        for pin in pins:
            if 'gpio' in pin and 'level' in pin:
                pin_data = {
                    'gpio': pin['gpio'],
                    'mode': 'input', # Default to input
                    'expect': pin['level']
                }
                self._add_pin_row(pin_data)
                imported_count += 1
        
        self._adjust_table_height(self.table_pins)
        
        chip_info = data.get('chip_model', 'Unknown')
        psram_info = "板型具备 PSRAM" if data.get('psram_enabled', False) else "板型不具备 PSRAM"
        filter_info = ["全部电平", "仅高电平", "仅低电平"][level_filter]
        QMessageBox.information(
            self,
            self.tr("导入成功"),
            self.tr(f"已导入 {imported_count} 个引脚 ({filter_info})\n芯片: {chip_info}\n{psram_info}")
        )

    def _import_i2c_from_data(self, data):
        from PyQt6.QtWidgets import QMessageBox
        devices = data.get('devices', [])
        sda = data.get('sda', -1)
        scl = data.get('scl', -1)
        freq = data.get('freq', 400000)
        
        if not devices:
            QMessageBox.warning(self, self.tr("导入失败"), self.tr("未找到 I2C 设备"))
            return

        # Ask user whether to replace or append
        reply = QMessageBox.question(
            self,
            self.tr("导入模式"),
            self.tr("是否清空现有 I2C 总线配置后导入？\n\n是 = 替换现有配置\n否 = 追加到现有配置"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )
        
        if reply == QMessageBox.StandardButton.Cancel:
            return
            
        if not hasattr(self, 'i2c_editors') or not hasattr(self, 'layout_i2c_items'):
             QMessageBox.warning(self, self.tr("导入失败"), self.tr("找不到 i2c_editors 编辑器列表或布局"))
             return

        if reply == QMessageBox.StandardButton.Yes:
            # Clear existing
            while self.i2c_editors:
                editor = self.i2c_editors.pop()
                widget = editor['widget']
                widget.setParent(None)
                widget.deleteLater()
        
        # Create a new I2C bus entry
        detect_list = []
        for addr in devices:
            detect_list.append({
                'addr': addr,
                'name': f'Unknown_0x{addr:02X}'
            })
            
        i2c_data = {
            'sda': sda,
            'scl': scl,
            'freq': freq,
            'port': 0, # Default port
            'detect': detect_list,
            'detect_count': len(detect_list)
        }
        
        self._add_i2c_bus_editor(i2c_data)

        QMessageBox.information(self, self.tr("导入成功"), self.tr(f"成功导入 I2C 总线，包含 {len(detect_list)} 个设备"))

    def _add_i2c_bus_editor(self, i2c_data):
        widget = QGroupBox()
        layout = QFormLayout(widget)
        
        # Port, SDA, SCL, Freq
        sb_port = NoScrollSpinBox()
        port_val = int(i2c_data.get('port', 0))
        sb_port.setValue(port_val)
        layout.addRow(self.tr("端口:"), sb_port)
        self._register_change_highlight(sb_port, sb_port.valueChanged, sb_port.value, port_val)
        
        sb_sda = NoScrollSpinBox()
        sb_sda.setRange(-1, 999)
        sda_val = int(i2c_data.get('sda', -1))
        sb_sda.setValue(sda_val)
        layout.addRow(self.tr("SDA:"), sb_sda)
        self._register_change_highlight(sb_sda, sb_sda.valueChanged, sb_sda.value, sda_val)
        
        sb_scl = NoScrollSpinBox()
        sb_scl.setRange(-1, 999)
        scl_val = int(i2c_data.get('scl', -1))
        sb_scl.setValue(scl_val)
        layout.addRow(self.tr("SCL:"), sb_scl)
        self._register_change_highlight(sb_scl, sb_scl.valueChanged, sb_scl.value, scl_val)
        
        sb_freq = NoScrollSpinBox()
        sb_freq.setRange(0, 1000000)
        sb_freq.setSingleStep(10000)
        freq_val = int(i2c_data.get('freq', 400000))
        sb_freq.setValue(freq_val)
        layout.addRow(self.tr("频率:"), sb_freq)
        self._register_change_highlight(sb_freq, sb_freq.valueChanged, sb_freq.value, freq_val)
        
        # Internal Pullup checkbox
        cb_internal_pullup = QCheckBox(self.tr("使用内部上拉 (无外部上拉时启用)"))
        internal_pullup_val = bool(i2c_data.get('internal_pullup', False))
        cb_internal_pullup.setChecked(internal_pullup_val)
        cb_internal_pullup.setToolTip(self.tr("当 I2C 总线没有外部上拉电阻时，启用 ESP32 内部上拉电阻。\n注意：内部上拉较弱，仅适用于短距离低速通信。"))
        layout.addRow(cb_internal_pullup)
        self._register_change_highlight(cb_internal_pullup, cb_internal_pullup.stateChanged, cb_internal_pullup.isChecked, internal_pullup_val)
        
        # Detect Count
        sb_detect_count = NoScrollSpinBox()
        sb_detect_count.setRange(-1, 999)
        sb_detect_count.setSpecialValueText(self.tr("全部"))
        detect_count_val = i2c_data.get('detect_count', -1)
        if detect_count_val is None: detect_count_val = -1
        # Default to total detect count when -1
        detects = i2c_data.get('detect', [])
        default_count = len(detects) if detect_count_val == -1 else int(detect_count_val)
        sb_detect_count.setValue(default_count)
        layout.addRow(self.tr("至少检测数量:"), sb_detect_count)
        self._register_change_highlight(sb_detect_count, sb_detect_count.valueChanged, sb_detect_count.value, default_count)

        # Detect Table
        lbl_detect = QLabel(self.tr("检测设备:"))
        layout.addRow(lbl_detect)
        
        table_detect = QTableWidget()
        table_detect.setColumnCount(2)
        table_detect.setHorizontalHeaderLabels([
            self.tr("名称"),
            self.tr("地址 (十六进制)")
        ])
        table_detect.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table_detect.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        table_detect.setRowCount(0)
        for d in detects:
            self._add_detect_row(table_detect, d)
            
        self._adjust_table_height(table_detect)
        layout.addRow(table_detect)
        
        # Detect Actions
        btn_add_detect = QPushButton(self.tr("➕ 添加设备"))
        btn_add_detect.clicked.connect(lambda: self._add_detect_row(table_detect, {}))
        
        btn_del_detect = QPushButton(self.tr("➖ 删除设备"))
        btn_del_detect.clicked.connect(lambda: self._delete_detect_row(table_detect))
        
        hbox_detect = QHBoxLayout()
        hbox_detect.addWidget(btn_add_detect)
        hbox_detect.addWidget(btn_del_detect)
        layout.addRow(hbox_detect)
        
        # Prerequisites
        prereq_entries = []
        grp_prereq = self._create_prerequisites_widget(i2c_data, prereq_entries)
        layout.addRow(grp_prereq)

        # Delete Bus Button
        btn_del_bus = QPushButton(self.tr("删除此总线"))
        btn_del_bus.setStyleSheet("background-color: #FFCDD2; color: #B71C1C;")
        
        # We need to pass the widget and the editor dict to delete function
        # But editor_dict is not created yet.
        # We can use a closure or just pass the widget and find it in the list.
        
        self.layout_i2c_items.addWidget(widget)
        
        editor_dict = {
            'widget': widget,
            'port': sb_port,
            'sda': sb_sda,
            'scl': sb_scl,
            'freq': sb_freq,
            'internal_pullup': cb_internal_pullup,
            'detect_count': sb_detect_count,
            'table_detect': table_detect,
            'prereq_entries': prereq_entries
        }
        self.i2c_editors.append(editor_dict)
        
        btn_del_bus.clicked.connect(lambda: self._delete_i2c_bus_editor(widget, editor_dict))
        layout.addRow(btn_del_bus)

    def _delete_i2c_bus_editor(self, widget, editor_dict):
        widget.deleteLater()
        if editor_dict in self.i2c_editors:
            self.i2c_editors.remove(editor_dict)

    def _add_detect_row(self, table, detect_data):
        row = table.rowCount()
        table.insertRow(row)
        
        # Name
        original_name = detect_data.get('name', '') or ''
        le_name = QLineEdit(original_name)
        table.setCellWidget(row, 0, le_name)
        self._register_change_highlight(le_name, le_name.textChanged, le_name.text, original_name)
        
        # Address
        le_addr = QLineEdit()
        addr = detect_data.get('addr', 0)
        original_addr = f"0x{addr:02X}" if isinstance(addr, int) else str(addr)
        le_addr.setText(original_addr)
        table.setCellWidget(row, 1, le_addr)
        self._register_change_highlight(le_addr, le_addr.textChanged, le_addr.text, original_addr)
        
        self._adjust_table_height(table)

    def _delete_detect_row(self, table):
        current_row = table.currentRow()
        if current_row >= 0:
            table.removeRow(current_row)
            self._adjust_table_height(table)

    def _create_yaml_editor_group(self, title, data_list):
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        
        # Convert data to YAML string
        if data_list:
            yaml_str = yaml.dump(data_list, sort_keys=False, allow_unicode=True)
        else:
            yaml_str = "[]"
        
        editor = QTextEdit()
        editor.setPlainText(yaml_str)
        editor.setFont(QFont("Consolas", 10))
        editor.setFixedHeight(150) # Limit height
        
        layout.addWidget(editor)
        self._register_change_highlight(editor, editor.textChanged, lambda e=editor: e.toPlainText(), yaml_str)
        return group, editor

    def _collect_data_from_ui(self):
        """Collect data from current UI editors"""
        new_data = {}
        
        # Basic Info
        if hasattr(self, 'edit_name'): new_data['name'] = self.edit_name.text()
        if hasattr(self, 'edit_desc'): new_data['description'] = self.edit_desc.text()
        if hasattr(self, 'edit_sku'): new_data['sku'] = self.edit_sku.text()
        if hasattr(self, 'edit_eol'): new_data['eol'] = self.edit_eol.currentText()
        if hasattr(self, 'edit_image'): new_data['image'] = self.edit_image.text()
        if hasattr(self, 'edit_docs'): new_data['docs'] = self.edit_docs.text()
        if hasattr(self, 'edit_mcu'): new_data['mcu'] = self.edit_mcu.currentText().upper()
        if hasattr(self, 'edit_psram'): new_data['psram_enabled'] = self.edit_psram.isChecked()

        # Check Pins
        if hasattr(self, 'table_pins'):
            new_pins = {}
            pin_count = self.sb_pin_count.value()
            if pin_count != -1:
                new_data['check_pins_count'] = pin_count
            
            for row in range(self.table_pins.rowCount()):
                sb_gpio = self.table_pins.cellWidget(row, 0)
                if sb_gpio:
                    try:
                        gpio = sb_gpio.value()
                        mode = self.table_pins.cellWidget(row, 1).currentText()
                        expect_idx = self.table_pins.cellWidget(row, 2).currentIndex()
                        new_pins[gpio] = {'mode': mode, 'expect': expect_idx}
                    except ValueError:
                        continue
            new_data['check_pins'] = new_pins

        # I2C Internal
        if hasattr(self, 'i2c_editors'):
            new_i2c_list = []
            for editor in self.i2c_editors:
                bus_data = {
                    'port': editor['port'].value(),
                    'sda': editor['sda'].value(),
                    'scl': editor['scl'].value(),
                    'freq': editor['freq'].value(),
                    'detect': []
                }
                table = editor['table_detect']
                for row in range(table.rowCount()):
                    name = table.cellWidget(row, 0).text()
                    addr_str = table.cellWidget(row, 1).text().strip()
                    if addr_str:
                        try:
                            addr = int(addr_str, 16) if addr_str.lower().startswith('0x') else int(addr_str)
                            bus_data['detect'].append({'name': name, 'addr': addr})
                        except ValueError:
                            pass
                
                if editor['detect_count'].value() != -1:
                    bus_data['detect_count'] = editor['detect_count'].value()
                if editor['internal_pullup'].isChecked():
                    bus_data['internal_pullup'] = True
                
                # Prerequisites
                prereq_list = []
                for pre in editor.get('prereq_entries', []):
                    p_type = pre['type'].currentText()
                    p_params = pre['get_params']()
                    if p_type or p_params:
                        entry = {'type': p_type}
                        if isinstance(p_params, dict):
                            entry.update(p_params)
                        else:
                            entry['params'] = p_params
                        prereq_list.append(entry)
                if prereq_list:
                    bus_data['prerequisites'] = prereq_list

                new_i2c_list.append(bus_data)
            new_data['i2c_internal'] = new_i2c_list

        # Display
        if hasattr(self, 'display_editors'):
            new_displays = []
            for editor in self.display_editors:
                d_data = {}
                d_data['bus_type'] = editor['bus_type'].currentText()
                d_data['driver'] = editor['driver'].text()
                d_data['width'] = editor['width'].value()
                d_data['height'] = editor['height'].value()
                d_data['freq'] = editor['freq'].value()
                
                if d_data['bus_type'] == 'i2c':
                    addr = self._parse_int_or_hex(editor['i2c_addr'].text())
                    if addr is not None: d_data['addr'] = addr

                pins = {}
                table = editor['tables'].get(d_data['bus_type'])
                if table:
                    for row in range(table.rowCount()):
                        pin_name = table.item(row, 0).text()
                        pin_val_str = table.cellWidget(row, 1).text().strip()
                        if pin_val_str:
                            try:
                                pins[pin_name] = int(pin_val_str)
                            except ValueError:
                                pins[pin_name] = pin_val_str
                d_data['pins'] = pins
                
                identify = {}
                cmd = self._parse_int_or_hex(editor['id_cmd'].text())
                if cmd is not None: identify['cmd'] = cmd
                expect = self._parse_int_or_hex(editor['id_expect'].text())
                if expect is not None: identify['expect'] = expect
                mask = self._parse_int_or_hex(editor['id_mask'].text())
                if mask is not None: identify['mask'] = mask
                if editor['id_rst'].isChecked(): identify['rst_before'] = True
                wait = editor['id_wait'].value()
                if wait > 0: identify['rst_wait'] = wait
                if identify: d_data['identify'] = identify
                
                # Prerequisites
                prereq_list = []
                for pre in editor.get('prereq_entries', []):
                    p_type = pre['type'].currentText()
                    p_params = pre['get_params']()
                    if p_type or p_params:
                        entry = {'type': p_type}
                        if isinstance(p_params, dict):
                            entry.update(p_params)
                        else:
                            entry['params'] = p_params
                        prereq_list.append(entry)
                if prereq_list:
                    d_data['prerequisites'] = prereq_list

                new_displays.append(d_data)
            new_data['display'] = new_displays

        # Touch - GUI
        if hasattr(self, 'touch_editors'):
            new_touch = []
            for t_editor in self.touch_editors:
                t_data = {}
                t_data['bus_type'] = t_editor['bus_type'].currentText()
                t_data['driver'] = t_editor['driver'].text()
                
                if t_data['bus_type'] == 'i2c':
                    addr_val = self._parse_int_or_hex(t_editor['addr'].text())
                    t_data['addr'] = addr_val if addr_val is not None else 0
                
                t_data['width'] = t_editor['width'].value()
                t_data['height'] = t_editor['height'].value()
                t_data['freq'] = t_editor['freq'].value()
                
                pins = {}
                def get_val(k): return t_editor[f'pin_{k}'].text().strip()
                
                pin_keys = ['int', 'rst']
                if t_data['bus_type'] == 'i2c':
                    pin_keys.extend(['sda', 'scl'])
                else:
                    pin_keys.extend(['cs', 'mosi', 'miso', 'sclk'])
                
                for k in pin_keys:
                    val = get_val(k)
                    if val:
                        parsed = self._parse_int_or_hex(val)
                        pins[k] = parsed if parsed is not None else val
                
                t_data['pins'] = pins

                # Prerequisites
                prereq_list = []
                for pre in t_editor.get('prereq_entries', []):
                    p_type = pre['type'].currentText()
                    p_params = pre['get_params']()
                    if p_type or p_params:
                        entry = {'type': p_type}
                        if isinstance(p_params, dict):
                            entry.update(p_params)
                        else:
                            entry['params'] = p_params
                        prereq_list.append(entry)
                if prereq_list:
                    t_data['prerequisites'] = prereq_list
                new_touch.append(t_data)
            new_data['touch'] = new_touch
        elif hasattr(self, 'edit_touch'): # Fallback
            try:
                new_data['touch'] = yaml.safe_load(self.edit_touch.toPlainText()) or []
            except Exception as e:
                raise ValueError(f"Touch YAML Error: {e}")

        # Additional Tests (Step 6)
        if hasattr(self, 'additional_test_editors'):
            new_tests = []
            for editor in self.additional_test_editors:
                t_data = {}
                type_idx = editor['type'].currentIndex()
                score = editor['score'].value()
                if score != 0: t_data['score'] = score
                
                widgets = editor['widgets']
                if type_idx == 0: # GPIO
                    t_data['type'] = 'gpio'
                    t_data['pin_a'] = widgets['gpio_pin'][1].value()
                    t_data['pin_b'] = widgets['gpio_mode'][1].currentIndex()
                    t_data['expect'] = widgets['gpio_expect'][1].value()
                elif type_idx == 1: # I2C
                    t_data['type'] = 'i2c'
                    t_data['port'] = widgets['i2c_port'][1].value()
                    t_data['pin_a'] = widgets['i2c_sda'][1].value()
                    t_data['pin_b'] = widgets['i2c_scl'][1].value()
                    t_data['freq'] = widgets['i2c_freq'][1].value()
                    t_data['addr'] = self._parse_int_or_hex(widgets['i2c_addr'][1].text()) or 0
                    t_data['reg'] = self._parse_int_or_hex(widgets['i2c_reg'][1].text()) or 0
                    t_data['mask'] = self._parse_int_or_hex(widgets['i2c_mask'][1].text()) or 0
                    t_data['expect'] = self._parse_int_or_hex(widgets['i2c_expect'][1].text()) or 0
                elif type_idx == 2: # SPI
                    t_data['type'] = 'spi'
                    t_data['pin_a'] = widgets['spi_mosi'][1].value()
                    t_data['pin_b'] = widgets['spi_miso'][1].value()
                    t_data['pin_c'] = widgets['spi_sclk'][1].value()
                    t_data['pin_d'] = widgets['spi_cs'][1].value()
                    t_data['reg'] = self._parse_int_or_hex(widgets['spi_cmd'][1].text()) or 0
                    t_data['mask'] = self._parse_int_or_hex(widgets['spi_mask'][1].text()) or 0
                    t_data['expect'] = self._parse_int_or_hex(widgets['spi_expect'][1].text()) or 0
                
                new_tests.append(t_data)
            new_data['additional_tests'] = new_tests

        return new_data

    def _populate_ui_from_data(self, device_data, base_data=None, variant_data=None):
        self._clear_layout(self.inner_detail_layout)
        self.form_layout = self.inner_detail_layout

        is_variant_view = isinstance(variant_data, dict)
        override_keys = set(variant_data.keys()) if is_variant_view else set()

        def field_is_overridden(key):
            if not is_variant_view or key == 'name':
                return False
            if key not in override_keys:
                return False
            if not self._is_effective_variant_override(variant_data.get(key)):
                return False
            return self._normalize_struct(variant_data.get(key)) != self._normalize_struct((base_data or {}).get(key))

        def apply_variant_override_style(widget, key):
            if is_variant_view and (key == 'name' or field_is_overridden(key)):
                widget.setStyleSheet(self.VARIANT_OVERRIDE_STYLE)

        def apply_variant_group_style(group_widget, keys):
            if not is_variant_view:
                return
            if any(field_is_overridden(key) for key in keys):
                group_widget.setStyleSheet("QGroupBox { color: #4A6B8F; }")
        
        # 1. Basic Info
        group_basic = QGroupBox(self.tr("基本信息"))
        form_basic = QFormLayout(group_basic)
        
        name_val = str((variant_data or {}).get('name') if is_variant_view else device_data.get('name') or '')
        desc_val = str(device_data.get('description') or '')
        sku_val = str(device_data.get('sku') or '')
        eol_val = str(device_data.get('eol') or '')
        image_val = str(device_data.get('image') or '')
        docs_val = str(device_data.get('docs') or '')
        
        # MCU: First check device-level, then fallback to category-level
        mcu_val = str(device_data.get('mcu') or '')
        if not mcu_val and hasattr(self, 'current_edit_data') and self.current_edit_data:
            mcu_idx = self.current_edit_data.get('mcu_index')
            if mcu_idx is not None and self.current_yaml_data:
                categories = self.current_yaml_data.get('mcu_categories', [])
                if 0 <= mcu_idx < len(categories):
                    mcu_val = str(categories[mcu_idx].get('mcu') or '')

        self.edit_name = QLineEdit(name_val)
        self.edit_desc = QLineEdit(desc_val)
        self.edit_sku = QLineEdit(sku_val)
        self.edit_eol = NoScrollComboBox()
        self.edit_eol.addItems(["", "EOL", "SALE"])
        self.edit_eol.setCurrentText(eol_val)
        self.edit_image = QLineEdit(image_val)
        self.edit_docs = QLineEdit(docs_val)
        
        self.edit_mcu = NoScrollComboBox()
        mcu_list = ["ESP32", "ESP32-S3", "ESP32-C3", "ESP32-C6", "ESP32-H2", "ESP32-S2", "ESP32-C2", "ESP32-P4"]
        self.edit_mcu.addItems(mcu_list)
        self.edit_mcu.setEditable(True) # Allow custom MCU if not in list
        self.edit_mcu.setCurrentText(mcu_val.upper() if mcu_val else '')
        
        self.edit_psram = QCheckBox(self.tr("板型具备 PSRAM"))
        psram_val = bool(device_data.get('psram_enabled', False))
        self.edit_psram.setChecked(psram_val)
        self.edit_psram.setToolTip(self.tr("当该板型硬件具备 PSRAM 时选中此项；这不是运行时是否启用的状态。"))

        if is_variant_view:
            generated_name = self._compose_variant_display_name((base_data or {}).get('name'), name_val)
            board_name_label = QLabel(generated_name)
            board_name_label.setStyleSheet("color: #24476B;")
            variant_hint = QLabel(self.tr("当前查看的是变体配置。未覆写的字段继承主设备；浅蓝色字段表示该变体已覆写。"))
            variant_hint.setWordWrap(True)
            variant_hint.setStyleSheet("color: #5F7285;")
            form_basic.addRow(self.tr("板名:"), board_name_label)
        
        form_basic.addRow(self.tr("名称:"), self.edit_name)
        form_basic.addRow(self.tr("描述:"), self.edit_desc)
        form_basic.addRow("SKU:", self.edit_sku)
        form_basic.addRow(self.tr("EOL 状态:"), self.edit_eol)
        form_basic.addRow(self.tr("图片链接:"), self.edit_image)
        form_basic.addRow(self.tr("文档链接:"), self.edit_docs)
        form_basic.addRow("MCU:", self.edit_mcu)
        form_basic.addRow("PSRAM:", self.edit_psram)

        apply_variant_override_style(self.edit_desc, 'description')
        apply_variant_override_style(self.edit_sku, 'sku')
        apply_variant_override_style(self.edit_eol, 'eol')
        apply_variant_override_style(self.edit_image, 'image')
        apply_variant_override_style(self.edit_docs, 'docs')
        apply_variant_override_style(self.edit_mcu, 'mcu')
        apply_variant_override_style(self.edit_psram, 'psram_enabled')

        if is_variant_view:
            form_basic.addRow(self.tr("说明:"), variant_hint)
        
        self.form_layout.addWidget(group_basic)
        
        # 2. Check Pins
        group_pins = QGroupBox(self.tr("Step 2: IOMAP - 检测引脚"))
        layout_pins = QVBoxLayout(group_pins)
        
        layout_pin_count = QHBoxLayout()
        lbl_pin_count = QLabel(self.tr("至少通过数量 (默认全部):"))
        self.sb_pin_count = NoScrollSpinBox()
        self.sb_pin_count.setRange(-1, 999)
        self.sb_pin_count.setSpecialValueText(self.tr("全部"))
        pin_count_val = device_data.get('check_pins_count', -1)
        if pin_count_val is None: pin_count_val = -1
        self.sb_pin_count.setValue(int(pin_count_val))
        layout_pin_count.addWidget(lbl_pin_count)
        layout_pin_count.addWidget(self.sb_pin_count)
        layout_pin_count.addStretch()
        layout_pins.addLayout(layout_pin_count)

        self.table_pins = QTableWidget()
        self.table_pins.setColumnCount(3)
        self.table_pins.setHorizontalHeaderLabels([self.tr("GPIO"), self.tr("模式"), self.tr("期望值")])
        self.table_pins.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_pins.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        check_pins = device_data.get('check_pins', {})
        pin_list = []
        if isinstance(check_pins, list):
            for p in check_pins:
                if isinstance(p, dict): pin_list.append(p)
        elif isinstance(check_pins, dict):
            for k, v in check_pins.items():
                if isinstance(v, dict):
                    v['gpio'] = k
                    pin_list.append(v)
        
        self.table_pins.setRowCount(0)
        for p in pin_list:
            self._add_pin_row(p)
        self._adjust_table_height(self.table_pins)
        layout_pins.addWidget(self.table_pins)
        
        layout_pin_actions = QHBoxLayout()
        btn_add_pin = QPushButton(self.tr("➕ 添加引脚"))
        btn_add_pin.clicked.connect(lambda: self._add_pin_row({}))
        btn_del_pin = QPushButton(self.tr("➖ 删除引脚"))
        btn_del_pin.clicked.connect(self._delete_selected_pin)
        btn_import_pins = QPushButton(self.tr("📥 批量导入"))
        btn_import_pins.clicked.connect(self._import_pins_from_json)
        
        layout_pin_actions.addWidget(btn_add_pin)
        layout_pin_actions.addWidget(btn_del_pin)
        layout_pin_actions.addWidget(btn_import_pins)
        layout_pin_actions.addStretch()
        layout_pins.addLayout(layout_pin_actions)
        apply_variant_group_style(group_pins, ['check_pins', 'check_pins_count'])
        self.form_layout.addWidget(group_pins)

        # Step 3: I2C Internal
        group_i2c = QGroupBox(self.tr("Step 3: I2C Internal - 内部 I2C"))
        layout_main_i2c = QVBoxLayout(group_i2c)
        self.layout_i2c_items = QVBoxLayout()
        layout_main_i2c.addLayout(self.layout_i2c_items)
        
        self.i2c_editors = []
        i2c_list = device_data.get('i2c_internal', [])
        if not isinstance(i2c_list, list): i2c_list = []
        for i2c in i2c_list:
            self._add_i2c_bus_editor(i2c)
            
        layout_i2c_actions = QHBoxLayout()
        btn_add_i2c = QPushButton(self.tr("➕ 添加 I2C 总线"))
        btn_add_i2c.clicked.connect(lambda: self._add_i2c_bus_editor({}))
        
        btn_import_i2c = QPushButton(self.tr("📥 批量导入 I2C"))
        btn_import_i2c.clicked.connect(self._import_i2c_from_json)
        
        layout_i2c_actions.addWidget(btn_add_i2c)
        layout_i2c_actions.addWidget(btn_import_i2c)
        layout_i2c_actions.addStretch()
        
        layout_main_i2c.addLayout(layout_i2c_actions)
        apply_variant_group_style(group_i2c, ['i2c_internal'])
        self.form_layout.addWidget(group_i2c)

        # Step 4: Additional Tests
        group_add_tests = QGroupBox(self.tr("Step 4: Additional Tests - 额外测试"))
        layout_main_add_tests = QVBoxLayout(group_add_tests)
        self.layout_test_items = QVBoxLayout()
        layout_main_add_tests.addLayout(self.layout_test_items)
        
        self.additional_test_editors = []
        additional_tests = device_data.get('additional_tests', [])
        if not isinstance(additional_tests, list): additional_tests = []
        for test in additional_tests:
            self._add_additional_test_editor(test)
            
        btn_add_test = QPushButton(self.tr("➕ 添加测试"))
        btn_add_test.clicked.connect(lambda: self._add_additional_test_editor({}))
        layout_main_add_tests.addWidget(btn_add_test)
        apply_variant_group_style(group_add_tests, ['additional_tests'])
        self.form_layout.addWidget(group_add_tests)

        # Step 5: Touch (GUI)
        group_touch = QGroupBox(self.tr("Step 5: 触摸"))
        layout_main_touch = QVBoxLayout(group_touch)
        self.layout_touch_items = QVBoxLayout()
        layout_main_touch.addLayout(self.layout_touch_items)
        
        self.touch_editors = []
        touches = device_data.get('touch', [])
        if not isinstance(touches, list): touches = []
        for t in touches:
            self._add_touch_editor(self.layout_touch_items, t, self.touch_editors)
            
        btn_add_touch = QPushButton(self.tr("➕ 添加触摸"))
        btn_add_touch.clicked.connect(lambda: self._add_touch_editor(self.layout_touch_items, {}, self.touch_editors))
        layout_main_touch.addWidget(btn_add_touch)
        apply_variant_group_style(group_touch, ['touch'])
        self.form_layout.addWidget(group_touch)

        # Step 6: Display
        group_disp = QGroupBox(self.tr("Step 6: 显示屏"))
        layout_main_disp = QVBoxLayout(group_disp)
        self.layout_display_items = QVBoxLayout()
        layout_main_disp.addLayout(self.layout_display_items)
        
        self.display_editors = []
        displays = device_data.get('display', [])
        if not isinstance(displays, list): displays = []
        for disp in displays:
            self._add_display_editor(disp)
            
        btn_add_disp = QPushButton(self.tr("➕ 添加显示屏"))
        btn_add_disp.clicked.connect(lambda: self._add_display_editor({}))
        layout_main_disp.addWidget(btn_add_disp)
        apply_variant_group_style(group_disp, ['display'])
        self.form_layout.addWidget(group_disp)

        # Add spacing
        self.form_layout.addSpacing(120)

    def save_device_details(self, silent=False):
        if not hasattr(self, 'current_edit_data'): return False
        
        try:
            new_data = self._collect_data_from_ui()
        except ValueError as e:
            if not silent:
                QMessageBox.warning(self, self.tr("验证错误"), str(e))
            return False
            
        # Update memory
        if self.current_config_index is None:
            # Main Device
            variants = self.device_data.get('variants', [])
            self.device_data.update(new_data)
            self.device_data['variants'] = variants
        else:
            variants = self.device_data.get('variants', [])
            if self.current_config_index < len(variants):
                base_view = copy.deepcopy(self.device_data)
                base_view.pop('variants', None)
                variant_name = new_data.get('name', variants[self.current_config_index].get('name', ''))
                variants[self.current_config_index] = self._extract_variant_override_data(base_view, new_data, variant_name)
                self.device_data['variants'] = variants
            
        # Handle MCU Change (Move device to another category if needed)
        need_tree_refresh = False
        mcu_idx = self.current_edit_data['mcu_index']
        dev_idx = self.current_edit_data['device_index']
        
        if self.current_config_index is None:
            old_category = self.current_yaml_data['mcu_categories'][mcu_idx]
            old_mcu_name = old_category.get('mcu', '')
            new_mcu_name = self.device_data.get('mcu', '')
            
            if new_mcu_name and new_mcu_name != old_mcu_name:
                # 1. Remove from old category
                if dev_idx < len(old_category['devices']):
                    del old_category['devices'][dev_idx]
                
                # 2. Find or create new category
                new_mcu_idx = -1
                for i, cat in enumerate(self.current_yaml_data['mcu_categories']):
                    if cat.get('mcu') == new_mcu_name:
                        new_mcu_idx = i
                        break
                
                if new_mcu_idx == -1:
                    new_category = {'mcu': new_mcu_name, 'devices': []}
                    self.current_yaml_data['mcu_categories'].append(new_category)
                    new_mcu_idx = len(self.current_yaml_data['mcu_categories']) - 1
                
                # 3. Add to new category
                self.current_yaml_data['mcu_categories'][new_mcu_idx]['devices'].append(self.device_data)
                new_dev_idx = len(self.current_yaml_data['mcu_categories'][new_mcu_idx]['devices']) - 1
                
                # 4. Update indices
                self.current_edit_data['mcu_index'] = new_mcu_idx
                self.current_edit_data['device_index'] = new_dev_idx
                
                need_tree_refresh = True
            else:
                self.current_yaml_data['mcu_categories'][mcu_idx]['devices'][dev_idx] = self.device_data
        else:
            self.current_yaml_data['mcu_categories'][mcu_idx]['devices'][dev_idx] = self.device_data

        if self.current_config_index is None:
            compare_data = copy.deepcopy(self.device_data)
        else:
            variants = self.device_data.get('variants', [])
            current_variant = variants[self.current_config_index] if self.current_config_index < len(variants) else {}
            compare_data = self._merge_variant_view_data(self.device_data, current_variant)
            compare_data['name'] = str(current_variant.get('name') or '')
        
        if not silent:
            if not self._confirm_device_changes(self.current_device_original, compare_data):
                return False
        
        # Update original snapshot
        self.current_device_original = copy.deepcopy(compare_data)
        
        # Write to file
        try:
            with open(YAML_FILE, 'w', encoding='utf-8') as f:
                yaml.dump(self.current_yaml_data, f, allow_unicode=True, sort_keys=False)
            # Keep editor text in sync so生成按钮不会读到旧内容
            try:
                self.editor.setPlainText(yaml.dump(self.current_yaml_data, allow_unicode=True, sort_keys=False))
            except Exception:
                pass
            
            if need_tree_refresh:
                self.populate_tree()
                self.populate_dashboard()
            
            if not silent:
                self.statusBar().showMessage(self.tr("已保存"))
                QMessageBox.information(self, self.tr("成功"), self.tr("已保存到 YAML 文件"))
            return True
        except Exception as e:
            if not silent:
                QMessageBox.critical(self, self.tr("错误"), self.tr("保存失败: {error}").format(error=e))
            return False
        if not hasattr(self, 'current_edit_data') or not self.current_edit_data:
            return False

        # Gather data from widgets
        # We reconstruct the dictionary to maintain a nice field order in YAML
        new_data = {}
        old_data = self.current_device_original or copy.deepcopy(self.current_edit_data.get('data', {}))
        
        new_data['name'] = self.edit_name.text()
        new_data['description'] = self.edit_desc.text()
        new_data['sku'] = self.edit_sku.text()
        new_data['eol'] = self.edit_eol.currentText()
        new_data['image'] = self.edit_image.text()
        new_data['docs'] = self.edit_docs.text()
        
        # Preserve any other fields that are not edited by this form
        if self.current_edit_data.get('data'):
            for k, v in self.current_edit_data['data'].items():
                known_keys = ['name', 'description', 'sku', 'eol', 'image', 'docs', 
                              'check_pins', 'check_pins_count', 'i2c_internal', 'identify_i2c', 'display', 'touch', 'additional_tests']
                if k not in known_keys:
                    new_data[k] = v
        
        # Pins
        new_pins = {}
        
        # Pin Count
        pin_count = self.sb_pin_count.value()
        if pin_count != -1:
            new_data['check_pins_count'] = pin_count
        elif 'check_pins_count' in new_data:
            del new_data['check_pins_count']

        for row in range(self.table_pins.rowCount()):
            sb_gpio = self.table_pins.cellWidget(row, 0)
            if sb_gpio:
                try:
                    gpio = sb_gpio.value()
                    mode = self.table_pins.cellWidget(row, 1).currentText()
                    expect_idx = self.table_pins.cellWidget(row, 2).currentIndex() # 0=LOW, 1=HIGH
                    new_pins[gpio] = {'mode': mode, 'expect': expect_idx}
                except ValueError:
                    continue
        new_data['check_pins'] = new_pins
        
        # I2C
        new_i2c_list = []
        for i, editor in enumerate(self.i2c_editors):
            try:
                port = editor['port'].value()
                sda = editor['sda'].value()
                scl = editor['scl'].value()
                freq = editor['freq'].value()
                detect_count = editor['detect_count'].value()
                
                detects = []
                table = editor['table_detect']
                for row in range(table.rowCount()):
                    name_widget = table.cellWidget(row, 0)
                    addr_widget = table.cellWidget(row, 1)
                    
                    if not name_widget or not addr_widget:
                        continue
                        
                    name = name_widget.text()
                    addr_str = addr_widget.text().strip()
                    
                    if not addr_str:
                        continue
                    
                    try:
                        if addr_str.lower().startswith('0x'):
                            addr = int(addr_str, 16)
                        else:
                            addr = int(addr_str)
                    except ValueError:
                        QMessageBox.warning(
                            self,
                            self.tr("验证错误"),
                            self.tr("I2C 总线 {bus} 第 {row} 行地址格式无效: '{addr}'").format(
                                bus=i + 1,
                                row=row + 1,
                                addr=addr_str
                            )
                        )
                        return False
                        
                    detects.append({'name': name, 'addr': addr})
                
                internal_pullup = editor['internal_pullup'].isChecked()
                
                bus_data = {
                    'port': port,
                    'sda': sda,
                    'scl': scl,
                    'freq': freq,
                    'detect': detects
                }
                if detect_count != -1:
                    bus_data['detect_count'] = detect_count
                if internal_pullup:
                    bus_data['internal_pullup'] = True
                
                new_i2c_list.append(bus_data)
            except ValueError as e:
                QMessageBox.warning(
                    self,
                    self.tr("验证错误"),
                    self.tr("I2C 总线 {bus} 的值无效: {error}").format(bus=i + 1, error=e)
                )
                return False
                
        new_data['i2c_internal'] = new_i2c_list

        # Identify I2C (Base)
        new_identify_i2c = []
        for id_editor in getattr(self, 'identify_i2c_editors', []):
            addr_val = self._parse_int_or_hex(id_editor['addr'].text())
            if addr_val is None:
                addr_val = 0
            new_identify_i2c.append({
                'port': id_editor['port'].value(),
                'sda': id_editor['sda'].value(),
                'scl': id_editor['scl'].value(),
                'freq': id_editor['freq'].value(),
                'addr': addr_val
            })
        new_data['identify_i2c'] = new_identify_i2c
        
        # Variants
        new_variants = []
        if hasattr(self, 'variant_editors'):
            for editor in self.variant_editors:
                try:
                    v_name = editor['name'].text()
                    
                    # Identify I2C
                    v_id_i2c = []
                    for id_editor in editor['identify_i2c_editors']:
                        v_id_i2c.append({
                            'port': id_editor['port'].value(),
                            'sda': id_editor['sda'].value(),
                            'scl': id_editor['scl'].value(),
                            'freq': id_editor['freq'].value(),
                            'addr': self._parse_int_or_hex(id_editor['addr'].text()) or 0
                        })
                    
                    # Display
                    v_disp = []
                    for d_editor in editor['display_editors']:
                        d_data = {}
                        d_data['driver'] = d_editor['driver'].text()
                        d_data['width'] = d_editor['width'].value()
                        d_data['height'] = d_editor['height'].value()
                        d_data['freq'] = d_editor['freq'].value()
                        
                        # Pins
                        pins = {}
                        table = d_editor['table_pins']
                        for row in range(table.rowCount()):
                            pin_name = table.item(row, 0).text()
                            pin_val_str = table.cellWidget(row, 1).text().strip()
                            if pin_val_str:
                                try:
                                    pins[pin_name] = int(pin_val_str)
                                except ValueError:
                                    pins[pin_name] = pin_val_str
                        
                        # Identify
                        identify = {}
                        cmd = self._parse_int_or_hex(d_editor['id_cmd'].text())
                        if cmd is not None: identify['cmd'] = cmd
                        
                        expect = self._parse_int_or_hex(d_editor['id_expect'].text())
                        if expect is not None: identify['expect'] = expect
                        
                        mask = self._parse_int_or_hex(d_editor['id_mask'].text())
                        if mask is not None: identify['mask'] = mask
                        
                        if d_editor['id_rst'].isChecked():
                            identify['rst_before'] = True
                            
                        wait = d_editor['id_wait'].value()
                        if wait > 0:
                            identify['rst_wait'] = wait
                            
                        if identify:
                            d_data['identify'] = identify
                            
                        v_disp.append(d_data)
                    
                    # Touch
                    v_touch = []
                    for t_editor in editor['touch_editors']:
                        t_data = {}
                        t_data['bus_type'] = t_editor['bus_type'].currentText()
                        t_data['driver'] = t_editor['driver'].text()
                        
                        if t_data['bus_type'] == 'i2c':
                            addr_val = self._parse_int_or_hex(t_editor['addr'].text())
                            t_data['addr'] = addr_val if addr_val is not None else 0
                        
                        t_data['width'] = t_editor['width'].value()
                        t_data['height'] = t_editor['height'].value()
                        t_data['freq'] = t_editor['freq'].value()
                        
                        pins = {}
                        def get_val(k): return t_editor[f'pin_{k}'].text().strip()
                        
                        pin_keys = ['int', 'rst']
                        if t_data['bus_type'] == 'i2c':
                            pin_keys.extend(['sda', 'scl'])
                        else:
                            pin_keys.extend(['cs', 'mosi', 'miso', 'sclk'])
                        
                        for k in pin_keys:
                            val = get_val(k)
                            if val:
                                parsed = self._parse_int_or_hex(val)
                                pins[k] = parsed if parsed is not None else val
                        
                        t_data['pins'] = pins

                        prereq_list = []
                        for pre in t_editor.get('prereq_entries', []):
                            p_type = pre['type'].currentText()
                            p_params = pre['params'].text().strip()
                            if p_type or p_params:
                                prereq_list.append({'type': p_type, 'params': p_params})
                        if prereq_list:
                            t_data['prerequisites'] = prereq_list
                        v_touch.append(t_data)
                    
                    new_variants.append({
                        'name': v_name,
                        'identify_i2c': v_id_i2c,
                        'display': v_disp,
                        'touch': v_touch
                    })
                except Exception as e:
                    QMessageBox.warning(
                        self,
                        self.tr("错误"),
                        self.tr("解析变体配置出错: {error}").format(error=e)
                    )
                    return False
        
        new_data['variants'] = new_variants
        
        # Displays
        new_displays = []
        for editor in self.display_editors:
            try:
                d_data = {}
                d_data['bus_type'] = editor['bus_type'].currentText()
                d_data['driver'] = editor['driver'].text()
                d_data['width'] = editor['width'].value()
                d_data['height'] = editor['height'].value()
                d_data['freq'] = editor['freq'].value()
                
                # I2C specific
                if d_data['bus_type'] == 'i2c':
                    addr = self._parse_int_or_hex(editor['i2c_addr'].text())
                    if addr is not None:
                        d_data['addr'] = addr

                # Pins
                pins = {}
                table = editor['tables'].get(d_data['bus_type'])
                if table:
                    for row in range(table.rowCount()):
                        pin_name = table.item(row, 0).text()
                        pin_val_str = table.cellWidget(row, 1).text().strip()
                        if pin_val_str:
                            # Try to convert to int if possible
                            try:
                                pins[pin_name] = int(pin_val_str)
                            except ValueError:
                                pins[pin_name] = pin_val_str
                d_data['pins'] = pins
                
                # Identify
                identify = {}
                cmd = self._parse_int_or_hex(editor['id_cmd'].text())
                if cmd is not None: identify['cmd'] = cmd
                
                expect = self._parse_int_or_hex(editor['id_expect'].text())
                if expect is not None: identify['expect'] = expect
                
                mask = self._parse_int_or_hex(editor['id_mask'].text())
                if mask is not None: identify['mask'] = mask
                
                if editor['id_rst'].isChecked():
                    identify['rst_before'] = True
                    
                wait = editor['id_wait'].value()
                if wait > 0:
                    identify['rst_wait'] = wait
                    
                if identify:
                    d_data['identify'] = identify
                    
                new_displays.append(d_data)
            except Exception as e:
                QMessageBox.warning(
                    self,
                    self.tr("错误"),
                    self.tr("保存显示屏配置出错: {error}").format(error=e),
                )
                return False

        new_data['display'] = new_displays

        # Touch
        try:
            touch_data = yaml.safe_load(self.edit_touch.toPlainText())
            if touch_data is not None:
                new_data['touch'] = touch_data
            else:
                new_data['touch'] = []
        except Exception as e:
            QMessageBox.warning(
                self,
                self.tr("YAML 错误"),
                self.tr("解析触摸 YAML 出错: {error}").format(error=e),
            )
            return False
        
        if not silent:
            if not self._confirm_device_changes(old_data, new_data):
                return False
        else:
            changes = self._collect_device_changes(old_data, new_data)
            if not changes:
                return True

        # Update in memory
        mcu_idx = self.current_edit_data['mcu_index']
        dev_idx = self.current_edit_data['device_index']
        self.current_yaml_data['mcu_categories'][mcu_idx]['devices'][dev_idx] = new_data
        
        # Update the reference in current_edit_data so next save uses this as base
        self.current_edit_data['data'] = new_data
        self.current_device_original = copy.deepcopy(new_data)
        
        # Preserve header comments from the current editor text
        current_text = self.editor.toPlainText()
        header_lines = []
        for line in current_text.splitlines():
            stripped = line.strip()
            if stripped.startswith('#') or not stripped:
                header_lines.append(line)
            else:
                break
        
        # Remove trailing empty lines from header to avoid accumulation
        while header_lines and not header_lines[-1].strip():
            header_lines.pop()
            
        header_text = "\n".join(header_lines)
        if header_text:
            header_text += "\n"
        
        # Update YAML text
        # Note: This will reformat the YAML and lose comments (except header which we preserved)
        yaml_text = yaml.dump(self.current_yaml_data, sort_keys=False, allow_unicode=True)
        self.editor.setPlainText(header_text + yaml_text)
        
        # Refresh UI
        self.populate_tree()
        self.populate_dashboard()
        
        # Restore selection
        if not silent:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(self.tr("已更新"))
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setText(self.tr("设备详情已更新到 YAML 编辑器。"))
            btn_write = msg_box.addButton(
                self.tr("写入 YAML"), QMessageBox.ButtonRole.AcceptRole
            )
            btn_later = msg_box.addButton(
                self.tr("稍后再写"), QMessageBox.ButtonRole.RejectRole
            )
            msg_box.setDefaultButton(btn_write)
            msg_box.exec()
            
            if msg_box.clickedButton() == btn_write:
                self.save_yaml()
            
        return True
    

    
    def show_pin_details(self, item_data):
        """Show pin configuration details"""
        pin_data = item_data.get('data', {})
        gpio = item_data.get('gpio', pin_data.get('gpio', -1))
        mode = pin_data.get('mode', 'input')
        expect = pin_data.get('expect', 0)
        
        self._set_header_text("引脚配置: GPIO {gpio}", gpio=gpio)
        
        info_template = self.tr("""
    <h2>引脚配置</h2>
    <p><b>GPIO 编号:</b> {gpio}</p>
    <p><b>模式:</b> {mode}</p>
    <p><b>期望值:</b> {expect}</p>
    <hr>
    <h3>模式选项:</h3>
    <ul>
    <li><b>input:</b> 标准输入模式</li>
    <li><b>input_pullup:</b> 带内部上拉电阻的输入</li>
    <li><b>input_pulldown:</b> 带内部下拉电阻的输入</li>
    </ul>
    """)
        info_text = info_template.format(gpio=gpio, mode=mode, expect=expect)

        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setTextFormat(Qt.TextFormat.RichText)
        
        self.clear_detail_layout()
        self.detail_layout.addWidget(info_label)
        self.detail_layout.addStretch()
    
    def _clear_layout(self, layout):
        if layout is None: return
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def clear_detail_layout(self):
        """Clear all widgets from detail layout"""
        # Hide floating button by default
        if isinstance(self.detail_container, FloatingButtonWidget):
            self.detail_container.btn_apply.hide()

        while self.detail_layout.count():
            item = self.detail_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def save_yaml(self):
        # If currently in detail view and editing a device, try to save details first
        if self.stacked_widget.currentWidget() == self.detail_container:
            # Check if we are editing a device
            if hasattr(self, 'current_edit_data') and self.current_edit_data:
                if self.current_edit_data.get('type') in ('device', 'variant'):
                    # Try to save device details silently
                    if not self.save_device_details(silent=True):
                        # If validation failed, stop saving
                        return

        content = self.editor.toPlainText()
        try:
            # Validate YAML and preview changes
            candidate_data = yaml.safe_load(content)
            if candidate_data is None:
                candidate_data = {}
            if not self._confirm_full_yaml_changes(candidate_data):
                return

            self.current_yaml_data = candidate_data
            with open(YAML_FILE, 'w', encoding='utf-8') as f:
                f.write(content)
            self.base_yaml_data = copy.deepcopy(self.current_yaml_data)
            
            self.populate_tree()  # Refresh tree view
            self.populate_dashboard()
            
            # Refresh current device view if we're editing a device to clear highlights
            if hasattr(self, 'current_edit_data') and self.current_edit_data and self.current_edit_data.get('type') in ('device', 'variant'):
                mcu_idx = self.current_edit_data.get('mcu_index')
                dev_idx = self.current_edit_data.get('device_index')
                if mcu_idx is not None and dev_idx is not None:
                    try:
                        updated_device = self.current_yaml_data['mcu_categories'][mcu_idx]['devices'][dev_idx]
                        updated_item_data = {
                            'type': self.current_edit_data.get('type', 'device'),
                            'mcu_index': mcu_idx,
                            'device_index': dev_idx,
                            'variant_index': self.current_edit_data.get('variant_index'),
                            'data': updated_device,
                            'base_data': updated_device,
                        }
                        if updated_item_data['type'] == 'variant':
                            self.show_variant_details(updated_item_data)
                        else:
                            self.show_device_details(updated_item_data)
                    except (KeyError, IndexError):
                        pass
            self.statusBar().showMessage(
                self.tr("已保存: {path}").format(path=YAML_FILE)
            )
            QMessageBox.information(
                self,
                self.tr("成功"),
                self.tr("YAML 配置已成功保存。")
            )
        except yaml.YAMLError as e:
            QMessageBox.critical(
                self,
                self.tr("YAML 错误"),
                self.tr("YAML 格式无效:\n{error}").format(error=str(e))
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                self.tr("错误"),
                self.tr("保存文件失败: {error}").format(error=str(e))
            )

    def generate_device_data_files(self):
        # Prefer in-memory YAML (包含表单修改)，否则回落到编辑器文本
        try:
            if self.current_yaml_data:
                data = self.current_yaml_data
            else:
                content = self.editor.toPlainText()
                data = yaml.safe_load(content)
                if data is None:
                    data = {}
                self.current_yaml_data = data

            success = M5HeaderGenerator.generate_from_data(data, OUTPUT_HEADER_FILE)
            
            if success:
                self.statusBar().showMessage(
                    self.tr("已生成: {header} 和 {source}").format(
                        header=OUTPUT_HEADER_FILE,
                        source=OUTPUT_SOURCE_FILE,
                    )
                )
                QMessageBox.information(
                    self,
                    self.tr("成功"),
                    self.tr("设备数据文件已成功生成到:\n{header}\n{source}").format(
                        header=OUTPUT_HEADER_FILE,
                        source=OUTPUT_SOURCE_FILE,
                    )
                )
            else:
                raise Exception("生成失败")
            
        except yaml.YAMLError as e:
            QMessageBox.critical(
                self,
                self.tr("生成错误"),
                self.tr("YAML 解析失败:\n{error}").format(error=str(e))
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                self.tr("生成错误"),
                self.tr("生成设备数据文件失败:\n{error}").format(error=str(e))
            )

    def _adjust_table_height(self, table_widget=None):
        """Adjust table height based on content"""
        if table_widget is None:
            table_widget = self.table_pins
            
        header_height = table_widget.horizontalHeader().height()
        row_height = table_widget.rowHeight(0) if table_widget.rowCount() > 0 else 30
        # Calculate total height: header + rows + some padding
        total_height = header_height + (row_height * table_widget.rowCount()) + 4
        
        # Set a minimum height (e.g. 100px) and let it grow
        table_widget.setMinimumHeight(max(100, total_height))
        table_widget.setMaximumHeight(max(100, total_height)) # Fix height to content to avoid scrollbar inside table if possible

    def _add_additional_test_editor(self, test_data):
        widget = QGroupBox()
        widget.setStyleSheet("QGroupBox { border: 1px solid #ccc; border-radius: 5px; margin-top: 10px; padding-top: 10px; }")
        layout = QVBoxLayout(widget)
        
        # Top Row: Type, Score, Delete
        top_layout = QHBoxLayout()
        
        combo_type = NoScrollComboBox()
        combo_type.addItems(["GPIO Read (0)", "I2C Read Reg (1)", "SPI Read Cmd (2)"])
        type_val = int(test_data.get('type', 0))
        if 0 <= type_val <= 2:
            combo_type.setCurrentIndex(type_val)
        
        sb_score = NoScrollSpinBox()
        sb_score.setRange(-999, 999)
        sb_score.setValue(int(test_data.get('score', 1)))
        sb_score.setPrefix("Score: ")
        
        btn_del = QPushButton(self.tr("删除"))
        btn_del.setStyleSheet("background-color: #FFCDD2; color: #B71C1C;")
        
        top_layout.addWidget(QLabel(self.tr("类型:")))
        top_layout.addWidget(combo_type)
        top_layout.addWidget(sb_score)
        top_layout.addStretch()
        top_layout.addWidget(btn_del)
        
        layout.addLayout(top_layout)
        
        # Parameters Grid
        grid = QGridLayout()
        layout.addLayout(grid)
        
        # Create all possible widgets
        widgets = {}
        
        def add_param(key, label, row, col, default=0, is_hex=False):
            lbl = QLabel(label)
            if is_hex:
                val = test_data.get(key, default)
                txt = f"0x{val:X}" if isinstance(val, int) else str(val)
                inp = QLineEdit(txt)
            else:
                inp = NoScrollSpinBox()
                inp.setRange(-1, 999999)
                inp.setValue(int(test_data.get(key, default)))
            
            grid.addWidget(lbl, row, col)
            grid.addWidget(inp, row, col+1)
            widgets[key] = (lbl, inp)
            return inp

        # GPIO Params
        # pin_a (GPIO), pin_b (Mode), expect
        add_param('gpio_pin', self.tr("GPIO:"), 0, 0, -1)
        
        lbl_mode = QLabel(self.tr("模式:"))
        combo_mode = NoScrollComboBox()
        combo_mode.addItems(["INPUT (0)", "INPUT_PULLUP (1)", "INPUT_PULLDOWN (2)"])
        mode_val = int(test_data.get('pin_b', 0)) if type_val == 0 else 0
        if 0 <= mode_val <= 2: combo_mode.setCurrentIndex(mode_val)
        grid.addWidget(lbl_mode, 0, 2)
        grid.addWidget(combo_mode, 0, 3)
        widgets['gpio_mode'] = (lbl_mode, combo_mode)
        
        add_param('gpio_expect', self.tr("期望(0/1):"), 0, 4, 0)

        # I2C Params
        # port, pin_a (SDA), pin_b (SCL), freq, addr, reg, mask, expect
        add_param('i2c_port', self.tr("Port:"), 1, 0, 0)
        add_param('i2c_sda', self.tr("SDA:"), 1, 2, -1)
        add_param('i2c_scl', self.tr("SCL:"), 1, 4, -1)
        add_param('i2c_freq', self.tr("Freq:"), 2, 0, 400000)
        add_param('i2c_addr', self.tr("Addr:"), 2, 2, 0, is_hex=True)
        add_param('i2c_reg', self.tr("Reg:"), 2, 4, 0, is_hex=True)
        add_param('i2c_mask', self.tr("Mask:"), 3, 0, 0xFF, is_hex=True)
        add_param('i2c_expect', self.tr("Expect:"), 3, 2, 0, is_hex=True)

        # SPI Params
        # pin_a (MOSI), pin_b (MISO), pin_c (SCLK), pin_d (CS), reg (CMD), mask, expect
        add_param('spi_mosi', self.tr("MOSI:"), 4, 0, -1)
        add_param('spi_miso', self.tr("MISO:"), 4, 2, -1)
        add_param('spi_sclk', self.tr("SCLK:"), 4, 4, -1)
        add_param('spi_cs', self.tr("CS:"), 5, 0, -1)
        add_param('spi_cmd', self.tr("CMD:"), 5, 2, 0, is_hex=True)
        add_param('spi_mask', self.tr("Mask:"), 5, 4, 0xFF, is_hex=True)
        add_param('spi_expect', self.tr("Expect:"), 6, 0, 0, is_hex=True)

        # Update visibility based on type
        def update_visibility():
            t = combo_type.currentIndex()
            
            # Hide all first
            for k, (l, w) in widgets.items():
                l.hide()
                w.hide()
            
            if t == 0: # GPIO
                widgets['gpio_pin'][0].show(); widgets['gpio_pin'][1].show()
                widgets['gpio_mode'][0].show(); widgets['gpio_mode'][1].show()
                widgets['gpio_expect'][0].show(); widgets['gpio_expect'][1].show()
                
                # Restore values if switching back? 
                # For now, we just map them on save.
                
            elif t == 1: # I2C
                widgets['i2c_port'][0].show(); widgets['i2c_port'][1].show()
                widgets['i2c_sda'][0].show(); widgets['i2c_sda'][1].show()
                widgets['i2c_scl'][0].show(); widgets['i2c_scl'][1].show()
                widgets['i2c_freq'][0].show(); widgets['i2c_freq'][1].show()
                widgets['i2c_addr'][0].show(); widgets['i2c_addr'][1].show()
                widgets['i2c_reg'][0].show(); widgets['i2c_reg'][1].show()
                widgets['i2c_mask'][0].show(); widgets['i2c_mask'][1].show()
                widgets['i2c_expect'][0].show(); widgets['i2c_expect'][1].show()
                
            elif t == 2: # SPI
                widgets['spi_mosi'][0].show(); widgets['spi_mosi'][1].show()
                widgets['spi_miso'][0].show(); widgets['spi_miso'][1].show()
                widgets['spi_sclk'][0].show(); widgets['spi_sclk'][1].show()
                widgets['spi_cs'][0].show(); widgets['spi_cs'][1].show()
                widgets['spi_cmd'][0].show(); widgets['spi_cmd'][1].show()
                widgets['spi_mask'][0].show(); widgets['spi_mask'][1].show()
                widgets['spi_expect'][0].show(); widgets['spi_expect'][1].show()

        combo_type.currentIndexChanged.connect(update_visibility)
        update_visibility() # Initial state
        
        self.layout_test_items.addWidget(widget)
        
        editor_dict = {
            'widget': widget,
            'type': combo_type,
            'score': sb_score,
            'widgets': widgets
        }
        self.additional_test_editors.append(editor_dict)
        
        btn_del.clicked.connect(lambda: self._delete_additional_test_editor(widget, editor_dict))

    def _delete_additional_test_editor(self, widget, editor_dict):
        widget.deleteLater()
        if editor_dict in self.additional_test_editors:
            self.additional_test_editors.remove(editor_dict)

    def show_mcu_details(self, item_data):
        """Show MCU category details"""
        mcu_data = item_data.get('data', {})
        mcu_name = mcu_data.get('mcu') or self.tr('Unknown')
        devices = mcu_data.get('devices', [])
        
        self._set_header_text("MCU 类别: {name}", name=mcu_name)
        
        info_template = self.tr("""
    <h2>MCU: {name}</h2>
    <p><b>设备数量:</b> {count}</p>
    <h3>设备列表:</h3>
    <ul>
    {items}
    </ul>
    """)
        items_html = "".join(
            f"<li>{device.get('name') or self.tr('Unknown')}</li>" for device in devices
        )
        info_text = info_template.format(name=mcu_name, count=len(devices), items=items_html)
        
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setTextFormat(Qt.TextFormat.RichText)
        
        # Replace detail widget content
        self.clear_detail_layout()
        self.detail_layout.addWidget(info_label)
        self.detail_layout.addStretch()
    
    def show_device_details(self, item_data):
        """Show device details in an editable form"""
        self._is_rebuilding_detail = True
        self.variant_editors = []
        self.current_edit_data = item_data
        mcu_idx = item_data.get('mcu_index')
        dev_idx = item_data.get('device_index')

        try:
            self.device_data = copy.deepcopy(self.current_yaml_data['mcu_categories'][mcu_idx]['devices'][dev_idx])
        except Exception:
            self.device_data = copy.deepcopy(item_data.get('base_data') or item_data.get('data', {}))

        self.current_config_index = item_data.get('variant_index') if item_data.get('type') == 'variant' else None

        if self.current_config_index is None:
            initial_view_data = copy.deepcopy(self.device_data)
            initial_base_data = None
            initial_variant_data = None
            self.current_device_original = copy.deepcopy(initial_view_data)
        else:
            variants = self.device_data.get('variants', [])
            variant_data = variants[self.current_config_index] if self.current_config_index < len(variants) else {}
            initial_base_data = copy.deepcopy(self.device_data)
            initial_variant_data = copy.deepcopy(variant_data)
            initial_view_data = self._merge_variant_view_data(initial_base_data, initial_variant_data)
            initial_view_data['name'] = str(initial_variant_data.get('name') or '')
            self.current_device_original = copy.deepcopy(initial_view_data)

        # Create Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        main_layout = QVBoxLayout(content_widget)
        
        # Configuration Selector
        layout_selector = QHBoxLayout()
        layout_selector.addWidget(QLabel(self.tr("当前配置:")))
        self.combo_config = NoScrollComboBox()
        self._refresh_config_selector()
        selected_index = 0 if self.current_config_index is None else self.current_config_index + 1
        if 0 <= selected_index < self.combo_config.count():
            self.combo_config.blockSignals(True)
            self.combo_config.setCurrentIndex(selected_index)
            self.combo_config.blockSignals(False)
        self.combo_config.currentIndexChanged.connect(self.switch_config)
        layout_selector.addWidget(self.combo_config)
        
        btn_add_variant = QPushButton(self.tr("➕ 新建变体"))
        btn_add_variant.clicked.connect(self._add_new_variant)
        layout_selector.addWidget(btn_add_variant)
        
        btn_del_variant = QPushButton(self.tr("➖ 删除当前变体"))
        btn_del_variant.clicked.connect(self._delete_current_variant)
        layout_selector.addWidget(btn_del_variant)
        
        layout_selector.addStretch()
        main_layout.addLayout(layout_selector)
        
        # Detail Container
        self.detail_container_widget = QWidget()
        self.inner_detail_layout = QVBoxLayout(self.detail_container_widget)
        self.inner_detail_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.detail_container_widget)
        
        self._populate_ui_from_data(initial_view_data, initial_base_data, initial_variant_data)
        
        # Setup Floating Button
        self._set_floating_button_text("💾 保存修改")
        try:
            self.detail_container.btn_apply.clicked.disconnect()
        except Exception:
            pass
        self.detail_container.btn_apply.clicked.connect(self.save_device_details)
        
        scroll.setWidget(content_widget)
        self.clear_detail_layout()
        self.detail_layout.addWidget(scroll)

        # Ensure floating button is visible and on top after layout settles
        def _ensure_button_visible():
            if hasattr(self.detail_container, 'btn_apply'):
                self.detail_container.btn_apply.show()
                self.detail_container.btn_apply.raise_()
                self.detail_container.btn_apply.update()
            self._is_rebuilding_detail = False

        QTimer.singleShot(0, _ensure_button_visible)

    def show_variant_details(self, item_data):
        self.show_device_details(item_data)

    def switch_config(self, index):
        if getattr(self, '_is_rebuilding_detail', False):
            return

        try:
            current_view_data = self._collect_data_from_ui()
        except (ValueError, RuntimeError):
            current_view_data = {}
        
        if self.current_config_index is None:
            variants = self.device_data.get('variants', [])
            self.device_data.update(current_view_data)
            self.device_data['variants'] = variants
        else:
            variants = self.device_data.get('variants', [])
            if self.current_config_index < len(variants):
                base_view = copy.deepcopy(self.device_data)
                base_view.pop('variants', None)
                variant_name = current_view_data.get('name', variants[self.current_config_index].get('name', ''))
                variants[self.current_config_index] = self._extract_variant_override_data(base_view, current_view_data, variant_name)
                self.device_data['variants'] = variants
        
        item_data = self.combo_config.currentData()
        self.current_config_index = item_data
        
        if self.current_config_index is None:
            data = copy.deepcopy(self.device_data)
            base_data = None
            variant_data = None
        else:
            variants = self.device_data.get('variants', [])
            if self.current_config_index < len(variants):
                variant_data = copy.deepcopy(variants[self.current_config_index])
                base_data = copy.deepcopy(self.device_data)
                data = self._merge_variant_view_data(base_data, variant_data)
                data['name'] = str(variant_data.get('name') or '')
            else:
                data = {}
                base_data = copy.deepcopy(self.device_data)
                variant_data = {}

        self._populate_ui_from_data(data, base_data, variant_data)

    def _add_new_variant(self):
        if getattr(self, '_is_rebuilding_detail', False):
            return
        self.switch_config(self.combo_config.currentIndex())
        
        variants = self.device_data.get('variants', [])
        if not isinstance(variants, list): variants = []
        
        new_variant = {'name': 'New Variant'}
        variants.append(new_variant)
        self.device_data['variants'] = variants

        self._refresh_config_selector()
        self.combo_config.blockSignals(True)
        self.combo_config.setCurrentIndex(self.combo_config.count()-1)
        self.combo_config.blockSignals(False)
        self.current_config_index = len(variants)-1
        self._populate_ui_from_data({'name': 'New Variant'}, self.device_data, new_variant)

    def _delete_current_variant(self):
        if self.current_config_index is None:
            QMessageBox.warning(self, self.tr("警告"), self.tr("不能删除主设备配置"))
            return
            
        reply = QMessageBox.question(self, self.tr("确认"), self.tr("确定要删除当前变体吗？"), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        variants = self.device_data.get('variants', [])
        if self.current_config_index < len(variants):
            del variants[self.current_config_index]
            
        self.device_data['variants'] = variants

        self._refresh_config_selector()
        self.combo_config.blockSignals(True)
        self.combo_config.setCurrentIndex(0)
        self.combo_config.blockSignals(False)
        self.current_config_index = None
        self._populate_ui_from_data(self.device_data)

        

        

        




        # Ensure floating button is visible and on top after layout settles
        def _ensure_button_visible():
            self.detail_container.btn_apply.show()
            self.detail_container.btn_apply.raise_()
            self.detail_container.btn_apply.update()

        QTimer.singleShot(0, _ensure_button_visible)

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        
        # Set light theme palette (white background)
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.ColorRole.Link, QColor(0, 122, 204))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 215))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        app.setPalette(palette)
        
        window = M5BuilderGUI()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()