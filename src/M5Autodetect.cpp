#include "M5Autodetect.h"

#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "data/M5Autodetect_DeviceData.h"
#include "platform/M5Autodetect_IdfI2C.h"

#if __has_include(<esp_lcd_mipi_dsi.h>)
#include <esp_ldo_regulator.h>
#include <esp_lcd_mipi_dsi.h>
#include <esp_lcd_panel_io.h>
#define M5_AUTODETECT_DSI_SUPPORTED 1
#else
#define M5_AUTODETECT_DSI_SUPPORTED 0
#endif

#define LOG_LOCAL_LEVEL ESP_LOG_VERBOSE
#include "esp_log.h"

#define LOG_TEXT(level, message) do { logMessage(level, message); } while(0)
#define LOG_PRINTF(level, fmt, ...) do { logPrintf(level, fmt, ##__VA_ARGS__); } while(0)

// Keep chip family distinctions so ESP32-P4 不会被误判成经典 ESP32。
enum class ChipKind {
    Unknown,
    Esp32,
    Esp32S2,
    Esp32S3,
    Esp32C2,
    Esp32C3,
    Esp32C5,
    Esp32C6,
    Esp32C61,
    Esp32H2,
    Esp32P4,
};

static ChipKind detectChipKind(const String& chip) {
    if (chip.indexOf("ESP32-S3") != -1) return ChipKind::Esp32S3;
    if (chip.indexOf("ESP32-S2") != -1) return ChipKind::Esp32S2;
    if (chip.indexOf("ESP32-C61") != -1) return ChipKind::Esp32C61;
    if (chip.indexOf("ESP32-C6") != -1) return ChipKind::Esp32C6;
    if (chip.indexOf("ESP32-C5") != -1) return ChipKind::Esp32C5;
    if (chip.indexOf("ESP32-C3") != -1) return ChipKind::Esp32C3;
    if (chip.indexOf("ESP32-C2") != -1) return ChipKind::Esp32C2;
    if (chip.indexOf("ESP32-H2") != -1 || chip.indexOf("ESP32-H4") != -1) return ChipKind::Esp32H2;
    if (chip.indexOf("ESP32-P4") != -1) return ChipKind::Esp32P4;
    if (chip.indexOf("ESP32") != -1) return ChipKind::Esp32;
    return ChipKind::Unknown;
}

constexpr const char* kLogTag = "M5Autodetect";

esp_log_level_t toEspLogLevel(M5Autodetect::debug_t level) {
    switch (level) {
        case M5Autodetect::debug_error:
            return ESP_LOG_ERROR;
        case M5Autodetect::debug_warn:
            return ESP_LOG_WARN;
        case M5Autodetect::debug_info:
            return ESP_LOG_INFO;
        case M5Autodetect::debug_debug:
            return ESP_LOG_DEBUG;
        case M5Autodetect::debug_verbose:
            return ESP_LOG_VERBOSE;
        case M5Autodetect::debug_none:
        default:
            return ESP_LOG_NONE;
    }
}

std::string trimTrailingLineBreaks(std::string text) {
    while (!text.empty() && (text.back() == '\r' || text.back() == '\n')) {
        text.pop_back();
    }
    return text;
}

static int getIdentifyReadLen(int mask, int configured_len, int default_len) {
    if (configured_len > 0) {
        return configured_len;
    }
    if (mask == -1) {
        return default_len;
    }

    uint32_t unsigned_mask = static_cast<uint32_t>(mask);
    if (unsigned_mask > 0xFFFF) return 3;
    if (unsigned_mask > 0xFF) return 2;
    return 1;
}

static uint32_t packBytesBE(const uint8_t* data, int len) {
    uint32_t result = 0;
    for (int i = 0; i < len; ++i) {
        result = (result << 8) | data[i];
    }
    return result;
}

std::string formatString(const char* format, va_list args) {
    va_list args_copy;
    va_copy(args_copy, args);
    const int required = vsnprintf(nullptr, 0, format, args_copy);
    va_end(args_copy);

    if (required <= 0) {
        return {};
    }

    std::vector<char> buffer(static_cast<size_t>(required) + 1);
    vsnprintf(buffer.data(), buffer.size(), format, args);
    return std::string(buffer.data(), static_cast<size_t>(required));
}

std::string formatHexBytes(const uint8_t* data, int len) {
    if (data == nullptr || len <= 0) {
        return {};
    }

    std::string text;
    text.reserve(static_cast<size_t>(len) * 3);
    char buffer[4] = {};
    for (int index = 0; index < len; ++index) {
        if (!text.empty()) {
            text += ' ';
        }
        snprintf(buffer, sizeof(buffer), "%02X", data[index]);
        text += buffer;
    }
    return text;
}

void writeEspLog(esp_log_level_t level, const std::string& message) {
    switch (level) {
        case ESP_LOG_ERROR:
            ESP_LOGE(kLogTag, "%s", message.c_str());
            break;
        case ESP_LOG_WARN:
            ESP_LOGW(kLogTag, "%s", message.c_str());
            break;
        case ESP_LOG_INFO:
            ESP_LOGI(kLogTag, "%s", message.c_str());
            break;
        case ESP_LOG_DEBUG:
            ESP_LOGD(kLogTag, "%s", message.c_str());
            break;
        case ESP_LOG_VERBOSE:
            ESP_LOGV(kLogTag, "%s", message.c_str());
            break;
        case ESP_LOG_NONE:
        default:
            break;
    }
}

enum class TouchIdentifyReadPath {
    RawI2C,
    PanelIoI2C,
};

static void runPrerequisites(const std::vector<m5::autodetect::Prerequisite>& prereqs,
                             int pin_sda, int pin_scl,
                             int pin_mosi, int pin_miso, int pin_sclk, int pin_cs,
                             uint32_t freq, int i2c_port = 0);

static bool isSt712xTouch(const m5::autodetect::TouchConfig& touch) {
    return touch.driver != nullptr
        && (strcmp(touch.driver, "ST7121") == 0 || strcmp(touch.driver, "ST7123") == 0);
}

static const char* touchIdentifyReadPathName(TouchIdentifyReadPath path) {
    switch (path) {
        case TouchIdentifyReadPath::PanelIoI2C:
            return "panel-io";
        case TouchIdentifyReadPath::RawI2C:
        default:
            return "raw-i2c";
    }
}

static bool readTouchIdentifyRegRaw(TwoWire& i2c, const m5::autodetect::TouchConfig& touch, uint8_t* reg_value) {
    if (reg_value == nullptr || touch.addr <= 0 || touch.identify_reg < 0) {
        return false;
    }

    i2c.beginTransmission(static_cast<uint8_t>(touch.addr));
    i2c.write((touch.identify_reg >> 8) & 0xFF);
    i2c.write(touch.identify_reg & 0xFF);
    if (i2c.endTransmission(false) != 0) {
        return false;
    }
    if (i2c.requestFrom(touch.addr, 1) != 1) {
        return false;
    }

    const int read_value = i2c.read();
    if (read_value < 0) {
        return false;
    }

    *reg_value = static_cast<uint8_t>(read_value);
    return true;
}

