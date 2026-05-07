"""Touch editor manager – builds and serializes touch editor widgets."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QPushButton, QLabel,
    QGroupBox, QLineEdit, QCheckBox,
)

from M5Autodetect_Widgets import NoScrollSpinBox, NoScrollComboBox, PinValueEditor
from M5Autodetect_EditorUtils import (
    parse_int_or_hex, int_to_hex_str, read_pin_widget_value,
    delete_editor_from_list, set_combo_items,
    get_touch_probe_options, infer_touch_probe, build_probe_hint,
)
from M5Autodetect_EditorPrereq import PrereqEditorManager


class TouchEditorManager:
    """Builds touch-editor widgets delegated from M5BuilderGUI."""

    def __init__(self, gui):
        self.gui = gui

    # ---- public API ------------------------------------------------

    def add_editor(self, parent_layout, touch_data, editor_list):
        """Create a full touch editor and append its dict to *editor_list*."""
        tr = self.gui.tr

        widget = QGroupBox()
        layout = QVBoxLayout(widget)

        grid = QGridLayout()

        cb_bus_type = NoScrollComboBox()
        cb_bus_type.addItems(['i2c', 'spi'])
        bus_type_val = str(touch_data.get('bus_type', 'i2c'))
        cb_bus_type.setCurrentText(bus_type_val)
        grid.addWidget(QLabel(tr("总线类型:")), 0, 0)
        grid.addWidget(cb_bus_type, 0, 1)

        controller_value = str(touch_data.get('controller', touch_data.get('driver', '')))
        le_controller = QLineEdit(controller_value)
        grid.addWidget(QLabel(tr("控制器/型号:")), 0, 2)
        grid.addWidget(le_controller, 0, 3)

        sb_width = NoScrollSpinBox()
        sb_width.setRange(0, 9999)
        sb_width.setValue(int(touch_data.get('width', 0)))
        grid.addWidget(QLabel(tr("宽度:")), 1, 0)
        grid.addWidget(sb_width, 1, 1)

        sb_height = NoScrollSpinBox()
        sb_height.setRange(0, 9999)
        sb_height.setValue(int(touch_data.get('height', 0)))
        grid.addWidget(QLabel(tr("高度:")), 1, 2)
        grid.addWidget(sb_height, 1, 3)

        sb_freq = NoScrollSpinBox()
        sb_freq.setRange(0, 10000000)
        sb_freq.setSingleStep(10000)
        sb_freq.setValue(int(touch_data.get('freq', 0)))
        grid.addWidget(QLabel(tr("频率:")), 2, 0)
        grid.addWidget(sb_freq, 2, 1)

        layout.addLayout(grid)

        # ── pins ──────────────────────────────────────────────────
        grp_pins = QGroupBox(tr("引脚"))
        layout_pins = QGridLayout(grp_pins)

        pins_data = touch_data.get('pins', {})

        le_int = PinValueEditor(pins_data.get('int'))
        le_rst = PinValueEditor(pins_data.get('rst'))
        le_sda = PinValueEditor(pins_data.get('sda'))
        le_scl = PinValueEditor(pins_data.get('scl'))
        le_cs = PinValueEditor(pins_data.get('cs'))
        le_mosi = PinValueEditor(pins_data.get('mosi'))
        le_miso = PinValueEditor(pins_data.get('miso'))
        le_sclk = PinValueEditor(pins_data.get('sclk'))

        lbl_sda = QLabel("SDA:")
        lbl_scl = QLabel("SCL:")
        lbl_cs = QLabel("CS:")
        lbl_mosi = QLabel("MOSI:")
        lbl_miso = QLabel("MISO:")
        lbl_sclk = QLabel("SCLK:")
        lbl_int = QLabel("INT:")
        lbl_rst = QLabel("RST:")

        layout_pins.addWidget(lbl_sda, 0, 0)
        layout_pins.addWidget(le_sda, 0, 1)
        layout_pins.addWidget(lbl_scl, 0, 2)
        layout_pins.addWidget(le_scl, 0, 3)

        layout_pins.addWidget(lbl_cs, 1, 0)
        layout_pins.addWidget(le_cs, 1, 1)
        layout_pins.addWidget(lbl_mosi, 1, 2)
        layout_pins.addWidget(le_mosi, 1, 3)

        layout_pins.addWidget(lbl_miso, 2, 0)
        layout_pins.addWidget(le_miso, 2, 1)
        layout_pins.addWidget(lbl_sclk, 2, 2)
        layout_pins.addWidget(le_sclk, 2, 3)

        layout_pins.addWidget(lbl_int, 3, 0)
        layout_pins.addWidget(le_int, 3, 1)
        layout_pins.addWidget(lbl_rst, 3, 2)
        layout_pins.addWidget(le_rst, 3, 3)

        layout.addWidget(grp_pins)

        # ── probe group ───────────────────────────────────────────
        probe_data = infer_touch_probe(touch_data, bus_type_val)
        grp_probe = QGroupBox(tr("识别方式 (Probe)"))
        layout_probe = QGridLayout(grp_probe)

        combo_probe = NoScrollComboBox()
        set_combo_items(combo_probe, get_touch_probe_options(tr, bus_type_val),
                        probe_data.get('type', 'none'))
        layout_probe.addWidget(QLabel(tr("探测方式:")), 0, 0)
        layout_probe.addWidget(combo_probe, 0, 1, 1, 3)

        lbl_probe_addr = QLabel(tr("地址:"))
        le_probe_addr = QLineEdit(int_to_hex_str(probe_data.get('addr', touch_data.get('addr'))))
        le_probe_addr.setPlaceholderText("0x14")
        layout_probe.addWidget(lbl_probe_addr, 1, 0)
        layout_probe.addWidget(le_probe_addr, 1, 1)

        lbl_probe_reg = QLabel(tr("寄存器 (REG):"))
        le_probe_reg = QLineEdit(int_to_hex_str(probe_data.get('reg')))
        le_probe_reg.setPlaceholderText("0x00")
        layout_probe.addWidget(lbl_probe_reg, 1, 2)
        layout_probe.addWidget(le_probe_reg, 1, 3)

        lbl_probe_cmd = QLabel(tr("命令 (CMD):"))
        le_probe_cmd = QLineEdit(int_to_hex_str(probe_data.get('cmd')))
        le_probe_cmd.setPlaceholderText("0x04")
        layout_probe.addWidget(lbl_probe_cmd, 2, 0)
        layout_probe.addWidget(le_probe_cmd, 2, 1)

        lbl_probe_expect = QLabel(tr("期望值:"))
        le_probe_expect = QLineEdit(int_to_hex_str(probe_data.get('expect')))
        le_probe_expect.setPlaceholderText("0x0000")
        layout_probe.addWidget(lbl_probe_expect, 2, 2)
        layout_probe.addWidget(le_probe_expect, 2, 3)

        lbl_probe_mask = QLabel(tr("掩码:"))
        le_probe_mask = QLineEdit(int_to_hex_str(probe_data.get('mask')))
        le_probe_mask.setPlaceholderText("0xFFFF")
        layout_probe.addWidget(lbl_probe_mask, 3, 0)
        layout_probe.addWidget(le_probe_mask, 3, 1)

        chk_probe_rst = QCheckBox(tr("探测前复位"))
        chk_probe_rst.setChecked(bool(probe_data.get('rst_before', False)))
        layout_probe.addWidget(chk_probe_rst, 3, 2)

        sb_probe_wait = NoScrollSpinBox()
        sb_probe_wait.setRange(0, 5000)
        sb_probe_wait.setSuffix(" ms")
        sb_probe_wait.setValue(int(probe_data.get('rst_wait', 0)))
        layout_probe.addWidget(sb_probe_wait, 3, 3)

        lbl_probe_hint = QLabel()
        lbl_probe_hint.setWordWrap(True)
        lbl_probe_hint.setStyleSheet("color: #546E7A; padding-top: 4px;")
        layout_probe.addWidget(lbl_probe_hint, 4, 0, 1, 4)

        def update_visibility(bus_type):
            is_i2c = (bus_type == 'i2c')

            lbl_sda.setVisible(is_i2c)
            le_sda.setVisible(is_i2c)
            lbl_scl.setVisible(is_i2c)
            le_scl.setVisible(is_i2c)

            lbl_cs.setVisible(not is_i2c)
            le_cs.setVisible(not is_i2c)
            lbl_mosi.setVisible(not is_i2c)
            le_mosi.setVisible(not is_i2c)
            lbl_miso.setVisible(not is_i2c)
            le_miso.setVisible(not is_i2c)
            lbl_sclk.setVisible(not is_i2c)
            le_sclk.setVisible(not is_i2c)

            probe_options = get_touch_probe_options(tr, bus_type)
            current_probe = combo_probe.currentData() or 'none'
            available_probe_values = [value for value, _label in probe_options]
            if current_probe not in available_probe_values:
                current_probe = probe_options[0][0]
            set_combo_items(combo_probe, probe_options, current_probe)
            update_probe_ui()

        def update_probe_ui():
            probe_type = combo_probe.currentData() or 'none'
            show_addr = probe_type in ('i2c_addr_ack', 'i2c_reg_match')
            show_reg = probe_type == 'i2c_reg_match'
            show_cmd = probe_type == 'spi_cmd_match'
            show_expect = probe_type in ('i2c_reg_match', 'spi_cmd_match')
            show_mask = show_expect
            show_rst = probe_type == 'spi_cmd_match'

            for label, field, visible in [
                (lbl_probe_addr, le_probe_addr, show_addr),
                (lbl_probe_reg, le_probe_reg, show_reg),
                (lbl_probe_cmd, le_probe_cmd, show_cmd),
                (lbl_probe_expect, le_probe_expect, show_expect),
                (lbl_probe_mask, le_probe_mask, show_mask),
            ]:
                label.setVisible(visible)
                field.setVisible(visible)

            chk_probe_rst.setVisible(show_rst)
            sb_probe_wait.setVisible(show_rst)
            lbl_probe_hint.setText(build_probe_hint(tr, 'touch', probe_type))

        cb_bus_type.currentTextChanged.connect(update_visibility)
        update_visibility(bus_type_val)
        combo_probe.currentIndexChanged.connect(update_probe_ui)
        update_probe_ui()

        layout.addWidget(grp_probe)

        # ── prerequisites ─────────────────────────────────────────
        prereq_entries = []
        grp_prereq = PrereqEditorManager.create_prerequisites_widget(
            tr, touch_data, prereq_entries
        )
        layout.addWidget(grp_prereq)

        # ── delete button ─────────────────────────────────────────
        btn_del = QPushButton(tr("删除此触摸"))
        btn_del.setStyleSheet("background-color: #FFCDD2; color: #B71C1C;")
        layout.addWidget(btn_del)

        parent_layout.addWidget(widget)

        editor_dict = {
            'widget': widget,
            'bus_type': cb_bus_type,
            'controller': le_controller,
            'driver': le_controller,
            'probe_type': combo_probe,
            'probe_addr': le_probe_addr,
            'probe_reg': le_probe_reg,
            'probe_cmd': le_probe_cmd,
            'probe_expect': le_probe_expect,
            'probe_mask': le_probe_mask,
            'probe_rst': chk_probe_rst,
            'probe_wait': sb_probe_wait,
            'addr': le_probe_addr,
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
            'prereq_entries': prereq_entries,
        }
        editor_list.append(editor_dict)

        btn_del.clicked.connect(
            lambda: delete_editor_from_list(widget, editor_dict, editor_list)
        )

    # ---- serialization --------------------------------------------

    def serialize(self, editor):
        """Collect the current values from a touch editor dict → data dict."""
        t_data = {
            'bus_type': editor['bus_type'].currentText(),
            'width': editor['width'].value(),
            'height': editor['height'].value(),
            'freq': editor['freq'].value(),
        }

        controller = editor['controller'].text().strip()
        if controller:
            t_data['controller'] = controller
            t_data['driver'] = controller

        pins = {}
        for key in ['int', 'rst', 'sda', 'scl', 'cs', 'mosi', 'miso', 'sclk']:
            value = read_pin_widget_value(editor[f'pin_{key}'])
            if value is not None:
                pins[key] = value
        t_data['pins'] = pins

        probe_type = editor['probe_type'].currentData() or 'none'
        probe = {'type': probe_type}
        probe_addr = parse_int_or_hex(editor['probe_addr'].text())
        probe_cmd = parse_int_or_hex(editor['probe_cmd'].text())
        probe_reg = parse_int_or_hex(editor['probe_reg'].text())
        probe_expect = parse_int_or_hex(editor['probe_expect'].text())
        probe_mask = parse_int_or_hex(editor['probe_mask'].text())

        if probe_addr is not None:
            probe['addr'] = probe_addr
            if t_data['bus_type'] == 'i2c':
                t_data['addr'] = probe_addr
        if probe_type == 'spi_cmd_match' and probe_cmd is not None:
            probe['cmd'] = probe_cmd
        if probe_type == 'i2c_reg_match' and probe_reg is not None:
            probe['reg'] = probe_reg
        if probe_expect is not None:
            probe['expect'] = probe_expect
        if probe_mask is not None:
            probe['mask'] = probe_mask
        if editor['probe_rst'].isChecked():
            probe['rst_before'] = True
        if editor['probe_wait'].value() > 0:
            probe['rst_wait'] = editor['probe_wait'].value()
        if probe_type != 'none' or len(probe) > 1:
            t_data['probe'] = probe

        legacy_identify = {}
        if probe_type == 'i2c_reg_match':
            if probe_reg is not None:
                legacy_identify['reg'] = probe_reg
            if probe_expect is not None:
                legacy_identify['expect'] = probe_expect
            if probe_mask is not None:
                legacy_identify['mask'] = probe_mask
        elif probe_type == 'spi_cmd_match':
            if probe_cmd is not None:
                legacy_identify['cmd'] = probe_cmd
            if probe_expect is not None:
                legacy_identify['expect'] = probe_expect
            if probe_mask is not None:
                legacy_identify['mask'] = probe_mask
        if legacy_identify:
            t_data['identify'] = legacy_identify

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
            t_data['prerequisites'] = prereq_list

        return t_data
