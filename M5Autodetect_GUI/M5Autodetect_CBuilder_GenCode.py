import os
import yaml
import sys

class M5HeaderGenerator:
    # Test type mapping
    TEST_TYPE_MAP = {
        'gpio': 0,
        'i2c': 1,
        'spi': 2,
        0: 0,
        1: 1,
        2: 2,
    }

    # Bus type mapping for display
    BUS_TYPE_MAP = {
        'spi': 0,
        'i2c': 1,
        'parallel8': 2,
        'parallel16': 3,
        'rgb': 4,
        'dsi': 5,
    }

    @staticmethod
    def _make_safe_name(base_name, suffix=''):
        """Create a safe C++ identifier from device name and optional suffix"""
        safe_name = base_name.replace(" ", "_").replace("-", "_").replace(".", "_").replace("(", "").replace(")", "")
        if suffix:
            safe_suffix = suffix.replace(" ", "_").replace("-", "_").replace(".", "_").replace("(", "").replace(")", "")
            safe_name += "_" + safe_suffix
        return safe_name

    @staticmethod
    def _compose_board_name(base_name, suffix=''):
        base = str(base_name or 'Unknown')
        suffix = str(suffix or '').strip()
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
    def _get_prereq_type(val):
        """Convert prereq type to enum string"""
        val = str(val).lower()
        if val == 'gpio': return 'PrereqType::GPIO_WRITE'
        if val == 'i2c_read': return 'PrereqType::I2C_READ'
        if val == 'i2c_write': return 'PrereqType::I2C_WRITE'
        if val == 'spi_read': return 'PrereqType::SPI_READ'
        if val == 'spi_write': return 'PrereqType::SPI_WRITE'
        return 'PrereqType::NONE'

    @staticmethod
    def _generate_prerequisites(prereq_list):
        """Generate C++ code for prerequisites vector"""
        if not prereq_list:
            return "{}"
        
        lines = []
        lines.append("{")
        for p in prereq_list:
            p_type = M5HeaderGenerator._get_prereq_type(p.get('type', ''))
            gpio = M5HeaderGenerator._parse_int(p.get('gpio', -1))
            level = M5HeaderGenerator._parse_int(p.get('level', 0))
            addr = M5HeaderGenerator._parse_int(p.get('addr', 0))
            reg = M5HeaderGenerator._parse_int(p.get('reg', 0))
            cmd = M5HeaderGenerator._parse_int(p.get('cmd', 0))
            data = M5HeaderGenerator._parse_int(p.get('data', 0))
            length = M5HeaderGenerator._parse_int(p.get('len', 0))
            
            lines.append(f"            {{ {p_type}, {gpio}, {level}, 0x{addr:02X}, 0x{reg:02X}, 0x{cmd:02X}, 0x{data:02X}, {length} }},")
        lines.append("        }")
        return "\n".join(lines)

    @staticmethod
    def generate_header(data):
        mcu_categories = data.get('mcu_categories', [])
        
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
            devices = category.get('devices', [])
            for dev in devices:
                base_name = dev.get('name', 'Unknown')
                variants = dev.get('variants', [])
                
                if not variants:
                    variants = [{'name': ''}]
                
                for variant in variants:
                    suffix = variant.get('name', '')
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
        content.append("    SPI_WRITE = 5")
        content.append("};")
        content.append("")

        content.append("struct Prerequisite {")
        content.append("    PrereqType type;")
        content.append("    int gpio;")
        content.append("    int level;")
        content.append("    uint8_t addr;")
        content.append("    uint8_t reg;")
        content.append("    uint8_t cmd;")
        content.append("    uint8_t data;")
        content.append("    int len;")
        content.append("};")
        content.append("")

        content.append("struct I2CDetect {")
        content.append("    uint8_t addr;")
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

        content.append("struct DisplayConfig {")
        content.append("    const char* driver;")
        content.append("    int bus_type;")
        content.append("    int width;")
        content.append("    int height;")
        content.append("    int freq;")
        content.append("    int pin_mosi;  // or d0 for parallel")
        content.append("    int pin_miso;  // or d1 for parallel")
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
        content.append("    std::vector<Prerequisite> prerequisites;")
        content.append("};")
        content.append("")

        content.append("struct TouchConfig {")
        content.append("    const char* driver;")
        content.append("    int addr;")
        content.append("    int width;")
        content.append("    int height;")
        content.append("    int freq;")
        content.append("    int pin_sda;")
        content.append("    int pin_scl;")
        content.append("    int pin_int;")
        content.append("    int pin_rst;")
        content.append("    const char* pin_rst_str;")
        content.append("    std::vector<Prerequisite> prerequisites;")
        content.append("};")
        content.append("")

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
            if val.lower().startswith('0x'):
                return int(val, 16)
            try:
                return int(val)
            except ValueError:
                return 0
        return 0

    @staticmethod
    def generate_source(data):
        mcu_categories = data.get('mcu_categories', [])
        
        content = []
        content.append('#include "M5Autodetect_DeviceData.h"')
        content.append("")
        content.append("namespace m5 {")
        content.append("namespace autodetect {")
        content.append("")
        
        # Generate data
        content.append("const std::vector<DeviceInfo> devices_data = {")
        
        for category in mcu_categories:
            mcu = category.get('mcu', 'Unknown')
            devices = category.get('devices', [])
            
            for dev in devices:
                base_name = dev.get('name', 'Unknown')
                variants = dev.get('variants', [])
                base_identify_i2c = dev.get('identify_i2c', [])
                if not isinstance(base_identify_i2c, list):
                    base_identify_i2c = []
                
                base_additional_tests = dev.get('additional_tests', [])
                if not isinstance(base_additional_tests, list):
                    base_additional_tests = []

                base_psram = bool(dev.get('psram_enabled', False))
                
                # If no variants, treat as single device
                if not variants:
                    variants = [{
                        'name': '',
                        'display': dev.get('display', []),
                        'touch': dev.get('touch', []),
                        'identify_i2c': base_identify_i2c,
                        'additional_tests': base_additional_tests
                    }]
                
                for variant in variants:
                    suffix = variant.get('name', '')
                    name = M5HeaderGenerator._compose_board_name(base_name, suffix)
                    
                    sku = dev.get('sku', 'Unknown')
                    
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
                    base_pins = dev.get('check_pins', {})
                    variant_pins = variant.get('check_pins')
                    pins = get_with_fallback(variant_pins, base_pins, is_empty_list_or_dict)
                    
                    # Calculate default check_pins_count
                    pin_count = 0
                    if isinstance(pins, list):
                        pin_count = len(pins)
                    elif isinstance(pins, dict):
                        pin_count = len(pins)
                    
                    # Check pins count - variant can override
                    base_pins_count = dev.get('check_pins_count', pin_count)
                    variant_pins_count = variant.get('check_pins_count')
                    if variant_pins_count is not None:
                        check_pins_count = variant_pins_count
                    else:
                        # Recalculate if pins were overridden
                        if variant_pins is not None and not is_empty_list_or_dict(variant_pins):
                            check_pins_count = pin_count
                        else:
                            check_pins_count = base_pins_count

                    # I2C Internal - variant can override, empty falls back to base
                    base_i2c_internal = dev.get('i2c_internal', [])
                    variant_i2c = variant.get('i2c_internal')
                    i2c_internal = get_with_fallback(variant_i2c, base_i2c_internal, is_empty_list)

                    # Displays - variant can override, empty falls back to base
                    base_displays = dev.get('display', [])
                    variant_display = variant.get('display')
                    displays = get_with_fallback(variant_display, base_displays, is_empty_list)
                    
                    # Touches - variant can override, empty falls back to base
                    base_touches = dev.get('touch', [])
                    variant_touch = variant.get('touch')
                    touches = get_with_fallback(variant_touch, base_touches, is_empty_list)
                    
                    # Identify I2C - variant can override, empty falls back to base
                    variant_identify = variant.get('identify_i2c')
                    identify_i2c = get_with_fallback(variant_identify, base_identify_i2c, is_empty_list)

                    # Additional Tests - variant can override, empty falls back to base
                    variant_tests = variant.get('additional_tests')
                    additional_tests = get_with_fallback(variant_tests, base_additional_tests, is_empty_list)

                    # PSRAM - variant can override (None falls back to base)
                    variant_psram = variant.get('psram_enabled')
                    psram_enabled = variant_psram if variant_psram is not None else base_psram
                    
                    content.append("    {")
                    content.append(f'        "{name}",')
                    content.append(f'        "{sku}",')
                    content.append(f'        "{mcu}",')
                    content.append(f'        board_{safe_name},')
                    content.append(f'        {"true" if psram_enabled else "false"},')
                    content.append(f'        {check_pins_count},')
                    content.append("        {")
                    
                    if isinstance(pins, list):
                        for pin in pins:
                            gpio = pin.get('gpio', -1)
                            mode_str = pin.get('mode', 'input')
                            mode = 0
                            if mode_str == 'input_pullup':
                                mode = 1
                            elif mode_str == 'input_pulldown':
                                mode = 2
                            
                            expect = pin.get('expect', 0)
                            content.append(f"            {{ {gpio}, {mode}, {expect} }},")
                    elif isinstance(pins, dict):
                        for gpio, pin in pins.items():
                            mode_str = pin.get('mode', 'input')
                            mode = 0
                            if mode_str == 'input_pullup':
                                mode = 1
                            elif mode_str == 'input_pulldown':
                                mode = 2
                            
                            expect = pin.get('expect', 0)
                            content.append(f"            {{ {gpio}, {mode}, {expect} }},")
                        
                    content.append("        },")
                    
                    content.append("        {")
                    for i2c in i2c_internal:
                        port = i2c.get('port', 0)
                        sda = i2c.get('sda', -1)
                        scl = i2c.get('scl', -1)
                        freq = i2c.get('freq', 400000)
                        detect = i2c.get('detect', [])
                        detect_count = i2c.get('detect_count', len(detect))
                        internal_pullup = "true" if i2c.get('internal_pullup', False) else "false"
                        prereqs = i2c.get('prerequisites', [])
                        prereq_str = M5HeaderGenerator._generate_prerequisites(prereqs)
                        
                        content.append(f"            {{ {port}, {sda}, {scl}, {freq}, {detect_count}, {internal_pullup}, {{")
                        for d in detect:
                            addr = M5HeaderGenerator._parse_int(d.get('addr', 0))
                            content.append(f"                {{ 0x{addr:02X} }},")
                        content.append(f"            }}, {prereq_str} }},")
                    content.append("        },")

                    # Identify I2C
                    content.append("        {")
                    for i2c in identify_i2c:
                        port = i2c.get('port', 0)
                        sda = i2c.get('sda', -1)
                        scl = i2c.get('scl', -1)
                        freq = i2c.get('freq', 400000)
                        addr = M5HeaderGenerator._parse_int(i2c.get('addr', 0))
                        content.append(f"            {{ {port}, {sda}, {scl}, {freq}, 0x{addr:02X} }},")
                    content.append("        },")

                    # Displays
                    content.append("        {")
                    for disp in displays:
                        driver = disp.get('driver', '')
                        bus_type = M5HeaderGenerator._get_bus_type(disp.get('bus_type', 'spi'))
                        width = disp.get('width', 0)
                        height = disp.get('height', 0)
                        freq = disp.get('freq', 0)
                        d_pins = disp.get('pins', {})
                        i2c_addr = M5HeaderGenerator._parse_int(disp.get('addr', 0))
                        
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

                        identify = disp.get('identify', {})
                        id_cmd = M5HeaderGenerator._parse_int(identify.get('cmd', -1))
                        id_expect = M5HeaderGenerator._parse_int(identify.get('expect', -1))
                        id_mask = M5HeaderGenerator._parse_int(identify.get('mask', -1))
                        id_rst_before = "true" if identify.get('rst_before', False) else "false"
                        id_rst_wait = M5HeaderGenerator._parse_int(identify.get('rst_wait', 0))

                        prereqs = disp.get('prerequisites', [])
                        prereq_str = M5HeaderGenerator._generate_prerequisites(prereqs)

                        content.append(f'            {{ "{driver}", {bus_type}, {width}, {height}, {freq}, '
                                    f'{get_pin_val("mosi")}, {get_pin_val("miso")}, {get_pin_val("sclk")}, '
                                    f'{get_pin_val("cs")}, {get_pin_val("dc")}, {get_pin_val("rst")}, {get_pin_val("bl")}, '
                                    f'0x{i2c_addr:02X}, '
                                    f'{get_pin_str("rst")}, {get_pin_str("bl")}, '
                                    f'{id_cmd}, {id_expect}, {id_mask}, {id_rst_before}, {id_rst_wait}, {prereq_str} }},')
                    content.append("        },")

                    # Touches
                    content.append("        {")
                    for touch in touches:
                        driver = touch.get('driver', '')
                        addr = M5HeaderGenerator._parse_int(touch.get('addr', 0))
                        width = touch.get('width', 0)
                        height = touch.get('height', 0)
                        freq = touch.get('freq', 0)
                        t_pins = touch.get('pins', {})

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

                        prereqs = touch.get('prerequisites', [])
                        prereq_str = M5HeaderGenerator._generate_prerequisites(prereqs)

                        content.append(f'            {{ "{driver}", 0x{addr:02X}, {width}, {height}, {freq}, '
                                    f'{get_pin_val("sda")}, {get_pin_val("scl")}, {get_pin_val("int")}, {get_pin_val("rst")}, '
                                    f'{get_pin_str("rst")}, {prereq_str} }},')
                    content.append("        },")

                    # Additional Tests
                    content.append("        {")
                    for test in additional_tests:
                        t_type = M5HeaderGenerator._get_test_type(test.get('type', 0))
                        score = M5HeaderGenerator._parse_int(test.get('score', 1))
                        
                        # Common fields with different meanings per type
                        port = test.get('port', 0)
                        pin_a = test.get('pin_a', -1)
                        pin_b = test.get('pin_b', -1)
                        pin_c = test.get('pin_c', -1)
                        pin_d = test.get('pin_d', -1)
                        freq = test.get('freq', 0)
                        addr = M5HeaderGenerator._parse_int(test.get('addr', 0))
                        reg = M5HeaderGenerator._parse_int(test.get('reg', 0))
                        mask = M5HeaderGenerator._parse_int(test.get('mask', 0))
                        expect = M5HeaderGenerator._parse_int(test.get('expect', 0))
                        
                        content.append(f"            {{ {t_type}, {score}, {port}, {pin_a}, {pin_b}, {pin_c}, {pin_d}, {freq}, 0x{addr:02X}, 0x{reg:02X}, 0x{mask:02X}, 0x{expect:02X} }},")
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
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(header_content)
        print(f"Successfully generated {output_path}")

        source_path = os.path.splitext(output_path)[0] + ".cpp"
        with open(source_path, 'w', encoding='utf-8') as f:
            f.write(source_content)
        print(f"Successfully generated {source_path}")

        return True

    @staticmethod
    def generate_file(yaml_path, output_path):
        if not os.path.exists(yaml_path):
            print(f"Error: YAML file not found at {yaml_path}")
            return False
            
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
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
    default_yaml = os.path.join(current_dir, 'm5stack_dev_config.yaml')
    default_output = os.path.join(current_dir, '../src/data/M5Autodetect_DeviceData.h')
    
    yaml_file = default_yaml
    output_file = default_output
    
    if len(sys.argv) > 1:
        yaml_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
        
    M5HeaderGenerator.generate_file(yaml_file, output_file)