static bool readTouchIdentifyRegRaw(const m5::autodetect::TouchConfig& touch, uint8_t* reg_value) {
    if (reg_value == nullptr || touch.addr <= 0 || touch.pin_sda < 0 || touch.pin_scl < 0 || touch.identify_reg < 0) {
        return false;
    }

    TwoWire i2c(0);
    const uint32_t freq = (touch.freq > 0) ? static_cast<uint32_t>(touch.freq) : 400000;
    if (!i2c.begin(touch.pin_sda, touch.pin_scl, freq)) {
        return false;
    }

    return readTouchIdentifyRegRaw(i2c, touch, reg_value);
}

static bool readTouchIdentifyRegPanelIo(const m5::autodetect::TouchConfig& touch, uint8_t* reg_value) {
    if (reg_value == nullptr || touch.addr <= 0 || touch.pin_sda < 0 || touch.pin_scl < 0 || touch.identify_reg < 0) {
        return false;
    }

    i2c_master_bus_handle_t bus_handle = nullptr;
    esp_lcd_panel_io_handle_t io_handle = nullptr;
    bool read_ok = false;

    i2c_master_bus_config_t bus_config = {};
    esp_lcd_panel_io_i2c_config_t io_config = {};
    bus_config.i2c_port = 0;
    bus_config.sda_io_num = static_cast<gpio_num_t>(touch.pin_sda);
    bus_config.scl_io_num = static_cast<gpio_num_t>(touch.pin_scl);
    bus_config.clk_source = I2C_CLK_SRC_DEFAULT;
    bus_config.glitch_ignore_cnt = 7;
    bus_config.intr_priority = 0;
    bus_config.trans_queue_depth = 0;
    bus_config.flags.enable_internal_pullup = 1;
    if (i2c_new_master_bus(&bus_config, &bus_handle) != ESP_OK) {
        goto cleanup;
    }

    io_config.dev_addr = static_cast<uint32_t>(touch.addr);
    io_config.scl_speed_hz = (touch.freq > 0) ? static_cast<uint32_t>(touch.freq) : 100000;
    io_config.control_phase_bytes = 1;
    io_config.lcd_cmd_bits = 16;
    io_config.flags.disable_control_phase = 1;
    if (esp_lcd_new_panel_io_i2c(bus_handle, &io_config, &io_handle) != ESP_OK) {
        goto cleanup;
    }

    if (esp_lcd_panel_io_rx_param(io_handle, touch.identify_reg, reg_value, 1) != ESP_OK) {
        goto cleanup;
    }

    read_ok = true;

cleanup:
    if (io_handle) {
        esp_lcd_panel_io_del(io_handle);
    }
    if (bus_handle) {
        i2c_del_master_bus(bus_handle);
    }
    return read_ok;
}

static bool readTouchIdentifyReg(const m5::autodetect::TouchConfig& touch,
                                 uint8_t* reg_value,
                                 TouchIdentifyReadPath* read_path) {
    if (reg_value == nullptr) {
        return false;
    }

    if (isSt712xTouch(touch)) {
        if (readTouchIdentifyRegPanelIo(touch, reg_value)) {
            if (read_path) {
                *read_path = TouchIdentifyReadPath::PanelIoI2C;
            }
            return true;
        }
        if (readTouchIdentifyRegRaw(touch, reg_value)) {
            if (read_path) {
                *read_path = TouchIdentifyReadPath::RawI2C;
            }
            return true;
        }
        return false;
    }

    if (readTouchIdentifyRegRaw(touch, reg_value)) {
        if (read_path) {
            *read_path = TouchIdentifyReadPath::RawI2C;
        }
        return true;
    }
    if (readTouchIdentifyRegPanelIo(touch, reg_value)) {
        if (read_path) {
            *read_path = TouchIdentifyReadPath::PanelIoI2C;
        }
        return true;
    }
    return false;
}

static bool readTouchIdentifyReg(TwoWire& i2c,
                                 const m5::autodetect::TouchConfig& touch,
                                 uint8_t* reg_value,
                                 TouchIdentifyReadPath* read_path) {
    if (readTouchIdentifyRegRaw(i2c, touch, reg_value)) {
        if (read_path) {
            *read_path = TouchIdentifyReadPath::RawI2C;
        }
        return true;
    }

    return readTouchIdentifyReg(touch, reg_value, read_path);
}

// Helper for bit-banging SPI to read display ID
static uint32_t readDisplayID(const m5::autodetect::DisplayConfig& disp) {
    int sclk = disp.pin_sclk;
    int mosi = disp.pin_mosi;
    int miso = disp.pin_miso;
    int cs = disp.pin_cs;
    int dc = disp.pin_dc;
    int rst = disp.pin_rst;

    if (sclk < 0 || mosi < 0 || cs < 0) return 0;

    // Handle Reset if requested
    if (disp.identify_rst_before && rst >= 0) {
        pinMode(rst, OUTPUT);
        digitalWrite(rst, LOW);
        delay(10); // Short reset pulse
        digitalWrite(rst, HIGH);
        if (disp.identify_rst_wait > 0) {
            delay(disp.identify_rst_wait);
        } else {
            delay(120); // Default wait
        }
    }

    pinMode(cs, OUTPUT); digitalWrite(cs, HIGH);
    pinMode(sclk, OUTPUT); digitalWrite(sclk, LOW); // Mode 0
    if (dc >= 0) {
        pinMode(dc, OUTPUT);
        digitalWrite(dc, HIGH);
    }
    pinMode(mosi, OUTPUT);
    
    // Start Transaction
    digitalWrite(cs, LOW);
    
    // Send Command
    if (dc >= 0) digitalWrite(dc, LOW);
    
    uint8_t cmd = (uint8_t)disp.identify_cmd;
    for (int i = 0; i < 8; i++) {
        digitalWrite(mosi, (cmd & 0x80) ? HIGH : LOW);
        digitalWrite(sclk, HIGH);
        digitalWrite(sclk, LOW);
        cmd <<= 1;
    }
    
    // Switch to Data
    if (dc >= 0) digitalWrite(dc, HIGH);
    
    // Handle 3-wire (MISO on MOSI)
    int read_pin = miso;
    if (read_pin < 0) {
        read_pin = mosi;
        pinMode(read_pin, INPUT);
    } else {
        pinMode(read_pin, INPUT);
    }
    
    // Dummy Bit (1 bit)
    digitalWrite(sclk, HIGH);
    digitalWrite(sclk, LOW);
    
    // Read 32 bits
    uint32_t result = 0;
    for (int i = 0; i < 32; i++) {
        result <<= 1;
        digitalWrite(sclk, HIGH);
        if (digitalRead(read_pin)) result |= 1;
        digitalWrite(sclk, LOW);
    }
    
    digitalWrite(cs, HIGH);
    
    // Restore MOSI if it was input
    if (read_pin == mosi) {
        pinMode(mosi, OUTPUT);
    }
    
    return result;
}

struct I2CIdentifyReadResult {
    bool ok = false;
    uint32_t value = 0;
    uint8_t data[4] = {};
    int len = 0;
};

