"""Prerequisites and additional-test editor widgets.

These are used by the display, touch and I2C editors, so they
must be importable before those modules.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QLineEdit, QCheckBox, QSpinBox, QComboBox,
)
from PyQt6.QtCore import Qt

from M5Autodetect_Widgets import NoScrollSpinBox, NoScrollComboBox
from M5Autodetect_EditorUtils import (
    parse_int_or_hex, int_to_hex_str,
    register_change_highlight, adjust_table_height,
)


class PrereqEditorManager:
    """Manages creation of prerequisite and additional-test widgets."""

    # ------------------------------------------------------------------
    # prerequisites (used by display / touch / i2c editors)
    # ------------------------------------------------------------------

    @staticmethod
    def create_prerequisites_widget(tr, data, entries_list):
        """Build and return a QGroupBox for prerequisite rows.

        *tr* – translation callable (e.g. ``gui.tr``).
        *data* – the device/editor dict that may contain ``'prerequisites'``.
        *entries_list* – mutable list; new entry dicts are appended here.
        """
        grp_prereq = QGroupBox(tr("前置条件 (Prerequisites)"))
        layout_prereq = QVBoxLayout(grp_prereq)

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

            def parse_params(val):
                if isinstance(val, dict):
                    return val
                if not val:
                    return {}
                res = {}
                parts = str(val).split(',')
                for part in parts:
                    if ':' in part:
                        k, v = part.split(':', 1)
                        res[k.strip()] = v.strip()
                return res

            current_params = parse_params(p_params_val)
            widgets = {}

            def create_label(text):
                lbl = QLabel(text)
                lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                lbl.setFixedWidth(40)
                return lbl

            def update_params_ui(type_text):
                while param_layout.count():
                    item = param_layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                widgets.clear()

                if type_text == 'gpio':
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
                    addr_val = str(current_params.get('addr', ''))
                    try:
                        addr_int = int(addr_val, 16) if addr_val.strip().lower().startswith('0x') else int(addr_val)
                        addr_disp = f"0x{addr_int:02X}"
                    except Exception:
                        addr_disp = addr_val
                    le_addr = QLineEdit(addr_disp)
                    le_addr.setPlaceholderText("0x00")
                    le_addr.setFixedWidth(60)
                    param_layout.addWidget(create_label("Addr:"))
                    param_layout.addWidget(le_addr)
                    widgets['addr'] = le_addr

                    reg_val = str(current_params.get('reg', ''))
                    try:
                        reg_int = int(reg_val, 16) if reg_val.strip().lower().startswith('0x') else int(reg_val)
                        reg_disp = f"0x{reg_int:02X}"
                    except Exception:
                        reg_disp = reg_val
                    le_reg = QLineEdit(reg_disp)
                    le_reg.setPlaceholderText("0x00")
                    le_reg.setFixedWidth(60)
                    param_layout.addWidget(create_label("Reg:"))
                    param_layout.addWidget(le_reg)
                    widgets['reg'] = le_reg

                    if 'write' in type_text:
                        val_str = str(current_params.get('data', '0'))
                        try:
                            val_int = int(val_str, 16) if val_str.strip().lower().startswith('0x') else int(val_str)
                        except Exception:
                            val_int = 0

                        le_data = QLineEdit(f"0x{val_int:02X}")
                        le_data.setPlaceholderText("0x00")
                        le_data.setFixedWidth(60)
                        param_layout.addWidget(create_label("Data:"))
                        param_layout.addWidget(le_data)
                        widgets['data'] = le_data

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
                            except Exception:
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
                    le_cmd = QLineEdit(str(current_params.get('cmd', '')))
                    le_cmd.setPlaceholderText("0x00")
                    le_cmd.setFixedWidth(60)
                    param_layout.addWidget(create_label("Cmd:"))
                    param_layout.addWidget(le_cmd)
                    widgets['cmd'] = le_cmd

                    if 'write' in type_text:
                        val_str = str(current_params.get('data', '0'))
                        try:
                            val_int = int(val_str, 16) if val_str.strip().lower().startswith('0x') else int(val_str)
                        except Exception:
                            val_int = 0

                        le_data = QLineEdit(f"0x{val_int:02X}")
                        le_data.setPlaceholderText("0x00")
                        le_data.setFixedWidth(60)
                        param_layout.addWidget(create_label("Data:"))
                        param_layout.addWidget(le_data)
                        widgets['data'] = le_data

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
                            except Exception:
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

            def get_params_dict():
                res = {}
                for k, w in widgets.items():
                    val = None
                    if isinstance(w, QComboBox):
                        val = w.currentText()
                        try:
                            val = int(val)
                        except ValueError:
                            pass
                    elif isinstance(w, QSpinBox):
                        val = w.value()
                    elif isinstance(w, QLineEdit):
                        val = w.text().strip()
                        if val:
                            try:
                                if val.lower().startswith('0x'):
                                    val = int(val, 16)
                                else:
                                    val = int(val)
                            except ValueError:
                                pass
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

        # Load existing prerequisites
        existing_prereqs = data.get('prerequisites', [])
        for p in existing_prereqs:
            params = p.get('params')
            if params is None:
                params = p.copy()
                if 'type' in params:
                    del params['type']
            add_prereq_row(p.get('type'), params)

        btn_add_prereq = QPushButton(tr("➕ 添加前置条件"))
        btn_add_prereq.setMinimumHeight(28)
        btn_add_prereq.setStyleSheet("text-align: left; padding-left: 10px;")
        btn_add_prereq.clicked.connect(lambda: add_prereq_row())
        layout_prereq.addWidget(btn_add_prereq)

        return grp_prereq

    # ------------------------------------------------------------------
    # additional tests (GPIO / I2C / SPI)
    # ------------------------------------------------------------------

    @staticmethod
    def add_additional_test_editor(tr, layout_test_items, test_data,
                                   editor_list):
        """Create an additional-test editor widget and append to *editor_list*.

        *tr* – translation callable.
        *layout_test_items* – the parent QVBoxLayout to place the widget.
        *test_data* – dict with existing test data (may be empty).
        *editor_list* – mutable list of editor dicts.
        """
        widget = QGroupBox()
        widget.setStyleSheet(
            "QGroupBox { border: 1px solid #ccc; border-radius: 5px; "
            "margin-top: 10px; padding-top: 10px; }"
        )
        layout = QVBoxLayout(widget)

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

        btn_del = QPushButton(tr("删除"))
        btn_del.setStyleSheet("background-color: #FFCDD2; color: #B71C1C;")

        top_layout.addWidget(QLabel(tr("类型:")))
        top_layout.addWidget(combo_type)
        top_layout.addWidget(sb_score)
        top_layout.addStretch()
        top_layout.addWidget(btn_del)
        layout.addLayout(top_layout)

        from PyQt6.QtWidgets import QGridLayout
        grid = QGridLayout()
        layout.addLayout(grid)

        test_widgets = {}

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
            grid.addWidget(inp, row, col + 1)
            test_widgets[key] = (lbl, inp)
            return inp

        add_param('gpio_pin', tr("GPIO:"), 0, 0, -1)

        lbl_mode = QLabel(tr("模式:"))
        combo_mode = NoScrollComboBox()
        combo_mode.addItems(["INPUT (0)", "INPUT_PULLUP (1)", "INPUT_PULLDOWN (2)"])
        mode_val = int(test_data.get('pin_b', 0)) if type_val == 0 else 0
        if 0 <= mode_val <= 2:
            combo_mode.setCurrentIndex(mode_val)
        grid.addWidget(lbl_mode, 0, 2)
        grid.addWidget(combo_mode, 0, 3)
        test_widgets['gpio_mode'] = (lbl_mode, combo_mode)

        add_param('gpio_expect', tr("期望(0/1):"), 0, 4, 0)

        add_param('i2c_port', tr("Port:"), 1, 0, 0)
        add_param('i2c_sda', tr("SDA:"), 1, 2, -1)
        add_param('i2c_scl', tr("SCL:"), 1, 4, -1)
        add_param('i2c_freq', tr("Freq:"), 2, 0, 400000)
        add_param('i2c_addr', tr("Addr:"), 2, 2, 0, is_hex=True)
        add_param('i2c_reg', tr("Reg:"), 2, 4, 0, is_hex=True)
        add_param('i2c_mask', tr("Mask:"), 3, 0, 0xFF, is_hex=True)
        add_param('i2c_expect', tr("Expect:"), 3, 2, 0, is_hex=True)

        add_param('spi_mosi', tr("MOSI:"), 4, 0, -1)
        add_param('spi_miso', tr("MISO:"), 4, 2, -1)
        add_param('spi_sclk', tr("SCLK:"), 4, 4, -1)
        add_param('spi_cs', tr("CS:"), 5, 0, -1)
        add_param('spi_cmd', tr("CMD:"), 5, 2, 0, is_hex=True)
        add_param('spi_mask', tr("Mask:"), 5, 4, 0xFF, is_hex=True)
        add_param('spi_expect', tr("Expect:"), 6, 0, 0, is_hex=True)

        def update_visibility():
            t = combo_type.currentIndex()
            for k, (l, w) in test_widgets.items():
                l.hide()
                w.hide()
            if t == 0:
                for k in ('gpio_pin', 'gpio_mode', 'gpio_expect'):
                    test_widgets[k][0].show()
                    test_widgets[k][1].show()
            elif t == 1:
                for k in ('i2c_port', 'i2c_sda', 'i2c_scl', 'i2c_freq',
                          'i2c_addr', 'i2c_reg', 'i2c_mask', 'i2c_expect'):
                    test_widgets[k][0].show()
                    test_widgets[k][1].show()
            elif t == 2:
                for k in ('spi_mosi', 'spi_miso', 'spi_sclk', 'spi_cs',
                          'spi_cmd', 'spi_mask', 'spi_expect'):
                    test_widgets[k][0].show()
                    test_widgets[k][1].show()

        combo_type.currentIndexChanged.connect(update_visibility)
        update_visibility()

        layout_test_items.addWidget(widget)

        editor_dict = {
            'widget': widget,
            'type': combo_type,
            'score': sb_score,
            'widgets': test_widgets,
        }
        editor_list.append(editor_dict)

        btn_del.clicked.connect(
            lambda: PrereqEditorManager.delete_additional_test_editor(
                widget, editor_dict, editor_list
            )
        )

    @staticmethod
    def delete_additional_test_editor(widget, editor_dict, editor_list):
        widget.deleteLater()
        if editor_dict in editor_list:
            editor_list.remove(editor_dict)
