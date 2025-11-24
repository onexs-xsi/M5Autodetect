print("Starting script...")
print(f"__name__ is {__name__}")
import sys
import os
import copy
import html
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
                             QGridLayout, QTabWidget)
from PyQt6.QtGui import QFont, QIcon, QPixmap, QColor, QPainter, QPen, QBrush, QPalette
from PyQt6.QtCore import Qt, QSize, QRect, QTimer
from M5Autodetect_CBuilder_GenCode import M5HeaderGenerator

# Paths
YAML_FILE = os.path.join(os.path.dirname(__file__), 'm5stack_dev_config.yaml')
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '../src/M5Autodetect_Data.h')
CACHE_DIR = os.path.join(os.path.dirname(__file__), '.cache')

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
            painter.drawText(QRect(-30, -15, 60, 30), Qt.AlignmentFlag.AlignCenter, "EOL")
            painter.restore()

    def sizeHint(self, option, index):
        return QSize(140, 160)


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
        self.btn_apply = QPushButton("💾 Apply Changes", self)
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background-color: #2196F3; 
                color: white; 
                font-weight: bold; 
                padding: 12px 24px;
                border-radius: 25px;
                font-size: 14px;
                border: 2px solid #1976D2;
                min-width: 200px;
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
        btn_w = 280
        btn_h = 50
        
        self.btn_apply.setGeometry(
            self.width() - btn_w - margin_right,
            self.height() - btn_h - margin_bottom,
            btn_w, btn_h
        )
        self.btn_apply.raise_()