static I2CIdentifyReadResult readDisplayID_I2C(const m5::autodetect::DisplayConfig& disp) {
    I2CIdentifyReadResult result = {};
    const int sda = disp.pin_mosi;
    const int scl = disp.pin_miso;
    if (disp.i2c_addr == 0 || sda < 0 || scl < 0) {
        return result;
    }

    TwoWire i2c(0);
    const uint32_t freq = (disp.freq > 0) ? static_cast<uint32_t>(disp.freq) : 400000;
    if (!i2c.begin(sda, scl, freq)) {
        return result;
    }

    i2c.beginTransmission(disp.i2c_addr);
    if (disp.identify_cmd < 0) {
        result.ok = (i2c.endTransmission() == 0);
        return result;
    }

    if (disp.identify_cmd > 0xFF) {
        i2c.write((disp.identify_cmd >> 8) & 0xFF);
    }
    i2c.write(disp.identify_cmd & 0xFF);
    if (i2c.endTransmission(false) != 0) {
        return result;
    }

    const int read_len = getIdentifyReadLen(disp.identify_mask, 0, 1);
    if (read_len <= 0 || read_len > static_cast<int>(sizeof(result.data))) {
        return result;
    }
    if (i2c.requestFrom(static_cast<int>(disp.i2c_addr), read_len) != read_len) {
        return result;
    }
    for (int i = 0; i < read_len; ++i) {
        const int read_value = i2c.read();
        if (read_value < 0) {
            return {};
        }
        result.data[i] = static_cast<uint8_t>(read_value);
    }

    result.len = read_len;
    result.value = packBytesBE(result.data, read_len);
    result.ok = true;
    return result;
}

static bool readTouchIdentifyRegSpi(const m5::autodetect::TouchConfig& touch, uint8_t* reg_value) {
    if (reg_value == nullptr || touch.identify_reg < 0 || touch.pin_mosi < 0 || touch.pin_sclk < 0 || touch.pin_cs < 0) {
        return false;
    }

    const int mosi = touch.pin_mosi;
    const int miso = touch.pin_miso;
    const int sclk = touch.pin_sclk;
    const int cs = touch.pin_cs;

    pinMode(cs, OUTPUT);
    digitalWrite(cs, HIGH);
    pinMode(sclk, OUTPUT);
    digitalWrite(sclk, LOW);
    pinMode(mosi, OUTPUT);
    if (miso >= 0) {
        pinMode(miso, INPUT);
    }

    digitalWrite(cs, LOW);

    uint8_t cmd = static_cast<uint8_t>(touch.identify_reg);
    for (int i = 0; i < 8; ++i) {
        digitalWrite(mosi, (cmd & 0x80) ? HIGH : LOW);
        digitalWrite(sclk, HIGH);
        digitalWrite(sclk, LOW);
        cmd <<= 1;
    }

    const int read_pin = (miso >= 0) ? miso : mosi;
    pinMode(read_pin, INPUT);

    uint8_t value = 0;
    for (int i = 0; i < 8; ++i) {
        value <<= 1;
        digitalWrite(sclk, HIGH);
        if (digitalRead(read_pin)) {
            value |= 1;
        }
        digitalWrite(sclk, LOW);
    }

    digitalWrite(cs, HIGH);
    if (read_pin == mosi) {
        pinMode(mosi, OUTPUT);
    }

    *reg_value = value;
    return true;
}



#if M5_AUTODETECT_DSI_SUPPORTED
struct DsiIdentifyReadResult {
    bool ok = false;
    uint32_t value = 0;
    uint8_t data[8] = {};
    int len = 0;
};

static bool readDisplayID_DSI_singleCmd(const m5::autodetect::DisplayConfig& disp,
                                        esp_lcd_panel_io_handle_t io_dbi,
                                        DsiIdentifyReadResult* out_result) {
    if (out_result == nullptr) {
        return false;
    }

    const int read_len = getIdentifyReadLen(disp.identify_mask, disp.dsi_identify_read_len, 2);
    if (read_len <= 0 || read_len > 8) {
        return false;
    }

    *out_result = {};
    out_result->len = read_len;
    if (esp_lcd_panel_io_rx_param(io_dbi, disp.identify_cmd, out_result->data, read_len) != ESP_OK) {
        return false;
    }

    out_result->value = packBytesBE(out_result->data, read_len);
    out_result->ok = true;
    return true;
}

static bool readDisplayID_DSI_sequentialCmd(const m5::autodetect::DisplayConfig& disp,
                                            esp_lcd_panel_io_handle_t io_dbi,
                                            DsiIdentifyReadResult* out_result) {
    if (out_result == nullptr) {
        return false;
    }

    const int read_len = getIdentifyReadLen(disp.identify_mask, disp.dsi_identify_read_len, 2);
    const int read_stride = disp.dsi_identify_read_stride > 0 ? disp.dsi_identify_read_stride : 1;
    if (read_len <= 0 || read_len > 8) {
        return false;
    }

    *out_result = {};
    out_result->len = read_len;
    for (int i = 0; i < read_len; ++i) {
        if (esp_lcd_panel_io_rx_param(io_dbi, disp.identify_cmd + (i * read_stride), &out_result->data[i], 1) != ESP_OK) {
            return false;
        }
    }

    out_result->value = packBytesBE(out_result->data, read_len);
    out_result->ok = true;
    return true;
}

/// Temporarily initialise a MIPI-DSI DBI channel, run board-local prerequisites,
/// send `identify_cmd` via DCS generic read, and return the panel ID.
/// The DSI bus / LDO / IO are fully released before returning so that the
/// application can later initialise them independently.
static DsiIdentifyReadResult readDisplayID_DSI(const m5::autodetect::DisplayConfig& disp) {
    esp_ldo_channel_handle_t phy_pwr = nullptr;
    esp_lcd_dsi_bus_handle_t dsi_bus = nullptr;
    esp_lcd_panel_io_handle_t io_dbi = nullptr;
    DsiIdentifyReadResult result = {};

    // 1. Run I2C/GPIO prerequisites BEFORE DSI bus creation so that the IO
    //    expander configures power/reset pins and the panel finishes its
    //    power-on sequence before the DSI host PHY comes up.
    runPrerequisites(disp.prerequisites, 31, 32, -1, -1, -1, -1, 400000, 0);

    // 2. Power LDO for MIPI PHY
    {
        esp_ldo_channel_config_t ldo_cfg = {};
        ldo_cfg.chan_id = disp.dsi_ldo_chan_id;
        ldo_cfg.voltage_mv = disp.dsi_ldo_voltage_mv;
        if (esp_ldo_acquire_channel(&ldo_cfg, &phy_pwr) != ESP_OK) goto cleanup;
    }

    // 3. Create DSI bus
    {
        esp_lcd_dsi_bus_config_t bus_cfg = {};
        bus_cfg.bus_id = disp.dsi_bus_id;
        bus_cfg.num_data_lanes = disp.dsi_lane_num;
        bus_cfg.phy_clk_src = MIPI_DSI_PHY_CLK_SRC_DEFAULT;
        bus_cfg.lane_bit_rate_mbps = disp.dsi_lane_mbps;
        if (esp_lcd_new_dsi_bus(&bus_cfg, &dsi_bus) != ESP_OK) goto cleanup;
    }

    // 3. Create DBI panel IO for DCS commands
    {
        esp_lcd_dbi_io_config_t dbi_cfg = {};
        dbi_cfg.virtual_channel = 0;
        dbi_cfg.lcd_cmd_bits = 8;
        dbi_cfg.lcd_param_bits = 8;
        if (esp_lcd_new_panel_io_dbi(dsi_bus, &dbi_cfg, &io_dbi) != ESP_OK) goto cleanup;
    }

    // 4. Software reset + wait for panel to become readable
    esp_lcd_panel_io_tx_param(io_dbi, 0x01, nullptr, 0);
    delay(120);

    // 5. Execute DSI-bus prerequisites (e.g. ILI9881C page-select command)
    //    These require io_dbi so they cannot be handled by runPrerequisites.
    for (const auto& p : disp.prerequisites) {
        if (p.type == m5::autodetect::PrereqType::DSI_WRITE) {
            esp_lcd_panel_io_tx_param(io_dbi, p.cmd, p.data.data(), p.data.size());
            if (p.delay_ms > 0) delay(p.delay_ms);
        } else if (p.type == m5::autodetect::PrereqType::DSI_READ) {
            uint8_t discard[8] = {};
            const int read_len = (p.len > 0 && p.len <= static_cast<int>(sizeof(discard))) ? p.len : 1;
            if (esp_lcd_panel_io_rx_param(io_dbi, p.cmd, discard, read_len) != ESP_OK) {
                goto cleanup;
            }
            if (p.delay_ms > 0) delay(p.delay_ms);
        }
    }

    // 6. Read panel ID using the configured strategy.
    {
        using m5::autodetect::DSIIdentifyReadMode;
        bool ok = false;

        for (int attempt = 0; attempt < 3 && !ok; ++attempt) {
            if (attempt > 0) {
                delay(40);
            }

            if (disp.dsi_identify_read_mode == DSIIdentifyReadMode::SINGLE_CMD) {
                ok = readDisplayID_DSI_singleCmd(disp, io_dbi, &result);
            } else if (disp.dsi_identify_read_mode == DSIIdentifyReadMode::SEQUENTIAL_CMD) {
                ok = readDisplayID_DSI_sequentialCmd(disp, io_dbi, &result);
            } else {
                ok = readDisplayID_DSI_singleCmd(disp, io_dbi, &result);
                if (!ok) {
                    ok = readDisplayID_DSI_sequentialCmd(disp, io_dbi, &result);
                }
            }
        }

        if (!ok) {
            result = {};
        }
    }

cleanup:
    if (io_dbi) esp_lcd_panel_io_del(io_dbi);
    if (dsi_bus) esp_lcd_del_dsi_bus(dsi_bus);
    if (phy_pwr) esp_ldo_release_channel(phy_pwr);
    return result;
}
#endif // M5_AUTODETECT_DSI_SUPPORTED

