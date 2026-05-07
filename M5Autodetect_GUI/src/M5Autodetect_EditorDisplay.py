"""Display editor manager – builds and serializes display editor widgets."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QGroupBox,
    QGridLayout,
    QFormLayout,
    QLineEdit,
    QCheckBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from PyQt6.QtCore import Qt

from M5Autodetect_Widgets import NoScrollSpinBox, NoScrollComboBox, PinValueEditor
from M5Autodetect_EditorUtils import (
    parse_int_or_hex,
    int_to_hex_str,
    collect_pin_table_values,
    delete_editor_from_list,
    set_combo_items,
    adjust_table_height,
    get_display_probe_options,
    infer_display_probe,
    build_probe_hint,
)
from M5Autodetect_EditorPrereq import PrereqEditorManager


class DisplayEditorManager:
    """Builds display-editor widgets delegated from M5BuilderGUI."""

    def __init__(self, gui):
        self.gui = gui

    # ---- public API ------------------------------------------------

    def add_editor_to_layout(self, parent_layout, display_data, editor_list):
        """Create a full display editor and append its dict to *editor_list*."""
        tr = self.gui.tr
        widget = QGroupBox()
        widget.setStyleSheet(
            "QGroupBox { border: 1px solid #ccc; border-radius: 5px; "
            "margin-top: 10px; padding-top: 10px; } "
            "QGroupBox::title { subcontrol-origin: margin; "
            "subcontrol-position: top left; padding: 0 3px; font-weight: bold; }"
        )
        layout = QVBoxLayout(widget)
        grid_basic = QGridLayout()

        combo_bus = NoScrollComboBox()
        combo_bus.addItems(["spi", "i2c", "parallel8", "parallel16", "rgb", "dsi"])
        current_bus = str(display_data.get("bus_type", "spi"))
        combo_bus.setCurrentText(current_bus)
        grid_basic.addWidget(QLabel(tr("接口类型:")), 0, 0)
        grid_basic.addWidget(combo_bus, 0, 1)

        controller_value = str(
            display_data.get("controller", display_data.get("driver", ""))
        )
        le_controller = QLineEdit(controller_value)
        grid_basic.addWidget(QLabel(tr("控制器/型号:")), 0, 2)
        grid_basic.addWidget(le_controller, 0, 3)

        sb_width = NoScrollSpinBox()
        sb_width.setRange(0, 9999)
        sb_width.setValue(int(display_data.get("width", 0)))
        grid_basic.addWidget(QLabel(tr("宽度:")), 1, 0)
        grid_basic.addWidget(sb_width, 1, 1)

        sb_height = NoScrollSpinBox()
        sb_height.setRange(0, 9999)
        sb_height.setValue(int(display_data.get("height", 0)))
        grid_basic.addWidget(QLabel(tr("高度:")), 1, 2)
        grid_basic.addWidget(sb_height, 1, 3)

        sb_freq = NoScrollSpinBox()
        sb_freq.setRange(0, 100000000)
        sb_freq.setSingleStep(1000000)
        sb_freq.setValue(int(display_data.get("freq", 0)))
        grid_basic.addWidget(QLabel(tr("频率:")), 2, 0)
        grid_basic.addWidget(sb_freq, 2, 1)

        layout.addLayout(grid_basic)

        # ── per-bus config pages ──────────────────────────────────
        container_config = QWidget()
        layout_config = QVBoxLayout(container_config)
        layout_config.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(container_config)

        def create_pin_table(pins_list, data):
            grp = QGroupBox(tr("引脚配置"))
            l = QVBoxLayout(grp)
            t = QTableWidget()
            t.setColumnCount(2)
            t.setHorizontalHeaderLabels([tr("功能"), tr("引脚")])
            t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            t.setRowCount(len(pins_list))
            for i, p in enumerate(pins_list):
                item = QTableWidgetItem(p)
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                t.setItem(i, 0, item)
                t.setCellWidget(i, 1, PinValueEditor(data.get(p)))
            adjust_table_height(t)
            l.addWidget(t)
            return grp, t

        pins_data = display_data.get("pins", {})
        config_pages = {}

        page_spi, table_spi = create_pin_table(
            ["mosi", "miso", "sclk", "cs", "dc", "rst", "bl"], pins_data
        )
        config_pages["spi"] = page_spi
        layout_config.addWidget(page_spi)

        page_i2c = QWidget()
        l_i2c = QVBoxLayout(page_i2c)
        l_i2c.setContentsMargins(0, 0, 0, 0)
        l_i2c_form = QFormLayout()
        le_i2c_addr = QLineEdit(int_to_hex_str(display_data.get("addr")))
        le_i2c_addr.setPlaceholderText("0x3C")
        l_i2c_form.addRow(tr("I2C 地址:"), le_i2c_addr)
        l_i2c.addLayout(l_i2c_form)
        grp_i2c_pins, table_i2c = create_pin_table(
            ["sda", "scl", "rst", "bl"], pins_data
        )
        l_i2c.addWidget(grp_i2c_pins)
        config_pages["i2c"] = page_i2c
        layout_config.addWidget(page_i2c)

        page_p8, table_p8 = create_pin_table(
            [
                "d0",
                "d1",
                "d2",
                "d3",
                "d4",
                "d5",
                "d6",
                "d7",
                "wr",
                "rd",
                "rs",
                "cs",
                "rst",
                "bl",
            ],
            pins_data,
        )
        config_pages["parallel8"] = page_p8
        layout_config.addWidget(page_p8)

        page_p16, table_p16 = create_pin_table(
            [f"d{i}" for i in range(16)] + ["wr", "rd", "rs", "cs", "rst", "bl"],
            pins_data,
        )
        config_pages["parallel16"] = page_p16
        layout_config.addWidget(page_p16)

        page_rgb, table_rgb = create_pin_table(
            [
                "hsync",
                "vsync",
                "de",
                "pclk",
                "d0",
                "d1",
                "d2",
                "d3",
                "d4",
                "d5",
                "d6",
                "d7",
                "d8",
                "d9",
                "d10",
                "d11",
                "d12",
                "d13",
                "d14",
                "d15",
                "disp_en",
                "rst",
                "bl",
            ],
            pins_data,
        )
        config_pages["rgb"] = page_rgb
        layout_config.addWidget(page_rgb)

        # DSI page
        protocol_dsi = (display_data.get("protocol") or {}).get("dsi", {})
        page_dsi = QWidget()
        dsi_layout = QVBoxLayout(page_dsi)
        dsi_layout.setContentsMargins(0, 0, 0, 0)
        dsi_form = QFormLayout()

        sb_dsi_bus_id = NoScrollSpinBox()
        sb_dsi_bus_id.setRange(0, 7)
        sb_dsi_bus_id.setValue(int(protocol_dsi.get("bus_id", 0)))
        dsi_form.addRow(tr("DSI Bus ID:"), sb_dsi_bus_id)

        sb_dsi_lane_num = NoScrollSpinBox()
        sb_dsi_lane_num.setRange(1, 4)
        sb_dsi_lane_num.setValue(int(protocol_dsi.get("lane_num", 2)))
        dsi_form.addRow(tr("Lane 数量:"), sb_dsi_lane_num)

        sb_dsi_lane_mbps = NoScrollSpinBox()
        sb_dsi_lane_mbps.setRange(0, 4000)
        sb_dsi_lane_mbps.setValue(int(protocol_dsi.get("lane_mbps", 1040)))
        dsi_form.addRow(tr("Lane Mbps:"), sb_dsi_lane_mbps)

        sb_dsi_ldo_chan_id = NoScrollSpinBox()
        sb_dsi_ldo_chan_id.setRange(0, 7)
        sb_dsi_ldo_chan_id.setValue(int(protocol_dsi.get("ldo_chan_id", 3)))
        dsi_form.addRow(tr("LDO 通道:"), sb_dsi_ldo_chan_id)

        sb_dsi_ldo_voltage_mv = NoScrollSpinBox()
        sb_dsi_ldo_voltage_mv.setRange(0, 5000)
        sb_dsi_ldo_voltage_mv.setSingleStep(100)
        sb_dsi_ldo_voltage_mv.setValue(int(protocol_dsi.get("ldo_voltage_mv", 2500)))
        dsi_form.addRow(tr("LDO 电压(mV):"), sb_dsi_ldo_voltage_mv)

        dsi_layout.addLayout(dsi_form)
        grp_dsi_pins, table_dsi = create_pin_table(["te", "rst", "bl"], pins_data)
        dsi_layout.addWidget(grp_dsi_pins)
        config_pages["dsi"] = page_dsi
        layout_config.addWidget(page_dsi)

        # ── probe group ───────────────────────────────────────────
        probe_data = infer_display_probe(display_data, current_bus)
        grp_probe = QGroupBox(tr("识别方式 (Probe)"))
        layout_probe = QGridLayout(grp_probe)

        combo_probe = NoScrollComboBox()
        set_combo_items(
            combo_probe,
            get_display_probe_options(tr, current_bus),
            probe_data.get("type", "none"),
        )
        layout_probe.addWidget(QLabel(tr("探测方式:")), 0, 0)
        layout_probe.addWidget(combo_probe, 0, 1, 1, 3)

        lbl_probe_addr = QLabel(tr("探测地址:"))
        le_probe_addr = QLineEdit(int_to_hex_str(probe_data.get("addr")))
        le_probe_addr.setPlaceholderText(tr("留空表示沿用总线地址"))
        layout_probe.addWidget(lbl_probe_addr, 1, 0)
        layout_probe.addWidget(le_probe_addr, 1, 1)

        lbl_probe_cmd = QLabel(tr("命令 (CMD):"))
        le_probe_cmd = QLineEdit(int_to_hex_str(probe_data.get("cmd")))
        le_probe_cmd.setPlaceholderText("0x04")
        layout_probe.addWidget(lbl_probe_cmd, 1, 2)
        layout_probe.addWidget(le_probe_cmd, 1, 3)

        lbl_probe_reg = QLabel(tr("寄存器 (REG):"))
        le_probe_reg = QLineEdit(int_to_hex_str(probe_data.get("reg")))
        le_probe_reg.setPlaceholderText("0x00")
        layout_probe.addWidget(lbl_probe_reg, 2, 0)
        layout_probe.addWidget(le_probe_reg, 2, 1)

        lbl_probe_expect = QLabel(tr("期望值:"))
        le_probe_expect = QLineEdit(int_to_hex_str(probe_data.get("expect")))
        le_probe_expect.setPlaceholderText("0x0000")
        layout_probe.addWidget(lbl_probe_expect, 2, 2)
        layout_probe.addWidget(le_probe_expect, 2, 3)

        lbl_probe_mask = QLabel(tr("掩码:"))
        le_probe_mask = QLineEdit(int_to_hex_str(probe_data.get("mask")))
        le_probe_mask.setPlaceholderText("0xFFFF")
        layout_probe.addWidget(lbl_probe_mask, 3, 0)
        layout_probe.addWidget(le_probe_mask, 3, 1)

        lbl_dsi_read_mode = QLabel(tr("DSI 读取模式:"))
        combo_dsi_read_mode = NoScrollComboBox()
        set_combo_items(
            combo_dsi_read_mode,
            [
                ("auto", tr("自动")),
                ("single_cmd", tr("单命令多字节")),
                ("sequential_cmd", tr("连续命令单字节")),
            ],
            probe_data.get("read_mode", "auto"),
        )
        layout_probe.addWidget(lbl_dsi_read_mode, 4, 0)
        layout_probe.addWidget(combo_dsi_read_mode, 4, 1)

        lbl_dsi_read_len = QLabel(tr("DSI 字节数:"))
        sb_dsi_read_len = NoScrollSpinBox()
        sb_dsi_read_len.setRange(0, 8)
        sb_dsi_read_len.setValue(int(probe_data.get("read_len", 0) or 0))
        layout_probe.addWidget(lbl_dsi_read_len, 4, 2)
        layout_probe.addWidget(sb_dsi_read_len, 4, 3)

        lbl_dsi_read_stride = QLabel(tr("DSI 命令步进:"))
        sb_dsi_read_stride = NoScrollSpinBox()
        sb_dsi_read_stride.setRange(1, 8)
        sb_dsi_read_stride.setValue(int(probe_data.get("read_stride", 1) or 1))
        layout_probe.addWidget(lbl_dsi_read_stride, 5, 0)
        layout_probe.addWidget(sb_dsi_read_stride, 5, 1)

        chk_probe_rst = QCheckBox(tr("探测前复位"))
        chk_probe_rst.setChecked(bool(probe_data.get("rst_before", False)))
        layout_probe.addWidget(chk_probe_rst, 5, 2)

        sb_probe_wait = NoScrollSpinBox()
        sb_probe_wait.setRange(0, 5000)
        sb_probe_wait.setSuffix(" ms")
        sb_probe_wait.setValue(int(probe_data.get("rst_wait", 0)))
        layout_probe.addWidget(sb_probe_wait, 5, 3)

        lbl_probe_hint = QLabel()
        lbl_probe_hint.setWordWrap(True)
        lbl_probe_hint.setStyleSheet("color: #546E7A; padding-top: 4px;")
        layout_probe.addWidget(lbl_probe_hint, 6, 0, 1, 4)

        def update_probe_ui():
            probe_type = combo_probe.currentData() or "none"
            show_addr = probe_type in ("i2c_addr_ack", "i2c_reg_match")
            show_cmd = probe_type in ("spi_cmd_match", "dsi_cmd_match")
            show_reg = probe_type == "i2c_reg_match"
            show_expect = probe_type in (
                "spi_cmd_match",
                "dsi_cmd_match",
                "i2c_reg_match",
            )
            show_mask = show_expect
            show_rst = probe_type in ("spi_cmd_match", "dsi_cmd_match")
            show_dsi_read_fields = probe_type == "dsi_cmd_match"

            for label, field, visible in [
                (lbl_probe_addr, le_probe_addr, show_addr),
                (lbl_probe_cmd, le_probe_cmd, show_cmd),
                (lbl_probe_reg, le_probe_reg, show_reg),
                (lbl_probe_expect, le_probe_expect, show_expect),
                (lbl_probe_mask, le_probe_mask, show_mask),
                (lbl_dsi_read_mode, combo_dsi_read_mode, show_dsi_read_fields),
                (lbl_dsi_read_len, sb_dsi_read_len, show_dsi_read_fields),
                (lbl_dsi_read_stride, sb_dsi_read_stride, show_dsi_read_fields),
            ]:
                label.setVisible(visible)
                field.setVisible(visible)

            chk_probe_rst.setVisible(show_rst)
            sb_probe_wait.setVisible(show_rst)
            lbl_probe_hint.setText(build_probe_hint(tr, "display", probe_type))

        def on_bus_changed(text):
            for bus_name, page in config_pages.items():
                page.setVisible(bus_name == text)
            probe_options = get_display_probe_options(tr, text)
            current_probe = (
                combo_probe.currentData() or combo_probe.currentText() or "none"
            )
            available = [v for v, _ in probe_options]
            if current_probe not in available:
                current_probe = probe_options[0][0]
            set_combo_items(combo_probe, probe_options, current_probe)
            update_probe_ui()

        combo_probe.currentIndexChanged.connect(update_probe_ui)
        update_probe_ui()
        combo_bus.currentTextChanged.connect(on_bus_changed)
        on_bus_changed(current_bus)
        layout.addWidget(grp_probe)

        # ── prerequisites ─────────────────────────────────────────
        prereq_entries = []
        grp_prereq = PrereqEditorManager.create_prerequisites_widget(
            tr, display_data, prereq_entries
        )
        layout.addWidget(grp_prereq)

        # ── delete button ─────────────────────────────────────────
        btn_del = QPushButton(tr("删除此屏幕"))
        btn_del.setStyleSheet("background-color: #FFCDD2; color: #B71C1C;")
        layout.addWidget(btn_del)

        parent_layout.addWidget(widget)

        editor_dict = {
            "widget": widget,
            "bus_type": combo_bus,
            "controller": le_controller,
            "driver": le_controller,
            "width": sb_width,
            "height": sb_height,
            "freq": sb_freq,
            "tables": {
                "spi": table_spi,
                "i2c": table_i2c,
                "parallel8": table_p8,
                "parallel16": table_p16,
                "rgb": table_rgb,
                "dsi": table_dsi,
            },
            "i2c_addr": le_i2c_addr,
            "probe_type": combo_probe,
            "probe_addr": le_probe_addr,
            "probe_cmd": le_probe_cmd,
            "probe_reg": le_probe_reg,
            "probe_expect": le_probe_expect,
            "probe_mask": le_probe_mask,
            "probe_rst": chk_probe_rst,
            "probe_wait": sb_probe_wait,
            "dsi_read_mode": combo_dsi_read_mode,
            "dsi_read_len": sb_dsi_read_len,
            "dsi_read_stride": sb_dsi_read_stride,
            "id_cmd": le_probe_cmd,
            "id_expect": le_probe_expect,
            "id_mask": le_probe_mask,
            "id_rst": chk_probe_rst,
            "id_wait": sb_probe_wait,
            "dsi_bus_id": sb_dsi_bus_id,
            "dsi_lane_num": sb_dsi_lane_num,
            "dsi_lane_mbps": sb_dsi_lane_mbps,
            "dsi_ldo_chan_id": sb_dsi_ldo_chan_id,
            "dsi_ldo_voltage_mv": sb_dsi_ldo_voltage_mv,
            "prereq_entries": prereq_entries,
        }
        editor_list.append(editor_dict)

        btn_del.clicked.connect(
            lambda: delete_editor_from_list(widget, editor_dict, editor_list)
        )

    # ---- serialization --------------------------------------------

    def serialize(self, editor):
        """Collect the current values from a display editor dict → data dict."""
        d_data = {
            "bus_type": editor["bus_type"].currentText(),
            "width": editor["width"].value(),
            "height": editor["height"].value(),
            "freq": editor["freq"].value(),
        }

        controller = editor["controller"].text().strip()
        if controller:
            d_data["controller"] = controller
            d_data["driver"] = controller

        if d_data["bus_type"] == "i2c":
            addr = parse_int_or_hex(editor["i2c_addr"].text())
            if addr is not None:
                d_data["addr"] = addr

        protocol = {}
        if d_data["bus_type"] == "dsi":
            dsi = {
                "bus_id": editor["dsi_bus_id"].value(),
                "lane_num": editor["dsi_lane_num"].value(),
                "lane_mbps": editor["dsi_lane_mbps"].value(),
                "ldo_chan_id": editor["dsi_ldo_chan_id"].value(),
                "ldo_voltage_mv": editor["dsi_ldo_voltage_mv"].value(),
            }
            protocol["dsi"] = dsi
        if protocol:
            d_data["protocol"] = protocol

        d_data["pins"] = collect_pin_table_values(
            editor["tables"].get(d_data["bus_type"])
        )

        probe_type = editor["probe_type"].currentData() or "none"
        probe = {"type": probe_type}
        probe_addr = parse_int_or_hex(editor["probe_addr"].text())
        probe_cmd = parse_int_or_hex(editor["probe_cmd"].text())
        probe_reg = parse_int_or_hex(editor["probe_reg"].text())
        probe_expect = parse_int_or_hex(editor["probe_expect"].text())
        probe_mask = parse_int_or_hex(editor["probe_mask"].text())

        if probe_addr is not None:
            probe["addr"] = probe_addr
        if probe_type in ("spi_cmd_match", "dsi_cmd_match") and probe_cmd is not None:
            probe["cmd"] = probe_cmd
        if probe_type == "i2c_reg_match" and probe_reg is not None:
            probe["reg"] = probe_reg
        if probe_expect is not None:
            probe["expect"] = probe_expect
        if probe_mask is not None:
            probe["mask"] = probe_mask
        if probe_type == "dsi_cmd_match":
            probe["read_mode"] = editor["dsi_read_mode"].currentData() or "auto"
            if editor["dsi_read_len"].value() > 0:
                probe["read_len"] = editor["dsi_read_len"].value()
            if editor["dsi_read_stride"].value() != 1:
                probe["read_stride"] = editor["dsi_read_stride"].value()
        if editor["probe_rst"].isChecked():
            probe["rst_before"] = True
        if editor["probe_wait"].value() > 0:
            probe["rst_wait"] = editor["probe_wait"].value()
        if probe_type != "none" or len(probe) > 1:
            d_data["probe"] = probe

        legacy_identify = {}
        if probe_type in ("spi_cmd_match", "dsi_cmd_match", "i2c_reg_match"):
            if probe_type in ("spi_cmd_match", "dsi_cmd_match") and probe_cmd is not None:
                legacy_identify["cmd"] = probe_cmd
            if probe_type == "i2c_reg_match" and probe_reg is not None:
                legacy_identify["reg"] = probe_reg
            if probe_expect is not None:
                legacy_identify["expect"] = probe_expect
            if probe_mask is not None:
                legacy_identify["mask"] = probe_mask
            if probe_type == "dsi_cmd_match":
                legacy_identify["read_mode"] = (
                    editor["dsi_read_mode"].currentData() or "auto"
                )
                if editor["dsi_read_len"].value() > 0:
                    legacy_identify["read_len"] = editor["dsi_read_len"].value()
                if editor["dsi_read_stride"].value() != 1:
                    legacy_identify["read_stride"] = editor["dsi_read_stride"].value()
            if editor["probe_rst"].isChecked():
                legacy_identify["rst_before"] = True
            if editor["probe_wait"].value() > 0:
                legacy_identify["rst_wait"] = editor["probe_wait"].value()
        if legacy_identify:
            d_data["identify"] = legacy_identify

        if (
            d_data["bus_type"] == "i2c"
            and "addr" not in d_data
            and probe_addr is not None
        ):
            d_data["addr"] = probe_addr

        prereq_list = []
        for pre in editor.get("prereq_entries", []):
            p_type = pre["type"].currentText()
            p_params = pre["get_params"]()
            if p_type or p_params:
                entry = {"type": p_type}
                if isinstance(p_params, dict):
                    entry.update(p_params)
                else:
                    entry["params"] = p_params
                prereq_list.append(entry)
        if prereq_list:
            d_data["prerequisites"] = prereq_list

        return d_data
