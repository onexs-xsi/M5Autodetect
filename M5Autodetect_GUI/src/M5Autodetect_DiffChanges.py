"""Change detection / diff dialog manager for the CBuilder GUI."""

import html

from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import Qt

from M5Autodetect_EditorUtils import normalize_struct


class DiffChangesManager:
    """Collects, formats and shows change-detection diffs."""

    def __init__(self, gui):
        self.gui = gui

    # ================================================================
    #  Per-device change collection
    # ================================================================

    def collect_device_changes(self, old_data, new_data):
        tr = self.gui.tr
        if not isinstance(old_data, dict):
            old_data = {}
        if not isinstance(new_data, dict):
            new_data = {}
        change_lines = []

        field_labels = {
            'name': tr('名称'),
            'description': tr('描述'),
            'sku': 'SKU',
            'eol': tr('EOL 状态'),
            'image': tr('图片链接'),
            'docs': tr('文档链接'),
            'mcu': 'MCU',
        }
        empty_placeholder = tr('[空]')

        for key, label in field_labels.items():
            old_val = str(old_data.get(key) or '').strip()
            new_val = str(new_data.get(key) or '').strip()
            if old_val != new_val:
                change_lines.append(
                    tr("{label}: {old} → {new}").format(
                        label=label,
                        old=old_val or empty_placeholder,
                        new=new_val or empty_placeholder,
                    )
                )

        old_psram = bool(old_data.get('psram_enabled', False))
        new_psram = bool(new_data.get('psram_enabled', False))
        if old_psram != new_psram:
            old_text = tr("启用") if old_psram else tr("禁用")
            new_text = tr("启用") if new_psram else tr("禁用")
            change_lines.append(
                tr("{label}: {old} → {new}").format(
                    label=tr("PSRAM 启用"), old=old_text, new=new_text
                )
            )

        self._check_pins_changes(old_data, new_data, change_lines)
        self._check_i2c_changes(old_data, new_data, change_lines)
        self._check_display_changes(old_data, new_data, change_lines)
        self._check_touch_changes(old_data, new_data, change_lines)
        self._check_variants_changes(old_data, new_data, change_lines)
        self._check_additional_tests_changes(old_data, new_data, change_lines)

        return change_lines

    # ── sub-checks ────────────────────────────────────────────────

    def _check_additional_tests_changes(self, old_data, new_data, change_lines):
        tr = self.gui.tr
        old_tests = old_data.get('additional_tests', [])
        new_tests = new_data.get('additional_tests', [])
        if normalize_struct(old_tests) != normalize_struct(new_tests):
            if isinstance(new_tests, list) and isinstance(old_tests, list):
                change_lines.append(
                    tr("额外测试数量: {old} → {new}").format(old=len(old_tests), new=len(new_tests))
                )
            else:
                change_lines.append(tr("额外测试配置已更新"))

    def _check_identify_i2c_changes(self, old_data, new_data, change_lines):
        tr = self.gui.tr
        old_val = old_data.get('identify_i2c', [])
        new_val = new_data.get('identify_i2c', [])
        if normalize_struct(old_val) != normalize_struct(new_val):
            change_lines.append(tr("identify_i2c 配置已更新"))

    def _check_tests_changes(self, old_data, new_data, change_lines):
        tr = self.gui.tr
        old_tests = old_data.get('tests', [])
        new_tests = new_data.get('tests', [])
        if normalize_struct(old_tests) != normalize_struct(new_tests):
            if isinstance(new_tests, list) and isinstance(old_tests, list):
                change_lines.append(
                    tr("测试项数量: {old} → {new}").format(old=len(old_tests), new=len(new_tests))
                )
            else:
                change_lines.append(tr("测试项配置已更新"))

    def _check_variants_changes(self, old_data, new_data, change_lines):
        tr = self.gui.tr
        old_val = old_data.get('variants', [])
        new_val = new_data.get('variants', [])
        if normalize_struct(old_val) != normalize_struct(new_val):
            change_lines.append(
                tr("变体配置已更新: {old} → {new}").format(old=len(old_val), new=len(new_val))
            )

    def _check_pins_changes(self, old_data, new_data, change_lines):
        tr = self.gui.tr
        old_pins = old_data.get('check_pins', {})
        new_pins = new_data.get('check_pins', {})

        old_count = old_data.get('check_pins_count')
        new_count = new_data.get('check_pins_count')
        if old_count != new_count:
            change_lines.append(
                tr("检测引脚通过数量: {old} → {new}").format(old=old_count, new=new_count)
            )

        if not isinstance(old_pins, dict):
            old_pins = {}
        if not isinstance(new_pins, dict):
            new_pins = {}

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

        def sort_key(k):
            if isinstance(k, int):
                return k
            if isinstance(k, str) and k.isdigit():
                return int(k)
            return 0

        for key in sorted(list(all_keys), key=sort_key):
            old_pin = old_pins_norm.get(key)
            new_pin = new_pins_norm.get(key)

            if old_pin is not None and new_pin is not None:
                old_mode = old_pin.get('mode', 'input')
                old_expect = old_pin.get('expect', 0)
                new_mode = new_pin.get('mode', 'input')
                new_expect = new_pin.get('expect', 0)
                if old_mode != new_mode or old_expect != new_expect:
                    change_lines.append(
                        tr("检测引脚: GPIO{gpio}({old_mode}={old_expect}) → GPIO{gpio}({new_mode}={new_expect})").format(
                            gpio=key, old_mode=old_mode, old_expect=old_expect,
                            new_mode=new_mode, new_expect=new_expect,
                        )
                    )
            elif old_pin is not None:
                old_mode = old_pin.get('mode', 'input')
                old_expect = old_pin.get('expect', 0)
                change_lines.append(
                    tr("检测引脚: GPIO{gpio}({mode}={expect}) → [已删除]").format(
                        gpio=key, mode=old_mode, expect=old_expect
                    )
                )
            else:
                new_mode = new_pin.get('mode', 'input')
                new_expect = new_pin.get('expect', 0)
                change_lines.append(
                    tr("检测引脚: [新增] → GPIO{gpio}({mode}={expect})").format(
                        gpio=key, mode=new_mode, expect=new_expect
                    )
                )

    def _check_i2c_changes(self, old_data, new_data, change_lines):
        tr = self.gui.tr
        old_i2c_list = old_data.get('i2c_internal', [])
        new_i2c_list = new_data.get('i2c_internal', [])
        if not isinstance(old_i2c_list, list):
            old_i2c_list = []
        if not isinstance(new_i2c_list, list):
            new_i2c_list = []

        def map_by_port(i2c_list):
            mapping = {}
            for item in i2c_list:
                if isinstance(item, dict):
                    port = item.get('port', 0)
                    mapping[port] = item
            return mapping

        old_map = map_by_port(old_i2c_list)
        new_map = map_by_port(new_i2c_list)

        for port in sorted(set(old_map.keys()) | set(new_map.keys())):
            old_bus = old_map.get(port)
            new_bus = new_map.get(port)

            if old_bus and new_bus:
                changes = []
                if old_bus.get('sda') != new_bus.get('sda'):
                    changes.append(tr("SDA: {old}→{new}").format(old=old_bus.get('sda'), new=new_bus.get('sda')))
                if old_bus.get('scl') != new_bus.get('scl'):
                    changes.append(tr("SCL: {old}→{new}").format(old=old_bus.get('scl'), new=new_bus.get('scl')))
                if old_bus.get('freq') != new_bus.get('freq'):
                    changes.append(tr("频率: {old}→{new}").format(old=old_bus.get('freq'), new=new_bus.get('freq')))
                if old_bus.get('internal_pullup', False) != new_bus.get('internal_pullup', False):
                    changes.append(
                        tr("内部上拉: {old}→{new}").format(
                            old=tr("是") if old_bus.get('internal_pullup', False) else tr("否"),
                            new=tr("是") if new_bus.get('internal_pullup', False) else tr("否"),
                        )
                    )
                if changes:
                    change_lines.append(
                        tr("内部 I2C Port{port}: {changes}").format(port=port, changes=", ".join(changes))
                    )

                old_detect_count = old_bus.get('detect_count')
                new_detect_count = new_bus.get('detect_count')
                if old_detect_count != new_detect_count:
                    change_lines.append(
                        tr("内部 I2C Port{port} 检测通过数量: {old} → {new}").format(
                            port=port, old=old_detect_count, new=new_detect_count
                        )
                    )

                def map_detects(detect_list):
                    d_map = {}
                    for d in detect_list:
                        if isinstance(d, dict):
                            addr = d.get('addr')
                            if addr is not None:
                                d_map[addr] = d
                    return d_map

                old_d_map = map_detects(old_bus.get('detect', []))
                new_d_map = map_detects(new_bus.get('detect', []))

                for addr in sorted(set(old_d_map.keys()) | set(new_d_map.keys())):
                    old_d = old_d_map.get(addr)
                    new_d = new_d_map.get(addr)
                    addr_hex = f"0x{addr:02X}"

                    if old_d and new_d:
                        if old_d.get('name') != new_d.get('name'):
                            change_lines.append(
                                tr("内部 I2C Port{port} 设备 {addr}: 名称 '{old}' → '{new}'").format(
                                    port=port, addr=addr_hex,
                                    old=old_d.get('name'), new=new_d.get('name'),
                                )
                            )
                    elif old_d:
                        change_lines.append(
                            tr("内部 I2C Port{port} 设备: [删除] {addr} ({name})").format(
                                port=port, addr=addr_hex, name=old_d.get('name')
                            )
                        )
                    else:
                        change_lines.append(
                            tr("内部 I2C Port{port} 设备: [新增] {addr} ({name})").format(
                                port=port, addr=addr_hex, name=new_d.get('name')
                            )
                        )
            elif old_bus:
                change_lines.append(tr("内部 I2C Port{port}: [已删除]").format(port=port))
            else:
                change_lines.append(
                    tr("内部 I2C Port{port}: [新增] (SDA:{sda} SCL:{scl})").format(
                        port=port, sda=new_bus.get('sda'), scl=new_bus.get('scl')
                    )
                )

    def _check_display_changes(self, old_data, new_data, change_lines):
        tr = self.gui.tr
        old_display = old_data.get('display', [])
        new_display = new_data.get('display', [])
        if normalize_struct(old_display) != normalize_struct(new_display):
            if isinstance(new_display, list) and isinstance(old_display, list):
                change_lines.append(
                    tr("显示屏配置项数量: {old} → {new}").format(old=len(old_display), new=len(new_display))
                )
            else:
                change_lines.append(tr("显示屏配置已更新"))

    def _check_touch_changes(self, old_data, new_data, change_lines):
        tr = self.gui.tr
        old_touch = old_data.get('touch', [])
        new_touch = new_data.get('touch', [])
        if normalize_struct(old_touch) != normalize_struct(new_touch):
            if isinstance(new_touch, list) and isinstance(old_touch, list):
                change_lines.append(
                    tr("触摸配置项数量: {old} → {new}").format(old=len(old_touch), new=len(new_touch))
                )
            else:
                change_lines.append(tr("触摸配置已更新"))

    # ================================================================
    #  HTML builders & dialog helpers
    # ================================================================

    def build_changes_html(self, change_lines):
        if not change_lines:
            return ""
        tr = self.gui.tr
        rows = []
        for line in change_lines:
            rows.append(
                f"<li><span style='background-color:#FFCDD2;padding:4px 8px;"
                f"border-radius:6px;display:block;margin-bottom:6px;'>"
                f"{html.escape(line)}</span></li>"
            )
        header_html = tr("<p>以下字段将被保存：</p>")
        return header_html + "<ul>" + "".join(rows) + "</ul>"

    def show_change_dialog(self, title, body_html):
        if not body_html:
            return True
        box = QMessageBox(self.gui)
        box.setWindowTitle(title)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setTextFormat(Qt.TextFormat.RichText)
        box.setText(body_html)
        box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        box.setDefaultButton(QMessageBox.StandardButton.Ok)
        return box.exec() == QMessageBox.StandardButton.Ok

    def collect_all_changes(self, candidate_data=None):
        tr = self.gui.tr
        target_data = candidate_data or self.gui.current_yaml_data
        if not target_data:
            return {}

        base_source = self.gui.base_yaml_data or {}
        base_categories = base_source.get('mcu_categories', [])
        current_categories = (
            target_data.get('mcu_categories', []) if isinstance(target_data, dict) else []
        )
        summary = {}

        base_map = {
            cat.get('mcu'): cat
            for cat in base_categories
            if isinstance(cat, dict) and cat.get('mcu')
        }

        for current_cat in current_categories:
            if not isinstance(current_cat, dict):
                continue
            mcu_name = current_cat.get('mcu') or tr('Unknown MCU')
            base_cat = base_map.get(mcu_name, {})
            base_devices = base_cat.get('devices', []) if isinstance(base_cat, dict) else []
            current_devices = current_cat.get('devices', [])
            if not isinstance(current_devices, list):
                current_devices = []

            base_dev_map = {
                dev.get('name'): dev
                for dev in base_devices
                if isinstance(dev, dict) and dev.get('name')
            }

            for current_dev in current_devices:
                if not isinstance(current_dev, dict):
                    continue
                dev_key = current_dev.get('name')
                dev_name = dev_key or tr('Unknown Device')
                base_dev = base_dev_map.get(dev_key)
                changes = self.collect_device_changes(base_dev or {}, current_dev)
                if changes:
                    summary.setdefault(mcu_name, {})[dev_name] = changes

        return summary

    def build_grouped_changes_html(self, summary):
        if not summary:
            return ""
        tr = self.gui.tr
        sections = []
        for mcu, devices in summary.items():
            device_rows = []
            for device_name, changes in devices.items():
                change_list = ''.join(
                    f"<li><span style='background-color:#FFCDD2;padding:3px 6px;"
                    f"border-radius:4px;display:block;margin-bottom:4px;'>"
                    f"{html.escape(c)}</span></li>"
                    for c in changes
                )
                device_rows.append(
                    f"<div style='margin-bottom:10px;'><strong>{html.escape(device_name)}</strong>"
                    f"<ul style='margin-top:4px;'>{change_list}</ul></div>"
                )
            sections.append(
                f"<div style='margin-bottom:14px;'><h4 style='margin-bottom:6px;'>"
                f"{html.escape(mcu)}</h4>{''.join(device_rows)}</div>"
            )
        header_html = tr("<p>以下设备将被修改：</p>")
        return header_html + "".join(sections)

    # ================================================================
    #  Convenience confirm methods
    # ================================================================

    def confirm_device_changes(self, old_data, new_data):
        tr = self.gui.tr
        change_lines = self.collect_device_changes(old_data, new_data)
        if not change_lines:
            QMessageBox.information(self.gui, tr("无变更"), tr("当前没有任何修改，无需保存。"))
            return False
        body_html = self.build_changes_html(change_lines)
        return self.show_change_dialog(tr("保存前确认"), body_html)

    def confirm_full_yaml_changes(self, candidate_data=None):
        tr = self.gui.tr
        summary = self.collect_all_changes(candidate_data)
        base_snapshot = self.gui.base_yaml_data or {}
        candidate_snapshot = candidate_data or {}
        if not summary and base_snapshot != candidate_snapshot:
            summary = {
                tr('整体'): {tr('YAML 配置'): [tr('整体结构发生变化')]}
            }
        if not summary:
            QMessageBox.information(self.gui, tr("无变更"), tr("当前 YAML 没有任何改动。"))
            return False
        html_body = self.build_grouped_changes_html(summary)
        return self.show_change_dialog(tr("写入 YAML 前确认"), html_body)