M5Autodetect::M5Autodetect() {
}

void M5Autodetect::begin(debug_t debug, Print* serial) {
    _debug = debug;
    _serial = serial;
    esp_log_level_set(kLogTag, toEspLogLevel(debug));
}

void M5Autodetect::logMessage(debug_t level, const char* message) const {
    if (_debug < level || !message) {
        return;
    }

    if (_serial) {
        _serial->print(message);
        return;
    }

    const std::string trimmed = trimTrailingLineBreaks(message);
    if (trimmed.empty()) {
        return;
    }

    writeEspLog(toEspLogLevel(level), trimmed);
}

void M5Autodetect::logPrintf(debug_t level, const char* format, ...) const {
    if (_debug < level || !format) {
        return;
    }

    va_list args;
    va_start(args, format);
    const std::string formatted = formatString(format, args);
    va_end(args);

    if (formatted.empty()) {
        return;
    }

    if (_serial) {
        _serial->write(reinterpret_cast<const uint8_t*>(formatted.data()), formatted.size());
        return;
    }

    const std::string trimmed = trimTrailingLineBreaks(formatted);
    if (trimmed.empty()) {
        return;
    }

    writeEspLog(toEspLogLevel(level), trimmed);
}

static void runPrerequisites(const std::vector<m5::autodetect::Prerequisite>& prereqs, 
                             int pin_sda, int pin_scl, 
                             int pin_mosi, int pin_miso, int pin_sclk, int pin_cs,
                             uint32_t freq, int i2c_port) {
    for (const auto& p : prereqs) {
        const uint32_t delay_ms = (p.delay_ms > 0) ? static_cast<uint32_t>(p.delay_ms) : 10U;
        if (p.type == m5::autodetect::PrereqType::GPIO_WRITE) {
            if (p.gpio >= 0) {
                pinMode(p.gpio, OUTPUT);
                digitalWrite(p.gpio, p.level ? HIGH : LOW);
                delay(delay_ms);
            }
        }
        else if (p.type == m5::autodetect::PrereqType::I2C_WRITE || p.type == m5::autodetect::PrereqType::I2C_READ) {
            if (pin_sda >= 0 && pin_scl >= 0) {
                TwoWire i2c(i2c_port);
                i2c.begin(pin_sda, pin_scl, freq);
                i2c.beginTransmission(p.addr);
                i2c.write(p.reg);
                if (p.type == m5::autodetect::PrereqType::I2C_WRITE) {
                    for (auto b : p.data) { i2c.write(b); }
                    i2c.endTransmission();
                } else {
                    i2c.endTransmission(false);
                    i2c.requestFrom((int)p.addr, (int)p.len > 0 ? (int)p.len : 1);
                    while(i2c.available()) i2c.read();
                }
                delay(delay_ms);
            }
        }
        else if (p.type == m5::autodetect::PrereqType::SPI_WRITE || p.type == m5::autodetect::PrereqType::SPI_READ) {
            if (pin_mosi >= 0 && pin_sclk >= 0 && pin_cs >= 0) {
                pinMode(pin_cs, OUTPUT);
                pinMode(pin_sclk, OUTPUT);
                pinMode(pin_mosi, OUTPUT);
                if (pin_miso >= 0) pinMode(pin_miso, INPUT);
                
                digitalWrite(pin_cs, HIGH);
                digitalWrite(pin_sclk, LOW);
                
                digitalWrite(pin_cs, LOW);
                
                auto spi_write = [&](uint8_t b) {
                    for (int i = 0; i < 8; i++) {
                        digitalWrite(pin_mosi, (b & 0x80) ? HIGH : LOW);
                        digitalWrite(pin_sclk, HIGH);
                        digitalWrite(pin_sclk, LOW);
                        b <<= 1;
                    }
                };
                
                spi_write(p.cmd);
                
                if (p.type == m5::autodetect::PrereqType::SPI_WRITE) {
                    for (auto b : p.data) { spi_write(b); }
                } else {
                    int len = (p.len > 0) ? p.len : 1;
                    for (int j=0; j<len; j++) {
                        uint8_t val = 0;
                        for (int i = 0; i < 8; i++) {
                            val <<= 1;
                            digitalWrite(pin_sclk, HIGH);
                            if (pin_miso >= 0 && digitalRead(pin_miso)) val |= 1;
                            digitalWrite(pin_sclk, LOW);
                        }
                    }
                }
                
                digitalWrite(pin_cs, HIGH);
                delay(delay_ms);
            }
        }
        else if (p.type == m5::autodetect::PrereqType::DSI_WRITE || p.type == m5::autodetect::PrereqType::DSI_READ) {
            // DSI prerequisites need a DBI IO handle and are executed by readDisplayID_DSI().
        }
    }
}

