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

# ── Extracted modules (in src/) ───────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))
from M5Autodetect_Widgets import (
    DeviceItemDelegate, DictTranslator,
    NoScrollSpinBox, NoScrollComboBox, PinValueEditor, FloatingButtonWidget,
)
from M5Autodetect_EditorUtils import (
    parse_int_or_hex as _parse_int_or_hex_fn,
    int_to_hex_str as _int_to_hex_str_fn,
    normalize_struct as _normalize_struct_fn,
    set_combo_items as _set_combo_items_fn,
    register_change_highlight as _register_change_highlight_fn,
    adjust_table_height as _adjust_table_height_fn,
    read_pin_widget_value as _read_pin_widget_value_fn,
    collect_pin_table_values as _collect_pin_table_values_fn,
    delete_editor_from_list as _delete_editor_from_list_fn,
    get_display_probe_options as _get_display_probe_options_fn,
    get_touch_probe_options as _get_touch_probe_options_fn,
    build_probe_hint as _build_probe_hint_fn,
    infer_display_probe as _infer_display_probe_fn,
    infer_touch_probe as _infer_touch_probe_fn,
)
from M5Autodetect_EditorPrereq import PrereqEditorManager
from M5Autodetect_EditorDisplay import DisplayEditorManager
from M5Autodetect_EditorTouch import TouchEditorManager
from M5Autodetect_EditorI2CPin import I2CPinEditorManager
from M5Autodetect_DiffChanges import DiffChangesManager

