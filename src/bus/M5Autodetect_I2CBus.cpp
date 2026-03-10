#include "M5Autodetect_Bus.h"

namespace m5 {
namespace autodetect {

namespace {

constexpr int kI2cTimeoutMs = 100;

bool addBusDevice(i2c_master_bus_handle_t bus_handle, uint8_t address, uint32_t frequency, i2c_master_dev_handle_t* dev_handle) {
    if (!bus_handle || !dev_handle) {
        return false;
    }

    i2c_device_config_t dev_config = {};
    dev_config.dev_addr_length = I2C_ADDR_BIT_LEN_7;
    dev_config.device_address = address;
    dev_config.scl_speed_hz = frequency;
    dev_config.scl_wait_us = 0;
    dev_config.flags.disable_ack_check = 0;
    return i2c_master_bus_add_device(bus_handle, &dev_config, dev_handle) == ESP_OK;
}

} // namespace

I2CBus::I2CBus(const BusConfig& config)
    : _cfg(config), _init(false), _bus_handle(nullptr), _dev_handle(nullptr) {}

I2CBus::~I2CBus() {
    release();
}

bool I2CBus::init() {
    if (_init) {
        return true;
    }

    i2c_master_bus_config_t bus_config = {};
    bus_config.i2c_port = _cfg.i2c.port_num;
    bus_config.sda_io_num = static_cast<gpio_num_t>(_cfg.i2c.sda);
    bus_config.scl_io_num = static_cast<gpio_num_t>(_cfg.i2c.scl);
    bus_config.glitch_ignore_cnt = 7;
    bus_config.intr_priority = 0;
    bus_config.trans_queue_depth = 1;
    bus_config.flags.enable_internal_pullup = _cfg.i2c.internal_pullup ? 1 : 0;

    if (i2c_new_master_bus(&bus_config, &_bus_handle) != ESP_OK) {
        return false;
    }

    if (!addBusDevice(_bus_handle, _cfg.i2c.addr, _cfg.i2c.freq, &_dev_handle)) {
        i2c_del_master_bus(_bus_handle);
        _bus_handle = nullptr;
        return false;
    }

    _init = true;
    return true;
}

void I2CBus::release() {
    if (!_init) {
        return;
    }

    if (_dev_handle) {
        i2c_master_bus_rm_device(_dev_handle);
        _dev_handle = nullptr;
    }
    if (_bus_handle) {
        i2c_del_master_bus(_bus_handle);
        _bus_handle = nullptr;
    }
    _init = false;
}

bool I2CBus::write(const uint8_t* data, size_t len) {
    if (!_init) {
        return false;
    }
    return i2c_master_transmit(_dev_handle, data, len, kI2cTimeoutMs) == ESP_OK;
}

bool I2CBus::read(uint8_t* data, size_t len) {
    if (!_init) {
        return false;
    }
    return i2c_master_receive(_dev_handle, data, len, kI2cTimeoutMs) == ESP_OK;
}

bool I2CBus::writeRead(const uint8_t* write_data, size_t write_len, uint8_t* read_data, size_t read_len) {
    if (!_init) {
        return false;
    }
    return i2c_master_transmit_receive(_dev_handle, write_data, write_len, read_data, read_len, kI2cTimeoutMs) == ESP_OK;
}

bool I2CBus::scan(uint8_t* found_addresses, size_t max_devices, size_t* found_count) {
    if (!_init || !found_addresses || !found_count) {
        return false;
    }

    *found_count = 0;
    for (uint8_t addr = 0x08; addr < 0x78; ++addr) {
        if (*found_count >= max_devices) {
            break;
        }
        if (i2c_master_probe(_bus_handle, addr, kI2cTimeoutMs) == ESP_OK) {
            found_addresses[*found_count] = addr;
            ++(*found_count);
        }
        delay(1);
    }

    return true;
}

bool I2CBus::probeAddress(uint8_t addr) {
    if (!_init || addr < 0x08 || addr > 0x77) {
        return false;
    }
    return i2c_master_probe(_bus_handle, addr, kI2cTimeoutMs) == ESP_OK;
}

} // namespace autodetect
} // namespace m5