const m5::autodetect::DeviceInfo* M5Autodetect::detect() {
    String chipModel = ESP.getChipModel();
    const ChipKind chipKind = detectChipKind(chipModel);
    const m5::autodetect::DeviceInfo* best_device = nullptr;
    int max_score = -1;
    int min_skip_count = 999;  // Lower is better (fewer skips = higher priority)
    
    if (_debug >= debug_info) {
        LOG_TEXT(debug_info, "=== Autodetect Start ===\r\n");
        LOG_PRINTF(debug_info, "Chip Model: %s\r\n", chipModel.c_str());
    }

    for (const auto& device : m5::autodetect::devices_data) {
        int current_score = 0;
        int skip_count = 0;  // Track number of skipped steps (fewer = higher priority)
        bool step_failed = false;  // Track if any step failed
        
        if (_debug >= debug_debug) {
            LOG_TEXT(debug_debug, "-------------------\r\n");
            LOG_PRINTF(debug_debug, "Checking: %s (%s)\r\n", device.name, device.sku);
        }

        // 1. SOC（严格按家族匹配，避免 ESP32-P4 命中经典 ESP32 条目）
        const ChipKind deviceKind = detectChipKind(String(device.mcu));
        bool soc_match = false;
        if (chipKind != ChipKind::Unknown && deviceKind != ChipKind::Unknown) {
            soc_match = (chipKind == deviceKind);
        } else {
            // Fallback: substring match for未知型号
            soc_match = (chipModel.indexOf(device.mcu) != -1);
        }

        if (soc_match) {
            current_score++;
            if (_debug >= debug_debug) LOG_TEXT(debug_debug, "  [Pass] SOC Match (+1)\r\n");
        } else {
            if (_debug >= debug_debug) LOG_PRINTF(debug_debug, "  [Fail] SOC Mismatch (Expected: %s, Got: %s)\r\n", device.mcu, chipModel.c_str());
            continue;  // SOC mismatch, skip this device entirely
        }

        // 1.5 PSRAM check: treat PSRAM as a weak signal because many users leave it disabled.
        bool psram_detected = psramFound() || ESP.getPsramSize() > 0;
        if (device.psram_enabled && !psram_detected) {
            skip_count++;
            if (_debug >= debug_debug) LOG_TEXT(debug_debug, "  [Warn] PSRAM expected but not detected, continuing without bonus\r\n");
        } else if (device.psram_enabled && psram_detected) {
            current_score++;  // Bonus for matching PSRAM requirement
            if (_debug >= debug_debug) LOG_TEXT(debug_debug, "  [Pass] PSRAM Match (+1)\r\n");
        }

        // 2. IOMAP
        int pin_match_count = 0;
        for (const auto& pinCheck : device.check_pins) {
            if (pinCheck.gpio < 0) continue;

            if (pinCheck.mode == 1) {
                pinMode(pinCheck.gpio, INPUT_PULLUP);
            } else if (pinCheck.mode == 2) {
                pinMode(pinCheck.gpio, INPUT_PULLDOWN);
            } else {
                pinMode(pinCheck.gpio, INPUT);
            }
            
            delay(1);
            
            int val = digitalRead(pinCheck.gpio);
            if (val == pinCheck.expect) {
                pin_match_count++;
            } else {
                if (_debug >= debug_debug) LOG_PRINTF(debug_debug, "  [Fail] Pin %d check failed. Expected %d, got %d\r\n", pinCheck.gpio, pinCheck.expect, val);
            }
        }
        if (pin_match_count >= device.check_pins_count) {
            current_score++;
            if (_debug >= debug_debug) LOG_PRINTF(debug_debug, "  [Pass] IOMAP Match (+1) (%d/%d)\r\n", pin_match_count, device.check_pins_count);
        } else {
            step_failed = true;
            if (_debug >= debug_debug) LOG_PRINTF(debug_debug, "  [Fail] IOMAP Match (%d/%d)\r\n", pin_match_count, device.check_pins_count);
        }

        // 3. Internal I2C pins High
        if (!step_failed) {
            bool i2c_pins_high = true;
            bool has_i2c_to_check = !device.i2c_checks.empty() || !device.identify_i2c.empty();
            
            if (has_i2c_to_check) {
                // Check i2c_checks pins
                for (const auto& i2c_bus : device.i2c_checks) {
                    if (i2c_bus.internal_pullup) {
                        pinMode(i2c_bus.sda, INPUT_PULLUP);
                        pinMode(i2c_bus.scl, INPUT_PULLUP);
                        delay(5); // Extra delay for internal pullup to stabilize
                    } else {
                        pinMode(i2c_bus.sda, INPUT);
                        pinMode(i2c_bus.scl, INPUT);
                        delay(1);
                    }
                    if (digitalRead(i2c_bus.sda) == LOW || digitalRead(i2c_bus.scl) == LOW) {
                        i2c_pins_high = false;
                        if (_debug >= debug_debug) LOG_PRINTF(debug_debug, "  [Fail] I2C Pin Low (SDA:%d, SCL:%d)\r\n", i2c_bus.sda, i2c_bus.scl);
                        break;
                    }
                }
                
                // Also check identify_i2c pins if exists
                if (i2c_pins_high) {
                    for (const auto& i2c_id : device.identify_i2c) {
                        pinMode(i2c_id.sda, INPUT);
                        pinMode(i2c_id.scl, INPUT);
                        delay(1);
                        if (digitalRead(i2c_id.sda) == LOW || digitalRead(i2c_id.scl) == LOW) {
                            i2c_pins_high = false;
                            if (_debug >= debug_debug) LOG_PRINTF(debug_debug, "  [Fail] I2C Pin Low (SDA:%d, SCL:%d)\r\n", i2c_id.sda, i2c_id.scl);
                            break;
                        }
                    }
                }
                
                if (i2c_pins_high) {
                    current_score++;
                    if (_debug >= debug_debug) LOG_TEXT(debug_debug, "  [Pass] I2C Pins High (+1)\r\n");
                } else {
                    step_failed = true;
                }
            } else {
                current_score++;  // Still add score
                skip_count++;     // But count as skip (lower priority)
                if (_debug >= debug_debug) LOG_TEXT(debug_debug, "  [Skip] No I2C Pins to check (+1)\r\n");
            }
        }

        // 3. I2C MAP (Communication Test)
        if (!step_failed) {
            bool i2c_comm_match = true;
            int i2c_device_found_count = 0;
            int i2c_device_total_count = 0;
            int i2c_device_required_count = 0;
            
            // Check devices on i2c_checks buses
            for (const auto& i2c_bus : device.i2c_checks) {
                runPrerequisites(i2c_bus.prerequisites, i2c_bus.sda, i2c_bus.scl, -1, -1, -1, -1, i2c_bus.freq, i2c_bus.port);
                TwoWire i2c(i2c_bus.port);
                i2c.begin(i2c_bus.sda, i2c_bus.scl, i2c_bus.freq);
                
                // Enable internal pullup if configured (for buses without external pullup)
                if (i2c_bus.internal_pullup) {
                    pinMode(i2c_bus.sda, INPUT_PULLUP);
                    pinMode(i2c_bus.scl, INPUT_PULLUP);
                    delay(2); // Brief delay for pullup to stabilize
                }
                
                int bus_found_count = 0;
                bool bus_required_all_found = true;
                int bus_required_count = 0;
                for (const auto& detect : i2c_bus.detect) {
                    i2c_device_total_count++;
                    if (detect.required) bus_required_count++;
                    i2c.beginTransmission(detect.addr);
                    if (i2c.endTransmission() == 0) {
                        bus_found_count++;
                        i2c_device_found_count++;
                    } else {
                        if (detect.required) {
                            bus_required_all_found = false;
                            if (_debug >= debug_debug) LOG_PRINTF(debug_debug, "  [Fail] I2C Required device not found at addr 0x%02X\r\n", detect.addr);
                        } else {
                            if (_debug >= debug_debug) LOG_PRINTF(debug_debug, "  [Info] I2C Optional device not found at addr 0x%02X\r\n", detect.addr);
                        }
                    }
                }
                
                i2c_device_required_count += bus_required_count;
            
                if (!bus_required_all_found || bus_found_count < i2c_bus.detect_count) {
                    i2c_comm_match = false;
                    if (_debug >= debug_debug) LOG_PRINTF(debug_debug, "  [Fail] I2C Bus Check Failed. Found %d/%d, All-required: %s\r\n", bus_found_count, i2c_bus.detect_count, bus_required_all_found ? "yes" : "no");
                    break;
                }
            }
            
            // Check identify_i2c addresses
            for (const auto& i2c_id : device.identify_i2c) {
                i2c_device_total_count++;
                i2c_device_required_count++;
                TwoWire i2c(i2c_id.port);
                i2c.begin(i2c_id.sda, i2c_id.scl, i2c_id.freq);
                
                i2c.beginTransmission(i2c_id.addr);
                if (i2c.endTransmission() == 0) {
                    i2c_device_found_count++;
                } else {
                    i2c_comm_match = false;
                    if (_debug >= debug_debug) LOG_PRINTF(debug_debug, "  [Fail] I2C Comm Failed at addr 0x%02X\r\n", i2c_id.addr);
                }
                
                if (!i2c_comm_match) break;
            }
            
            if (i2c_device_total_count > 0) {
                if (i2c_comm_match) {
                    current_score++;
                    if (_debug >= debug_debug) LOG_PRINTF(debug_debug, "  [Pass] I2C Comm Match (+1) (%d/%d)\r\n", i2c_device_found_count, i2c_device_required_count);
                } else {
                    step_failed = true;
                }
            } else {
                current_score++;  // Still add score
                skip_count++;     // But count as skip (lower priority)
                if (_debug >= debug_debug) LOG_TEXT(debug_debug, "  [Skip] No I2C Comm to check (+1)\r\n");
            }
        }

        // 4. Additional Tests
        if (!step_failed) {
            bool additional_tests_passed = true;
            for (const auto& test : device.additional_tests) {
                bool pass = false;
                switch (test.type) {
                    case m5::autodetect::TEST_GPIO_READ:
                        if (test.pin_a >= 0) {
                            // pin_b as mode: 0=INPUT, 1=INPUT_PULLUP, 2=INPUT_PULLDOWN
                            if (test.pin_b == 1) pinMode(test.pin_a, INPUT_PULLUP);
                            else if (test.pin_b == 2) pinMode(test.pin_a, INPUT_PULLDOWN);
                            else pinMode(test.pin_a, INPUT);
                            
                            delay(1);
                            if (digitalRead(test.pin_a) == (int)test.expect) {
                                pass = true;
                            }
                        }
                        break;
                        
                    case m5::autodetect::TEST_I2C_READ_REG:
                    {
                        TwoWire i2c(test.port);
                        // pin_a=sda, pin_b=scl
                        i2c.begin(test.pin_a, test.pin_b, test.freq);
                        i2c.beginTransmission((uint8_t)test.addr);
                        i2c.write((uint8_t)test.reg);
                        if (i2c.endTransmission(false) == 0) {
                            i2c.requestFrom((uint8_t)test.addr, (uint8_t)1);
                            if (i2c.available()) {
                                uint8_t val = i2c.read();
                                if ((val & test.mask) == test.expect) {
                                    pass = true;
                                } else {
                                    if (_debug >= debug_verbose) LOG_PRINTF(debug_verbose, "    I2C Reg 0x%02X: Got 0x%02X, Exp 0x%02X\r\n", test.reg, val & test.mask, test.expect);
                                }
                            }
                        }
                    }
                    break;
                    
                    case m5::autodetect::TEST_SPI_READ_CMD:
                        {
                            // pin_a=mosi, pin_b=miso, pin_c=sclk, pin_d=cs
                            int mosi = test.pin_a;
                            int miso = test.pin_b;
                            int sclk = test.pin_c;
                            int cs = test.pin_d;
                            
                            if (mosi >= 0 && sclk >= 0 && cs >= 0) {
                                pinMode(cs, OUTPUT); digitalWrite(cs, HIGH);
                                pinMode(sclk, OUTPUT); digitalWrite(sclk, LOW);
                                pinMode(mosi, OUTPUT);
                                if (miso >= 0) pinMode(miso, INPUT);
                                
                                digitalWrite(cs, LOW);
                                
                                // Send Command (reg)
                                uint8_t cmd = (uint8_t)test.reg;
                                for (int i = 0; i < 8; i++) {
                                    digitalWrite(mosi, (cmd & 0x80) ? HIGH : LOW);
                                    digitalWrite(sclk, HIGH);
                                    digitalWrite(sclk, LOW);
                                    cmd <<= 1;
                                }
                                
                                // Read 1 byte
                                uint8_t val = 0;
                                for (int i = 0; i < 8; i++) {
                                    val <<= 1;
                                    digitalWrite(sclk, HIGH);
                                    if (miso >= 0 && digitalRead(miso)) val |= 1;
                                    digitalWrite(sclk, LOW);
                                }
                                
                                digitalWrite(cs, HIGH);
                                
                                if ((val & test.mask) == test.expect) {
                                    pass = true;
                                } else {
                                    if (_debug >= debug_verbose) LOG_PRINTF(debug_verbose, "    SPI Cmd 0x%02X: Got 0x%02X, Exp 0x%02X\r\n", test.reg, val & test.mask, test.expect);
                                }
                            }
                        }
                        break;
                }
                
                if (pass) {
                    current_score += test.score;
                    if (_debug >= debug_debug) LOG_PRINTF(debug_debug, "  [Pass] Additional Test %d (+%d)\r\n", test.type, test.score);
                } else {
                    if (_debug >= debug_debug) LOG_PRINTF(debug_debug, "  [Fail] Additional Test %d\r\n", test.type);
                    additional_tests_passed = false;
                    break;  // Stop on first failed additional test
                }
            }

            if (!additional_tests_passed) {
                step_failed = true;
            }
            
            // If no additional tests and all previous steps passed, give bonus point
            if (device.additional_tests.empty()) {
                current_score++;
                skip_count++;     // Count as skip (lower priority)
                if (_debug >= debug_debug) LOG_TEXT(debug_debug, "  [Skip] No Additional Tests (+1)\r\n");
            }
        }

        // 5. Screen parameters (SPI bit-bang + DSI DCS probing) — read screen ID before touch
        if (!step_failed) {
            bool screen_checked = false;
            bool screen_matched = false;
            bool screen_probe_skipped = false;
            for (const auto& disp : device.displays) {
                if (disp.bus_type == static_cast<int>(m5::autodetect::DisplayBusType::BUS_SPI)) {
                    runPrerequisites(disp.prerequisites, -1, -1, disp.pin_mosi, disp.pin_miso, disp.pin_sclk, disp.pin_cs, disp.freq);
                    if (disp.identify_cmd >= 0) {
                        screen_checked = true;
                        uint32_t id = readDisplayID(disp);
                        uint32_t mask = (disp.identify_mask == -1) ? 0xFFFFFFFF : (uint32_t)disp.identify_mask;
                        uint32_t expect = (uint32_t)disp.identify_expect;
                        if ((id & mask) == expect) {
                            screen_matched = true;
                            current_score++;
                            if (_debug >= debug_debug) LOG_PRINTF(debug_debug, "  [Pass] Screen ID Match (+1) (0x%06X)\r\n", id);
                        } else {
                            if (_debug >= debug_debug) LOG_PRINTF(debug_debug, "  [Fail] Screen ID Mismatch (Got: 0x%06X, Exp: 0x%06X)\r\n", id & mask, expect);
                        }
                    }
                }
                else if (disp.bus_type == static_cast<int>(m5::autodetect::DisplayBusType::BUS_I2C)) {
                    runPrerequisites(disp.prerequisites, disp.pin_mosi, disp.pin_miso, -1, -1, -1, -1, disp.freq);
                    if (disp.i2c_addr > 0 && disp.pin_mosi >= 0 && disp.pin_miso >= 0) {
                        const I2CIdentifyReadResult read_result = readDisplayID_I2C(disp);
                        if (!read_result.ok) {
                            screen_checked = true;
                            if (_debug >= debug_debug) {
                                if (disp.identify_cmd < 0) {
                                    LOG_PRINTF(debug_debug,
                                               "  [Fail] I2C Screen ACK failed (addr: 0x%02X)\r\n",
                                               disp.i2c_addr);
                                } else {
                                    LOG_PRINTF(debug_debug,
                                               "  [Fail] I2C Screen probe failed (addr: 0x%02X, reg: 0x%02X)\r\n",
                                               disp.i2c_addr, disp.identify_cmd & 0xFF);
                                }
                            }
                        } else if (disp.identify_cmd < 0) {
                            screen_checked = true;
                            screen_matched = true;
                            current_score++;
                            if (_debug >= debug_debug) {
                                LOG_PRINTF(debug_debug,
                                           "  [Pass] I2C Screen ACK Match (+1) (addr: 0x%02X)\r\n",
                                           disp.i2c_addr);
                            }
                        } else if (disp.identify_expect < 0) {
                            screen_probe_skipped = true;
                            current_score++;
                            skip_count++;
                            if (_debug >= debug_debug) {
                                const std::string raw_bytes = formatHexBytes(read_result.data, read_result.len);
                                LOG_PRINTF(debug_debug,
                                           "  [Info] I2C Screen ID raw read (%d bytes): %s (0x%0*X)\r\n",
                                           read_result.len, raw_bytes.c_str(),
                                           read_result.len * 2, read_result.value);
                                LOG_PRINTF(debug_debug,
                                           "  [Skip] I2C Screen ID telemetry-only (+1)\r\n");
                            }
                        } else {
                            screen_checked = true;
                            const uint32_t mask = (disp.identify_mask == -1) ? 0xFFFFFFFF : static_cast<uint32_t>(disp.identify_mask);
                            if ((read_result.value & mask) == static_cast<uint32_t>(disp.identify_expect)) {
                                screen_matched = true;
                                current_score++;
                                if (_debug >= debug_debug) {
                                    LOG_PRINTF(debug_debug,
                                               "  [Pass] I2C Screen ID Match (+1) (0x%0*X)\r\n",
                                               read_result.len * 2, read_result.value);
                                }
                            } else if (_debug >= debug_debug) {
                                LOG_PRINTF(debug_debug,
                                           "  [Fail] I2C Screen ID Mismatch (Got: 0x%0*X, Exp: 0x%0*X)\r\n",
                                           read_result.len * 2, read_result.value & mask,
                                           read_result.len * 2, static_cast<uint32_t>(disp.identify_expect));
                            }
                        }
                    }
                }
#if M5_AUTODETECT_DSI_SUPPORTED
                else if (disp.bus_type == static_cast<int>(m5::autodetect::DisplayBusType::BUS_DSI)
                         && disp.identify_cmd >= 0 && disp.dsi_lane_num > 0) {
                    uint32_t mask = (disp.identify_mask == -1) ? 0xFFFFFFFF : (uint32_t)disp.identify_mask;
                    const DsiIdentifyReadResult read_result = readDisplayID_DSI(disp);
                    if (!read_result.ok) {
                        screen_probe_skipped = true;
                        current_score++;
                        skip_count++;
                        if (_debug >= debug_debug) {
                            LOG_PRINTF(debug_debug,
                                       "  [Skip] DSI Screen ID read failed (cmd=0x%02X) (+1)\r\n",
                                       disp.identify_cmd & 0xFF);
                        }
                    } else if (disp.identify_expect < 0) {
                        // Telemetry-only: log raw ID but don't use for matching
                        screen_probe_skipped = true;
                        current_score++;
                        skip_count++;
                        if (_debug >= debug_debug) {
                            const std::string raw_bytes = formatHexBytes(read_result.data, read_result.len);
                            LOG_PRINTF(debug_debug,
                                       "  [Info] DSI Screen ID raw read (%d bytes): %s (0x%0*X)\r\n",
                                       read_result.len, raw_bytes.c_str(),
                                       read_result.len * 2, read_result.value);
                            LOG_PRINTF(debug_debug,
                                       "  [Skip] DSI Screen ID telemetry-only (+1)\r\n");
                        }
                    } else if ((read_result.value & mask) == static_cast<uint32_t>(disp.identify_expect)) {
                        screen_checked = true;
                        screen_matched = true;
                        current_score++;
                        if (_debug >= debug_debug) {
                            LOG_PRINTF(debug_debug,
                                       "  [Pass] DSI Screen ID Match (+1) (0x%0*X)\r\n",
                                       read_result.len * 2, read_result.value);
                        }
                    } else {
                        screen_checked = true;
                        if (_debug >= debug_debug) {
                            LOG_PRINTF(debug_debug,
                                       "  [Fail] DSI Screen ID Mismatch (Got: 0x%0*X, Exp: 0x%0*X)\r\n",
                                       read_result.len * 2, read_result.value & mask,
                                       read_result.len * 2, (uint32_t)disp.identify_expect);
                        }
                    }
                }
#endif
                else if (disp.bus_type != static_cast<int>(m5::autodetect::DisplayBusType::BUS_SPI)) {
                    // Non-SPI / non-DSI displays: skip
                    screen_probe_skipped = true;
                    current_score++;
                    skip_count++;
                    if (_debug >= debug_debug) LOG_PRINTF(debug_debug, "  [Skip] Display (%s, bus=%d) - no probe path (+1)\r\n", disp.driver, disp.bus_type);
                }
            }
            
            if (screen_checked && !screen_matched) {
                step_failed = true;
            } else if (!screen_checked && !screen_probe_skipped) {
                current_score++;  // No screen to check, give point
                skip_count++;     // But count as skip (lower priority)
                if (_debug >= debug_debug) LOG_TEXT(debug_debug, "  [Skip] No Screen ID to check (+1)\r\n");
            }
        }

        // 6. Touch Detection (I2C ACK/register or SPI command based touch panels)
        if (!step_failed) {
            bool touch_checked = false;
            bool touch_matched = false;
            
            for (const auto& touch : device.touches) {
                runPrerequisites(touch.prerequisites, touch.pin_sda, touch.pin_scl,
                                 touch.pin_mosi, touch.pin_miso, touch.pin_sclk, touch.pin_cs,
                                 touch.freq);

                if (touch.bus_type == static_cast<int>(m5::autodetect::DisplayBusType::BUS_I2C)
                    && touch.addr > 0 && touch.pin_sda >= 0 && touch.pin_scl >= 0) {
                    touch_checked = true;
                    
                    TwoWire i2c(0);  // Use I2C port 0 for touch
                    int freq = (touch.freq > 0) ? touch.freq : 400000;
                    i2c.begin(touch.pin_sda, touch.pin_scl, freq);
                    
                    i2c.beginTransmission(touch.addr);
                    if (i2c.endTransmission() == 0) {
                        touch_matched = true;
                        current_score++;
                        if (_debug >= debug_debug) LOG_PRINTF(debug_debug, "  [Pass] Touch I2C Match (+1) (addr: 0x%02X)\r\n", touch.addr);

                        // Identify by register value if configured (e.g. fw_version to distinguish ST7121/ST7123)
                        if (touch.identify_reg >= 0) {
                            bool ident_ok = false;
                            uint8_t reg_val = 0;
                            TouchIdentifyReadPath read_path = TouchIdentifyReadPath::RawI2C;
                            if (readTouchIdentifyReg(i2c, touch, &reg_val, &read_path)) {
                                uint32_t mask = (touch.identify_mask < 0) ? 0xFF : (uint32_t)touch.identify_mask;
                                uint32_t expect = (uint32_t)touch.identify_expect & mask;
                                if ((reg_val & mask) == expect) {
                                    ident_ok = true;
                                    if (_debug >= debug_debug) LOG_PRINTF(debug_debug, "  [Pass] Touch ID Reg[0x%04X]=0x%02X (%s)\r\n", touch.identify_reg, reg_val, touchIdentifyReadPathName(read_path));
                                } else {
                                    if (_debug >= debug_debug) LOG_PRINTF(debug_debug, "  [Fail] Touch ID Reg Mismatch (reg[0x%04X] Got: 0x%02X, Exp: 0x%02X, via %s)\r\n", touch.identify_reg, (uint8_t)(reg_val & mask), (uint8_t)expect, touchIdentifyReadPathName(read_path));
                                }
                            } else {
                                if (_debug >= debug_debug) LOG_PRINTF(debug_debug, "  [Fail] Touch ID Reg Read Failed (reg: 0x%04X)\r\n", touch.identify_reg);
                            }
                            if (!ident_ok) {
                                touch_matched = false;
                                current_score--;
                                step_failed = true;
                            }
                        }
                    } else {
                        if (_debug >= debug_debug) LOG_PRINTF(debug_debug, "  [Fail] Touch I2C Failed (addr: 0x%02X)\r\n", touch.addr);
                    }
                    break;  // Only check first touch config
                }

                if (touch.bus_type == static_cast<int>(m5::autodetect::DisplayBusType::BUS_SPI)
                    && touch.pin_mosi >= 0 && touch.pin_sclk >= 0 && touch.pin_cs >= 0
                    && touch.identify_reg >= 0) {
                    touch_checked = true;

                    uint8_t reg_val = 0;
                    if (readTouchIdentifyRegSpi(touch, &reg_val)) {
                        uint32_t mask = (touch.identify_mask < 0) ? 0xFF : static_cast<uint32_t>(touch.identify_mask);
                        uint32_t expect = static_cast<uint32_t>(touch.identify_expect) & mask;
                        if ((reg_val & mask) == expect) {
                            touch_matched = true;
                            current_score++;
                            if (_debug >= debug_debug) {
                                LOG_PRINTF(debug_debug,
                                           "  [Pass] Touch SPI ID Match (+1) (cmd: 0x%02X, val: 0x%02X)\r\n",
                                           touch.identify_reg & 0xFF, reg_val);
                            }
                        } else if (_debug >= debug_debug) {
                            LOG_PRINTF(debug_debug,
                                       "  [Fail] Touch SPI ID Mismatch (cmd[0x%02X] Got: 0x%02X, Exp: 0x%02X)\r\n",
                                       touch.identify_reg & 0xFF,
                                       static_cast<uint8_t>(reg_val & mask),
                                       static_cast<uint8_t>(expect));
                        }
                    } else if (_debug >= debug_debug) {
                        LOG_PRINTF(debug_debug,
                                   "  [Fail] Touch SPI ID Read Failed (cmd: 0x%02X)\r\n",
                                   touch.identify_reg & 0xFF);
                    }
                    break;
                }
            }
            
            if (touch_checked && !touch_matched) {
                step_failed = true;
            } else if (!touch_checked) {
                current_score++;  // No touch to check, give point
                skip_count++;     // But count as skip (lower priority)
                if (_debug >= debug_debug) LOG_TEXT(debug_debug, "  [Skip] No Touch to check (+1)\r\n");
            }
        }

        if (step_failed) {
            if (_debug >= debug_debug) LOG_TEXT(debug_debug, "  [Result] Failed at some step. Discarding.\r\n");
            continue;
        }

        if (_debug >= debug_debug) {
            LOG_PRINTF(debug_debug, "  Total Score: %d (Skips: %d)\r\n", current_score, skip_count);
        }

        // Compare: higher score wins, if equal score then fewer skips wins
        if (current_score > max_score || 
            (current_score == max_score && skip_count < min_skip_count)) {
            max_score = current_score;
            min_skip_count = skip_count;
            best_device = &device;
        }
    }
    
    if (_debug >= debug_info) {
        LOG_TEXT(debug_info, "=== Detection Result ===\r\n");
        if (best_device) {
            LOG_PRINTF(debug_info, "Best Match: %s (Score: %d, Skips: %d)\r\n", best_device->name, max_score, min_skip_count);
            LOG_PRINTF(debug_info, "Board ID: %d (%s)\r\n", best_device->board_id, m5::autodetect::getBoardName(best_device->board_id));
            LOG_PRINTF(debug_info, "SKU: %s\r\n", best_device->sku);
        } else {
            LOG_TEXT(debug_warn, "No matching device found.\r\n");
        }
    }

    _device_info = best_device;
    return _device_info;
}

