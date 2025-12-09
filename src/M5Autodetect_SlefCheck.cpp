#include "M5Autodetect_SlefCheck.h"
#include <algorithm>
#include <esp32-hal-psram.h>
#include <Wire.h>

namespace {

bool contains(const std::vector<int>& pins, int gpio) {
	return std::find(pins.begin(), pins.end(), gpio) != pins.end();
}

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

ChipKind detectChipKind(const String& chip) {
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

int maxPinForChip(ChipKind kind) {
	switch (kind) {
		case ChipKind::Esp32S3: return 48;
		case ChipKind::Esp32S2: return 46;
		case ChipKind::Esp32P4: return 48; // upper bound; avoids probing beyond valid pads
		case ChipKind::Esp32C3: return 21;
		case ChipKind::Esp32C2: return 20;
		case ChipKind::Esp32C5: return 31; // conservative upper bound
		case ChipKind::Esp32C6: return 25;
		case ChipKind::Esp32C61: return 25;
		case ChipKind::Esp32H2: return 25;
		case ChipKind::Esp32: return 39;
		case ChipKind::Unknown: default: return 39;
	}
}

std::vector<int> reservedPins(ChipKind kind, bool psram_enabled) {
	std::vector<int> pins;

	// Reserved pins include:
	// 1. SPI Flash / PSRAM pins (Critical: touching these crashes the system)
	// 2. Strapping pins (Reading is safe, but they have specific boot functions)
	// 3. USB/JTAG pins (If used for debugging/upload)
	
	switch (kind) {
		case ChipKind::Esp32S3:
			// Strapping: 0, 3, 45, 46
			// SPI0/1 (Flash/PSRAM): 26-32
			// USB-JTAG: 19, 20
			pins = {0, 3, 19, 20, 26, 27, 28, 29, 30, 31, 32, 45, 46};
			
			// If PSRAM is enabled, it might be Octal PSRAM which uses 33-37.
			// Even for Quad PSRAM, some pins might be used for CS1 etc.
			// To be safe, if PSRAM is present, we skip the extended SPI range.
			if (psram_enabled) {
				pins.push_back(33);
				pins.push_back(34);
				pins.push_back(35);
				pins.push_back(36);
				pins.push_back(37);
			}
			break;

		case ChipKind::Esp32S2:
			// Strapping: 0, 45, 46
			// SPI0/1 (Flash/PSRAM): 26-32
			// JTAG: 39-42
			// USB: 19, 20
			pins = {0, 19, 20, 26, 27, 28, 29, 30, 31, 32, 39, 40, 41, 42, 45, 46};
			break;

		case ChipKind::Esp32C3:
			// Strapping: 2, 8, 9
			// SPI0/1 (Flash): 12-17
			// USB-JTAG: 18, 19
			pins = {2, 8, 9, 12, 13, 14, 15, 16, 17, 18, 19};
			break;

		case ChipKind::Esp32C2:
			// Strapping: 8, 9
			// SPI0/1 (Flash): 12-17
			// USB-JTAG: 18, 19 (if available/mapped) - C2 is similar to C3 but smaller
			// C2 Datasheet: Strapping 8, 9. SPI 12-17.
			pins = {8, 9, 12, 13, 14, 15, 16, 17, 18, 19};
			break;

		case ChipKind::Esp32C5:
			// Preliminary C5 info (RISC-V)
			// Assuming similar to C6/C3 for now, but let's be conservative.
			// Strapping usually includes 8, 9. Flash 12-17 or 24-30 depending on package.
			// USB-JTAG: 13, 14
			// Safe bet: Skip standard strapping and flash ranges.
			pins = {0, 1, 2, 8, 9, 12, 13, 14, 15, 16, 17}; 
			break;

		case ChipKind::Esp32C6:
		case ChipKind::Esp32C61:
			// Strapping: 8, 9, 15 (and 4, 5 on some docs)
			// SPI0/1 (Flash): 24-30
			// USB-JTAG: 12, 13
			// SDIO/Other: 14
			pins = {4, 5, 8, 9, 12, 13, 14, 15, 24, 25, 26, 27, 28, 29, 30};
			break;

		case ChipKind::Esp32H2:
			// Strapping: 8, 9, 15
			// SPI0/1: 24-30
			// USB-JTAG: 26, 27
			pins = {8, 9, 12, 13, 15, 24, 25, 26, 27, 28, 29, 30};
			break;

		case ChipKind::Esp32P4:
			// P4 is high pin count (GPIO0-54).
			// Strapping: 34, 35, 36, 37, 38
			// Flash/PSRAM: P4 uses dedicated MSPI pins (not GPIO).
			// USB 1.1 Full Speed (USB-JTAG): GPIO24, GPIO25, GPIO26, GPIO27
			// USB 2.0 OTG High Speed: Dedicated USB PHY pins (not GPIO).
			// Safe default: Skip strapping pins and USB 1.1 pins.
			pins = {24, 25, 26, 27, 34, 35, 36, 37, 38};
			break;

		case ChipKind::Esp32:
		case ChipKind::Unknown:
		default:
			// Classic ESP32
			// Strapping: 0, 2, 5, 12, 15
			// Flash: 6-11
			// JTAG: 12-15
			// UART0: 1, 3 (Keep them for logging)
			pins = {0, 1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15};
			if (psram_enabled) {
				// PSRAM uses 16, 17
				pins.push_back(16);
				pins.push_back(17);
			}
			break;
	}

	return pins;
}

std::vector<int> candidatePins(ChipKind kind, bool psram_enabled) {
	const int max_pin = maxPinForChip(kind);
	const auto reserved = reservedPins(kind, psram_enabled);

	std::vector<int> pins;
	pins.reserve(max_pin + 1);

	for (int gpio = 0; gpio <= max_pin; ++gpio) {
		if (contains(reserved, gpio)) continue;
		pins.push_back(gpio);
	}

	return pins;
}

void logHeader(Print* log, const String& chip, bool psram_enabled, size_t count) {
	if (!log) return;
	log->print("\r\n");
	log->print("==================================================\r\n");
	log->print("              M5Autodetect SelfCheck              \r\n");
	log->print("==================================================\r\n");
	log->printf(" Chip Model    : %s\r\n", chip.c_str());
	log->printf(" PSRAM Status  : %s\r\n", psram_enabled ? "Enabled" : "Disabled");
	log->printf(" Probing Pins  : %u (Safe Mode)\r\n", static_cast<unsigned>(count));
	log->print("--------------------------------------------------\r\n");
}

} // namespace

namespace m5 {
namespace autodetect {

String SelfCheckReport::toJson() const {
	String json = "{";
	json += "\"chip_model\":\"" + chip_model + "\",";
	json += "\"psram_enabled\":" + String(psram_enabled ? "true" : "false") + ",";
	json += "\"pins\":[";
	for (size_t i = 0; i < pins.size(); ++i) {
		if (i > 0) json += ",";
		json += "{\"gpio\":" + String(pins[i].gpio) + ",\"level\":" + String(pins[i].level) + "}";
	}
	json += "]}";
	return json;
}

SelfCheckReport SelfCheck::GPIO_SelfCheck_Run(Print* log, OutputFormat format) {
	SelfCheckReport report;
	report.chip_model = ESP.getChipModel();
	report.psram_enabled = psramFound() || ESP.getPsramSize() > 0;
	const ChipKind kind = detectChipKind(report.chip_model);

	const auto pins = candidatePins(kind, report.psram_enabled);
	report.pins.reserve(pins.size());

	// Only show header for Pretty format
	if (format == OutputFormat::Pretty) {
		logHeader(log, report.chip_model, report.psram_enabled, pins.size());
	}

	int col = 0;
	for (int gpio : pins) {
		pinMode(gpio, INPUT);
		delayMicroseconds(20);

		GpioProbe probe;
		probe.gpio = gpio;
		probe.level = digitalRead(gpio);

		report.pins.push_back(probe);

		if (log && format == OutputFormat::Pretty) {
			log->printf("GPIO%02d: %d", gpio, probe.level);
			col++;
			if (col % 4 == 0) {
				log->print("\r\n");
			} else {
				log->print("   |   ");
			}
		}
	}

	if (log) {
		if (format == OutputFormat::Pretty) {
			if (col % 4 != 0) log->print("\r\n");
			log->print("--------------------------------------------------\r\n");
			log->print("                  Probe Complete                  \r\n");
			log->print("==================================================\r\n");
			log->print("\r\n");
		} else if (format == OutputFormat::Json) {
			// Output JSON format for GUI import
			log->print(report.toJson());
			log->print("\r\n");
		}
	}

	return report;
}

void SelfCheck::I2C_SelfCheck_Run(Print* log, int sda, int scl, uint32_t freq, bool internal_pullup, OutputFormat format) {
	if (log && format == OutputFormat::Pretty) {
		log->print("\r\n");
		log->print("==================================================\r\n");
		log->print("              I2C Bus Scan                        \r\n");
		log->print("==================================================\r\n");
	}

    // Resolve default pins if -1
    int pin_sda = sda;
    int pin_scl = scl;
    if (pin_sda < 0) {
        #if defined(SDA)
            pin_sda = SDA;
        #else
            pin_sda = 21;
        #endif
    }
    if (pin_scl < 0) {
        #if defined(SCL)
            pin_scl = SCL;
        #else
            pin_scl = 22;
        #endif
    }

    if (log && format == OutputFormat::Pretty) {
        log->printf(" SDA: %d, SCL: %d, Freq: %u, Pullup: %s\r\n", 
            pin_sda, pin_scl, freq, internal_pullup ? "Yes" : "No");
        log->print("--------------------------------------------------\r\n");
    }

    m5::autodetect::BusConfig config;
    config.type = m5::autodetect::BusType::I2C;
    config.i2c.port_num = 0;
    config.i2c.sda = pin_sda;
    config.i2c.scl = pin_scl;
    config.i2c.freq = freq;
    config.i2c.addr = 0;
    config.i2c.internal_pullup = internal_pullup;

    m5::autodetect::I2CBus bus(config);
    if (!bus.init()) {
        if (log && format == OutputFormat::Pretty) log->println("Failed to initialize I2C Bus");
        return;
    }

    uint8_t found_addresses[128];
    size_t found_count = 0;
    bool scan_success = bus.scan(found_addresses, 128, &found_count);
    
    if (scan_success) {
        if (log && format == OutputFormat::Pretty) {
            for (size_t i = 0; i < found_count; i++) {
                log->printf("I2C device found at address 0x%02X\r\n", found_addresses[i]);
            }
            if (found_count == 0) log->print("No I2C devices found\r\n");
        }
    } else {
        if (log && format == OutputFormat::Pretty) log->print("I2C Scan failed\r\n");
    }

    bus.release();

	if (log) {
        if (format == OutputFormat::Pretty) {
            log->print("Scan done\r\n");
            log->print("--------------------------------------------------\r\n");
            log->print("\r\n");
        } else if (format == OutputFormat::Json) {
            String json = "{";
            json += "\"type\":\"I2C\",";
            json += "\"sda\":" + String(pin_sda) + ",";
            json += "\"scl\":" + String(pin_scl) + ",";
            json += "\"freq\":" + String(freq) + ",";
            json += "\"devices\":[";
            if (scan_success) {
                for (size_t i = 0; i < found_count; ++i) {
                    if (i > 0) json += ",";
                    json += String(found_addresses[i]);
                }
            }
            json += "]}";
            log->println(json);
        }
	}
}

} // namespace autodetect
} // namespace m5