# Paths
BASE_DIR = os.path.dirname(__file__)
YAML_FILE = os.path.join(BASE_DIR, 'm5stack_dev_config.yaml')
OUTPUT_HEADER_FILE = os.path.join(BASE_DIR, '../src/data/M5Autodetect_DeviceData.h')
OUTPUT_SOURCE_FILE = os.path.join(BASE_DIR, '../src/data/M5Autodetect_DeviceData.cpp')
CACHE_DIR = os.path.join(BASE_DIR, '.cache')
LOCALES_DIR = os.path.join(BASE_DIR, 'locales')

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
        
        # ── Managers (extracted modules) ──
        self._display_mgr = DisplayEditorManager(self)
        self._touch_mgr = TouchEditorManager(self)
        self._i2c_pin_mgr = I2CPinEditorManager(self)
        self._diff_mgr = DiffChangesManager(self)

        # Load initial data
        self.load_yaml()
        print("GUI Initialized successfully")

    def _register_change_highlight(self, widget, signal, getter, original_value):
        _register_change_highlight_fn(widget, signal, getter, original_value)

    def _normalize_struct(self, value):
        return _normalize_struct_fn(value)

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

    def _set_combo_items(self, combo, options, current_value=None):
        _set_combo_items_fn(combo, options, current_value)

    def _get_display_probe_options(self, bus_type):
        return _get_display_probe_options_fn(self.tr, bus_type)

    def _get_touch_probe_options(self, bus_type):
        return _get_touch_probe_options_fn(self.tr, bus_type)

    def _build_probe_hint(self, target, probe_type):
        return _build_probe_hint_fn(self.tr, target, probe_type)

    def _infer_display_probe(self, display_data, bus_type):
        return _infer_display_probe_fn(display_data, bus_type)

    def _infer_touch_probe(self, touch_data, bus_type):
        return _infer_touch_probe_fn(touch_data, bus_type)

    def _read_pin_widget_value(self, widget):
        return _read_pin_widget_value_fn(widget)

    def _collect_pin_table_values(self, table):
        return _collect_pin_table_values_fn(table)

    def _serialize_display_editor(self, editor):
        return self._display_mgr.serialize(editor)

    def _serialize_touch_editor(self, editor):
        return self._touch_mgr.serialize(editor)

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

    # ── Change detection (delegated to DiffChangesManager) ────────
    def _collect_device_changes(self, old_data, new_data):
        return self._diff_mgr.collect_device_changes(old_data, new_data)

    def _check_additional_tests_changes(self, old_data, new_data, change_lines):
        return self._diff_mgr._check_additional_tests_changes(old_data, new_data, change_lines)

    def _check_identify_i2c_changes(self, old_data, new_data, change_lines):
        return self._diff_mgr._check_identify_i2c_changes(old_data, new_data, change_lines)

    def _check_tests_changes(self, old_data, new_data, change_lines):
        return self._diff_mgr._check_tests_changes(old_data, new_data, change_lines)

    def _check_variants_changes(self, old_data, new_data, change_lines):
        return self._diff_mgr._check_variants_changes(old_data, new_data, change_lines)

    def _check_pins_changes(self, old_data, new_data, change_lines):
        return self._diff_mgr._check_pins_changes(old_data, new_data, change_lines)

    def _check_i2c_changes(self, old_data, new_data, change_lines):
        return self._diff_mgr._check_i2c_changes(old_data, new_data, change_lines)

    def _check_display_changes(self, old_data, new_data, change_lines):
        return self._diff_mgr._check_display_changes(old_data, new_data, change_lines)

    def _check_touch_changes(self, old_data, new_data, change_lines):
        return self._diff_mgr._check_touch_changes(old_data, new_data, change_lines)

    def _build_changes_html(self, change_lines):
        return self._diff_mgr.build_changes_html(change_lines)

    def _show_change_dialog(self, title, body_html):
        return self._diff_mgr.show_change_dialog(title, body_html)

    def _collect_all_changes(self, candidate_data=None):
        return self._diff_mgr.collect_all_changes(candidate_data)

    def _build_grouped_changes_html(self, summary):
        return self._diff_mgr.build_grouped_changes_html(summary)

    def _confirm_device_changes(self, old_data, new_data):
        return self._diff_mgr.confirm_device_changes(old_data, new_data)

    def _confirm_full_yaml_changes(self, candidate_data=None):
        return self._diff_mgr.confirm_full_yaml_changes(candidate_data)

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
        self._i2c_pin_mgr.add_identify_i2c_editor(parent_layout, id_i2c_data, editor_list)

    def _add_display_editor_to_layout(self, parent_layout, display_data, editor_list):
        self._display_mgr.add_editor_to_layout(parent_layout, display_data, editor_list)

    def _create_prerequisites_widget(self, data, entries_list):
        return PrereqEditorManager.create_prerequisites_widget(self.tr, data, entries_list)

    def _add_touch_editor(self, parent_layout, touch_data, editor_list):
        self._touch_mgr.add_editor(parent_layout, touch_data, editor_list)

    def _add_display_editor(self, display_data):
        self._add_display_editor_to_layout(self.layout_display_items, display_data, self.display_editors)

    def _int_to_hex_str(self, val):
        return _int_to_hex_str_fn(val)

    def _parse_int_or_hex(self, val_str):
        return _parse_int_or_hex_fn(val_str)

    def _delete_editor_from_list(self, widget, editor_dict, editor_list):
        _delete_editor_from_list_fn(widget, editor_dict, editor_list)

    def _add_pin_row(self, pin_data):
        self._i2c_pin_mgr.add_pin_row(pin_data)

    def _delete_selected_pin(self):
        self._i2c_pin_mgr.delete_selected_pin()

    def _import_pins_from_json(self):
        self._i2c_pin_mgr.import_pins_from_json()

    def _import_i2c_from_json(self):
        self._i2c_pin_mgr.import_i2c_from_json()

    def _import_pins_from_data(self, data, level_filter):
        self._i2c_pin_mgr._import_pins_from_data(data, level_filter)

    def _import_i2c_from_data(self, data):
        self._i2c_pin_mgr._import_i2c_from_data(data)

    def _add_i2c_bus_editor(self, i2c_data):
        self._i2c_pin_mgr.add_i2c_bus_editor(i2c_data)

    def _delete_i2c_bus_editor(self, widget, editor_dict):
        self._i2c_pin_mgr._delete_i2c_bus_editor(widget, editor_dict)

    def _add_detect_row(self, table, detect_data):
        self._i2c_pin_mgr._add_detect_row(table, detect_data)

    def _delete_detect_row(self, table):
        I2CPinEditorManager._delete_detect_row(table)

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
                    # Read required flag from the container widget's QCheckBox
                    required = True
                    container_w = table.cellWidget(row, 2)
                    if container_w is not None:
                        cb = container_w.findChild(QCheckBox)
                        if cb is not None:
                            required = cb.isChecked()
                    if addr_str:
                        try:
                            addr = int(addr_str, 16) if addr_str.lower().startswith('0x') else int(addr_str)
                            entry = {'name': name, 'addr': addr}
                            if not required:  # Only write when false (true is default, keep YAML clean)
                                entry['required'] = False
                            bus_data['detect'].append(entry)
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
                new_displays.append(self._serialize_display_editor(editor))
            new_data['display'] = new_displays

        # Touch - GUI
        if hasattr(self, 'touch_editors'):
            new_touch = []
            for t_editor in self.touch_editors:
                new_touch.append(self._serialize_touch_editor(t_editor))
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
                        v_disp.append(self._serialize_display_editor(d_editor))
                    
                    # Touch
                    v_touch = []
                    for t_editor in editor['touch_editors']:
                        v_touch.append(self._serialize_touch_editor(t_editor))
                    
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
                new_displays.append(self._serialize_display_editor(editor))
            except Exception as e:
                QMessageBox.warning(
                    self,
                    self.tr("错误"),
                    self.tr("保存显示屏配置出错: {error}").format(error=e),
                )
                return False

        new_data['display'] = new_displays

        # Touch
        if hasattr(self, 'touch_editors'):
            try:
                new_data['touch'] = [self._serialize_touch_editor(editor) for editor in self.touch_editors]
            except Exception as e:
                QMessageBox.warning(
                    self,
                    self.tr("错误"),
                    self.tr("保存触摸配置出错: {error}").format(error=e),
                )
                return False
        else:
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
        _adjust_table_height_fn(table_widget if table_widget is not None else self.table_pins)

    def _add_additional_test_editor(self, test_data):
        PrereqEditorManager.add_additional_test_editor(self.tr, self.layout_test_items, test_data, self.additional_test_editors)

    def _delete_additional_test_editor(self, widget, editor_dict):
        PrereqEditorManager.delete_additional_test_editor(widget, editor_dict, self.additional_test_editors)

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