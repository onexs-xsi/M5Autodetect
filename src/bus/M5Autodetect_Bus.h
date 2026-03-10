#ifndef M5_AUTODETECT_BUS_H
#define M5_AUTODETECT_BUS_H

#include <stddef.h>
#include <stdint.h>

#include "driver/i2c_master.h"
#include "driver/spi_master.h"

#include "platform/M5Autodetect_Runtime.h"
#include "platform/M5Autodetect_IdfSPI.h"

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
            bool internal_pullup;
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
    bool scan(uint8_t* found_addresses, size_t max_devices, size_t* found_count);
    bool probeAddress(uint8_t addr);

private:
    BusConfig _cfg;
    bool _init;
    i2c_master_bus_handle_t _bus_handle;
    i2c_master_dev_handle_t _dev_handle;
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
    IdfSpiDevice _device;
};

namespace gpio {
    int readPinWithRestore(int pin, int mode = INPUT);
    bool readPinsWithRestore(const int* pins, size_t pin_count, int* levels, int mode = INPUT);
} // namespace gpio

} // namespace autodetect
} // namespace m5

#endif // M5_AUTODETECT_BUS_H