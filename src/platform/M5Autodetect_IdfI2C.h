#ifndef M5_AUTODETECT_IDF_I2C_H
#define M5_AUTODETECT_IDF_I2C_H

#include <deque>
#include <vector>

#include "driver/i2c_master.h"

#include "M5Autodetect_Runtime.h"

class TwoWire {
public:
    explicit TwoWire(int port_num = 0);
    ~TwoWire();

    bool begin(int sda, int scl, uint32_t frequency = 100000);
    void end();
    void beginTransmission(uint8_t address);
    size_t write(uint8_t value);
    size_t write(const uint8_t* data, size_t len);
    uint8_t endTransmission(bool sendStop = true);
    size_t requestFrom(int address, int quantity);
    int available() const;
    int read();

private:
    esp_err_t ensureBus();
    esp_err_t withDevice(uint8_t address, i2c_master_dev_handle_t* device_handle);
    void releaseDevice(i2c_master_dev_handle_t device_handle);

    int _port_num;
    int _sda = -1;
    int _scl = -1;
    uint32_t _frequency = 100000;
    uint8_t _target_address = 0;
    bool _initialized = false;
    bool _pending_repeated_start = false;
    std::vector<uint8_t> _tx_buffer;
    std::deque<uint8_t> _rx_buffer;
    i2c_master_bus_handle_t _bus_handle = nullptr;
};

#endif