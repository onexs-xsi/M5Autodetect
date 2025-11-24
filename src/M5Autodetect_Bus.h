#ifndef M5_AUTODETECT_BUS_H
#define M5_AUTODETECT_BUS_H

#include <stdint.h>
#include <stddef.h>

#if defined(ARDUINO)
#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>
#else
#include "driver/i2c.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include "esp_err.h"
#endif

namespace m5 {
namespace autodetect {

enum class BusType {
    UNKNOWN,
    I2C,
    SPI
};

struct BusConfig {
    BusType type;
    union {
        struct {
            int port_num;
            int sda;
            int scl;
            uint32_t freq;
            uint8_t addr;
        } i2c;
        struct {
            int host_id;
            int mosi;
            int miso;
            int sclk;
            int cs;
            uint32_t freq;
            int spi_mode;
        } spi;
    };
};

class Bus {
public:
    virtual ~Bus() = default;
    virtual bool init() = 0;
    virtual bool write(const uint8_t* data, size_t len) = 0;
    virtual bool read(uint8_t* data, size_t len) = 0;
    virtual bool writeRead(const uint8_t* write_data, size_t write_len, uint8_t* read_data, size_t read_len) = 0;
    virtual void release() = 0;
};

class I2CBus : public Bus {
public:
    I2CBus(const BusConfig& config);
    virtual ~I2CBus();
    bool init() override;
    bool write(const uint8_t* data, size_t len) override;
    bool read(uint8_t* data, size_t len) override;
    bool writeRead(const uint8_t* write_data, size_t write_len, uint8_t* read_data, size_t read_len) override;
    void release() override;
    
    // I2C Scan functionality
    bool scan(uint8_t* found_addresses, size_t max_devices, size_t* found_count);
    bool probeAddress(uint8_t addr);
    
private:
    BusConfig _cfg;
    bool _init;
#if defined(ARDUINO)
    TwoWire* _wire;
#endif
};

class SPIBus : public Bus {
public:
    SPIBus(const BusConfig& config);
    virtual ~SPIBus();
    bool init() override;
    bool write(const uint8_t* data, size_t len) override;
    bool read(uint8_t* data, size_t len) override;
    bool writeRead(const uint8_t* write_data, size_t write_len, uint8_t* read_data, size_t read_len) override;
    void release() override;
private:
    BusConfig _cfg;
    bool _init;
#if defined(ARDUINO)
    SPIClass* _spi;
#else
    spi_device_handle_t _spi_handle;
#endif
};

// GPIO Helper Functions
namespace gpio {
    // Read GPIO level and restore to original state after reading
    // Returns: GPIO level (0 or 1), or -1 on error
    int readPinWithRestore(int pin, int mode = INPUT);
    
    // Batch read multiple GPIO pins
    bool readPinsWithRestore(const int* pins, size_t pin_count, int* levels, int mode = INPUT);
} // namespace gpio

} // namespace autodetect
} // namespace m5

#endif // M5_AUTODETECT_BUS_H
