#ifndef M5_AUTODETECT_DATA_H
#define M5_AUTODETECT_DATA_H

#include <stdint.h>
#include <vector>

namespace m5 {
namespace autodetect {

enum board_t {
    board_unknown = -1,
    board_M5AtomS3R,
    board_M5AtomEchoS3R,
    board_M5AtomS3,
    board_M5AtomS3Lite,
    board_M5Tab5_ST7123,
    board_M5Tab5_IlI9881c,
    board_M5AtomLite,
    board_M5AtomMatrix,
};

inline const char* getBoardName(board_t board) {
    switch (board) {
        case board_M5AtomS3R: return "M5AtomS3R";
        case board_M5AtomEchoS3R: return "M5AtomEchoS3R";
        case board_M5AtomS3: return "M5AtomS3";
        case board_M5AtomS3Lite: return "M5AtomS3Lite";
        case board_M5Tab5_ST7123: return "M5Tab5_ST7123";
        case board_M5Tab5_IlI9881c: return "M5Tab5_IlI9881c";
        case board_M5AtomLite: return "M5AtomLite";
        case board_M5AtomMatrix: return "M5AtomMatrix";
        default: return "Unknown";
    }
}

struct PinCheck {
    int gpio;
    int mode; // 0: input, 1: input_pullup, 2: input_pulldown
    int expect; // 0 or 1
};

struct I2CDetect {
    uint8_t addr;
};

struct I2CBusCheck {
    int port;
    int sda;
    int scl;
    uint32_t freq;
    int detect_count;
    bool internal_pullup;
    std::vector<I2CDetect> detect;
};

struct I2CIdentify {
    int port;
    int sda;
    int scl;
    uint32_t freq;
    uint8_t addr;
};

struct DisplayConfig {
    const char* driver;
    int width;
    int height;
    int freq;
    int pin_mosi;
    int pin_miso;
    int pin_sclk;
    int pin_cs;
    int pin_dc;
    int pin_rst;
    int pin_bl;
    const char* pin_rst_str;
    const char* pin_bl_str;
    int identify_cmd;
    int identify_expect;
    int identify_mask;
    bool identify_rst_before;
    int identify_rst_wait;
};

struct TouchConfig {
    const char* driver;
    int addr;
    int width;
    int height;
    int freq;
    int pin_sda;
    int pin_scl;
    int pin_int;
    int pin_rst;
    const char* pin_rst_str;
};

enum TestType {
    TEST_GPIO_READ = 0,
    TEST_I2C_READ_REG = 1,
    TEST_SPI_READ_CMD = 2,
};

struct AdHocTest {
    int type;
    uint32_t score;
    int port;
    int pin_a;
    int pin_b;
    int pin_c;
    int pin_d;
    uint32_t freq;
    uint32_t addr;
    uint32_t reg;
    uint32_t mask;
    uint32_t expect;
};

struct DeviceInfo {
    const char* name;
    const char* sku;
    const char* mcu;
    board_t board_id;
    int check_pins_count;
    const std::vector<PinCheck> check_pins;
    const std::vector<I2CBusCheck> i2c_checks;
    const std::vector<I2CIdentify> identify_i2c;
    const std::vector<DisplayConfig> displays;
    const std::vector<TouchConfig> touches;
    const std::vector<AdHocTest> additional_tests;
};

extern const std::vector<DeviceInfo> devices_data;

} // namespace autodetect
} // namespace m5

#endif // M5_AUTODETECT_DATA_H