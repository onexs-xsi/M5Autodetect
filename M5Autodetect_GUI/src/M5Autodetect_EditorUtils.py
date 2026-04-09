"""Shared utility functions for all editor modules.

All helpers are pure functions (no class state).  Functions that produce
user-visible text accept a *tr* callable so that they remain independent
of QMainWindow.
"""

import copy
import yaml

from PyQt6.QtWidgets import QLineEdit, QComboBox

from M5Autodetect_Widgets import PinValueEditor

# ── constants ──────────────────────────────────────────────────────────
HIGHLIGHT_STYLE = "background-color: #DFF7E0;"


# ── low-level value helpers ────────────────────────────────────────────

def parse_int_or_hex(val_str):
    """Parse a decimal or ``0x`` hex string.  Returns ``int`` or ``None``."""
    if val_str is None:
        return None
    val_str = str(val_str).strip()
    if not val_str:
        return None
    try:
        if val_str.lower().startswith('0x'):
            return int(val_str, 16)
        return int(val_str)
    except ValueError:
        return None


def int_to_hex_str(val):
    """Format *val* as ``0xNN``.  Returns empty string for ``None``."""
    if val is None:
        return ""
    if isinstance(val, int):
        return f"0x{val:X}"
    return str(val)


def normalize_struct(value):
    """Normalize a value for structural comparison."""
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        try:
            return yaml.dump(value, sort_keys=True, allow_unicode=True)
        except Exception:
            return str(value)
    return str(value).strip()


# ── widget helpers ─────────────────────────────────────────────────────

def set_combo_items(combo, options, current_value=None):
    """Populate *combo* with ``(value, label)`` tuples, preserving *current_value*."""
    combo.blockSignals(True)
    combo.clear()
    for value, label in options:
        combo.addItem(label, value)
    index = combo.findData(current_value)
    if index < 0:
        index = 0
    combo.setCurrentIndex(index)
    combo.blockSignals(False)


def register_change_highlight(widget, signal, getter, original_value,
                              style=HIGHLIGHT_STYLE):
    """Connect *signal* so that *widget* gets a highlight when value diverges."""
    if widget is None or signal is None:
        return

    def update_highlight(*_):
        try:
            current = getter()
        except Exception:
            current = None
        widget.setStyleSheet(style if current != original_value else "")

    signal.connect(update_highlight)
    update_highlight()


def adjust_table_height(table_widget):
    """Resize *table_widget* so it shows all rows without internal scrollbar."""
    header_height = table_widget.horizontalHeader().height()
    row_height = table_widget.rowHeight(0) if table_widget.rowCount() > 0 else 30
    total_height = header_height + (row_height * table_widget.rowCount()) + 4
    table_widget.setMinimumHeight(max(100, total_height))
    table_widget.setMaximumHeight(max(100, total_height))


def read_pin_widget_value(widget):
    """Read a value from a *PinValueEditor* or plain *QLineEdit*."""
    if widget is None:
        return None
    if isinstance(widget, PinValueEditor):
        return widget.value()
    if isinstance(widget, QLineEdit):
        text = widget.text().strip()
        if not text:
            return None
        parsed = parse_int_or_hex(text)
        return parsed if parsed is not None else text
    return None


def collect_pin_table_values(table):
    """Collect ``{pin_name: value}`` from a two-column pin table."""
    pins = {}
    if not table:
        return pins
    for row in range(table.rowCount()):
        pin_name_item = table.item(row, 0)
        if pin_name_item is None:
            continue
        pin_name = pin_name_item.text()
        pin_value = read_pin_widget_value(table.cellWidget(row, 1))
        if pin_value is not None:
            pins[pin_name] = pin_value
    return pins


def delete_editor_from_list(widget, editor_dict, editor_list):
    """Remove *widget* from the GUI and *editor_dict* from *editor_list*."""
    widget.deleteLater()
    if editor_dict in editor_list:
        editor_list.remove(editor_dict)


# ── probe helpers ──────────────────────────────────────────────────────