class M5BuilderGUI(QMainWindow):
    HIGHLIGHT_STYLE = "background-color: #DFF7E0;"
    def __init__(self):
        super().__init__()
        self.setWindowTitle("M5Autodetect CBuilder GUI - byonexs.")
        self.resize(1200, 700)
        
        # Ensure cache directory exists
        os.makedirs(CACHE_DIR, exist_ok=True)
        
        self.current_yaml_data = None
        self.base_yaml_data = None
        self.current_device_original = None
        
        # Central widget with splitter
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout(self.central_widget)
        
        # Create splitter for left navigation and right content
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - Navigation Tree
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabel("MCU 类别与设备")
        self.tree_widget.setMinimumWidth(250)
        self.tree_widget.itemClicked.connect(self.on_tree_item_clicked)
        self.splitter.addWidget(self.tree_widget)
        
        # Right side - Detail view
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Header
        self.header_label = QLabel("设备仪表板")
        self.header_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        right_layout.addWidget(self.header_label)
        
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
        
        # View 3: YAML Editor
        self.editor = QTextEdit()
        self.editor.setFont(QFont("Consolas", 10))
        self.stacked_widget.addWidget(self.editor)
        
        right_layout.addWidget(self.stacked_widget)
        
        # Buttons
        self.button_layout = QHBoxLayout()
        
        self.btn_home = QPushButton("🏠 仪表板")
        self.btn_home.clicked.connect(self.show_dashboard)
        self.button_layout.addWidget(self.btn_home)
        
        self.btn_edit_yaml = QPushButton("📝 编辑 YAML")
        self.btn_edit_yaml.clicked.connect(self.show_yaml_editor)
        self.button_layout.addWidget(self.btn_edit_yaml)
        
        self.btn_load = QPushButton("🔄 重新加载")
        self.btn_load.clicked.connect(self.load_yaml)
        self.button_layout.addWidget(self.btn_load)
        
        self.btn_save = QPushButton("💾 写入 YAML")
        self.btn_save.clicked.connect(self.save_yaml)
        self.button_layout.addWidget(self.btn_save)
        
        self.btn_generate = QPushButton("⚙️ 生成头文件 (.h)")
        self.btn_generate.clicked.connect(self.generate_header_file)
        self.btn_generate.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.button_layout.addWidget(self.btn_generate)
        
        right_layout.addLayout(self.button_layout)
        
        self.splitter.addWidget(right_widget)
        self.splitter.setSizes([300, 900])
        
        main_layout.addWidget(self.splitter)
        
        # Load initial data
        self.load_yaml()

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

    def _collect_device_changes(self, old_data, new_data):
        if not isinstance(old_data, dict):
            old_data = {}
        if not isinstance(new_data, dict):
            new_data = {}
        change_lines = []

        field_labels = {
            'name': '名称',
            'description': '描述',
            'sku': 'SKU',
            'eol': 'EOL 状态',
            'image': '图片链接',
            'docs': '文档链接'
        }

        for key, label in field_labels.items():
            old_val = str(old_data.get(key) or '').strip()
            new_val = str(new_data.get(key) or '').strip()
            if old_val != new_val:
                change_lines.append(f"{label}: {old_val or '[empty]'} → {new_val or '[empty]'}")

        # Check complex fields with detailed diff
        self._check_pins_changes(old_data, new_data, change_lines)
        self._check_i2c_changes(old_data, new_data, change_lines)
        self._check_display_changes(old_data, new_data, change_lines)
        self._check_touch_changes(old_data, new_data, change_lines)
        self._check_identify_i2c_changes(old_data, new_data, change_lines)
        self._check_variants_changes(old_data, new_data, change_lines)

        return change_lines
    
    def _check_identify_i2c_changes(self, old_data, new_data, change_lines):
        old_val = old_data.get('identify_i2c', [])
        new_val = new_data.get('identify_i2c', [])
        if self._normalize_struct(old_val) != self._normalize_struct(new_val):
             change_lines.append("identify_i2c 配置已更新")

    def _check_variants_changes(self, old_data, new_data, change_lines):
        old_val = old_data.get('variants', [])
        new_val = new_data.get('variants', [])
        if self._normalize_struct(old_val) != self._normalize_struct(new_val):
             change_lines.append(f"变体配置已更新: {len(old_val)} → {len(new_val)}")
    
    def _check_pins_changes(self, old_data, new_data, change_lines):
        old_pins = old_data.get('check_pins', {})
        new_pins = new_data.get('check_pins', {})
        
        # Check count
        old_count = old_data.get('check_pins_count')
        new_count = new_data.get('check_pins_count')
        if old_count != new_count:
             change_lines.append(f"检测引脚通过数量: {old_count} → {new_count}")

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
                    change_lines.append(f"检测引脚: GPIO{key}({old_mode}={old_expect}) → GPIO{key}({new_mode}={new_expect})")
            elif old_pin is not None:
                # Removed
                old_mode = old_pin.get('mode', 'input')
                old_expect = old_pin.get('expect', 0)
                change_lines.append(f"检测引脚: GPIO{key}({old_mode}={old_expect}) → [已删除]")
            else:
                # Added
                new_mode = new_pin.get('mode', 'input')
                new_expect = new_pin.get('expect', 0)
                change_lines.append(f"检测引脚: [新增] → GPIO{key}({new_mode}={new_expect})")
    
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
                    changes.append(f"SDA: {old_bus.get('sda')}→{new_bus.get('sda')}")
                if old_bus.get('scl') != new_bus.get('scl'):
                    changes.append(f"SCL: {old_bus.get('scl')}→{new_bus.get('scl')}")
                if old_bus.get('freq') != new_bus.get('freq'):
                    changes.append(f"Freq: {old_bus.get('freq')}→{new_bus.get('freq')}")
                
                if changes:
                    change_lines.append(f"内部 I2C Port{port}: " + ", ".join(changes))
                
                # Check detect count
                old_detect_count = old_bus.get('detect_count')
                new_detect_count = new_bus.get('detect_count')
                if old_detect_count != new_detect_count:
                    change_lines.append(f"内部 I2C Port{port} 检测通过数量: {old_detect_count} → {new_detect_count}")

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
                            change_lines.append(f"内部 I2C Port{port} 设备 {addr_hex}: 名称 '{old_d.get('name')}' → '{new_d.get('name')}'")
                    elif old_d:
                        change_lines.append(f"内部 I2C Port{port} 设备: [删除] {addr_hex} ({old_d.get('name')})")
                    else:
                        change_lines.append(f"内部 I2C Port{port} 设备: [新增] {addr_hex} ({new_d.get('name')})")

            elif old_bus:
                # Bus removed
                change_lines.append(f"内部 I2C Port{port}: [已删除]")
            else:
                # Bus added
                change_lines.append(f"内部 I2C Port{port}: [新增] (SDA:{new_bus.get('sda')} SCL:{new_bus.get('scl')})")
    
    def _check_display_changes(self, old_data, new_data, change_lines):
        old_display = old_data.get('display', [])
        new_display = new_data.get('display', [])
        
        if self._normalize_struct(old_display) != self._normalize_struct(new_display):
            if isinstance(new_display, list) and isinstance(old_display, list):
                change_lines.append(f"显示屏配置项数量: {len(old_display)} → {len(new_display)}")
            else:
                change_lines.append(f"显示屏配置已更新")
    
    def _check_touch_changes(self, old_data, new_data, change_lines):
        old_touch = old_data.get('touch', [])
        new_touch = new_data.get('touch', [])
        
        if self._normalize_struct(old_touch) != self._normalize_struct(new_touch):
            if isinstance(new_touch, list) and isinstance(old_touch, list):
                change_lines.append(f"触摸配置项数量: {len(old_touch)} → {len(new_touch)}")
            else:
                change_lines.append(f"触摸配置已更新")

    def _build_changes_html(self, change_lines):
        if not change_lines:
            return ""
        rows = []
        for line in change_lines:
            rows.append(
                f"<li><span style='background-color:#FFCDD2;padding:4px 8px;border-radius:6px;display:block;margin-bottom:6px;'>{html.escape(line)}</span></li>"
            )
        return "<p>以下字段将被保存：</p><ul>" + "".join(rows) + "</ul>"

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
            mcu_name = current_cat.get('mcu') or 'Unknown MCU'
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
                dev_name = dev_key or 'Unknown Device'
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
    def _confirm_device_changes(self, old_data, new_data):
        change_lines = self._collect_device_changes(old_data, new_data)
        if not change_lines:
            QMessageBox.information(self, "无变更", "当前没有任何修改，无需保存。")
            return False

        body_html = self._build_changes_html(change_lines)
        return self._show_change_dialog("保存前确认", body_html)

    def _confirm_full_yaml_changes(self, candidate_data=None):
        summary = self._collect_all_changes(candidate_data)
        base_snapshot = self.base_yaml_data or {}
        candidate_snapshot = candidate_data or {}
        if not summary and base_snapshot != candidate_snapshot:
            summary = {
                'Overall': {
                    'YAML Config': ['Overall structure changed']
                }
            }
        if not summary:
            QMessageBox.information(self, "无变更", "当前 YAML 没有任何改动。")
            return False

        html_body = self._build_grouped_changes_html(summary)
        return self._show_change_dialog("写入 YAML 前确认", html_body)

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
                self.statusBar().showMessage(f"Loaded {YAML_FILE}")
                self.base_yaml_data = copy.deepcopy(self.current_yaml_data)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载 YAML 失败: {str(e)}")
        else:
            self.editor.setPlainText("# m5stack_dev_config.yaml not found. Create a new one.")
            self.current_yaml_data = None
            self.base_yaml_data = None
            
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
                device_name = device.get('name', 'Unknown Device')
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
                    'mcu_index': category_idx,
                    'device_index': dev_idx,
                    'sku': sku,
                    'eol': eol,
                    'variants': device.get('variants', [])
                })
                self.dashboard_widget.addItem(item)

    def on_dashboard_item_clicked(self, item):
        """Handle dashboard item click"""
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
            
        mcu_idx = data.get('mcu_index')
        dev_idx = data.get('device_index')
        
        # Find corresponding tree item
        # Root -> MCU Item -> Device Item
        if mcu_idx < self.tree_widget.topLevelItemCount():
            mcu_item = self.tree_widget.topLevelItem(mcu_idx)
            if dev_idx < mcu_item.childCount():
                device_item = mcu_item.child(dev_idx)
                self.tree_widget.setCurrentItem(device_item)
                self.on_tree_item_clicked(device_item, 0)

    def show_dashboard(self):
        self.stacked_widget.setCurrentWidget(self.dashboard_widget)
        self.header_label.setText("设备仪表板")
        self.tree_widget.clearSelection()

    def show_yaml_editor(self):
        self.stacked_widget.setCurrentWidget(self.editor)
        self.header_label.setText("YAML 编辑器")
        
    def populate_tree(self):
        """Populate the navigation tree with MCU categories and devices"""
        self.tree_widget.clear()
        
        if not self.current_yaml_data:
            return
        
        mcu_categories = self.current_yaml_data.get('mcu_categories', [])
        
        for category_idx, category in enumerate(mcu_categories):
            mcu_name = category.get('mcu', 'Unknown MCU')
            
            # Create MCU category item
            mcu_item = QTreeWidgetItem(self.tree_widget)
            mcu_item.setText(0, f"📦 {mcu_name}")
            mcu_item.setData(0, Qt.ItemDataRole.UserRole, {
                'type': 'mcu',
                'index': category_idx,
                'data': category
            })
            mcu_item.setExpanded(True)
            
            # Add devices under this MCU
            devices = category.get('devices', [])
            for dev_idx, device in enumerate(devices):
                device_name = device.get('name', 'Unknown Device')
                device_item = QTreeWidgetItem(mcu_item)
                device_item.setText(0, f"🔧 {device_name}")
                device_item.setData(0, Qt.ItemDataRole.UserRole, {
                    'type': 'device',
                    'mcu_index': category_idx,
                    'device_index': dev_idx,
                    'data': device
                })
                
                # Add check pins under device
                check_pins = device.get('check_pins', {})
                
                if isinstance(check_pins, list):
                    for pin_idx, pin in enumerate(check_pins):
                        gpio = pin.get('gpio', -1)
                        mode = pin.get('mode', 'input')
                        expect = pin.get('expect', 0)
                        pin_item = QTreeWidgetItem(device_item)
                        pin_item.setText(0, f"📍 GPIO{gpio} ({mode}={expect})")
                        pin_item.setData(0, Qt.ItemDataRole.UserRole, {
                            'type': 'pin',
                            'mcu_index': category_idx,
                            'device_index': dev_idx,
                            'pin_index': pin_idx,
                            'gpio': gpio,
                            'data': pin
                        })
                elif isinstance(check_pins, dict):
                    for gpio, pin in check_pins.items():
                        mode = pin.get('mode', 'input')
                        expect = pin.get('expect', 0)
                        pin_item = QTreeWidgetItem(device_item)
                        pin_item.setText(0, f"📍 GPIO{gpio} ({mode}={expect})")
                        pin_item.setData(0, Qt.ItemDataRole.UserRole, {
                            'type': 'pin',
                            'mcu_index': category_idx,
                            'device_index': dev_idx,
                            'gpio': gpio,
                            'data': pin
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
        elif item_type == 'pin':
            self.show_pin_details(item_data)
    
    def _add_variant_tab(self, variant_data):
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        
        # Name
        form_layout = QFormLayout()
        name_val = str(variant_data.get('name') or '')
        le_name = QLineEdit(name_val)
        form_layout.addRow("变体名称:", le_name)
        self._register_change_highlight(le_name, le_name.textChanged, le_name.text, name_val)
        layout.addLayout(form_layout)
        
        # Update Tab Title when name changes
        index = self.tabs_variants.addTab(tab_widget, name_val or "新变体")
        le_name.textChanged.connect(lambda text, w=tab_widget: self.tabs_variants.setTabText(self.tabs_variants.indexOf(w), text or "新变体"))
        
        # Identify I2C (Visual)
        grp_id_i2c = QGroupBox("识别 I2C (Identify I2C)")
        layout_id_i2c = QVBoxLayout(grp_id_i2c)
        id_i2c_editors = [] # List to store editors for this variant
        
        for item in variant_data.get('identify_i2c', []):
            self._add_identify_i2c_editor(layout_id_i2c, item, id_i2c_editors)
            
        btn_add_id_i2c = QPushButton("➕ 添加识别 I2C")
        btn_add_id_i2c.clicked.connect(lambda: self._add_identify_i2c_editor(layout_id_i2c, {}, id_i2c_editors))
        layout_id_i2c.addWidget(btn_add_id_i2c)
        layout.addWidget(grp_id_i2c)

        # Display (Visual - Reusing logic)
        grp_disp = QGroupBox("显示屏 (Display)")
        layout_disp = QVBoxLayout(grp_disp)
        disp_editors = []
        
        for item in variant_data.get('display', []):
            self._add_display_editor_to_layout(layout_disp, item, disp_editors)
            
        btn_add_disp = QPushButton("➕ 添加显示屏")
        btn_add_disp.clicked.connect(lambda: self._add_display_editor_to_layout(layout_disp, {}, disp_editors))
        layout_disp.addWidget(btn_add_disp)
        layout.addWidget(grp_disp)

        # Touch (Visual)
        grp_touch = QGroupBox("触摸 (Touch)")
        layout_touch = QVBoxLayout(grp_touch)
        touch_editors = []
        
        for item in variant_data.get('touch', []):
            self._add_touch_editor(layout_touch, item, touch_editors)
            
        btn_add_touch = QPushButton("➕ 添加触摸")
        btn_add_touch.clicked.connect(lambda: self._add_touch_editor(layout_touch, {}, touch_editors))
        layout_touch.addWidget(btn_add_touch)
        layout.addWidget(grp_touch)

        # Store editor references
        self.variant_editors.append({
            'widget': tab_widget,
            'name': le_name,
            'identify_i2c_editors': id_i2c_editors,
            'display_editors': disp_editors,
            'touch_editors': touch_editors
        })
        
        self.tabs_variants.setCurrentWidget(tab_widget)
        self._update_main_display_touch_visibility()

    def _delete_variant_tab(self, index):
        widget = self.tabs_variants.widget(index)
        if widget:
            # Find editor dict
            editor_dict = next((e for e in self.variant_editors if e['widget'] == widget), None)
            if editor_dict:
                self.variant_editors.remove(editor_dict)
            
            self.tabs_variants.removeTab(index)
            widget.deleteLater()
            self._update_main_display_touch_visibility()

    def _add_identify_i2c_editor(self, parent_layout, id_i2c_data, editor_list):
        widget = QGroupBox()
        layout = QGridLayout(widget)
        
        # Port
        sb_port = NoScrollSpinBox()
        sb_port.setValue(int(id_i2c_data.get('port', 0)))
        layout.addWidget(QLabel("Port:"), 0, 0)
        layout.addWidget(sb_port, 0, 1)
        
        # SDA
        sb_sda = NoScrollSpinBox()
        sb_sda.setRange(-1, 999)
        sb_sda.setValue(int(id_i2c_data.get('sda', -1)))
        layout.addWidget(QLabel("SDA:"), 0, 2)
        layout.addWidget(sb_sda, 0, 3)
        
        # SCL
        sb_scl = NoScrollSpinBox()
        sb_scl.setRange(-1, 999)
        sb_scl.setValue(int(id_i2c_data.get('scl', -1)))
        layout.addWidget(QLabel("SCL:"), 0, 4)
        layout.addWidget(sb_scl, 0, 5)
        
        # Freq
        sb_freq = NoScrollSpinBox()
        sb_freq.setRange(0, 1000000)
        sb_freq.setSingleStep(10000)
        sb_freq.setValue(int(id_i2c_data.get('freq', 400000)))
        layout.addWidget(QLabel("Freq:"), 1, 0)
        layout.addWidget(sb_freq, 1, 1)
        
        # Addr
        le_addr = QLineEdit(self._int_to_hex_str(id_i2c_data.get('addr')))
        le_addr.setPlaceholderText("0x55")
        layout.addWidget(QLabel("Addr:"), 1, 2)
        layout.addWidget(le_addr, 1, 3)
        
        # Delete
        btn_del = QPushButton("删除")
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
        
        # Driver
        le_driver = QLineEdit(str(display_data.get('driver', '')))
        grid_basic.addWidget(QLabel("驱动:"), 0, 0)
        grid_basic.addWidget(le_driver, 0, 1)
        
        # Width
        sb_width = NoScrollSpinBox()
        sb_width.setRange(0, 9999)
        sb_width.setValue(int(display_data.get('width', 0)))
        grid_basic.addWidget(QLabel("宽度:"), 0, 2)
        grid_basic.addWidget(sb_width, 0, 3)
        
        # Height
        sb_height = NoScrollSpinBox()
        sb_height.setRange(0, 9999)
        sb_height.setValue(int(display_data.get('height', 0)))
        grid_basic.addWidget(QLabel("高度:"), 1, 0)
        grid_basic.addWidget(sb_height, 1, 1)
        
        # Freq
        sb_freq = NoScrollSpinBox()
        sb_freq.setRange(0, 100000000)
        sb_freq.setSingleStep(1000000)
        sb_freq.setValue(int(display_data.get('freq', 0)))
        grid_basic.addWidget(QLabel("频率:"), 1, 2)
        grid_basic.addWidget(sb_freq, 1, 3)
        
        layout.addLayout(grid_basic)
        
        # 2. Pins (Table)
        grp_pins = QGroupBox("引脚配置")
        layout_pins = QVBoxLayout(grp_pins)
        table_pins = QTableWidget()
        table_pins.setColumnCount(2)
        table_pins.setHorizontalHeaderLabels(["功能", "引脚 (GPIO 或 字符串)"])
        table_pins.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        pins_data = display_data.get('pins', {})
        # Ensure common pins are present or added
        common_pins = ['mosi', 'miso', 'sclk', 'cs', 'dc', 'rst', 'bl']
        current_pins = list(pins_data.keys())
        all_pins = sorted(list(set(common_pins + current_pins)))
        
        table_pins.setRowCount(len(all_pins))
        
        for i, pin_name in enumerate(all_pins):
            # Pin Name (Read-only item)
            item_name = QTableWidgetItem(pin_name)
            item_name.setFlags(item_name.flags() ^ Qt.ItemFlag.ItemIsEditable)
            table_pins.setItem(i, 0, item_name)
            
            # Pin Value
            val = pins_data.get(pin_name, -1)
            if val == -1: val = ""
            le_val = QLineEdit(str(val))
            table_pins.setCellWidget(i, 1, le_val)
            
        self._adjust_table_height(table_pins)
        layout_pins.addWidget(table_pins)
        layout.addWidget(grp_pins)
        
        # 3. Identify (Form)
        grp_id = QGroupBox("识别参数 (Identify)")
        layout_id = QFormLayout(grp_id)
        
        id_data = display_data.get('identify', {})
        
        le_cmd = QLineEdit(self._int_to_hex_str(id_data.get('cmd')))
        le_cmd.setPlaceholderText("例如: 0x04")
        layout_id.addRow("指令 (CMD):", le_cmd)
        
        le_expect = QLineEdit(self._int_to_hex_str(id_data.get('expect')))
        le_expect.setPlaceholderText("例如: 0x079100")
        layout_id.addRow("期望值 (Expect):", le_expect)
        
        le_mask = QLineEdit(self._int_to_hex_str(id_data.get('mask')))
        le_mask.setPlaceholderText("例如: 0xFFFFFF")
        layout_id.addRow("掩码 (Mask):", le_mask)
        
        chk_rst = QCheckBox("读取前复位 (RST Before)")
        chk_rst.setChecked(bool(id_data.get('rst_before', False)))
        layout_id.addRow("", chk_rst)
        
        sb_wait = NoScrollSpinBox()
        sb_wait.setRange(0, 5000)
        sb_wait.setValue(int(id_data.get('rst_wait', 0)))
        sb_wait.setSuffix(" ms")
        layout_id.addRow("复位等待 (Wait):", sb_wait)
        
        layout.addWidget(grp_id)
        
        # Delete Button
        btn_del = QPushButton("删除此屏幕")
        btn_del.setStyleSheet("background-color: #FFCDD2; color: #B71C1C;")
        layout.addWidget(btn_del)
        
        parent_layout.addWidget(widget)
        
        editor_dict = {
            'widget': widget,
            'driver': le_driver,
            'width': sb_width,
            'height': sb_height,
            'freq': sb_freq,
            'table_pins': table_pins,
            'id_cmd': le_cmd,
            'id_expect': le_expect,
            'id_mask': le_mask,
            'id_rst': chk_rst,
            'id_wait': sb_wait
        }
        editor_list.append(editor_dict)
        
        btn_del.clicked.connect(lambda: self._delete_editor_from_list(widget, editor_dict, editor_list))

    def _add_touch_editor(self, parent_layout, touch_data, editor_list):
        widget = QGroupBox()
        layout = QVBoxLayout(widget)
        
        grid = QGridLayout()
        
        # Driver
        le_driver = QLineEdit(str(touch_data.get('driver', '')))
        grid.addWidget(QLabel("驱动:"), 0, 0)
        grid.addWidget(le_driver, 0, 1)
        
        # Addr
        le_addr = QLineEdit(self._int_to_hex_str(touch_data.get('addr')))
        le_addr.setPlaceholderText("0x14")
        grid.addWidget(QLabel("地址:"), 0, 2)
        grid.addWidget(le_addr, 0, 3)
        
        # Width/Height (Optional for touch but good to have)
        sb_width = NoScrollSpinBox()
        sb_width.setRange(0, 9999)
        sb_width.setValue(int(touch_data.get('width', 0)))
        grid.addWidget(QLabel("宽度:"), 1, 0)
        grid.addWidget(sb_width, 1, 1)
        
        sb_height = NoScrollSpinBox()
        sb_height.setRange(0, 9999)
        sb_height.setValue(int(touch_data.get('height', 0)))
        grid.addWidget(QLabel("高度:"), 1, 2)
        grid.addWidget(sb_height, 1, 3)

        sb_freq = NoScrollSpinBox()
        sb_freq.setRange(0, 1000000)
        sb_freq.setSingleStep(10000)
        sb_freq.setValue(int(touch_data.get('freq', 0)))
        grid.addWidget(QLabel("频率:"), 2, 0)
        grid.addWidget(sb_freq, 2, 1)
        
        layout.addLayout(grid)
        
        # Pins
        grp_pins = QGroupBox("引脚")
        layout_pins = QGridLayout(grp_pins)
        
        pins_data = touch_data.get('pins', {})
        
        le_sda = QLineEdit(str(pins_data.get('sda', '')))
        layout_pins.addWidget(QLabel("SDA:"), 0, 0)
        layout_pins.addWidget(le_sda, 0, 1)
        
        le_scl = QLineEdit(str(pins_data.get('scl', '')))
        layout_pins.addWidget(QLabel("SCL:"), 0, 2)
        layout_pins.addWidget(le_scl, 0, 3)
        
        le_int = QLineEdit(str(pins_data.get('int', '')))
        layout_pins.addWidget(QLabel("INT:"), 1, 0)
        layout_pins.addWidget(le_int, 1, 1)
        
        le_rst = QLineEdit(str(pins_data.get('rst', '')))
        layout_pins.addWidget(QLabel("RST:"), 1, 2)
        layout_pins.addWidget(le_rst, 1, 3)
        
        layout.addWidget(grp_pins)
        
        # Delete
        btn_del = QPushButton("删除此触摸")
        btn_del.setStyleSheet("background-color: #FFCDD2; color: #B71C1C;")
        layout.addWidget(btn_del)
        
        parent_layout.addWidget(widget)
        
        editor_dict = {
            'widget': widget,
            'driver': le_driver,
            'addr': le_addr,
            'width': sb_width,
            'height': sb_height,
            'freq': sb_freq,
            'pin_sda': le_sda,
            'pin_scl': le_scl,
            'pin_int': le_int,
            'pin_rst': le_rst
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

    def _add_i2c_bus_editor(self, i2c_data):
        widget = QGroupBox()
        layout = QFormLayout(widget)
        
        # Port, SDA, SCL, Freq
        sb_port = NoScrollSpinBox()
        port_val = int(i2c_data.get('port', 0))
        sb_port.setValue(port_val)
        layout.addRow("端口:", sb_port)
        self._register_change_highlight(sb_port, sb_port.valueChanged, sb_port.value, port_val)
        
        sb_sda = NoScrollSpinBox()
        sb_sda.setRange(-1, 999)
        sda_val = int(i2c_data.get('sda', -1))
        sb_sda.setValue(sda_val)
        layout.addRow("SDA:", sb_sda)
        self._register_change_highlight(sb_sda, sb_sda.valueChanged, sb_sda.value, sda_val)
        
        sb_scl = NoScrollSpinBox()
        sb_scl.setRange(-1, 999)
        scl_val = int(i2c_data.get('scl', -1))
        sb_scl.setValue(scl_val)
        layout.addRow("SCL:", sb_scl)
        self._register_change_highlight(sb_scl, sb_scl.valueChanged, sb_scl.value, scl_val)
        
        sb_freq = NoScrollSpinBox()
        sb_freq.setRange(0, 1000000)
        sb_freq.setSingleStep(10000)
        freq_val = int(i2c_data.get('freq', 400000))
        sb_freq.setValue(freq_val)
        layout.addRow("频率:", sb_freq)
        self._register_change_highlight(sb_freq, sb_freq.valueChanged, sb_freq.value, freq_val)
        
        # Detect Count
        sb_detect_count = NoScrollSpinBox()
        sb_detect_count.setRange(-1, 999)
        sb_detect_count.setSpecialValueText("全部")
        detect_count_val = i2c_data.get('detect_count', -1)
        if detect_count_val is None: detect_count_val = -1
        sb_detect_count.setValue(int(detect_count_val))
        layout.addRow("至少检测数量:", sb_detect_count)
        self._register_change_highlight(sb_detect_count, sb_detect_count.valueChanged, sb_detect_count.value, int(detect_count_val))

        # Detect Table
        lbl_detect = QLabel("检测设备:")
        layout.addRow(lbl_detect)
        
        table_detect = QTableWidget()
        table_detect.setColumnCount(2)
        table_detect.setHorizontalHeaderLabels(["名称", "地址 (十六进制)"])
        table_detect.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table_detect.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        detects = i2c_data.get('detect', [])
        table_detect.setRowCount(0)
        for d in detects:
            self._add_detect_row(table_detect, d)
            
        self._adjust_table_height(table_detect)
        layout.addRow(table_detect)
        
        # Detect Actions
        btn_add_detect = QPushButton("➕ 添加设备")
        btn_add_detect.clicked.connect(lambda: self._add_detect_row(table_detect, {}))
        
        btn_del_detect = QPushButton("➖ 删除设备")
        btn_del_detect.clicked.connect(lambda: self._delete_detect_row(table_detect))
        
        hbox_detect = QHBoxLayout()
        hbox_detect.addWidget(btn_add_detect)
        hbox_detect.addWidget(btn_del_detect)
        layout.addRow(hbox_detect)
        
        # Delete Bus Button
        btn_del_bus = QPushButton("删除此总线")
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
            'detect_count': sb_detect_count,
            'table_detect': table_detect
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

    def _build_changes_html(self, change_lines):
        if not change_lines:
            return ""
        rows = []
        for line in change_lines:
            rows.append(
                f"<li><span style='background-color:#FFCDD2;padding:4px 8px;border-radius:6px;display:block;margin-bottom:6px;'>{html.escape(line)}</span></li>"
            )
        return "<p>以下字段将被保存：</p><ul>" + "".join(rows) + "</ul>"

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
            mcu_name = current_cat.get('mcu') or 'Unknown MCU'
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
                dev_name = dev_key or 'Unknown Device'
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
    def _confirm_device_changes(self, old_data, new_data):
        change_lines = self._collect_device_changes(old_data, new_data)
        if not change_lines:
            QMessageBox.information(self, "无变更", "当前没有任何修改，无需保存。")
            return False

        body_html = self._build_changes_html(change_lines)
        return self._show_change_dialog("保存前确认", body_html)

    def _confirm_full_yaml_changes(self, candidate_data=None):
        summary = self._collect_all_changes(candidate_data)
        base_snapshot = self.base_yaml_data or {}
        candidate_snapshot = candidate_data or {}
        if not summary and base_snapshot != candidate_snapshot:
            summary = {
                'Overall': {
                    'YAML Config': ['Overall structure changed']
                }
            }
        if not summary:
            QMessageBox.information(self, "无变更", "当前 YAML 没有任何改动。")
            return False

        html_body = self._build_grouped_changes_html(summary)
        return self._show_change_dialog("写入 YAML 前确认", html_body)

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
                self.statusBar().showMessage(f"Loaded {YAML_FILE}")
                self.base_yaml_data = copy.deepcopy(self.current_yaml_data)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载 YAML 失败: {str(e)}")
        else:
            self.editor.setPlainText("# m5stack_dev_config.yaml not found. Create a new one.")
            self.current_yaml_data = None
            self.base_yaml_data = None
            
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
                device_name = device.get('name', 'Unknown Device')
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
                    'mcu_index': category_idx,
                    'device_index': dev_idx,
                    'sku': sku,
                    'eol': eol,
                    'variants': device.get('variants', [])
                })
                self.dashboard_widget.addItem(item)

    def on_dashboard_item_clicked(self, item):
        """Handle dashboard item click"""
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
            
        mcu_idx = data.get('mcu_index')
        dev_idx = data.get('device_index')
        
        # Find corresponding tree item
        # Root -> MCU Item -> Device Item
        if mcu_idx < self.tree_widget.topLevelItemCount():
            mcu_item = self.tree_widget.topLevelItem(mcu_idx)
            if dev_idx < mcu_item.childCount():
                device_item = mcu_item.child(dev_idx)
                self.tree_widget.setCurrentItem(device_item)
                self.on_tree_item_clicked(device_item, 0)

    def show_dashboard(self):
        self.stacked_widget.setCurrentWidget(self.dashboard_widget)
        self.header_label.setText("设备仪表板")
        self.tree_widget.clearSelection()

    def show_yaml_editor(self):
        self.stacked_widget.setCurrentWidget(self.editor)
        self.header_label.setText("YAML 编辑器")
        
    def populate_tree(self):
        """Populate the navigation tree with MCU categories and devices"""
        self.tree_widget.clear()
        
        if not self.current_yaml_data:
            return
        
        mcu_categories = self.current_yaml_data.get('mcu_categories', [])
        
        for category_idx, category in enumerate(mcu_categories):
            mcu_name = category.get('mcu', 'Unknown MCU')
            
            # Create MCU category item
            mcu_item = QTreeWidgetItem(self.tree_widget)
            mcu_item.setText(0, f"📦 {mcu_name}")
            mcu_item.setData(0, Qt.ItemDataRole.UserRole, {
                'type': 'mcu',
                'index': category_idx,
                'data': category
            })
            mcu_item.setExpanded(True)
            
            # Add devices under this MCU
            devices = category.get('devices', [])
            for dev_idx, device in enumerate(devices):
                device_name = device.get('name', 'Unknown Device')
                device_item = QTreeWidgetItem(mcu_item)
                device_item.setText(0, f"🔧 {device_name}")
                device_item.setData(0, Qt.ItemDataRole.UserRole, {
                    'type': 'device',
                    'mcu_index': category_idx,
                    'device_index': dev_idx,
                    'data': device
                })
                
                # Add check pins under device
                check_pins = device.get('check_pins', {})
                
                if isinstance(check_pins, list):
                    for pin_idx, pin in enumerate(check_pins):
                        gpio = pin.get('gpio', -1)
                        mode = pin.get('mode', 'input')
                        expect = pin.get('expect', 0)
                        pin_item = QTreeWidgetItem(device_item)
                        pin_item.setText(0, f"📍 GPIO{gpio} ({mode}={expect})")
                        pin_item.setData(0, Qt.ItemDataRole.UserRole, {
                            'type': 'pin',
                            'mcu_index': category_idx,
                            'device_index': dev_idx,
                            'pin_index': pin_idx,
                            'gpio': gpio,
                            'data': pin
                        })
                elif isinstance(check_pins, dict):
                    for gpio, pin in check_pins.items():
                        mode = pin.get('mode', 'input')
                        expect = pin.get('expect', 0)
                        pin_item = QTreeWidgetItem(device_item)
                        pin_item.setText(0, f"📍 GPIO{gpio} ({mode}={expect})")
                        pin_item.setData(0, Qt.ItemDataRole.UserRole, {
                            'type': 'pin',
                            'mcu_index': category_idx,
                            'device_index': dev_idx,
                            'gpio': gpio,
                            'data': pin
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
        elif item_type == 'pin':
            self.show_pin_details(item_data)
    


    def _update_main_display_touch_visibility(self):
        has_variants = len(self.variant_editors) > 0
        if has_variants:
            if hasattr(self, 'group_disp'): self.group_disp.hide()
            if hasattr(self, 'group_touch'): self.group_touch.hide()
            if hasattr(self, 'group_identify_i2c'): self.group_identify_i2c.hide()
            if hasattr(self, 'lbl_main_hidden_hint'): self.lbl_main_hidden_hint.show()
        else:
            if hasattr(self, 'group_disp'): self.group_disp.show()
            if hasattr(self, 'group_touch'): self.group_touch.show()
            if hasattr(self, 'group_identify_i2c'): self.group_identify_i2c.show()
            if hasattr(self, 'lbl_main_hidden_hint'): self.lbl_main_hidden_hint.hide()



    def show_mcu_details(self, item_data):
        """Show MCU category details"""
        mcu_data = item_data.get('data', {})
        mcu_name = mcu_data.get('mcu', 'Unknown')
        devices = mcu_data.get('devices', [])
        
        self.header_label.setText(f"MCU 类别: {mcu_name}")
        
        info_text = f"""
<h2>MCU: {mcu_name}</h2>
<p><b>设备数量:</b> {len(devices)}</p>
<h3>设备列表:</h3>
<ul>
"""
        for device in devices:
            device_name = device.get('name', 'Unknown')
            info_text += f"<li>{device_name}</li>"
        
        info_text += "</ul>"
        
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setTextFormat(Qt.TextFormat.RichText)
        
        # Replace detail widget content
        self.clear_detail_layout()
        self.detail_layout.addWidget(info_label)
        self.detail_layout.addStretch()
    
    def show_device_details(self, item_data):
        """Show device details in an editable form"""
        self.current_edit_data = item_data
        device_data = item_data.get('data', {})
        self.current_device_original = copy.deepcopy(device_data)
        
        # Create Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        self.form_layout = QVBoxLayout(content_widget)
        

        
        # 1. Basic Info
        group_basic = QGroupBox("基本信息")
        form_basic = QFormLayout(group_basic)
        
        name_val = str(device_data.get('name') or '')
        desc_val = str(device_data.get('description') or '')
        sku_val = str(device_data.get('sku') or '')
        eol_val = str(device_data.get('eol') or '')
        image_val = str(device_data.get('image') or '')
        docs_val = str(device_data.get('docs') or '')

        self.edit_name = QLineEdit(name_val)
        self._register_change_highlight(self.edit_name, self.edit_name.textChanged, self.edit_name.text, name_val)
        self.edit_desc = QLineEdit(desc_val)
        self._register_change_highlight(self.edit_desc, self.edit_desc.textChanged, self.edit_desc.text, desc_val)
        self.edit_sku = QLineEdit(sku_val)
        self._register_change_highlight(self.edit_sku, self.edit_sku.textChanged, self.edit_sku.text, sku_val)
        self.edit_eol = NoScrollComboBox()
        self.edit_eol.addItems(["", "EOL", "SALE"])
        self.edit_eol.setCurrentText(eol_val)
        self._register_change_highlight(self.edit_eol, self.edit_eol.currentTextChanged, self.edit_eol.currentText, eol_val)
        self.edit_image = QLineEdit(image_val)
        self._register_change_highlight(self.edit_image, self.edit_image.textChanged, self.edit_image.text, image_val)
        self.edit_docs = QLineEdit(docs_val)
        self._register_change_highlight(self.edit_docs, self.edit_docs.textChanged, self.edit_docs.text, docs_val)
        
        form_basic.addRow("名称:", self.edit_name)
        form_basic.addRow("描述:", self.edit_desc)
        form_basic.addRow("SKU:", self.edit_sku)
        form_basic.addRow("EOL 状态:", self.edit_eol)
        form_basic.addRow("图片链接:", self.edit_image)
        form_basic.addRow("文档链接:", self.edit_docs)
        
        self.form_layout.addWidget(group_basic)
        
        # 2. Check Pins (Table)
        group_pins = QGroupBox("检测引脚")
        layout_pins = QVBoxLayout(group_pins)
        
        # Pin Count
        layout_pin_count = QHBoxLayout()
        lbl_pin_count = QLabel("至少通过数量 (默认全部):")
        self.sb_pin_count = NoScrollSpinBox()
        self.sb_pin_count.setRange(-1, 999)
        self.sb_pin_count.setSpecialValueText("全部")
        pin_count_val = device_data.get('check_pins_count', -1)
        if pin_count_val is None: pin_count_val = -1
        self.sb_pin_count.setValue(int(pin_count_val))
        layout_pin_count.addWidget(lbl_pin_count)
        layout_pin_count.addWidget(self.sb_pin_count)
        layout_pin_count.addStretch()
        layout_pins.addLayout(layout_pin_count)
        self._register_change_highlight(self.sb_pin_count, self.sb_pin_count.valueChanged, self.sb_pin_count.value, int(pin_count_val))

        self.table_pins = QTableWidget()
        self.table_pins.setColumnCount(3)
        self.table_pins.setHorizontalHeaderLabels(["GPIO", "模式", "期望值"])
        self.table_pins.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_pins.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        check_pins = device_data.get('check_pins', {})
        pin_list = []
        if isinstance(check_pins, list):
            pin_list = [p.copy() for p in check_pins]
        elif isinstance(check_pins, dict):
            for gpio, p in check_pins.items():
                new_p = p.copy()
                new_p['gpio'] = gpio
                pin_list.append(new_p)
                
        self.table_pins.setRowCount(0)
        for pin in pin_list:
            self._add_pin_row(pin)
            
        self._adjust_table_height()
        layout_pins.addWidget(self.table_pins)
        
        # Pin Actions
        layout_pin_actions = QHBoxLayout()
        btn_add_pin = QPushButton("➕ 添加引脚")
        btn_add_pin.clicked.connect(lambda: self._add_pin_row({}))
        btn_del_pin = QPushButton("➖ 删除选中引脚")
        btn_del_pin.clicked.connect(self._delete_selected_pin)
        
        layout_pin_actions.addWidget(btn_add_pin)
        layout_pin_actions.addWidget(btn_del_pin)
        layout_pin_actions.addStretch()
        layout_pins.addLayout(layout_pin_actions)
        
        self.form_layout.addWidget(group_pins)
        
        # 3. Internal I2C
        group_i2c = QGroupBox("内部 I2C")
        layout_main_i2c = QVBoxLayout(group_i2c)
        self.layout_i2c_items = QVBoxLayout()
        layout_main_i2c.addLayout(self.layout_i2c_items)
        
        self.i2c_editors = []
        i2c_internal = device_data.get('i2c_internal', [])
        if not isinstance(i2c_internal, list):
             i2c_internal = []

        for i2c in i2c_internal:
            self._add_i2c_bus_editor(i2c)
            
        # I2C Actions
        layout_i2c_actions = QHBoxLayout()
        btn_add_i2c = QPushButton("➕ 添加 I2C 总线")
        btn_add_i2c.clicked.connect(lambda: self._add_i2c_bus_editor({}))
        
        layout_i2c_actions.addWidget(btn_add_i2c)
        layout_i2c_actions.addStretch()
        layout_main_i2c.addLayout(layout_i2c_actions)
        
        self.form_layout.addWidget(group_i2c)

        # Identify I2C (Base Device)
        group_identify_i2c = QGroupBox("识别 I2C")
        layout_main_identify = QVBoxLayout(group_identify_i2c)
        self.layout_identify_i2c_items = QVBoxLayout()
        layout_main_identify.addLayout(self.layout_identify_i2c_items)

        self.identify_i2c_editors = []
        identify_i2c = device_data.get('identify_i2c', [])
        if not isinstance(identify_i2c, list):
             identify_i2c = []

        for item in identify_i2c:
            self._add_identify_i2c_editor(self.layout_identify_i2c_items, item, self.identify_i2c_editors)

        btn_add_identify = QPushButton("➕ 添加识别 I2C")
        btn_add_identify.clicked.connect(lambda: self._add_identify_i2c_editor(self.layout_identify_i2c_items, {}, self.identify_i2c_editors))
        layout_main_identify.addWidget(btn_add_identify)
        self.form_layout.addWidget(group_identify_i2c)
        self.group_identify_i2c = group_identify_i2c

        # Variants (Tab Widget)
        group_variants = QGroupBox("设备变体")
        layout_main_variants = QVBoxLayout(group_variants)
        
        self.tabs_variants = QTabWidget()
        self.tabs_variants.setTabsClosable(True)
        self.tabs_variants.tabCloseRequested.connect(self._delete_variant_tab)
        layout_main_variants.addWidget(self.tabs_variants)
        
        self.variant_editors = []
        variants = device_data.get('variants', [])
        if not isinstance(variants, list):
             variants = []

        for variant in variants:
            self._add_variant_tab(variant)
            
        # Variant Actions
        btn_add_variant = QPushButton("➕ 添加变体")
        btn_add_variant.clicked.connect(lambda: self._add_variant_tab({}))
        layout_main_variants.addWidget(btn_add_variant)
        
        self.form_layout.addWidget(group_variants)
        
        # Hint for hidden main display/touch
        self.lbl_main_hidden_hint = QLabel("⚠️ 注意: 由于存在变体配置，主设备的显示屏、触摸与识别 I2C 配置已被隐藏。")
        self.lbl_main_hidden_hint.setStyleSheet("color: #E65100; font-weight: bold; padding: 10px; background-color: #FFF3E0; border-radius: 5px;")
        self.lbl_main_hidden_hint.hide()
        self.form_layout.addWidget(self.lbl_main_hidden_hint)

        # 4. Displays (Structured Editor)
        group_disp = QGroupBox("显示屏")
        layout_main_disp = QVBoxLayout(group_disp)
        self.layout_display_items = QVBoxLayout()
        layout_main_disp.addLayout(self.layout_display_items)
        
        self.display_editors = []
        displays = device_data.get('display', [])
        if not isinstance(displays, list):
             displays = []

        for disp in displays:
            self._add_display_editor(disp)
            
        # Display Actions
        layout_disp_actions = QHBoxLayout()
        btn_add_disp = QPushButton("➕ 添加显示屏")
        btn_add_disp.clicked.connect(lambda: self._add_display_editor({}))
        
        layout_disp_actions.addWidget(btn_add_disp)
        layout_disp_actions.addStretch()
        layout_main_disp.addLayout(layout_disp_actions)
        
        self.form_layout.addWidget(group_disp)
        self.group_disp = group_disp # Keep reference for visibility toggling
        
        # 5. Touch (YAML Editor for complex structure)
        self.group_touch, self.edit_touch = self._create_yaml_editor_group("触摸 (YAML 编辑)", device_data.get('touch', []))
        self.form_layout.addWidget(self.group_touch)

        # Initial visibility check
        self._update_main_display_touch_visibility()

        # Add spacing for floating button overlay clearance
        self.form_layout.addSpacing(120)

        # Setup Floating Button
        self.detail_container.btn_apply.setText("💾 保存修改")
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
            self.detail_container.btn_apply.show()
            self.detail_container.btn_apply.raise_()
            self.detail_container.btn_apply.update()

        QTimer.singleShot(0, _ensure_button_visible)

    def _add_variant_tab(self, variant_data):
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        
        # Name
        form_layout = QFormLayout()
        name_val = str(variant_data.get('name') or '')
        le_name = QLineEdit(name_val)
        form_layout.addRow("变体名称:", le_name)
        self._register_change_highlight(le_name, le_name.textChanged, le_name.text, name_val)
        layout.addLayout(form_layout)
        
        # Update Tab Title when name changes
        index = self.tabs_variants.addTab(tab_widget, name_val or "新变体")
        le_name.textChanged.connect(lambda text, w=tab_widget: self.tabs_variants.setTabText(self.tabs_variants.indexOf(w), text or "新变体"))
        
        # Identify I2C (Visual)
        grp_id_i2c = QGroupBox("识别 I2C (Identify I2C)")
        layout_id_i2c = QVBoxLayout(grp_id_i2c)
        id_i2c_editors = [] # List to store editors for this variant
        
        for item in variant_data.get('identify_i2c', []):
            self._add_identify_i2c_editor(layout_id_i2c, item, id_i2c_editors)
            
        btn_add_id_i2c = QPushButton("➕ 添加识别 I2C")
        btn_add_id_i2c.clicked.connect(lambda: self._add_identify_i2c_editor(layout_id_i2c, {}, id_i2c_editors))
        layout_id_i2c.addWidget(btn_add_id_i2c)
        layout.addWidget(grp_id_i2c)

        # Display (Visual - Reusing logic)
        grp_disp = QGroupBox("显示屏 (Display)")
        layout_disp = QVBoxLayout(grp_disp)
        disp_editors = []
        
        for item in variant_data.get('display', []):
            self._add_display_editor_to_layout(layout_disp, item, disp_editors)
            
        btn_add_disp = QPushButton("➕ 添加显示屏")
        btn_add_disp.clicked.connect(lambda: self._add_display_editor_to_layout(layout_disp, {}, disp_editors))
        layout_disp.addWidget(btn_add_disp)
        layout.addWidget(grp_disp)

        # Touch (Visual)
        grp_touch = QGroupBox("触摸 (Touch)")
        layout_touch = QVBoxLayout(grp_touch)
        touch_editors = []
        
        for item in variant_data.get('touch', []):
            self._add_touch_editor(layout_touch, item, touch_editors)
            
        btn_add_touch = QPushButton("➕ 添加触摸")
        btn_add_touch.clicked.connect(lambda: self._add_touch_editor(layout_touch, {}, touch_editors))
        layout_touch.addWidget(btn_add_touch)
        layout.addWidget(grp_touch)

        # Store editor references
        self.variant_editors.append({
            'widget': tab_widget,
            'name': le_name,
            'identify_i2c_editors': id_i2c_editors,
            'display_editors': disp_editors,
            'touch_editors': touch_editors
        })
        
        self.tabs_variants.setCurrentWidget(tab_widget)
        self._update_main_display_touch_visibility()

    def _delete_variant_tab(self, index):
        widget = self.tabs_variants.widget(index)
        if widget:
            # Find editor dict
            editor_dict = next((e for e in self.variant_editors if e['widget'] == widget), None)
            if editor_dict:
                self.variant_editors.remove(editor_dict)
            
            self.tabs_variants.removeTab(index)
            widget.deleteLater()
            self._update_main_display_touch_visibility()

    def _add_identify_i2c_editor(self, parent_layout, id_i2c_data, editor_list):
        widget = QGroupBox()
        layout = QGridLayout(widget)
        
        # Port
        sb_port = NoScrollSpinBox()
        sb_port.setValue(int(id_i2c_data.get('port', 0)))
        layout.addWidget(QLabel("Port:"), 0, 0)
        layout.addWidget(sb_port, 0, 1)
        
        # SDA
        sb_sda = NoScrollSpinBox()
        sb_sda.setRange(-1, 999)
        sb_sda.setValue(int(id_i2c_data.get('sda', -1)))
        layout.addWidget(QLabel("SDA:"), 0, 2)
        layout.addWidget(sb_sda, 0, 3)
        
        # SCL
        sb_scl = NoScrollSpinBox()
        sb_scl.setRange(-1, 999)
        sb_scl.setValue(int(id_i2c_data.get('scl', -1)))
        layout.addWidget(QLabel("SCL:"), 0, 4)
        layout.addWidget(sb_scl, 0, 5)
        
        # Freq
        sb_freq = NoScrollSpinBox()
        sb_freq.setRange(0, 1000000)
        sb_freq.setSingleStep(10000)
        sb_freq.setValue(int(id_i2c_data.get('freq', 400000)))
        layout.addWidget(QLabel("Freq:"), 1, 0)
        layout.addWidget(sb_freq, 1, 1)
        
        # Addr
        le_addr = QLineEdit(self._int_to_hex_str(id_i2c_data.get('addr')))
        le_addr.setPlaceholderText("0x55")
        layout.addWidget(QLabel("Addr:"), 1, 2)
        layout.addWidget(le_addr, 1, 3)
        
        # Delete
        btn_del = QPushButton("删除")
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
        
        # Driver
        le_driver = QLineEdit(str(display_data.get('driver', '')))
        grid_basic.addWidget(QLabel("驱动:"), 0, 0)
        grid_basic.addWidget(le_driver, 0, 1)
        
        # Width
        sb_width = NoScrollSpinBox()
        sb_width.setRange(0, 9999)
        sb_width.setValue(int(display_data.get('width', 0)))
        grid_basic.addWidget(QLabel("宽度:"), 0, 2)
        grid_basic.addWidget(sb_width, 0, 3)
        
        # Height
        sb_height = NoScrollSpinBox()
        sb_height.setRange(0, 9999)
        sb_height.setValue(int(display_data.get('height', 0)))
        grid_basic.addWidget(QLabel("高度:"), 1, 0)
        grid_basic.addWidget(sb_height, 1, 1)
        
        # Freq
        sb_freq = NoScrollSpinBox()
        sb_freq.setRange(0, 100000000)
        sb_freq.setSingleStep(1000000)
        sb_freq.setValue(int(display_data.get('freq', 0)))
        grid_basic.addWidget(QLabel("频率:"), 1, 2)
        grid_basic.addWidget(sb_freq, 1, 3)
        
        layout.addLayout(grid_basic)
        
        # 2. Pins (Table)
        grp_pins = QGroupBox("引脚配置")
        layout_pins = QVBoxLayout(grp_pins)
        table_pins = QTableWidget()
        table_pins.setColumnCount(2)
        table_pins.setHorizontalHeaderLabels(["功能", "引脚 (GPIO 或 字符串)"])
        table_pins.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        pins_data = display_data.get('pins', {})
        # Ensure common pins are present or added
        common_pins = ['mosi', 'miso', 'sclk', 'cs', 'dc', 'rst', 'bl']
        current_pins = list(pins_data.keys())
        all_pins = sorted(list(set(common_pins + current_pins)))
        
        table_pins.setRowCount(len(all_pins))
        
        for i, pin_name in enumerate(all_pins):
            # Pin Name (Read-only item)
            item_name = QTableWidgetItem(pin_name)
            item_name.setFlags(item_name.flags() ^ Qt.ItemFlag.ItemIsEditable)
            table_pins.setItem(i, 0, item_name)
            
            # Pin Value
            val = pins_data.get(pin_name, -1)
            if val == -1: val = ""
            le_val = QLineEdit(str(val))
            table_pins.setCellWidget(i, 1, le_val)
            
        self._adjust_table_height(table_pins)
        layout_pins.addWidget(table_pins)
        layout.addWidget(grp_pins)
        
        # 3. Identify (Form)
        grp_id = QGroupBox("识别参数 (Identify)")
        layout_id = QFormLayout(grp_id)
        
        id_data = display_data.get('identify', {})
        
        le_cmd = QLineEdit(self._int_to_hex_str(id_data.get('cmd')))
        le_cmd.setPlaceholderText("例如: 0x04")
        layout_id.addRow("指令 (CMD):", le_cmd)
        
        le_expect = QLineEdit(self._int_to_hex_str(id_data.get('expect')))
        le_expect.setPlaceholderText("例如: 0x079100")
        layout_id.addRow("期望值 (Expect):", le_expect)
        
        le_mask = QLineEdit(self._int_to_hex_str(id_data.get('mask')))
        le_mask.setPlaceholderText("例如: 0xFFFFFF")
        layout_id.addRow("掩码 (Mask):", le_mask)
        
        chk_rst = QCheckBox("读取前复位 (RST Before)")
        chk_rst.setChecked(bool(id_data.get('rst_before', False)))
        layout_id.addRow("", chk_rst)
        
        sb_wait = NoScrollSpinBox()
        sb_wait.setRange(0, 5000)
        sb_wait.setValue(int(id_data.get('rst_wait', 0)))
        sb_wait.setSuffix(" ms")
        layout_id.addRow("复位等待 (Wait):", sb_wait)
        
        layout.addWidget(grp_id)
        
        # Delete Button
        btn_del = QPushButton("删除此屏幕")
        btn_del.setStyleSheet("background-color: #FFCDD2; color: #B71C1C;")
        layout.addWidget(btn_del)
        
        parent_layout.addWidget(widget)
        
        editor_dict = {
            'widget': widget,
            'driver': le_driver,
            'width': sb_width,
            'height': sb_height,
            'freq': sb_freq,
            'table_pins': table_pins,
            'id_cmd': le_cmd,
            'id_expect': le_expect,
            'id_mask': le_mask,
            'id_rst': chk_rst,
            'id_wait': sb_wait
        }
        editor_list.append(editor_dict)
        
        btn_del.clicked.connect(lambda: self._delete_editor_from_list(widget, editor_dict, editor_list))

    def _add_touch_editor(self, parent_layout, touch_data, editor_list):
        widget = QGroupBox()
        layout = QVBoxLayout(widget)
        
        grid = QGridLayout()
        
        # Driver
        le_driver = QLineEdit(str(touch_data.get('driver', '')))
        grid.addWidget(QLabel("驱动:"), 0, 0)
        grid.addWidget(le_driver, 0, 1)
        
        # Addr
        le_addr = QLineEdit(self._int_to_hex_str(touch_data.get('addr')))
        le_addr.setPlaceholderText("0x14")
        grid.addWidget(QLabel("地址:"), 0, 2)
        grid.addWidget(le_addr, 0, 3)
        
        # Width/Height (Optional for touch but good to have)
        sb_width = NoScrollSpinBox()
        sb_width.setRange(0, 9999)
        sb_width.setValue(int(touch_data.get('width', 0)))
        grid.addWidget(QLabel("宽度:"), 1, 0)
        grid.addWidget(sb_width, 1, 1)
        
        sb_height = NoScrollSpinBox()
        sb_height.setRange(0, 9999)
        sb_height.setValue(int(touch_data.get('height', 0)))
        grid.addWidget(QLabel("高度:"), 1, 2)
        grid.addWidget(sb_height, 1, 3)
        
        layout.addLayout(grid)
        
        # Pins
        grp_pins = QGroupBox("引脚")
        layout_pins = QGridLayout(grp_pins)
        
        pins_data = touch_data.get('pins', {})
        
        le_sda = QLineEdit(str(pins_data.get('sda', '')))
        layout_pins.addWidget(QLabel("SDA:"), 0, 0)
        layout_pins.addWidget(le_sda, 0, 1)
        
        le_scl = QLineEdit(str(pins_data.get('scl', '')))
        layout_pins.addWidget(QLabel("SCL:"), 0, 2)
        layout_pins.addWidget(le_scl, 0, 3)
        
        le_int = QLineEdit(str(pins_data.get('int', '')))
        layout_pins.addWidget(QLabel("INT:"), 1, 0)
        layout_pins.addWidget(le_int, 1, 1)
        
        le_rst = QLineEdit(str(pins_data.get('rst', '')))
        layout_pins.addWidget(QLabel("RST:"), 1, 2)
        layout_pins.addWidget(le_rst, 1, 3)
        
        layout.addWidget(grp_pins)
        
        # Delete
        btn_del = QPushButton("删除此触摸")
        btn_del.setStyleSheet("background-color: #FFCDD2; color: #B71C1C;")
        layout.addWidget(btn_del)
        
        parent_layout.addWidget(widget)
        
        editor_dict = {
            'widget': widget,
            'driver': le_driver,
            'addr': le_addr,
            'width': sb_width,
            'height': sb_height,
            'pin_sda': le_sda,
            'pin_scl': le_scl,
            'pin_int': le_int,
            'pin_rst': le_rst
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

    def _add_i2c_bus_editor(self, i2c_data):
        widget = QGroupBox()
        layout = QFormLayout(widget)
        
        # Port, SDA, SCL, Freq
        sb_port = NoScrollSpinBox()
        port_val = int(i2c_data.get('port', 0))
        sb_port.setValue(port_val)
        layout.addRow("端口:", sb_port)
        self._register_change_highlight(sb_port, sb_port.valueChanged, sb_port.value, port_val)
        
        sb_sda = NoScrollSpinBox()
        sb_sda.setRange(-1, 999)
        sda_val = int(i2c_data.get('sda', -1))
        sb_sda.setValue(sda_val)
        layout.addRow("SDA:", sb_sda)
        self._register_change_highlight(sb_sda, sb_sda.valueChanged, sb_sda.value, sda_val)
        
        sb_scl = NoScrollSpinBox()
        sb_scl.setRange(-1, 999)
        scl_val = int(i2c_data.get('scl', -1))
        sb_scl.setValue(scl_val)
        layout.addRow("SCL:", sb_scl)
        self._register_change_highlight(sb_scl, sb_scl.valueChanged, sb_scl.value, scl_val)
        
        sb_freq = NoScrollSpinBox()
        sb_freq.setRange(0, 1000000)
        sb_freq.setSingleStep(10000)
        freq_val = int(i2c_data.get('freq', 400000))
        sb_freq.setValue(freq_val)
        layout.addRow("频率:", sb_freq)
        self._register_change_highlight(sb_freq, sb_freq.valueChanged, sb_freq.value, freq_val)
        
        # Detect Count
        sb_detect_count = NoScrollSpinBox()
        sb_detect_count.setRange(-1, 999)
        sb_detect_count.setSpecialValueText("全部")
        detect_count_val = i2c_data.get('detect_count', -1)
        if detect_count_val is None: detect_count_val = -1
        sb_detect_count.setValue(int(detect_count_val))
        layout.addRow("至少检测数量:", sb_detect_count)
        self._register_change_highlight(sb_detect_count, sb_detect_count.valueChanged, sb_detect_count.value, int(detect_count_val))

        # Detect Table
        lbl_detect = QLabel("检测设备:")
        layout.addRow(lbl_detect)
        
        table_detect = QTableWidget()
        table_detect.setColumnCount(2)
        table_detect.setHorizontalHeaderLabels(["名称", "地址 (十六进制)"])
        table_detect.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table_detect.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        detects = i2c_data.get('detect', [])
        table_detect.setRowCount(0)
        for d in detects:
            self._add_detect_row(table_detect, d)
            
        self._adjust_table_height(table_detect)
        layout.addRow(table_detect)
        
        # Detect Actions
        btn_add_detect = QPushButton("➕ 添加设备")
        btn_add_detect.clicked.connect(lambda: self._add_detect_row(table_detect, {}))
        
        btn_del_detect = QPushButton("➖ 删除设备")
        btn_del_detect.clicked.connect(lambda: self._delete_detect_row(table_detect))
        
        hbox_detect = QHBoxLayout()
        hbox_detect.addWidget(btn_add_detect)
        hbox_detect.addWidget(btn_del_detect)
        layout.addRow(hbox_detect)
        
        # Delete Bus Button
        btn_del_bus = QPushButton("删除此总线")
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
            'detect_count': sb_detect_count,
            'table_detect': table_detect
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

    def save_device_details(self, silent=False):
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
                              'check_pins', 'check_pins_count', 'i2c_internal', 'identify_i2c', 'display', 'touch']
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
                        QMessageBox.warning(self, "验证错误", f"I2C 总线 {i+1} 第 {row+1} 行地址格式无效: '{addr_str}'")
                        return False
                        
                    detects.append({'name': name, 'addr': addr})
                
                bus_data = {
                    'port': port,
                    'sda': sda,
                    'scl': scl,
                    'freq': freq,
                    'detect': detects
                }
                if detect_count != -1:
                    bus_data['detect_count'] = detect_count
                
                new_i2c_list.append(bus_data)
            except ValueError as e:
                QMessageBox.warning(self, "验证错误", f"I2C 总线 {i+1} 的值无效: {e}")
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
                        d_data['pins'] = pins
                        
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
                        t_data['driver'] = t_editor['driver'].text()
                        addr_val = self._parse_int_or_hex(t_editor['addr'].text())
                        t_data['addr'] = addr_val if addr_val is not None else 0
                        t_data['width'] = t_editor['width'].value()
                        t_data['height'] = t_editor['height'].value()
                        t_data['freq'] = t_editor['freq'].value()
                        
                        pins = {}
                        if t_editor['pin_sda'].text().strip():
                            parsed = self._parse_int_or_hex(t_editor['pin_sda'].text())
                            pins['sda'] = parsed if parsed is not None else t_editor['pin_sda'].text()
                        if t_editor['pin_scl'].text().strip():
                            parsed = self._parse_int_or_hex(t_editor['pin_scl'].text())
                            pins['scl'] = parsed if parsed is not None else t_editor['pin_scl'].text()
                        if t_editor['pin_int'].text().strip():
                            parsed = self._parse_int_or_hex(t_editor['pin_int'].text())
                            pins['int'] = parsed if parsed is not None else t_editor['pin_int'].text()
                        if t_editor['pin_rst'].text().strip():
                            parsed = self._parse_int_or_hex(t_editor['pin_rst'].text())
                            pins['rst'] = parsed if parsed is not None else t_editor['pin_rst'].text()
                        
                        t_data['pins'] = pins
                        v_touch.append(t_data)
                    
                    new_variants.append({
                        'name': v_name,
                        'identify_i2c': v_id_i2c,
                        'display': v_disp,
                        'touch': v_touch
                    })
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"解析变体配置出错: {e}")
                    return False
        
        new_data['variants'] = new_variants
        
        # Displays
        new_displays = []
        for editor in self.display_editors:
            try:
                d_data = {}
                d_data['driver'] = editor['driver'].text()
                d_data['width'] = editor['width'].value()
                d_data['height'] = editor['height'].value()
                d_data['freq'] = editor['freq'].value()
                
                # Pins
                pins = {}
                table = editor['table_pins']
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
                QMessageBox.warning(self, "错误", f"保存显示屏配置出错: {e}")
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
            QMessageBox.warning(self, "YAML 错误", f"解析触摸 YAML 出错: {e}")
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
            msg_box.setWindowTitle("已更新")
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setText("设备详情已更新到 YAML 编辑器。")
            btn_write = msg_box.addButton("写入 YAML", QMessageBox.ButtonRole.AcceptRole)
            btn_later = msg_box.addButton("稍后再写", QMessageBox.ButtonRole.RejectRole)
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
        
        self.header_label.setText(f"引脚配置: GPIO {gpio}")
        
        info_text = f"""
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
"""
        
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setTextFormat(Qt.TextFormat.RichText)
        
        self.clear_detail_layout()
        self.detail_layout.addWidget(info_label)
        self.detail_layout.addStretch()
    
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
                if self.current_edit_data.get('type') == 'device':
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
            if hasattr(self, 'current_edit_data') and self.current_edit_data and self.current_edit_data.get('type') == 'device':
                mcu_idx = self.current_edit_data.get('mcu_index')
                dev_idx = self.current_edit_data.get('device_index')
                if mcu_idx is not None and dev_idx is not None:
                    try:
                        updated_device = self.current_yaml_data['mcu_categories'][mcu_idx]['devices'][dev_idx]
                        # Refresh the device detail view with updated data
                        updated_item_data = {
                            'type': 'device',
                            'mcu_index': mcu_idx,
                            'device_index': dev_idx,
                            'data': updated_device
                        }
                        self.show_device_details(updated_item_data)
                    except (KeyError, IndexError):
                        pass
            self.statusBar().showMessage(f"已保存 {YAML_FILE}")
            QMessageBox.information(self, "成功", "YAML 配置已成功保存。")
        except yaml.YAMLError as e:
            QMessageBox.critical(self, "YAML 错误", f"YAML 格式无效:\n{str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存文件失败: {str(e)}")

    def generate_header_file(self):
        content = self.editor.toPlainText()
        try:
            data = yaml.safe_load(content)
            if data is None:
                data = {}

            self.current_yaml_data = data

            success = M5HeaderGenerator.generate_from_data(data, OUTPUT_FILE)
            
            if success:
                self.statusBar().showMessage(f"已生成 {OUTPUT_FILE}")
                QMessageBox.information(self, "成功", f"头文件已成功生成到:\n{OUTPUT_FILE}")
            else:
                raise Exception("生成失败")
            
        except yaml.YAMLError as e:
            QMessageBox.critical(self, "生成错误", f"YAML 解析失败:\n{str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "生成错误", f"生成头文件失败:\n{str(e)}")

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
