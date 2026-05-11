"""I2C-bus / pin-table editor manager – build I2C and GPIO pin editors."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QGroupBox, QPushButton, QLabel, QLineEdit, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
)
from PyQt6.QtCore import Qt

from M5Autodetect_Widgets import NoScrollSpinBox, NoScrollComboBox
from M5Autodetect_EditorUtils import (
    int_to_hex_str, parse_int_or_hex,
    register_change_highlight, adjust_table_height, delete_editor_from_list,
)
from M5Autodetect_EditorPrereq import PrereqEditorManager


class I2CPinEditorManager:
    """Builds I2C-bus / GPIO-pin editors delegated from M5BuilderGUI."""

    def __init__(self, gui):
        self.gui = gui

    # ================================================================
    #  Identify-I2C editor (simple port/sda/scl/freq/addr row)
    # ================================================================

    def add_identify_i2c_editor(self, parent_layout, id_i2c_data, editor_list):
        tr = self.gui.tr
        widget = QGroupBox()
        layout = QGridLayout(widget)

        sb_port = NoScrollSpinBox()
        sb_port.setValue(int(id_i2c_data.get('port', 0)))
        layout.addWidget(QLabel(tr("Port:")), 0, 0)
        layout.addWidget(sb_port, 0, 1)

        sb_sda = NoScrollSpinBox()
        sb_sda.setRange(-1, 999)
        sb_sda.setValue(int(id_i2c_data.get('sda', -1)))
        layout.addWidget(QLabel(tr("SDA:")), 0, 2)
        layout.addWidget(sb_sda, 0, 3)

        sb_scl = NoScrollSpinBox()
        sb_scl.setRange(-1, 999)
        sb_scl.setValue(int(id_i2c_data.get('scl', -1)))
        layout.addWidget(QLabel(tr("SCL:")), 0, 4)
        layout.addWidget(sb_scl, 0, 5)

        sb_freq = NoScrollSpinBox()
        sb_freq.setRange(0, 1000000)
        sb_freq.setSingleStep(10000)
        sb_freq.setValue(int(id_i2c_data.get('freq', 400000)))
        layout.addWidget(QLabel(tr("Freq:")), 1, 0)
        layout.addWidget(sb_freq, 1, 1)

        le_addr = QLineEdit(int_to_hex_str(id_i2c_data.get('addr')))
        le_addr.setPlaceholderText("0x55")
        layout.addWidget(QLabel(tr("Addr:")), 1, 2)
        layout.addWidget(le_addr, 1, 3)

        btn_del = QPushButton(tr("删除"))
        btn_del.setStyleSheet("background-color: #FFCDD2; color: #B71C1C;")
        layout.addWidget(btn_del, 1, 4, 1, 2)

        parent_layout.addWidget(widget)

        editor_dict = {
            'widget': widget,
            'port': sb_port,
            'sda': sb_sda,
            'scl': sb_scl,
            'freq': sb_freq,
            'addr': le_addr,
        }
        editor_list.append(editor_dict)

        btn_del.clicked.connect(
            lambda: delete_editor_from_list(widget, editor_dict, editor_list)
        )

    # ================================================================
    #  Pin (GPIO) table helpers
    # ================================================================

    def add_pin_row(self, pin_data):
        """Append one GPIO row to ``self.gui.table_pins``."""
        table = self.gui.table_pins
        row = table.rowCount()
        table.insertRow(row)

        sb_gpio = NoScrollSpinBox()
        sb_gpio.setRange(0, 999)
        gpio_val = pin_data.get('gpio', None)
        if gpio_val is not None and int(gpio_val) != -1:
            sb_gpio.setValue(int(gpio_val))
        original_gpio = (
            int(gpio_val) if gpio_val is not None and int(gpio_val) != -1
            else sb_gpio.value()
        )
        table.setCellWidget(row, 0, sb_gpio)
        register_change_highlight(sb_gpio, sb_gpio.valueChanged, sb_gpio.value, original_gpio)

        combo_mode = NoScrollComboBox()
        combo_mode.addItems(['input', 'input_pullup', 'input_pulldown'])
        original_mode = pin_data.get('mode', 'input')
        combo_mode.setCurrentText(original_mode)
        table.setCellWidget(row, 1, combo_mode)
        register_change_highlight(combo_mode, combo_mode.currentTextChanged, combo_mode.currentText, original_mode)

        combo_expect = NoScrollComboBox()
        combo_expect.addItems(['LOW', 'HIGH'])
        expect_val = int(pin_data.get('expect', 0))
        combo_expect.setCurrentIndex(expect_val)
        table.setCellWidget(row, 2, combo_expect)
        register_change_highlight(combo_expect, combo_expect.currentIndexChanged, combo_expect.currentIndex, expect_val)

        adjust_table_height(table)

    def delete_selected_pin(self):
        """Remove the currently-selected row from ``self.gui.table_pins``."""
        table = self.gui.table_pins
        current_row = table.currentRow()
        if current_row >= 0:
            table.removeRow(current_row)
            adjust_table_height(table)

    # ================================================================
    #  Import pins / I2C from JSON dialogs
    # ================================================================

    def import_pins_from_json(self):
        """Show dialog, parse SelfCheck GPIO JSON, populate pin table."""
        from PyQt6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
            QComboBox, QPushButton, QMessageBox,
        )
        tr = self.gui.tr

        dialog = QDialog(self.gui)
        dialog.setWindowTitle(tr("批量导入引脚"))
        dialog.setMinimumSize(500, 400)
        layout = QVBoxLayout(dialog)

        label = QLabel(tr("请粘贴 SelfCheck JSON 数据 (GPIO):"))
        layout.addWidget(label)

        text_edit = QTextEdit()
        text_edit.setPlaceholderText('{"chip_model":"...","pins":[...]}')
        layout.addWidget(text_edit)

        bottom_layout = QHBoxLayout()
        filter_label = QLabel(tr("GPIO 电平过滤:"))
        combo_filter = QComboBox()
        combo_filter.addItems([tr("全部电平"), tr("仅高电平"), tr("仅低电平")])
        bottom_layout.addWidget(filter_label)
        bottom_layout.addWidget(combo_filter)
        bottom_layout.addStretch()

        btn_cancel = QPushButton(tr("取消"))
        btn_ok = QPushButton(tr("导入"))
        btn_ok.setDefault(True)
        bottom_layout.addWidget(btn_cancel)
        bottom_layout.addWidget(btn_ok)
        layout.addLayout(bottom_layout)

        btn_cancel.clicked.connect(dialog.reject)
        btn_ok.clicked.connect(dialog.accept)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        text = text_edit.toPlainText()
        level_filter = combo_filter.currentIndex()

        if not text.strip():
            return

        try:
            import json
            data = json.loads(text.strip())
            if 'pins' in data:
                self._import_pins_from_data(data, level_filter)
                return
            QMessageBox.warning(self.gui, tr("导入失败"),
                                tr("未识别的 JSON 格式 (未找到 'pins' 字段)"))
        except Exception as e:
            QMessageBox.warning(self.gui, tr("导入失败"), str(e))

    def import_i2c_from_json(self):
        """Show dialog, parse SelfCheck I2C JSON, populate I2C editors."""
        from PyQt6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
            QPushButton, QMessageBox,
        )
        tr = self.gui.tr

        dialog = QDialog(self.gui)
        dialog.setWindowTitle(tr("批量导入 I2C"))
        dialog.setMinimumSize(500, 400)
        layout = QVBoxLayout(dialog)

        label = QLabel(tr("请粘贴 SelfCheck JSON 数据 (I2C):"))
        layout.addWidget(label)

        text_edit = QTextEdit()
        text_edit.setPlaceholderText('{"type":"I2C","devices":[...]}')
        layout.addWidget(text_edit)

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        btn_cancel = QPushButton(tr("取消"))
        btn_ok = QPushButton(tr("导入"))
        btn_ok.setDefault(True)
        bottom_layout.addWidget(btn_cancel)
        bottom_layout.addWidget(btn_ok)
        layout.addLayout(bottom_layout)

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
            if 'type' in data and data['type'] == 'I2C' and 'devices' in data:
                self._import_i2c_from_data(data)
                return
            QMessageBox.warning(self.gui, tr("导入失败"),
                                tr("未识别的 JSON 格式 (未找到 I2C 数据)"))
        except Exception as e:
            QMessageBox.warning(self.gui, tr("导入失败"), str(e))

    # ── private import helpers ────────────────────────────────────

    def _import_pins_from_data(self, data, level_filter):
        from PyQt6.QtWidgets import QMessageBox
        tr = self.gui.tr
        pins = data['pins']
        if not isinstance(pins, list):
            QMessageBox.warning(self.gui, tr("导入失败"), tr("'pins' 字段必须是数组"))
            return

        if level_filter == 1:
            pins = [p for p in pins if p.get('level', 0) == 1]
        elif level_filter == 2:
            pins = [p for p in pins if p.get('level', 0) == 0]

        if len(pins) == 0:
            QMessageBox.warning(self.gui, tr("导入失败"), tr("没有符合过滤条件的引脚"))
            return

        reply = QMessageBox.question(
            self.gui, tr("导入模式"),
            tr("是否清空现有引脚后导入？\n\n是 = 替换现有引脚\n否 = 追加到现有引脚"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Cancel:
            return
        if reply == QMessageBox.StandardButton.Yes:
            self.gui.table_pins.setRowCount(0)

        imported_count = 0
        for pin in pins:
            if 'gpio' in pin and 'level' in pin:
                self.add_pin_row({
                    'gpio': pin['gpio'],
                    'mode': 'input',
                    'expect': pin['level'],
                })
                imported_count += 1

        adjust_table_height(self.gui.table_pins)

        chip_info = data.get('chip_model', 'Unknown')
        psram_info = "板型具备 PSRAM" if data.get('psram_enabled', False) else "板型不具备 PSRAM"
        filter_info = ["全部电平", "仅高电平", "仅低电平"][level_filter]
        QMessageBox.information(
            self.gui, tr("导入成功"),
            tr(f"已导入 {imported_count} 个引脚 ({filter_info})\n芯片: {chip_info}\n{psram_info}"),
        )

    def _import_i2c_from_data(self, data):
        from PyQt6.QtWidgets import QMessageBox
        tr = self.gui.tr
        devices = data.get('devices', [])
        sda = data.get('sda', -1)
        scl = data.get('scl', -1)
        freq = data.get('freq', 400000)

        if not devices:
            QMessageBox.warning(self.gui, tr("导入失败"), tr("未找到 I2C 设备"))
            return

        reply = QMessageBox.question(
            self.gui, tr("导入模式"),
            tr("是否清空现有 I2C 总线配置后导入？\n\n是 = 替换现有配置\n否 = 追加到现有配置"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Cancel:
            return

        if not hasattr(self.gui, 'i2c_editors') or not hasattr(self.gui, 'layout_i2c_items'):
            QMessageBox.warning(self.gui, tr("导入失败"), tr("找不到 i2c_editors 编辑器列表或布局"))
            return

        if reply == QMessageBox.StandardButton.Yes:
            while self.gui.i2c_editors:
                editor = self.gui.i2c_editors.pop()
                widget = editor['widget']
                widget.setParent(None)
                widget.deleteLater()

        detect_list = []
        for addr in devices:
            detect_list.append({'addr': addr, 'name': f'Unknown_0x{addr:02X}'})

        i2c_data = {
            'sda': sda,
            'scl': scl,
            'freq': freq,
            'port': 0,
            'detect': detect_list,
            'detect_count': len(detect_list),
        }
        self.add_i2c_bus_editor(i2c_data)
        QMessageBox.information(
            self.gui, tr("导入成功"),
            tr(f"成功导入 I2C 总线，包含 {len(detect_list)} 个设备"),
        )

    # ================================================================
    #  I2C bus editor
    # ================================================================

    def add_i2c_bus_editor(self, i2c_data):
        """Create a full I2C-bus editor and register it in ``self.gui.i2c_editors``."""
        tr = self.gui.tr
        widget = QGroupBox()
        layout = QFormLayout(widget)

        sb_port = NoScrollSpinBox()
        port_val = int(i2c_data.get('port', 0))
        sb_port.setValue(port_val)
        layout.addRow(tr("端口:"), sb_port)
        register_change_highlight(sb_port, sb_port.valueChanged, sb_port.value, port_val)

        sb_sda = NoScrollSpinBox()
        sb_sda.setRange(-1, 999)
        sda_val = int(i2c_data.get('sda', -1))
        sb_sda.setValue(sda_val)
        layout.addRow(tr("SDA:"), sb_sda)
        register_change_highlight(sb_sda, sb_sda.valueChanged, sb_sda.value, sda_val)

        sb_scl = NoScrollSpinBox()
        sb_scl.setRange(-1, 999)
        scl_val = int(i2c_data.get('scl', -1))
        sb_scl.setValue(scl_val)
        layout.addRow(tr("SCL:"), sb_scl)
        register_change_highlight(sb_scl, sb_scl.valueChanged, sb_scl.value, scl_val)

        sb_freq = NoScrollSpinBox()
        sb_freq.setRange(0, 1000000)
        sb_freq.setSingleStep(10000)
        freq_val = int(i2c_data.get('freq', 400000))
        sb_freq.setValue(freq_val)
        layout.addRow(tr("频率:"), sb_freq)
        register_change_highlight(sb_freq, sb_freq.valueChanged, sb_freq.value, freq_val)

        cb_internal_pullup = QCheckBox(tr("使用内部上拉 (无外部上拉时启用)"))
        internal_pullup_val = bool(i2c_data.get('internal_pullup', False))
        cb_internal_pullup.setChecked(internal_pullup_val)
        cb_internal_pullup.setToolTip(
            tr("当 I2C 总线没有外部上拉电阻时，启用 ESP32 内部上拉电阻。\n"
               "注意：内部上拉较弱，仅适用于短距离低速通信。"))
        layout.addRow(cb_internal_pullup)
        register_change_highlight(cb_internal_pullup, cb_internal_pullup.stateChanged, cb_internal_pullup.isChecked, internal_pullup_val)

        cb_low_level_hard_fail = QCheckBox(tr("SDA/SCL 低电平硬失败"))
        low_level_hard_fail_val = bool(i2c_data.get('low_level_hard_fail', True))
        cb_low_level_hard_fail.setChecked(low_level_hard_fail_val)
        cb_low_level_hard_fail.setToolTip(
            tr("勾选：SDA/SCL 空闲电平为低时立即判定该板型失败。\n"
               "取消：记录低电平并跳过该 I2C 总线失败，不直接淘汰板型。"))
        layout.addRow(cb_low_level_hard_fail)
        register_change_highlight(cb_low_level_hard_fail, cb_low_level_hard_fail.stateChanged, cb_low_level_hard_fail.isChecked, low_level_hard_fail_val)

        sb_detect_count = NoScrollSpinBox()
        sb_detect_count.setRange(-1, 999)
        sb_detect_count.setSpecialValueText(tr("全部"))
        detect_count_val = i2c_data.get('detect_count', -1)
        if detect_count_val is None:
            detect_count_val = -1
        detects = i2c_data.get('detect', [])
        default_count = len(detects) if detect_count_val == -1 else int(detect_count_val)
        sb_detect_count.setValue(default_count)
        layout.addRow(tr("至少检测数量:"), sb_detect_count)
        register_change_highlight(sb_detect_count, sb_detect_count.valueChanged, sb_detect_count.value, default_count)

        lbl_detect = QLabel(tr("检测设备:"))
        layout.addRow(lbl_detect)

        table_detect = QTableWidget()
        table_detect.setColumnCount(3)
        table_detect.setHorizontalHeaderLabels([tr("名称"), tr("地址 (十六进制)"), tr("必须")])
        table_detect.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table_detect.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table_detect.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        table_detect.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table_detect.setRowCount(0)

        for d in detects:
            self._add_detect_row(table_detect, d)
        adjust_table_height(table_detect)
        layout.addRow(table_detect)

        btn_add_detect = QPushButton(tr("➕ 添加设备"))
        btn_add_detect.clicked.connect(lambda: self._add_detect_row(table_detect, {}))
        btn_del_detect = QPushButton(tr("➖ 删除设备"))
        btn_del_detect.clicked.connect(lambda: self._delete_detect_row(table_detect))
        hbox_detect = QHBoxLayout()
        hbox_detect.addWidget(btn_add_detect)
        hbox_detect.addWidget(btn_del_detect)
        layout.addRow(hbox_detect)

        prereq_entries = []
        grp_prereq = PrereqEditorManager.create_prerequisites_widget(
            tr, i2c_data, prereq_entries
        )
        layout.addRow(grp_prereq)

        btn_del_bus = QPushButton(tr("删除此总线"))
        btn_del_bus.setStyleSheet("background-color: #FFCDD2; color: #B71C1C;")

        self.gui.layout_i2c_items.addWidget(widget)

        editor_dict = {
            'widget': widget,
            'port': sb_port,
            'sda': sb_sda,
            'scl': sb_scl,
            'freq': sb_freq,
            'internal_pullup': cb_internal_pullup,
            'low_level_hard_fail': cb_low_level_hard_fail,
            'detect_count': sb_detect_count,
            'table_detect': table_detect,
            'prereq_entries': prereq_entries,
        }
        self.gui.i2c_editors.append(editor_dict)

        btn_del_bus.clicked.connect(lambda: self._delete_i2c_bus_editor(widget, editor_dict))
        layout.addRow(btn_del_bus)

    def _delete_i2c_bus_editor(self, widget, editor_dict):
        widget.deleteLater()
        if editor_dict in self.gui.i2c_editors:
            self.gui.i2c_editors.remove(editor_dict)

    # ── detect table helpers ─────────────────────────────────────

    def _add_detect_row(self, table, detect_data):
        tr = self.gui.tr
        row = table.rowCount()
        table.insertRow(row)

        original_name = detect_data.get('name', '') or ''
        le_name = QLineEdit(original_name)
        table.setCellWidget(row, 0, le_name)
        register_change_highlight(le_name, le_name.textChanged, le_name.text, original_name)

        le_addr = QLineEdit()
        addr = detect_data.get('addr', 0)
        original_addr = f"0x{addr:02X}" if isinstance(addr, int) else str(addr)
        le_addr.setText(original_addr)
        table.setCellWidget(row, 1, le_addr)
        register_change_highlight(le_addr, le_addr.textChanged, le_addr.text, original_addr)

        required_val = bool(detect_data.get('required', True))
        cb_required = QCheckBox()
        cb_required.setChecked(required_val)
        cb_required.setToolTip(
            tr("必须存在：勾选 = 必须 ACK，否则总线检测失败；\n"
               "取消勾选 = 可选，不存在不影响通过判断。"))
        container = QWidget()
        layout_center = QHBoxLayout(container)
        layout_center.addWidget(cb_required)
        layout_center.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_center.setContentsMargins(0, 0, 0, 0)
        table.setCellWidget(row, 2, container)
        register_change_highlight(container, cb_required.stateChanged, cb_required.isChecked, required_val)

        adjust_table_height(table)

    @staticmethod
    def _delete_detect_row(table):
        current_row = table.currentRow()
        if current_row >= 0:
            table.removeRow(current_row)
            adjust_table_height(table)
