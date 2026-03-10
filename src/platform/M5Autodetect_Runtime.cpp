#include "M5Autodetect_Runtime.h"

#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <vector>

#include "esp_rom_sys.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "sdkconfig.h"

namespace {

size_t writeCString(Print& printer, const char* value) {
    if (!value) {
        return 0;
    }
    return printer.write(reinterpret_cast<const uint8_t*>(value), strlen(value));
}

gpio_config_t make_gpio_config(int pin, int mode) {
    gpio_config_t config = {};
    config.pin_bit_mask = (1ULL << pin);
    config.intr_type = GPIO_INTR_DISABLE;
    config.pull_up_en = GPIO_PULLUP_DISABLE;
    config.pull_down_en = GPIO_PULLDOWN_DISABLE;

    switch (mode) {
        case OUTPUT:
            config.mode = GPIO_MODE_OUTPUT;
            break;
        case INPUT_PULLUP:
            config.mode = GPIO_MODE_INPUT;
            config.pull_up_en = GPIO_PULLUP_ENABLE;
            break;
        case INPUT_PULLDOWN:
            config.mode = GPIO_MODE_INPUT;
            config.pull_down_en = GPIO_PULLDOWN_ENABLE;
            break;
        case INPUT:
        default:
            config.mode = GPIO_MODE_INPUT;
            break;
    }

    return config;
}

} // namespace

String::String(const char* value) : _value(value ? value : "") {}

String::String(const std::string& value) : _value(value) {}

const char* String::c_str() const {
    return _value.c_str();
}

int String::indexOf(const char* needle) const {
    const auto pos = _value.find(needle ? needle : "");
    return pos == std::string::npos ? -1 : static_cast<int>(pos);
}

size_t String::length() const {
    return _value.length();
}

String& String::operator+=(const String& other) {
    _value += other._value;
    return *this;
}

String& String::operator+=(const char* other) {
    _value += (other ? other : "");
    return *this;
}

String operator+(const String& lhs, const String& rhs) {
    return String(std::string(lhs.c_str()) + rhs.c_str());
}

String operator+(const String& lhs, const char* rhs) {
    return String(std::string(lhs.c_str()) + (rhs ? rhs : ""));
}

String operator+(const char* lhs, const String& rhs) {
    return String(std::string(lhs ? lhs : "") + rhs.c_str());
}

size_t Print::write(uint8_t value) {
    return write(&value, 1);
}

size_t Print::print(const char* value) {
    return writeCString(*this, value);
}

size_t Print::print(const String& value) {
    return writeCString(*this, value.c_str());
}

size_t Print::print(int value) {
    const auto text = std::to_string(value);
    return writeCString(*this, text.c_str());
}

size_t Print::print(unsigned value) {
    const auto text = std::to_string(value);
    return writeCString(*this, text.c_str());
}

size_t Print::println(const char* value) {
    size_t written = print(value);
    written += print("\r\n");
    return written;
}

size_t Print::println(const String& value) {
    size_t written = print(value);
    written += print("\r\n");
    return written;
}

size_t Print::printf(const char* format, ...) {
    if (!format) {
        return 0;
    }

    va_list args;
    va_start(args, format);
    va_list args_copy;
    va_copy(args_copy, args);
    const int required = vsnprintf(nullptr, 0, format, args_copy);
    va_end(args_copy);

    if (required <= 0) {
        va_end(args);
        return 0;
    }

    std::vector<char> buffer(static_cast<size_t>(required) + 1);
    vsnprintf(buffer.data(), buffer.size(), format, args);
    va_end(args);
    return write(reinterpret_cast<const uint8_t*>(buffer.data()), static_cast<size_t>(required));
}

String ESPClass::getChipModel() const {
#if CONFIG_IDF_TARGET_ESP32P4
    return String("ESP32-P4");
#elif CONFIG_IDF_TARGET_ESP32S3
    return String("ESP32-S3");
#elif CONFIG_IDF_TARGET_ESP32S2
    return String("ESP32-S2");
#elif CONFIG_IDF_TARGET_ESP32C61
    return String("ESP32-C61");
#elif CONFIG_IDF_TARGET_ESP32C6
    return String("ESP32-C6");
#elif CONFIG_IDF_TARGET_ESP32C5
    return String("ESP32-C5");
#elif CONFIG_IDF_TARGET_ESP32C3
    return String("ESP32-C3");
#elif CONFIG_IDF_TARGET_ESP32C2
    return String("ESP32-C2");
#elif CONFIG_IDF_TARGET_ESP32H2
    return String("ESP32-H2");
#elif CONFIG_IDF_TARGET_ESP32H4
    return String("ESP32-H4");
#elif CONFIG_IDF_TARGET_ESP32
    return String("ESP32");
#else
    return String("Unknown");
#endif
}

size_t ESPClass::getPsramSize() const {
#if CONFIG_SPIRAM
    return esp_psram_is_initialized() ? esp_psram_get_size() : 0;
#else
    return 0;
#endif
}

ESPClass ESP;

bool psramFound() {
#if CONFIG_SPIRAM
    return esp_psram_is_initialized();
#else
    return false;
#endif
}

void pinMode(int pin, int mode) {
    if (pin < 0) {
        return;
    }
    const gpio_config_t config = make_gpio_config(pin, mode);
    gpio_config(&config);
}

void digitalWrite(int pin, int level) {
    if (pin < 0) {
        return;
    }
    gpio_set_level(static_cast<gpio_num_t>(pin), level ? 1U : 0U);
}

int digitalRead(int pin) {
    if (pin < 0) {
        return LOW;
    }
    return gpio_get_level(static_cast<gpio_num_t>(pin));
}

void delay(uint32_t ms) {
    if (ms == 0) {
        return;
    }
    vTaskDelay(pdMS_TO_TICKS(ms));
}

void delayMicroseconds(uint32_t us) {
    if (us == 0) {
        return;
    }
    esp_rom_delay_us(us);
}

namespace m5 {
namespace autodetect {
namespace gpio {

int readPinWithRestore(int pin, int mode) {
    if (pin < 0) return -1;
    pinMode(pin, mode);
    int level = gpio_get_level((gpio_num_t)pin);
    gpio_reset_pin((gpio_num_t)pin);
    return level;
}

bool readPinsWithRestore(const int* pins, size_t pin_count, int* levels, int mode) {
    if (!pins || !levels || pin_count == 0) return false;

    for (size_t i = 0; i < pin_count; i++) {
        levels[i] = readPinWithRestore(pins[i], mode);
        if (levels[i] < 0) return false;
    }

    return true;
}

} // namespace gpio
} // namespace autodetect
} // namespace m5
