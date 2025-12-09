#include "M5Autodetect_Data.h"

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
                { 0x68 },
                { 0x30 },
            }, {} },
        },
        {
        },
        {
            { "gc9107", 0, 128, 128, 40000000, 21, -1, 15, 14, 42, 48, -1, 0x00, nullptr, "I2C(45,0)@0x30", 4, 9504767, 16777215, true, 120, {} },
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
                { 0x18 },
            }, {} },
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
                { 0x68 },
            }, {} },
        },
        {
        },
        {
            { "gc9107", 0, 128, 128, 40000000, 21, -1, 17, 15, 33, 34, 16, 0x00, nullptr, nullptr, 4, 9504767, 16777215, true, 120, {} },
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
            }, {} },
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
        "M5Tab5 (ST7123)",
        "SKU:C145/K145",
        "ESP32-P4",
        board_M5Tab5_ST7123,
        true,
        12,
        {
            { 21, 0, 1 },
            { 23, 0, 1 },
            { 29, 0, 1 },
            { 31, 0, 1 },
            { 32, 0, 1 },
            { 33, 0, 1 },
            { 39, 0, 1 },
            { 40, 0, 1 },
            { 41, 0, 1 },
            { 42, 0, 1 },
            { 43, 0, 1 },
            { 44, 0, 1 },
        },
        {
            { 0, 31, 32, 400000, 8, false, {
                { 0x10 },
                { 0x32 },
                { 0x40 },
                { 0x41 },
                { 0x43 },
                { 0x44 },
                { 0x68 },
                { 0x55 },
            }, {
            { PrereqType::I2C_WRITE, -1, 0, 0x43, 0x03, 0x00, 0x30, 0 },
            { PrereqType::I2C_WRITE, -1, 0, 0x43, 0x05, 0x00, 0x30, 0 },
            { PrereqType::I2C_WRITE, -1, 0, 0x43, 0x07, 0x00, 0x00, 0 },
        } },
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
        "M5Tab5 (IlI9881c)",
        "SKU:C145/K145",
        "ESP32-P4",
        board_M5Tab5_IlI9881c,
        true,
        12,
        {
            { 21, 0, 1 },
            { 23, 0, 1 },
            { 29, 0, 1 },
            { 31, 0, 1 },
            { 32, 0, 1 },
            { 33, 0, 1 },
            { 39, 0, 1 },
            { 40, 0, 1 },
            { 41, 0, 1 },
            { 42, 0, 1 },
            { 43, 0, 1 },
            { 44, 0, 1 },
        },
        {
            { 0, 31, 32, 400000, 8, false, {
                { 0x10 },
                { 0x32 },
                { 0x40 },
                { 0x41 },
                { 0x43 },
                { 0x44 },
                { 0x68 },
                { 0x14 },
            }, {
            { PrereqType::I2C_WRITE, -1, 0, 0x43, 0x03, 0x00, 0x30, 0 },
            { PrereqType::I2C_WRITE, -1, 0, 0x43, 0x05, 0x00, 0x30, 0 },
            { PrereqType::I2C_WRITE, -1, 0, 0x43, 0x07, 0x00, 0x00, 0 },
        } },
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
                { 0x68 },
            }, {} },
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