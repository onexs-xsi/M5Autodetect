#include "M5Autodetect.h"
#include "M5Autodetect_Data.h"
#include <Arduino.h>
#include <Wire.h>

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

void M5Autodetect::begin(debug_t debug) {
    _debug = debug;
}

const m5::autodetect::DeviceInfo* M5Autodetect::detect() {
    String chipModel = ESP.getChipModel();
    const m5::autodetect::DeviceInfo* best_device = nullptr;
    int max_score = -1;
    
    if (_debug >= debug_basic) {
        Serial.print("\r\n");
        Serial.print("=== Autodetect Start ===\r\n");
        Serial.printf("Chip Model: %s\r\n", chipModel.c_str());
        Serial.print("\r\n");
    }

    for (const auto& device : m5::autodetect::devices_data) {
        int current_score = 0;
        if (_debug >= debug_verbose) {
            Serial.print("-------------------\r\n");
            Serial.printf("Checking: %s (%s)\r\n", device.name, device.sku);
        }

        // 1. SOC
        if (chipModel.indexOf(device.mcu) != -1) {
            current_score++;
            if (_debug >= debug_verbose) Serial.print("  [Pass] SOC Match (+1)\r\n");
        } else {
            if (_debug >= debug_verbose) Serial.printf("  [Fail] SOC Mismatch (Expected: %s, Got: %s)\r\n", device.mcu, chipModel.c_str());
            continue;
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
                if (_debug >= debug_verbose) Serial.printf("  [Fail] Pin %d check failed. Expected %d, got %d\r\n", pinCheck.gpio, pinCheck.expect, val);
            }
        }
        if (pin_match_count >= device.check_pins_count) {
            current_score++;
            if (_debug >= debug_verbose) Serial.printf("  [Pass] IOMAP Match (+1) (%d/%d)\r\n", pin_match_count, device.check_pins_count);
        }

        // 3. Internal I2C pins High
        bool i2c_pins_high = true;
        bool has_i2c_to_check = !device.i2c_checks.empty() || !device.identify_i2c.empty();
        
        if (has_i2c_to_check) {
            // Check i2c_checks pins
            for (const auto& i2c_bus : device.i2c_checks) {
                pinMode(i2c_bus.sda, INPUT);
                pinMode(i2c_bus.scl, INPUT);
                delay(1);
                if (digitalRead(i2c_bus.sda) == LOW || digitalRead(i2c_bus.scl) == LOW) {
                    i2c_pins_high = false;
                    if (_debug >= debug_verbose) Serial.printf("  [Fail] I2C Pin Low (SDA:%d, SCL:%d)\r\n", i2c_bus.sda, i2c_bus.scl);
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
                        if (_debug >= debug_verbose) Serial.printf("  [Fail] I2C Pin Low (SDA:%d, SCL:%d)\r\n", i2c_id.sda, i2c_id.scl);
                        break;
                    }
                }
            }
            
            if (i2c_pins_high) {
                current_score++;
                if (_debug >= debug_verbose) Serial.print("  [Pass] I2C Pins High (+1)\r\n");
            }
        } else {
             if (_debug >= debug_verbose) Serial.print("  [Skip] No I2C Pins to check\r\n");
        }

        // 4. I2C MAP (Communication Test)
        bool i2c_comm_match = true;
        int i2c_device_found_count = 0;
        int i2c_device_total_count = 0;
        int i2c_device_required_count = 0;
        
        // Check devices on i2c_checks buses
        for (const auto& i2c_bus : device.i2c_checks) {
            TwoWire i2c(i2c_bus.port);
            i2c.begin(i2c_bus.sda, i2c_bus.scl, i2c_bus.freq);
            
            int bus_found_count = 0;
            for (const auto& detect : i2c_bus.detect) {
                i2c_device_total_count++;
                i2c.beginTransmission(detect.addr);
                if (i2c.endTransmission() == 0) {
                    bus_found_count++;
                    i2c_device_found_count++;
                } else {
                    if (_debug >= debug_verbose) Serial.printf("  [Fail] I2C Comm Failed at addr 0x%02X\r\n", detect.addr);
                }
            }
            
            i2c_device_required_count += i2c_bus.detect_count;
            
            if (bus_found_count < i2c_bus.detect_count) {
                i2c_comm_match = false;
                if (_debug >= debug_verbose) Serial.printf("  [Fail] I2C Bus Check Failed. Found %d, Needed %d\r\n", bus_found_count, i2c_bus.detect_count);
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
                if (_debug >= debug_verbose) Serial.printf("  [Fail] I2C Comm Failed at addr 0x%02X\r\n", i2c_id.addr);
            }
            
            if (!i2c_comm_match) break;
        }
        
        if (i2c_device_total_count > 0) {
            if (i2c_comm_match) {
                current_score++;
                if (_debug >= debug_verbose) Serial.printf("  [Pass] I2C Comm Match (+1) (%d/%d)\r\n", i2c_device_found_count, i2c_device_required_count);
            }
        } else {
             if (_debug >= debug_verbose) Serial.print("  [Skip] No I2C Comm to check\r\n");
        }

        // 5. Screen parameters
        for (const auto& disp : device.displays) {
            if (disp.identify_cmd >= 0) {
                uint32_t id = readDisplayID(disp);
                uint32_t mask = (disp.identify_mask == -1) ? 0xFFFFFFFF : (uint32_t)disp.identify_mask;
                uint32_t expect = (uint32_t)disp.identify_expect;
                
                if ((id & mask) == expect) {
                    current_score += 2;
                    if (_debug >= debug_verbose) Serial.printf("  [Pass] Screen ID Match (0x%06X)\r\n", id);
                } else {
                    if (_debug >= debug_verbose) Serial.printf("  [Fail] Screen ID Mismatch (Got: 0x%06X, Exp: 0x%06X)\r\n", id & mask, expect);
                }
            }
        }

        // 6. Additional (Future)
        // if (checkAdditional()) current_score++;

        if (_debug >= debug_verbose) {
            Serial.printf("  Total Score: %d\r\n", current_score);
        }

        if (current_score > max_score) {
            max_score = current_score;
            best_device = &device;
        }
    }
    
    if (_debug >= debug_basic) {
        Serial.print("\r\n");
        Serial.print("=== Detection Result ===\r\n");
        if (best_device) {
            Serial.printf("Best Match: %s (Score: %d)\r\n", best_device->name, max_score);
        } else {
            Serial.print("No matching device found.\r\n");
        }
        Serial.print("\r\n");
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
