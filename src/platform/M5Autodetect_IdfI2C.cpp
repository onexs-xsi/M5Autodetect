#include "M5Autodetect_IdfI2C.h"

#include <string.h>
namespace {

constexpr int kI2cTimeoutMs = 100;

} // namespace

TwoWire::TwoWire(int port_num) : _port_num(port_num) {}

TwoWire::~TwoWire() {
    end();
}

bool TwoWire::begin(int sda, int scl, uint32_t frequency) {
    end();
    _sda = sda;
    _scl = scl;
    _frequency = frequency;
    _initialized = (ensureBus() == ESP_OK);
    return _initialized;
}

void TwoWire::end() {
    _pending_repeated_start = false;
    _tx_buffer.clear();
    _rx_buffer.clear();
    if (_bus_handle) {
        i2c_del_master_bus(_bus_handle);
        _bus_handle = nullptr;
    }
    _initialized = false;
}

void TwoWire::beginTransmission(uint8_t address) {
    _target_address = address;
    _pending_repeated_start = false;
    _tx_buffer.clear();
}

size_t TwoWire::write(uint8_t value) {
    _tx_buffer.push_back(value);
    return 1;
}

size_t TwoWire::write(const uint8_t* data, size_t len) {
    if (!data || len == 0) {
        return 0;
    }
    _tx_buffer.insert(_tx_buffer.end(), data, data + len);
    return len;
}

uint8_t TwoWire::endTransmission(bool sendStop) {
    if (ensureBus() != ESP_OK) {
        _tx_buffer.clear();
        _pending_repeated_start = false;
        return 4;
    }

    if (!sendStop) {
        _pending_repeated_start = true;
        return 0;
    }

    if (_tx_buffer.empty()) {
        const esp_err_t probe_result = i2c_master_probe(_bus_handle, _target_address, kI2cTimeoutMs);
        _pending_repeated_start = false;
        return probe_result == ESP_OK ? 0 : 4;
    }

    i2c_master_dev_handle_t device_handle = nullptr;
    esp_err_t err = withDevice(_target_address, &device_handle);
    if (err == ESP_OK) {
        err = i2c_master_transmit(device_handle, _tx_buffer.data(), _tx_buffer.size(), kI2cTimeoutMs);
    }
    releaseDevice(device_handle);
    _tx_buffer.clear();
    _pending_repeated_start = false;
    return err == ESP_OK ? 0 : 4;
}

size_t TwoWire::requestFrom(int address, int quantity) {
    _rx_buffer.clear();
    if (quantity <= 0 || ensureBus() != ESP_OK) {
        _tx_buffer.clear();
        _pending_repeated_start = false;
        return 0;
    }

    std::vector<uint8_t> buffer(static_cast<size_t>(quantity));
    i2c_master_dev_handle_t device_handle = nullptr;
    esp_err_t err = withDevice(static_cast<uint8_t>(address), &device_handle);
    if (err == ESP_OK) {
        if (_pending_repeated_start && !_tx_buffer.empty() && static_cast<uint8_t>(address) == _target_address) {
            err = i2c_master_transmit_receive(device_handle, _tx_buffer.data(), _tx_buffer.size(), buffer.data(), buffer.size(), kI2cTimeoutMs);
        } else {
            err = i2c_master_receive(device_handle, buffer.data(), buffer.size(), kI2cTimeoutMs);
        }
    }
    releaseDevice(device_handle);
    _tx_buffer.clear();
    _pending_repeated_start = false;

    if (err != ESP_OK) {
        return 0;
    }

    for (uint8_t value : buffer) {
        _rx_buffer.push_back(value);
    }
    return _rx_buffer.size();
}

int TwoWire::available() const {
    return static_cast<int>(_rx_buffer.size());
}

int TwoWire::read() {
    if (_rx_buffer.empty()) {
        return -1;
    }

    const int value = _rx_buffer.front();
    _rx_buffer.pop_front();
    return value;
}

esp_err_t TwoWire::ensureBus() {
    if (_bus_handle) {
        return ESP_OK;
    }
    if (_sda < 0 || _scl < 0) {
        return ESP_ERR_INVALID_ARG;
    }

    i2c_master_bus_config_t bus_config = {};
    bus_config.i2c_port = _port_num;
    bus_config.sda_io_num = static_cast<gpio_num_t>(_sda);
    bus_config.scl_io_num = static_cast<gpio_num_t>(_scl);
    bus_config.clk_source = I2C_CLK_SRC_DEFAULT;
    bus_config.glitch_ignore_cnt = 7;
    bus_config.intr_priority = 0;
    bus_config.trans_queue_depth = 0;
    bus_config.flags.enable_internal_pullup = 1;
    return i2c_new_master_bus(&bus_config, &_bus_handle);
}

esp_err_t TwoWire::withDevice(uint8_t address, i2c_master_dev_handle_t* device_handle) {
    if (!device_handle) {
        return ESP_ERR_INVALID_ARG;
    }
    *device_handle = nullptr;

    const esp_err_t err = ensureBus();
    if (err != ESP_OK) {
        return err;
    }

    i2c_device_config_t device_config = {};
    device_config.dev_addr_length = I2C_ADDR_BIT_LEN_7;
    device_config.device_address = address;
    device_config.scl_speed_hz = _frequency;
    device_config.scl_wait_us = 0;
    device_config.flags.disable_ack_check = 0;
    return i2c_master_bus_add_device(_bus_handle, &device_config, device_handle);
}

void TwoWire::releaseDevice(i2c_master_dev_handle_t device_handle) {
    if (device_handle) {
        i2c_master_bus_rm_device(device_handle);
    }
}
