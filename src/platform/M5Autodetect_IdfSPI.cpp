#include "M5Autodetect_IdfSPI.h"

#include <string.h>

IdfSpiDevice::IdfSpiDevice(int host_id, int mosi, int miso, int sclk, int cs, uint32_t freq, int spi_mode)
    : _host_id(host_id),
      _mosi(mosi),
      _miso(miso),
      _sclk(sclk),
      _cs(cs),
      _freq(freq),
      _spi_mode(spi_mode),
      _initialized(false),
      _handle(nullptr) {}

IdfSpiDevice::~IdfSpiDevice() {
    release();
}

bool IdfSpiDevice::init() {
    if (_initialized) {
        return true;
    }

    spi_bus_config_t bus_config = {};
    bus_config.mosi_io_num = _mosi;
    bus_config.miso_io_num = _miso;
    bus_config.sclk_io_num = _sclk;
    bus_config.quadwp_io_num = -1;
    bus_config.quadhd_io_num = -1;
    bus_config.max_transfer_sz = 4096;

    if (spi_bus_initialize((spi_host_device_t)_host_id, &bus_config, SPI_DMA_CH_AUTO) != ESP_OK) {
        return false;
    }

    spi_device_interface_config_t device_config = {};
    device_config.clock_speed_hz = _freq;
    device_config.mode = _spi_mode;
    device_config.spics_io_num = _cs;
    device_config.queue_size = 1;

    if (spi_bus_add_device((spi_host_device_t)_host_id, &device_config, &_handle) != ESP_OK) {
        spi_bus_free((spi_host_device_t)_host_id);
        return false;
    }

    _initialized = true;
    return true;
}

void IdfSpiDevice::release() {
    if (!_initialized) {
        return;
    }

    if (_handle) {
        spi_bus_remove_device(_handle);
        _handle = nullptr;
    }
    spi_bus_free((spi_host_device_t)_host_id);
    _initialized = false;
}

bool IdfSpiDevice::write(const uint8_t* data, size_t len) {
    if (!_initialized) {
        return false;
    }

    spi_transaction_t transaction = {};
    transaction.length = 8 * len;
    transaction.tx_buffer = data;
    return spi_device_transmit(_handle, &transaction) == ESP_OK;
}

bool IdfSpiDevice::read(uint8_t* data, size_t len) {
    if (!_initialized) {
        return false;
    }

    spi_transaction_t transaction = {};
    transaction.length = 8 * len;
    transaction.rx_buffer = data;
    return spi_device_transmit(_handle, &transaction) == ESP_OK;
}

bool IdfSpiDevice::writeRead(const uint8_t* write_data, size_t write_len, uint8_t* read_data, size_t read_len) {
    if (!_initialized) {
        return false;
    }

    spi_transaction_t transaction = {};
    if (write_len > 0) {
        transaction.length = 8 * write_len;
        transaction.tx_buffer = write_data;
        if (read_len > 0) {
            transaction.flags = SPI_TRANS_CS_KEEP_ACTIVE;
        }
        if (spi_device_transmit(_handle, &transaction) != ESP_OK) {
            return false;
        }
    }

    if (read_len > 0) {
        memset(&transaction, 0, sizeof(transaction));
        transaction.length = 8 * read_len;
        transaction.rx_buffer = read_data;
        if (spi_device_transmit(_handle, &transaction) != ESP_OK) {
            return false;
        }
    }

    return true;
}