import os
import yaml
import sys


class M5HeaderGenerator:
    # Test type mapping
    TEST_TYPE_MAP = {
        "gpio": 0,
        "i2c": 1,
        "spi": 2,
        0: 0,
        1: 1,
        2: 2,
    }

    # Bus type mapping for display
    BUS_TYPE_MAP = {
        "spi": 0,
        "i2c": 1,
        "parallel8": 2,
        "parallel16": 3,
        "rgb": 4,
        "dsi": 5,
    }

    DSI_IDENTIFY_MODE_MAP = {
        "auto": 0,
        "single_cmd": 1,
        "sequential_cmd": 2,
        0: 0,
        1: 1,
        2: 2,
    }

    @staticmethod
    def _make_safe_name(base_name, suffix=""):
        """Create a safe C++ identifier from device name and optional suffix"""
        safe_name = (
            base_name.replace(" ", "_")
            .replace("-", "_")
            .replace(".", "_")
            .replace("(", "")
            .replace(")", "")
        )
        if suffix:
            safe_suffix = (
                suffix.replace(" ", "_")
                .replace("-", "_")
                .replace(".", "_")
                .replace("(", "")
                .replace(")", "")
            )
            safe_name += "_" + safe_suffix
        return safe_name

    @staticmethod
    def _compose_board_name(base_name, suffix=""):
        base = str(base_name or "Unknown")
        suffix = str(suffix or "").strip()
        return f"{base}_{suffix}" if suffix else base

    @staticmethod
    def _get_test_type(val):
        """Convert test type to integer"""
        if isinstance(val, str):
            return M5HeaderGenerator.TEST_TYPE_MAP.get(val.lower(), 0)
        return M5HeaderGenerator.TEST_TYPE_MAP.get(val, 0)

    @staticmethod
    def _get_bus_type(val):
        """Convert bus type to integer"""
        if isinstance(val, str):
            return M5HeaderGenerator.BUS_TYPE_MAP.get(val.lower(), 0)
        return 0

    @staticmethod
    def _get_dsi_identify_mode(val):
        """Convert DSI identify mode to integer enum value."""
        if isinstance(val, str):
            return M5HeaderGenerator.DSI_IDENTIFY_MODE_MAP.get(val.lower(), 0)
        return M5HeaderGenerator.DSI_IDENTIFY_MODE_MAP.get(val, 0)

    @staticmethod
    def _get_identify_config(item, supported_probe_types):
        """Return legacy identify fields, falling back to matching probe data."""
        identify = item.get("identify") or {}
        probe = item.get("probe") or {}

        if isinstance(probe, dict) and probe.get("type") in supported_probe_types:
            merged = dict(probe)
            if isinstance(identify, dict):
                merged.update(identify)
            return merged

        return identify if isinstance(identify, dict) else {}

    @staticmethod
    def _get_prereq_type(val):
        """Convert prereq type to enum string"""
        val = str(val).lower()
        if val == "gpio":
            return "PrereqType::GPIO_WRITE"
        if val == "i2c_read":
            return "PrereqType::I2C_READ"
        if val == "i2c_write":
            return "PrereqType::I2C_WRITE"
        if val == "spi_read":
            return "PrereqType::SPI_READ"
        if val == "spi_write":
            return "PrereqType::SPI_WRITE"
        if val == "dsi_write":
            return "PrereqType::DSI_WRITE"
        if val == "dsi_read":
            return "PrereqType::DSI_READ"
        return "PrereqType::NONE"

    @staticmethod
    def _generate_data_initializer(data_val):
        """Generate C++ initializer for std::vector<uint8_t> data field."""
        if isinstance(data_val, list):
            items = ", ".join(
                f"0x{M5HeaderGenerator._parse_int(b):02X}" for b in data_val
            )
            return "{" + items + "}"
        v = M5HeaderGenerator._parse_int(data_val)
        return "{" + f"0x{v:02X}" + "}"

    @staticmethod
    def _generate_prerequisites(prereq_list):
        """Generate C++ code for prerequisites vector"""
        if not prereq_list:
            return "{}"

        lines = []
        lines.append("{")
        for p in prereq_list:
            p_type = M5HeaderGenerator._get_prereq_type(p.get("type", ""))
            gpio = M5HeaderGenerator._parse_int(p.get("gpio", -1))
            level = M5HeaderGenerator._parse_int(p.get("level", 0))
            addr = M5HeaderGenerator._parse_int(p.get("addr", 0))
            reg = M5HeaderGenerator._parse_int(p.get("reg", 0))
            cmd = M5HeaderGenerator._parse_int(p.get("cmd", 0))
            data_init = M5HeaderGenerator._generate_data_initializer(p.get("data", 0))
            length = M5HeaderGenerator._parse_int(p.get("len", 0))
            delay_ms = M5HeaderGenerator._parse_int(p.get("delay_ms", 0))

            lines.append(
                f"            {{ {p_type}, {gpio}, {level}, 0x{addr:02X}, 0x{reg:02X}, 0x{cmd:02X}, {data_init}, {length}, {delay_ms} }},"
            )
        lines.append("        }")
        return "\n".join(lines)

    @staticmethod
    def generate_header(data):
        mcu_categories = data.get("mcu_categories", [])

        content = []
        content.append("#ifndef M5_AUTODETECT_DATA_H")
        content.append("#define M5_AUTODETECT_DATA_H")
        content.append("")
        content.append("#include <stdint.h>")
        content.append("#include <vector>")
        content.append("")

        # Define structs
        content.append("namespace m5 {")
        content.append("namespace autodetect {")
        content.append("")

        # Generate Enum and Helper Function
        content.append("enum board_t {")
        content.append("    board_unknown = -1,")

        all_devices = []
        for category in mcu_categories:
            devices = category.get("devices", [])
            for dev in devices:
                base_name = dev.get("name", "Unknown")
                variants = dev.get("variants", [])

                if not variants:
                    variants = [{"name": ""}]

                for variant in variants:
                    suffix = variant.get("name", "")
                    safe_name = M5HeaderGenerator._make_safe_name(base_name, suffix)

                    all_devices.append(safe_name)
                    content.append(f"    board_{safe_name},")

        content.append("};")
        content.append("")

        content.append("inline const char* getBoardName(board_t board) {")
        content.append("    switch (board) {")
        for safe_name in all_devices:
            content.append(f'        case board_{safe_name}: return "{safe_name}";')
        content.append('        default: return "Unknown";')
        content.append("    }")
        content.append("}")
        content.append("")

        content.append("struct PinCheck {")
        content.append("    int gpio;")
        content.append("    int mode; // 0: input, 1: input_pullup, 2: input_pulldown")
        content.append("    int expect; // 0 or 1")
        content.append("};")
        content.append("")

        content.append("enum class PrereqType {")
        content.append("    NONE = 0,")
        content.append("    GPIO_WRITE = 1,")
        content.append("    I2C_READ = 2,")
        content.append("    I2C_WRITE = 3,")
        content.append("    SPI_READ = 4,")
        content.append("    SPI_WRITE = 5,")
        content.append("    DSI_WRITE = 6,")
        content.append("    DSI_READ = 7")
        content.append("};")
        content.append("")

        content.append("struct Prerequisite {")
        content.append("    PrereqType type;")
        content.append("    int gpio;")
        content.append("    int level;")
        content.append("    uint8_t addr;")
        content.append("    uint8_t reg;")
        content.append("    uint8_t cmd;")
        content.append("    std::vector<uint8_t> data;")
        content.append("    int len;")
        content.append("    int delay_ms = 0;")
        content.append("};")
        content.append("")

        content.append("struct I2CDetect {")
        content.append("    uint8_t addr;")
        content.append(
            "    bool required;  // true = must ACK; false = optional (absence is not a failure)"
        )
        content.append("};")
        content.append("")

        content.append("struct I2CBusCheck {")
        content.append("    int port;")
        content.append("    int sda;")
        content.append("    int scl;")
        content.append("    uint32_t freq;")
        content.append("    int detect_count;")
        content.append("    bool internal_pullup;")
        content.append("    std::vector<I2CDetect> detect;")
        content.append("    std::vector<Prerequisite> prerequisites;")
        content.append("};")
        content.append("")

        content.append("struct I2CIdentify {")
        content.append("    int port;")
        content.append("    int sda;")
        content.append("    int scl;")
        content.append("    uint32_t freq;")
        content.append("    uint8_t addr;")
        content.append("};")
        content.append("")

        content.append("enum class DisplayBusType {")
        content.append("    BUS_SPI = 0,")
        content.append("    BUS_I2C = 1,")
        content.append("    BUS_PARALLEL8 = 2,")
        content.append("    BUS_PARALLEL16 = 3,")
        content.append("    BUS_RGB = 4,")
        content.append("    BUS_DSI = 5,")
        content.append("};")
        content.append("")

        content.append("enum class DSIIdentifyReadMode {")
        content.append("    AUTO = 0,")
        content.append("    SINGLE_CMD = 1,")
        content.append("    SEQUENTIAL_CMD = 2,")
        content.append("};")
        content.append("")

        content.append("struct DisplayConfig {")
        content.append("    const char* driver;")
        content.append("    int bus_type;")
        content.append("    int width;")
        content.append("    int height;")
        content.append("    int freq;")
        content.append("    int pin_mosi;  // or sda for I2C, d0 for parallel")
        content.append("    int pin_miso;  // or scl for I2C, d1 for parallel")
        content.append("    int pin_sclk;  // or wr for parallel")
        content.append("    int pin_cs;")
        content.append("    int pin_dc;    // or rs for parallel")
        content.append("    int pin_rst;")
        content.append("    int pin_bl;")
        content.append("    uint8_t i2c_addr;")
        content.append("    const char* pin_rst_str;")
        content.append("    const char* pin_bl_str;")
        content.append("    int identify_cmd;")
        content.append("    int identify_expect;")
        content.append("    int identify_mask;")
        content.append("    bool identify_rst_before;")
        content.append("    int identify_rst_wait;")
        content.append(
            "    // DSI protocol fields (only used when bus_type == BUS_DSI)"
        )
        content.append("    int dsi_bus_id;")
        content.append("    int dsi_lane_num;")
        content.append("    int dsi_lane_mbps;")
        content.append("    int dsi_ldo_chan_id;")
        content.append("    int dsi_ldo_voltage_mv;")
        content.append("    DSIIdentifyReadMode dsi_identify_read_mode;")
        content.append("    int dsi_identify_read_len;")
        content.append("    int dsi_identify_read_stride;")
        content.append("    std::vector<Prerequisite> prerequisites;")
        content.append("};")
        content.append("")

        content.append("struct TouchConfig {")
        content.append("    const char* driver;")
        content.append("    int bus_type;")
        content.append("    int addr;")
        content.append("    int width;")
        content.append("    int height;")
        content.append("    int freq;")
        content.append("    int pin_sda;")
        content.append("    int pin_scl;")
        content.append("    int pin_int;")
        content.append("    int pin_rst;")
        content.append("    const char* pin_rst_str;")
        content.append("    int pin_mosi;")
        content.append("    int pin_miso;")
        content.append("    int pin_sclk;")
        content.append("    int pin_cs;")
        content.append("    std::vector<Prerequisite> prerequisites;")
        content.append("    int identify_reg;  // I2C register or SPI command")
        content.append("    int identify_expect;")
        content.append("    int identify_mask;")
        content.append("};")

        content.append("enum TestType {")
        content.append("    TEST_GPIO_READ = 0,")
        content.append("    TEST_I2C_READ_REG = 1,")
        content.append("    TEST_SPI_READ_CMD = 2,")
        content.append("};")
        content.append("")

        content.append("struct AdHocTest {")
        content.append("    int type;")
        content.append("    int32_t score;")
        content.append("    int port;")
        content.append("    int pin_a;")
        content.append("    int pin_b;")
        content.append("    int pin_c;")
        content.append("    int pin_d;")
        content.append("    uint32_t freq;")
        content.append("    uint32_t addr;")
        content.append("    uint32_t reg;")
        content.append("    uint32_t mask;")
        content.append("    uint32_t expect;")
        content.append("};")
        content.append("")

        content.append("struct DeviceInfo {")
        content.append("    const char* name;")
        content.append("    const char* sku;")
        content.append("    const char* mcu;")
        content.append("    board_t board_id;")
        content.append("    bool psram_enabled;")
        content.append("    int check_pins_count;")
        content.append("    const std::vector<PinCheck> check_pins;")
        content.append("    const std::vector<I2CBusCheck> i2c_checks;")
        content.append("    const std::vector<I2CIdentify> identify_i2c;")
        content.append("    const std::vector<DisplayConfig> displays;")
        content.append("    const std::vector<TouchConfig> touches;")
        content.append("    const std::vector<AdHocTest> additional_tests;")
        content.append("};")
        content.append("")

        content.append("extern const std::vector<DeviceInfo> devices_data;")
        content.append("")
        content.append("} // namespace autodetect")
        content.append("} // namespace m5")
        content.append("")
        content.append("#endif // M5_AUTODETECT_DATA_H")

        return "\n".join(content)

    @staticmethod
    def _parse_int(val):
        if isinstance(val, int):
            return val
        if isinstance(val, str):
            val = val.strip()
            if val.lower().startswith("0x"):
                return int(val, 16)
            try:
                return int(val)
            except ValueError:
                return 0
        return 0

    @staticmethod
    def generate_source(data):
        mcu_categories = data.get("mcu_categories", [])

        content = []
        content.append('#include "M5Autodetect_DeviceData.h"')
        content.append("")
        content.append("namespace m5 {")
        content.append("namespace autodetect {")
        content.append("")

        # Generate data
        content.append("const std::vector<DeviceInfo> devices_data = {")

        for category in mcu_categories:
            mcu = category.get("mcu", "Unknown")
            devices = category.get("devices", [])

            for dev in devices:
                base_name = dev.get("name", "Unknown")
                variants = dev.get("variants", [])
                base_identify_i2c = dev.get("identify_i2c", [])
                if not isinstance(base_identify_i2c, list):
                    base_identify_i2c = []

                base_additional_tests = dev.get("additional_tests", [])
                if not isinstance(base_additional_tests, list):
                    base_additional_tests = []

                base_psram = bool(dev.get("psram_enabled", False))

                # If no variants, treat as single device
                if not variants:
                    variants = [
                        {
                            "name": "",
                            "display": dev.get("display", []),
                            "touch": dev.get("touch", []),
                            "identify_i2c": base_identify_i2c,
                            "additional_tests": base_additional_tests,
                        }
                    ]

                for variant in variants:
                    suffix = variant.get("name", "")
                    name = M5HeaderGenerator._compose_board_name(base_name, suffix)

                    sku = dev.get("sku", "Unknown")

                    safe_name = M5HeaderGenerator._make_safe_name(base_name, suffix)

                    # Helper function: variant value takes priority, but if variant value is empty, use base value
                    def get_with_fallback(variant_val, base_val, empty_check=None):
                        """
                        Variant value takes priority over base value.
                        If variant value is None or empty (based on empty_check), use base value.
                        """
                        if variant_val is None:
                            return base_val
                        if empty_check is not None and empty_check(variant_val):
                            return base_val
                        return variant_val

                    def is_empty_list(val):
                        return isinstance(val, list) and len(val) == 0

                    def is_empty_dict(val):
                        return isinstance(val, dict) and len(val) == 0

                    def is_empty_list_or_dict(val):
                        return is_empty_list(val) or is_empty_dict(val)

                    # Check pins - variant can override, empty falls back to base
                    base_pins = dev.get("check_pins", {})
                    variant_pins = variant.get("check_pins")
                    pins = get_with_fallback(
                        variant_pins, base_pins, is_empty_list_or_dict
                    )

                    # Calculate default check_pins_count
                    pin_count = 0
                    if isinstance(pins, list):
                        pin_count = len(pins)
                    elif isinstance(pins, dict):
                        pin_count = len(pins)

                    # Check pins count - variant can override
                    base_pins_count = dev.get("check_pins_count", pin_count)
                    variant_pins_count = variant.get("check_pins_count")
                    if variant_pins_count is not None:
                        check_pins_count = variant_pins_count
                    else:
                        # Recalculate if pins were overridden
                        if variant_pins is not None and not is_empty_list_or_dict(
                            variant_pins
                        ):
                            check_pins_count = pin_count
                        else:
                            check_pins_count = base_pins_count

                    # I2C Internal - variant can override, empty falls back to base
                    base_i2c_internal = dev.get("i2c_internal", [])
                    variant_i2c = variant.get("i2c_internal")
                    i2c_internal = get_with_fallback(
                        variant_i2c, base_i2c_internal, is_empty_list
                    )

                    # Displays - variant can override, empty falls back to base
                    base_displays = dev.get("display", [])
                    variant_display = variant.get("display")
                    displays = get_with_fallback(
                        variant_display, base_displays, is_empty_list
                    )

                    # Touches - variant can override, empty falls back to base
                    base_touches = dev.get("touch", [])
                    variant_touch = variant.get("touch")
                    touches = get_with_fallback(
                        variant_touch, base_touches, is_empty_list
                    )

                    # Identify I2C - variant can override, empty falls back to base
                    variant_identify = variant.get("identify_i2c")
                    identify_i2c = get_with_fallback(
                        variant_identify, base_identify_i2c, is_empty_list
                    )

                    # Additional Tests - variant can override, empty falls back to base
                    variant_tests = variant.get("additional_tests")
                    additional_tests = get_with_fallback(
                        variant_tests, base_additional_tests, is_empty_list
                    )

                    # PSRAM - variant can override (None falls back to base)
                    variant_psram = variant.get("psram_enabled")
                    psram_enabled = (
                        variant_psram if variant_psram is not None else base_psram
                    )

                    content.append("    {")
                    content.append(f'        "{name}",')
                    content.append(f'        "{sku}",')
                    content.append(f'        "{mcu}",')
                    content.append(f"        board_{safe_name},")
                    content.append(f"        {'true' if psram_enabled else 'false'},")
                    content.append(f"        {check_pins_count},")
                    content.append("        {")

                    if isinstance(pins, list):
                        for pin in pins:
                            gpio = pin.get("gpio", -1)
                            mode_str = pin.get("mode", "input")
                            mode = 0
                            if mode_str == "input_pullup":
                                mode = 1
                            elif mode_str == "input_pulldown":
                                mode = 2

                            expect = pin.get("expect", 0)
                            content.append(
                                f"            {{ {gpio}, {mode}, {expect} }},"
                            )
                    elif isinstance(pins, dict):
                        for gpio, pin in pins.items():
                            mode_str = pin.get("mode", "input")
                            mode = 0
                            if mode_str == "input_pullup":
                                mode = 1
                            elif mode_str == "input_pulldown":
                                mode = 2

                            expect = pin.get("expect", 0)
                            content.append(
                                f"            {{ {gpio}, {mode}, {expect} }},"
                            )

                    content.append("        },")

                    content.append("        {")
                    for i2c in i2c_internal:
                        port = i2c.get("port", 0)
                        sda = i2c.get("sda", -1)
                        scl = i2c.get("scl", -1)
                        freq = i2c.get("freq", 400000)
                        detect = i2c.get("detect", [])
                        required_count = sum(
                            1 for d in detect if d.get("required", True)
                        )
                        detect_count = i2c.get("detect_count", required_count)
                        internal_pullup = (
                            "true" if i2c.get("internal_pullup", False) else "false"
                        )
                        prereqs = i2c.get("prerequisites", [])
                        prereq_str = M5HeaderGenerator._generate_prerequisites(prereqs)

                        content.append(
                            f"            {{ {port}, {sda}, {scl}, {freq}, {detect_count}, {internal_pullup}, {{"
                        )
                        for d in detect:
                            addr = M5HeaderGenerator._parse_int(d.get("addr", 0))
                            required = "true" if d.get("required", True) else "false"
                            content.append(
                                f"                {{ 0x{addr:02X}, {required} }},"
                            )
                        content.append(f"            }}, {prereq_str} }},")
                    content.append("        },")

                    # Identify I2C
                    content.append("        {")
                    for i2c in identify_i2c:
                        port = i2c.get("port", 0)
                        sda = i2c.get("sda", -1)
                        scl = i2c.get("scl", -1)
                        freq = i2c.get("freq", 400000)
                        addr = M5HeaderGenerator._parse_int(i2c.get("addr", 0))
                        content.append(
                            f"            {{ {port}, {sda}, {scl}, {freq}, 0x{addr:02X} }},"
                        )
                    content.append("        },")

                    # Displays
                    content.append("        {")
                    for disp in displays:
                        controller = disp.get("controller", disp.get("driver", ""))
                        bus_type = M5HeaderGenerator._get_bus_type(
                            disp.get("bus_type", "spi")
                        )
                        width = disp.get("width", 0)
                        height = disp.get("height", 0)
                        freq = disp.get("freq", 0)
                        d_pins = disp.get("pins", {})
                        probe = disp.get("probe") or {}
                        i2c_addr = M5HeaderGenerator._parse_int(
                            disp.get("addr", probe.get("addr", 0))
                        )

                        def get_pin_val(p_name):
                            val = d_pins.get(p_name, -1)
                            if isinstance(val, int):
                                return val
                            return -1

                        def get_pin_str(p_name):
                            val = d_pins.get(p_name, None)
                            if isinstance(val, str):
                                return f'"{val}"'
                            return "nullptr"

                        identify = M5HeaderGenerator._get_identify_config(
                            disp, {"spi_cmd_match", "dsi_cmd_match", "i2c_reg_match"}
                        )
                        if bus_type == M5HeaderGenerator.BUS_TYPE_MAP["i2c"]:
                            id_cmd_value = identify.get("reg", identify.get("cmd", -1))
                        else:
                            id_cmd_value = identify.get("cmd", identify.get("reg", -1))
                        id_cmd = M5HeaderGenerator._parse_int(
                            id_cmd_value
                        )
                        id_expect = M5HeaderGenerator._parse_int(
                            identify.get("expect", -1)
                        )
                        id_mask = M5HeaderGenerator._parse_int(identify.get("mask", -1))
                        id_rst_before = (
                            "true" if identify.get("rst_before", False) else "false"
                        )
                        id_rst_wait = M5HeaderGenerator._parse_int(
                            identify.get("rst_wait", 0)
                        )
                        dsi_identify_mode = M5HeaderGenerator._get_dsi_identify_mode(
                            identify.get("read_mode", "auto")
                        )
                        dsi_identify_len = M5HeaderGenerator._parse_int(
                            identify.get("read_len", 0)
                        )
                        dsi_identify_stride = M5HeaderGenerator._parse_int(
                            identify.get("read_stride", 1)
                        )

                        # DSI protocol fields
                        protocol_dsi = disp.get("protocol", {}).get("dsi", {})
                        dsi_bus_id = M5HeaderGenerator._parse_int(
                            protocol_dsi.get("bus_id", 0)
                        )
                        dsi_lane_num = M5HeaderGenerator._parse_int(
                            protocol_dsi.get("lane_num", 0)
                        )
                        dsi_lane_mbps = M5HeaderGenerator._parse_int(
                            protocol_dsi.get("lane_mbps", 0)
                        )
                        dsi_ldo_chan_id = M5HeaderGenerator._parse_int(
                            protocol_dsi.get("ldo_chan_id", 0)
                        )
                        dsi_ldo_voltage_mv = M5HeaderGenerator._parse_int(
                            protocol_dsi.get("ldo_voltage_mv", 0)
                        )

                        prereqs = disp.get("prerequisites", [])
                        prereq_str = M5HeaderGenerator._generate_prerequisites(prereqs)

                        pin_mosi = get_pin_val("mosi")
                        pin_miso = get_pin_val("miso")
                        pin_sclk = get_pin_val("sclk")
                        pin_cs = get_pin_val("cs")
                        pin_dc = get_pin_val("dc")
                        if bus_type == M5HeaderGenerator.BUS_TYPE_MAP["i2c"]:
                            pin_mosi = get_pin_val("sda")
                            pin_miso = get_pin_val("scl")
                        elif bus_type in (
                            M5HeaderGenerator.BUS_TYPE_MAP["parallel8"],
                            M5HeaderGenerator.BUS_TYPE_MAP["parallel16"],
                        ):
                            pin_mosi = get_pin_val("d0")
                            pin_miso = get_pin_val("d1")
                            pin_sclk = get_pin_val("wr")
                            pin_dc = get_pin_val("rs")

                        content.append(
                            f'            {{ "{controller}", {bus_type}, {width}, {height}, {freq}, '
                            f"{pin_mosi}, {pin_miso}, {pin_sclk}, "
                            f"{pin_cs}, {pin_dc}, {get_pin_val('rst')}, {get_pin_val('bl')}, "
                            f"0x{i2c_addr:02X}, "
                            f"{get_pin_str('rst')}, {get_pin_str('bl')}, "
                            f"{id_cmd}, {id_expect}, {id_mask}, {id_rst_before}, {id_rst_wait}, "
                            f"{dsi_bus_id}, {dsi_lane_num}, {dsi_lane_mbps}, {dsi_ldo_chan_id}, {dsi_ldo_voltage_mv}, "
                            f"static_cast<DSIIdentifyReadMode>({dsi_identify_mode}), {dsi_identify_len}, {dsi_identify_stride}, "
                            f"{prereq_str} }},"
                        )
                    content.append("        },")

                    # Touches
                    content.append("        {")
                    for touch in touches:
                        controller = touch.get("controller", touch.get("driver", ""))
                        bus_type = M5HeaderGenerator._get_bus_type(
                            touch.get("bus_type", "i2c")
                        )
                        addr = M5HeaderGenerator._parse_int(touch.get("addr", 0))
                        width = touch.get("width", 0)
                        height = touch.get("height", 0)
                        freq = touch.get("freq", 0)
                        t_pins = touch.get("pins", {})

                        def get_pin_val(p_name):
                            val = t_pins.get(p_name, -1)
                            if isinstance(val, int):
                                return val
                            return -1

                        def get_pin_str(p_name):
                            val = t_pins.get(p_name, None)
                            if isinstance(val, str):
                                return f'"{val}"'
                            return "nullptr"

                        prereqs = touch.get("prerequisites", [])
                        prereq_str = M5HeaderGenerator._generate_prerequisites(prereqs)

                        identify_t = M5HeaderGenerator._get_identify_config(
                            touch, {"i2c_reg_match", "spi_cmd_match"}
                        )
                        if bus_type == M5HeaderGenerator.BUS_TYPE_MAP["spi"]:
                            touch_id_value = identify_t.get("cmd", identify_t.get("reg", -1))
                        else:
                            touch_id_value = identify_t.get("reg", identify_t.get("cmd", -1))
                        id_reg = (
                            M5HeaderGenerator._parse_int(
                                touch_id_value
                            )
                            if identify_t
                            else -1
                        )
                        id_expect = (
                            M5HeaderGenerator._parse_int(identify_t.get("expect", -1))
                            if identify_t
                            else -1
                        )
                        id_mask = (
                            M5HeaderGenerator._parse_int(identify_t.get("mask", -1))
                            if identify_t
                            else -1
                        )

                        content.append(
                            f'            {{ "{controller}", {bus_type}, 0x{addr:02X}, {width}, {height}, {freq}, '
                            f"{get_pin_val('sda')}, {get_pin_val('scl')}, {get_pin_val('int')}, {get_pin_val('rst')}, "
                            f"{get_pin_str('rst')}, "
                            f"{get_pin_val('mosi')}, {get_pin_val('miso')}, {get_pin_val('sclk')}, {get_pin_val('cs')}, "
                            f"{prereq_str}, {id_reg}, {id_expect}, {id_mask} }},"
                        )
                    content.append("        },")

                    # Additional Tests
                    content.append("        {")
                    for test in additional_tests:
                        t_type = M5HeaderGenerator._get_test_type(test.get("type", 0))
                        score = M5HeaderGenerator._parse_int(test.get("score", 1))

                        # Common fields with different meanings per type
                        port = test.get("port", 0)
                        pin_a = test.get("pin_a", -1)
                        pin_b = test.get("pin_b", -1)
                        pin_c = test.get("pin_c", -1)
                        pin_d = test.get("pin_d", -1)
                        freq = test.get("freq", 0)
                        addr = M5HeaderGenerator._parse_int(test.get("addr", 0))
                        reg = M5HeaderGenerator._parse_int(test.get("reg", 0))
                        mask = M5HeaderGenerator._parse_int(test.get("mask", 0))
                        expect = M5HeaderGenerator._parse_int(test.get("expect", 0))

                        content.append(
                            f"            {{ {t_type}, {score}, {port}, {pin_a}, {pin_b}, {pin_c}, {pin_d}, {freq}, 0x{addr:02X}, 0x{reg:02X}, 0x{mask:02X}, 0x{expect:02X} }},"
                        )
                    content.append("        }")

                    content.append("    },")

        content.append("};")
        content.append("")
        content.append("} // namespace autodetect")
        content.append("} // namespace m5")

        return "\n".join(content)

    @staticmethod
    def generate_from_data(data, output_path):
        if not isinstance(data, dict):
            raise ValueError("data must be a dict")

        header_content = M5HeaderGenerator.generate_header(data)
        source_content = M5HeaderGenerator.generate_source(data)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(header_content)
        print(f"Successfully generated {output_path}")

        source_path = os.path.splitext(output_path)[0] + ".cpp"
        with open(source_path, "w", encoding="utf-8") as f:
            f.write(source_content)
        print(f"Successfully generated {source_path}")

        return True

    @staticmethod
    def generate_file(yaml_path, output_path):
        if not os.path.exists(yaml_path):
            print(f"Error: YAML file not found at {yaml_path}")
            return False

        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data is None:
                    data = {}

            return M5HeaderGenerator.generate_from_data(data, output_path)
        except Exception as e:
            print(f"Error generating files: {e}")
            import traceback

            traceback.print_exc()
            return False


if __name__ == "__main__":
    # Default paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    default_yaml = os.path.join(current_dir, "m5stack_dev_config.yaml")
    default_output = os.path.join(current_dir, "../src/data/M5Autodetect_DeviceData.h")

    yaml_file = default_yaml
    output_file = default_output

    if len(sys.argv) > 1:
        yaml_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]

    M5HeaderGenerator.generate_file(yaml_file, output_file)
