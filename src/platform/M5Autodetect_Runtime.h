#ifndef M5_AUTODETECT_RUNTIME_H
#define M5_AUTODETECT_RUNTIME_H

#include <stddef.h>
#include <stdint.h>

#include <cstddef>
#include <cstdint>
#include <string>
#include <type_traits>

#include "driver/gpio.h"
#include "esp_psram.h"

constexpr int LOW = 0;
constexpr int HIGH = 1;
constexpr int INPUT = 0;
constexpr int OUTPUT = 1;
constexpr int INPUT_PULLUP = 2;
constexpr int INPUT_PULLDOWN = 3;

class String {
public:
    String() = default;
    String(const char* value);
    String(const std::string& value);

    template <typename T, typename = typename std::enable_if<std::is_arithmetic<T>::value>::type>
    String(T value) : _value(std::to_string(value)) {}

    const char* c_str() const;
    int indexOf(const char* needle) const;
    size_t length() const;

    String& operator+=(const String& other);
    String& operator+=(const char* other);

    friend String operator+(const String& lhs, const String& rhs);
    friend String operator+(const String& lhs, const char* rhs);
    friend String operator+(const char* lhs, const String& rhs);

private:
    std::string _value;
};

class Print {
public:
    virtual ~Print() = default;
    virtual size_t write(const uint8_t* buffer, size_t size) = 0;

    size_t write(uint8_t value);
    size_t print(const char* value);
    size_t print(const String& value);
    size_t print(int value);
    size_t print(unsigned value);
    size_t println(const char* value = "");
    size_t println(const String& value);
    size_t printf(const char* format, ...);
};

class ESPClass {
public:
    String getChipModel() const;
    size_t getPsramSize() const;
};

extern ESPClass ESP;

bool psramFound();
void pinMode(int pin, int mode);
void digitalWrite(int pin, int level);
int digitalRead(int pin);
void delay(uint32_t ms);
void delayMicroseconds(uint32_t us);

#endif