def get_display_probe_options(tr, bus_type):
    """Return ``[(value, label), …]`` for the display probe combo."""
    options = [('none', tr('仅记录，不探测'))]
    if bus_type == 'spi':
        options.append(('spi_cmd_match', tr('SPI 命令匹配')))
    elif bus_type == 'i2c':
        options.extend([
            ('i2c_addr_ack', tr('I2C 地址 ACK')),
            ('i2c_reg_match', tr('I2C 寄存器匹配')),
        ])
    elif bus_type == 'dsi':
        options.append(('dsi_cmd_match', tr('DSI 命令匹配')))
    return options


def get_touch_probe_options(tr, bus_type):
    """Return ``[(value, label), …]`` for the touch probe combo."""
    options = [('none', tr('仅记录，不探测'))]
    if bus_type == 'i2c':
        options.extend([
            ('i2c_addr_ack', tr('I2C 地址 ACK')),
            ('i2c_reg_match', tr('I2C 寄存器匹配')),
        ])
    elif bus_type == 'spi':
        options.append(('spi_cmd_match', tr('SPI 命令匹配')))
    return options


def build_probe_hint(tr, target, probe_type):
    """Return a human-readable hint string for a probe type."""
    hints = {
        'display:spi_cmd_match': tr('当前运行时已支持 SPI 屏幕读 ID。'),
        'display:i2c_addr_ack': tr('仅保存 I2C 地址确认信息，当前运行时未直接用于显示屏判定。'),
        'display:i2c_reg_match': tr('保存 I2C 寄存器匹配条件，适合后续扩展。'),
        'display:dsi_cmd_match': tr('适合 Tab5 这类 DSI 屏，当前运行时尚未接入 DSI 探测。'),
        'display:none': tr('只记录屏幕硬件参数，不参与自动探测。'),
        'touch:i2c_addr_ack': tr('当前运行时仅支持触摸 I2C 地址 ACK 探测。'),
        'touch:i2c_reg_match': tr('保存触摸寄存器匹配条件，当前运行时尚未使用。'),
        'touch:spi_cmd_match': tr('保存 SPI 触摸识别条件，当前运行时尚未使用。'),
        'touch:none': tr('只记录触摸硬件参数，不参与自动探测。'),
    }
    return hints.get(f'{target}:{probe_type}', tr('当前协议暂无专用识别逻辑。'))


def infer_display_probe(display_data, bus_type):
    """Infer a probe dict from legacy *display_data* fields."""
    probe = copy.deepcopy(display_data.get('probe') or {})
    if probe:
        probe.setdefault('type', 'none')
        return probe

    identify = display_data.get('identify') or {}
    if bus_type == 'spi' and identify:
        return {
            'type': 'spi_cmd_match',
            'cmd': identify.get('cmd'),
            'expect': identify.get('expect'),
            'mask': identify.get('mask'),
            'rst_before': identify.get('rst_before', False),
            'rst_wait': identify.get('rst_wait', 0),
        }
    if bus_type == 'dsi' and identify:
        return {
            'type': 'dsi_cmd_match',
            'cmd': identify.get('cmd'),
            'expect': identify.get('expect'),
            'mask': identify.get('mask'),
            'rst_before': identify.get('rst_before', False),
            'rst_wait': identify.get('rst_wait', 0),
        }
    if bus_type == 'i2c':
        addr = display_data.get('addr')
        if addr is not None:
            return {'type': 'i2c_addr_ack', 'addr': addr}
    return {'type': 'none'}


def infer_touch_probe(touch_data, bus_type):
    """Infer a probe dict from legacy *touch_data* fields."""
    probe = copy.deepcopy(touch_data.get('probe') or {})
    if probe:
        probe.setdefault('type', 'none')
        return probe
    if bus_type == 'i2c':
        addr = touch_data.get('addr')
        if addr is not None:
            return {'type': 'i2c_addr_ack', 'addr': addr}
    return {'type': 'none'}
