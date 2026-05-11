#include "M5Autodetect_DeviceData.h"

namespace m5 {
namespace autodetect {

const std::vector<DeviceInfo> devices_data = {
    {
        "M5AtomS3R",
        "SKU:C126",
        "ESP32-S3",
        board_M5AtomS3R,
        false,
        2,
        {
            { 45, 0, 1 },
            { 0, 0, 1 },
        },
        {
            { 0, 45, 0, 400000, 2, false, {
                { 0x68, true },
                { 0x30, true },
            }, {}, true },
        },
        {
        },
        {
            { "gc9107", 0, 128, 128, 40000000, 21, -1, 15, 14, 42, 48, -1, 0x00, nullptr, "I2C(45,0)@0x30", 4, 9504767, 16777215, true, 120, 0, 0, 0, 0, 0, static_cast<DSIIdentifyReadMode>(0), 0, 1, {} },
        },
        {
        },
        {
        }
    },
    {
        "M5AtomEchoS3R",
        "SKU:C126-ECHO",
        "ESP32-S3",
        board_M5AtomEchoS3R,
        false,
        2,
        {
            { 45, 0, 1 },
            { 0, 0, 1 },
        },
        {
            { 0, 45, 0, 400000, 1, false, {
                { 0x18, true },
            }, {}, true },
        },
        {
        },
        {
        },
        {
        },
        {
        }
    },
    {
        "M5AtomS3",
        "SKU:C123",
        "ESP32-S3",
        board_M5AtomS3,
        false,
        2,
        {
            { 38, 0, 1 },
            { 39, 0, 1 },
        },
        {
            { 0, 38, 39, 400000, 1, false, {
                { 0x68, true },
            }, {}, true },
        },
        {
        },
        {
            { "gc9107", 0, 128, 128, 40000000, 21, -1, 17, 15, 33, 34, 16, 0x00, nullptr, nullptr, 4, 9504767, 16777215, true, 120, 0, 0, 0, 0, 0, static_cast<DSIIdentifyReadMode>(0), 0, 1, {} },
        },
        {
        },
        {
        }
    },
    {
        "M5AtomS3Lite",
        "SKU:C124",
        "ESP32-S3",
        board_M5AtomS3Lite,
        false,
        2,
        {
            { 38, 0, 1 },
            { 39, 0, 1 },
        },
        {
            { 0, 38, 39, 400000, 0, false, {
            }, {}, true },
        },
        {
        },
        {
        },
        {
        },
        {
        }
    },
    {
        "M5Tab5_ST7121",
        "SKU:C145/K145",
        "ESP32-P4",
        board_M5Tab5_ST7121,
        true,
        9,
        {
            { 21, 0, 1 },
            { 23, 0, 1 },
            { 29, 0, 1 },
            { 31, 0, 1 },
            { 32, 0, 1 },
            { 39, 0, 1 },
            { 40, 0, 1 },
            { 41, 0, 1 },
            { 42, 0, 1 },
            { 43, 0, 1 },
            { 44, 0, 1 },
        },
        {
            { 0, 31, 32, 400000, 7, false, {
                { 0x10, true },
                { 0x32, true },
                { 0x40, true },
                { 0x41, true },
                { 0x43, true },
                { 0x44, true },
                { 0x68, true },
            }, {
            { PrereqType::I2C_WRITE, -1, 0, 0x43, 0x03, 0x00, {0x30}, 0, 10 },
            { PrereqType::I2C_WRITE, -1, 0, 0x43, 0x05, 0x00, {0x30}, 0, 10 },
            { PrereqType::I2C_WRITE, -1, 0, 0x43, 0x07, 0x00, {0x00}, 0, 10 },
        }, false },
        },
        {
        },
        {
            { "ST7121", 5, 720, 1280, 0, -1, -1, -1, -1, -1, -1, -1, 0x00, nullptr, nullptr, 244, 28963, 65535, false, 0, 0, 2, 1040, 3, 2500, static_cast<DSIIdentifyReadMode>(0), 0, 1, {} },
        },
        {
            { "ST7121", 1, 0x55, 720, 1280, 400000, 31, 32, 23, -1, nullptr, -1, -1, -1, -1, {}, 0, 1, 65535 },
        },
        {
        }
    },
    {
        "M5Tab5_ST7123",
        "SKU:C145/K145",
        "ESP32-P4",
        board_M5Tab5_ST7123,
        true,
        9,
        {
            { 21, 0, 1 },
            { 23, 0, 1 },
            { 29, 0, 1 },
            { 31, 0, 1 },
            { 32, 0, 1 },
            { 39, 0, 1 },
            { 40, 0, 1 },
            { 41, 0, 1 },
            { 42, 0, 1 },
            { 43, 0, 1 },
            { 44, 0, 1 },
        },
        {
            { 0, 31, 32, 400000, 7, false, {
                { 0x10, true },
                { 0x32, true },
                { 0x40, true },
                { 0x41, true },
                { 0x43, true },
                { 0x44, true },
                { 0x68, true },
            }, {
            { PrereqType::I2C_WRITE, -1, 0, 0x43, 0x03, 0x00, {0x30}, 0, 10 },
            { PrereqType::I2C_WRITE, -1, 0, 0x43, 0x05, 0x00, {0x30}, 0, 10 },
            { PrereqType::I2C_WRITE, -1, 0, 0x43, 0x07, 0x00, {0x00}, 0, 10 },
        }, false },
        },
        {
        },
        {
            { "ST7123", 5, 720, 1280, 0, -1, -1, -1, -1, -1, -1, -1, 0x00, nullptr, nullptr, 244, 28963, 65535, false, 0, 0, 2, 1040, 3, 2500, static_cast<DSIIdentifyReadMode>(0), 0, 1, {
            { PrereqType::I2C_WRITE, -1, 0, 0x43, 0x03, 0x00, {0x7F}, 0, 10 },
            { PrereqType::I2C_WRITE, -1, 0, 0x43, 0x07, 0x00, {0x00}, 0, 10 },
            { PrereqType::I2C_WRITE, -1, 0, 0x43, 0x05, 0x00, {0x74}, 0, 10 },
            { PrereqType::I2C_WRITE, -1, 0, 0x43, 0x05, 0x00, {0x44}, 0, 100 },
            { PrereqType::I2C_WRITE, -1, 0, 0x43, 0x05, 0x00, {0x74}, 0, 100 },
        } },
        },
        {
            { "ST7123", 1, 0x55, 720, 1280, 400000, 31, 32, 23, -1, nullptr, -1, -1, -1, -1, {}, 0, 3, 65535 },
        },
        {
        }
    },
    {
        "M5Tab5_IlI9881c",
        "SKU:C145/K145",
        "ESP32-P4",
        board_M5Tab5_IlI9881c,
        true,
        10,
        {
            { 21, 0, 1 },
            { 29, 0, 1 },
            { 31, 0, 1 },
            { 32, 0, 1 },
            { 39, 0, 1 },
            { 40, 0, 1 },
            { 41, 0, 1 },
            { 42, 0, 1 },
            { 43, 0, 1 },
            { 44, 0, 1 },
        },
        {
            { 0, 31, 32, 400000, 7, false, {
                { 0x10, true },
                { 0x32, true },
                { 0x40, true },
                { 0x41, true },
                { 0x43, true },
                { 0x44, true },
                { 0x68, true },
                { 0x14, false },
            }, {
            { PrereqType::GPIO_WRITE, 23, 1, 0x00, 0x00, 0x00, {0x00}, 0, 10 },
            { PrereqType::I2C_WRITE, -1, 0, 0x43, 0x03, 0x00, {0x30}, 0, 10 },
            { PrereqType::I2C_WRITE, -1, 0, 0x43, 0x05, 0x00, {0x30}, 0, 10 },
            { PrereqType::I2C_WRITE, -1, 0, 0x43, 0x07, 0x00, {0x00}, 0, 10 },
        }, false },
        },
        {
        },
        {
            { "ILI9881C", 5, 720, 1280, 0, -1, -1, -1, -1, -1, -1, -1, 0x00, nullptr, nullptr, 0, 39041, 65535, false, 0, 0, 2, 730, 3, 2500, static_cast<DSIIdentifyReadMode>(2), 2, 1, {
            { PrereqType::I2C_WRITE, -1, 0, 0x43, 0x03, 0x00, {0x7F}, 0, 10 },
            { PrereqType::I2C_WRITE, -1, 0, 0x43, 0x07, 0x00, {0x00}, 0, 10 },
            { PrereqType::I2C_WRITE, -1, 0, 0x43, 0x05, 0x00, {0x74}, 0, 10 },
            { PrereqType::I2C_WRITE, -1, 0, 0x43, 0x05, 0x00, {0x44}, 0, 10 },
            { PrereqType::I2C_WRITE, -1, 0, 0x43, 0x05, 0x00, {0x74}, 0, 10 },
            { PrereqType::DSI_WRITE, -1, 0, 0x00, 0x00, 0xFF, {0x98, 0x81, 0x01}, 0, 5 },
        } },
        },
        {
        },
        {
        }
    },
    {
        "M5AtomLite",
        "SKU:C008",
        "ESP32",
        board_M5AtomLite,
        false,
        1,
        {
            { 39, 0, 1 },
        },
        {
        },
        {
        },
        {
        },
        {
        },
        {
        }
    },
    {
        "M5AtomMatrix",
        "SKU:C008-B",
        "ESP32",
        board_M5AtomMatrix,
        false,
        2,
        {
            { 25, 0, 1 },
            { 21, 0, 1 },
        },
        {
            { 0, 25, 21, 400000, 1, false, {
                { 0x68, true },
            }, {}, true },
        },
        {
        },
        {
        },
        {
        },
        {
        }
    },
};

} // namespace autodetect
} // namespace m5