const m5::autodetect::DeviceInfo* M5Autodetect::getDetectedInfo() const {
    return _device_info;
}

m5::autodetect::board_t M5Autodetect::getBoard() const {
    if (_device_info) {
        return _device_info->board_id;
    }
    return m5::autodetect::board_unknown;
}

const char* M5Autodetect::getBoardName() const {
    if (_device_info) {
        return m5::autodetect::getBoardName(_device_info->board_id);
    }
    return "Unknown";
}

bool M5Autodetect::boardHasPsram() const {
    return _device_info ? _device_info->psram_enabled : false;
}

bool M5Autodetect::isPsramDetected() const {
    return psramFound() || ESP.getPsramSize() > 0;
}

const char* M5Autodetect::getPsramStatusText() const {
    const bool board_has_psram = boardHasPsram();
    const bool psram_detected = isPsramDetected();

    if (board_has_psram && psram_detected) {
        return "Present and enabled";
    }
    if (board_has_psram && !psram_detected) {
        return "Present but not enabled";
    }
    if (!board_has_psram && psram_detected) {
        return "Detected";
    }
    return "Not present";
}

m5::autodetect::Bus* M5Autodetect::createBus(const m5::autodetect::BusConfig& config) {
    switch (config.type) {
        case m5::autodetect::BusType::I2C:
            return new m5::autodetect::I2CBus(config);
        case m5::autodetect::BusType::SPI:
            return new m5::autodetect::SPIBus(config);
        default:
            return nullptr;
    }
}
