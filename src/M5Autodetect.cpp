#include "M5Autodetect.h"
#include "M5Autodetect_Data.h"
#include <Arduino.h>
#include <Wire.h>

// Helper macro for debug printing (only prints if _serial is set)
#define DBG_PRINT(fmt, ...) do { if (_serial) _serial->print(fmt); } while(0)
#define DBG_PRINTF(fmt, ...) do { if (_serial) _serial->printf(fmt, ##__VA_ARGS__); } while(0)

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

M5Autodetect::M5Autodetect() {
}

void M5Autodetect::begin(debug_t debug, Print* serial) {
    _debug = debug;
    _serial = serial;
}

const m5::autodetect::DeviceInfo* M5Autodetect::detect() {
    String chipModel = ESP.getChipModel();
    const m5::autodetect::DeviceInfo* best_device = nullptr;
    int max_score = -1;
    int min_skip_count = 999;  // Lower is better (fewer skips = higher priority)
    
    if (_debug >= debug_basic) {
        DBG_PRINT("\r\n");
        DBG_PRINT("=== Autodetect Start ===\r\n");
        DBG_PRINTF("Chip Model: %s\r\n", chipModel.c_str());
        DBG_PRINT("\r\n");
    }

    for (const auto& device : m5::autodetect::devices_data) {
        int current_score = 0;
        int skip_count = 0;  // Track number of skipped steps (fewer = higher priority)
        bool step_failed = false;  // Track if any step failed
        
        if (_debug >= debug_verbose) {
            DBG_PRINT("-------------------\r\n");
            DBG_PRINTF("Checking: %s (%s)\r\n", device.name, device.sku);
        }

        // 1. SOC
        if (chipModel.indexOf(device.mcu) != -1) {
            current_score++;
            if (_debug >= debug_verbose) DBG_PRINT("  [Pass] SOC Match (+1)\r\n");
        } else {
            if (_debug >= debug_verbose) DBG_PRINTF("  [Fail] SOC Mismatch (Expected: %s, Got: %s)\r\n", device.mcu, chipModel.c_str());
            continue;  // SOC mismatch, skip this device entirely
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
                if (_debug >= debug_verbose) DBG_PRINTF("  [Fail] Pin %d check failed. Expected %d, got %d\r\n", pinCheck.gpio, pinCheck.expect, val);
            }
        }
        if (pin_match_count >= device.check_pins_count) {
            current_score++;
            if (_debug >= debug_verbose) DBG_PRINTF("  [Pass] IOMAP Match (+1) (%d/%d)\r\n", pin_match_count, device.check_pins_count);
        } else {
            step_failed = true;
            if (_debug >= debug_verbose) DBG_PRINTF("  [Fail] IOMAP Match (%d/%d)\r\n", pin_match_count, device.check_pins_count);
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
                        if (_debug >= debug_verbose) DBG_PRINTF("  [Fail] I2C Pin Low (SDA:%d, SCL:%d)\r\n", i2c_bus.sda, i2c_bus.scl);
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
                            if (_debug >= debug_verbose) DBG_PRINTF("  [Fail] I2C Pin Low (SDA:%d, SCL:%d)\r\n", i2c_id.sda, i2c_id.scl);
                            break;
                        }
                    }
                }
                
                if (i2c_pins_high) {
                    current_score++;
                    if (_debug >= debug_verbose) DBG_PRINT("  [Pass] I2C Pins High (+1)\r\n");
                } else {
                    step_failed = true;
                }
            } else {
                current_score++;  // Still add score
                skip_count++;     // But count as skip (lower priority)
                if (_debug >= debug_verbose) DBG_PRINT("  [Skip] No I2C Pins to check (+1)\r\n");
            }
        }

        // 4. I2C MAP (Communication Test)
        if (!step_failed) {
            bool i2c_comm_match = true;
            int i2c_device_found_count = 0;
            int i2c_device_total_count = 0;
            int i2c_device_required_count = 0;
            
            // Check devices on i2c_checks buses
            for (const auto& i2c_bus : device.i2c_checks) {
                TwoWire i2c(i2c_bus.port);
                i2c.begin(i2c_bus.sda, i2c_bus.scl, i2c_bus.freq);
                
                // Enable internal pullup if configured (for buses without external pullup)
                if (i2c_bus.internal_pullup) {
                    pinMode(i2c_bus.sda, INPUT_PULLUP);
                    pinMode(i2c_bus.scl, INPUT_PULLUP);
                    delay(2); // Brief delay for pullup to stabilize
                }
                
                int bus_found_count = 0;
                for (const auto& detect : i2c_bus.detect) {
                    i2c_device_total_count++;
                    i2c.beginTransmission(detect.addr);
                    if (i2c.endTransmission() == 0) {
                        bus_found_count++;
                        i2c_device_found_count++;
                    } else {
                        if (_debug >= debug_verbose) DBG_PRINTF("  [Fail] I2C Comm Failed at addr 0x%02X\r\n", detect.addr);
                    }
                }
                
                i2c_device_required_count += i2c_bus.detect_count;
            
                if (bus_found_count < i2c_bus.detect_count) {
                    i2c_comm_match = false;
                    if (_debug >= debug_verbose) DBG_PRINTF("  [Fail] I2C Bus Check Failed. Found %d, Needed %d\r\n", bus_found_count, i2c_bus.detect_count);
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
                    if (_debug >= debug_verbose) DBG_PRINTF("  [Fail] I2C Comm Failed at addr 0x%02X\r\n", i2c_id.addr);
                }
                
                if (!i2c_comm_match) break;
            }
            
            if (i2c_device_total_count > 0) {
                if (i2c_comm_match) {
                    current_score++;
                    if (_debug >= debug_verbose) DBG_PRINTF("  [Pass] I2C Comm Match (+1) (%d/%d)\r\n", i2c_device_found_count, i2c_device_required_count);
                } else {
                    step_failed = true;
                }
            } else {
                current_score++;  // Still add score
                skip_count++;     // But count as skip (lower priority)
                if (_debug >= debug_verbose) DBG_PRINT("  [Skip] No I2C Comm to check (+1)\r\n");
            }
        }

        // 5. Screen parameters
        if (!step_failed) {
            bool screen_checked = false;
            bool screen_matched = false;
            for (const auto& disp : device.displays) {
                if (disp.identify_cmd >= 0) {
                    screen_checked = true;
                    uint32_t id = readDisplayID(disp);
                    uint32_t mask = (disp.identify_mask == -1) ? 0xFFFFFFFF : (uint32_t)disp.identify_mask;
                    uint32_t expect = (uint32_t)disp.identify_expect;
                    
                    if ((id & mask) == expect) {
                        screen_matched = true;
                        current_score++;
                        if (_debug >= debug_verbose) DBG_PRINTF("  [Pass] Screen ID Match (+1) (0x%06X)\r\n", id);
                    } else {
                        if (_debug >= debug_verbose) DBG_PRINTF("  [Fail] Screen ID Mismatch (Got: 0x%06X, Exp: 0x%06X)\r\n", id & mask, expect);
                    }
                }
            }
            
            if (screen_checked && !screen_matched) {
                step_failed = true;
            } else if (!screen_checked) {
                current_score++;  // No screen to check, give point
                skip_count++;     // But count as skip (lower priority)
                if (_debug >= debug_verbose) DBG_PRINT("  [Skip] No Screen ID to check (+1)\r\n");
            }
        }

        // 6. Additional Tests
        if (!step_failed) {
            bool additional_test_failed = false;
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
                                    if (_debug >= debug_verbose) DBG_PRINTF("    I2C Reg 0x%02X: Got 0x%02X, Exp 0x%02X\r\n", test.reg, val & test.mask, test.expect);
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
                                    if (_debug >= debug_verbose) DBG_PRINTF("    SPI Cmd 0x%02X: Got 0x%02X, Exp 0x%02X\r\n", test.reg, val & test.mask, test.expect);
                                }
                            }
                        }
                        break;
                }
                
                if (pass) {
                    current_score += test.score;
                    if (_debug >= debug_verbose) DBG_PRINTF("  [Pass] Additional Test %d (+%d)\r\n", test.type, test.score);
                } else {
                    additional_test_failed = true;
                    if (_debug >= debug_verbose) DBG_PRINTF("  [Fail] Additional Test %d\r\n", test.type);
                    break;  // Stop on first failed additional test
                }
            }
            
            // If no additional tests and all previous steps passed, give bonus point
            if (device.additional_tests.empty()) {
                current_score++;
                skip_count++;     // Count as skip (lower priority)
                if (_debug >= debug_verbose) DBG_PRINT("  [Skip] No Additional Tests (+1)\r\n");
            }
        }  // end of if (!step_failed) for Step 6

        if (_debug >= debug_verbose) {
            DBG_PRINTF("  Total Score: %d (Skips: %d)\r\n", current_score, skip_count);
        }

        // Compare: higher score wins, if equal score then fewer skips wins
        if (current_score > max_score || 
            (current_score == max_score && skip_count < min_skip_count)) {
            max_score = current_score;
            min_skip_count = skip_count;
            best_device = &device;
        }
    }
    
    if (_debug >= debug_basic) {
        DBG_PRINT("\r\n");
        DBG_PRINT("=== Detection Result ===\r\n");
        if (best_device) {
            DBG_PRINTF("Best Match: %s (Score: %d, Skips: %d)\r\n", best_device->name, max_score, min_skip_count);
        } else {
            DBG_PRINT("No matching device found.\r\n");
        }
        DBG_PRINT("\r\n");
    }

    _device_info = best_device;
    return _device_info;
}

const m5::autodetect::DeviceInfo* M5Autodetect::getDetectedInfo() const {
    return _device_info;
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
