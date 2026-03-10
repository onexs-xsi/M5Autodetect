#include "M5Autodetect_Bus.h"

namespace m5 {
namespace autodetect {

SPIBus::SPIBus(const BusConfig& config)
        : _cfg(config),
            _init(false),
            _device(config.spi.host_id,
                            config.spi.mosi,
                            config.spi.miso,
                            config.spi.sclk,
                            config.spi.cs,
                            config.spi.freq,
                            config.spi.spi_mode) {}

SPIBus::~SPIBus() {
    release();
}

bool SPIBus::init() {
    if (_init) return true;
    _init = _device.init();
    return _init;
}

void SPIBus::release() {
    if (!_init) return;
    _device.release();
    _init = false;
}

bool SPIBus::write(const uint8_t* data, size_t len) {
    return _init && _device.write(data, len);
}

bool SPIBus::read(uint8_t* data, size_t len) {
    return _init && _device.read(data, len);
}

bool SPIBus::writeRead(const uint8_t* write_data, size_t write_len, uint8_t* read_data, size_t read_len) {
    return _init && _device.writeRead(write_data, write_len, read_data, read_len);
}

} // namespace autodetect
} // namespace m5