// Lightweight GPIO self-check helper for probing unknown boards.
#ifndef M5_AUTODETECT_SELF_CHECK_H
#define M5_AUTODETECT_SELF_CHECK_H

#include <Arduino.h>
#include <vector>
#include "M5Autodetect_Bus.h"

namespace m5 {
namespace autodetect {

/// Output format for SelfCheck::Run()
enum class OutputFormat {
	Pretty,  ///< Human-readable formatted output
	Json     ///< JSON format for GUI import
};

struct GpioProbe {
	int gpio;
	int level;
};

struct SelfCheckReport {
	String chip_model;
	bool psram_enabled;
	std::vector<GpioProbe> pins;
	
	/// Convert report to JSON string
	String toJson() const;
};

class SelfCheck {
public:
	// Scan readable GPIOs while skipping flash/PSRAM critical pins.
	static SelfCheckReport GPIO_SelfCheck_Run(Print* log = nullptr, OutputFormat format = OutputFormat::Pretty);
	
	// Scan I2C bus for devices.
	static void I2C_SelfCheck_Run(Print* log = nullptr, int sda = -1, int scl = -1, uint32_t freq = 100000, bool internal_pullup = true, OutputFormat format = OutputFormat::Pretty);
};

} // namespace autodetect
} // namespace m5

#endif // M5_AUTODETECT_SELF_CHECK_H
