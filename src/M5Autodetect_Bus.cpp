#include "M5Autodetect_Bus.h"
#include <string.h>

namespace m5 {
namespace autodetect {

// ==================================================================================
// I2CBus Implementation
// ==================================================================================

I2CBus::I2CBus(const BusConfig& config) : _cfg(config), _init(false) {
#if defined(ARDUINO)
    _wire = &Wire;
    if (_cfg.i2c.port_num == 1) {
#if defined(Wire1)
        _wire = &Wire1;
#endif
    }
#endif
}

I2CBus::~I2CBus() {
    release();
}

bool I2CBus::init() {
    if (_init) return true;
#if defined(ARDUINO)
    if (_cfg.i2c.sda < 0 || _cfg.i2c.scl < 0) return false;
    // Ensure clean state
    _wire->end();
    if (!_wire->begin(_cfg.i2c.sda, _cfg.i2c.scl, _cfg.i2c.freq)) {
        return false;
    }
    // Note: Wire.begin() enables internal pullups by default.
    // Calling pinMode() after begin() breaks I2C on ESP32 as it reconfigures the pins as GPIO.
    // If we need to disable pullups, we should use gpio_set_pull_mode() or similar, 
    // but for now we rely on Wire.begin() default (PULLUP).
#else
    i2c_config_t conf = {0};
    conf.mode = I2C_MODE_MASTER;
    conf.sda_io_num = _cfg.i2c.sda;
    conf.scl_io_num = _cfg.i2c.scl;
    conf.sda_pullup_en = _cfg.i2c.internal_pullup ? GPIO_PULLUP_ENABLE : GPIO_PULLUP_DISABLE;
    conf.scl_pullup_en = _cfg.i2c.internal_pullup ? GPIO_PULLUP_ENABLE : GPIO_PULLUP_DISABLE;
    conf.master.clk_speed = _cfg.i2c.freq;
    
    esp_err_t err = i2c_param_config((i2c_port_t)_cfg.i2c.port_num, &conf);
    if (err != ESP_OK) return false;
    
    err = i2c_driver_install((i2c_port_t)_cfg.i2c.port_num, conf.mode, 0, 0, 0);
    if (err != ESP_OK) return false;
#endif
    _init = true;
    return true;
}

void I2CBus::release() {
    if (!_init) return;
#if defined(ARDUINO)
    // Arduino Wire library doesn't have a standard end() or release() that frees pins completely in all cores.
#else
    i2c_driver_delete((i2c_port_t)_cfg.i2c.port_num);
#endif
    _init = false;
}

bool I2CBus::write(const uint8_t* data, size_t len) {
    if (!_init) return false;
#if defined(ARDUINO)
    _wire->beginTransmission(_cfg.i2c.addr);
    _wire->write(data, len);
    return (_wire->endTransmission() == 0);
#else
    // Use i2c_master_write_to_device if available (IDF 4.4+), otherwise use legacy commands
    // Assuming IDF 4.4+ for simplicity as it is common now.
    esp_err_t err = i2c_master_write_to_device((i2c_port_t)_cfg.i2c.port_num, _cfg.i2c.addr, data, len, 1000 / portTICK_PERIOD_MS);
    return (err == ESP_OK);
#endif
}

bool I2CBus::read(uint8_t* data, size_t len) {
    if (!_init) return false;
#if defined(ARDUINO)
    _wire->requestFrom(_cfg.i2c.addr, (uint8_t)len);
    if (_wire->available() != (int)len) return false;
    for (size_t i = 0; i < len; i++) {
        data[i] = _wire->read();
    }
    return true;
#else
    esp_err_t err = i2c_master_read_from_device((i2c_port_t)_cfg.i2c.port_num, _cfg.i2c.addr, data, len, 1000 / portTICK_PERIOD_MS);
    return (err == ESP_OK);
#endif
}

bool I2CBus::writeRead(const uint8_t* write_data, size_t write_len, uint8_t* read_data, size_t read_len) {
    if (!_init) return false;
#if defined(ARDUINO)
    if (write(write_data, write_len)) {
        return read(read_data, read_len);
    }
    return false;
#else
    esp_err_t err = i2c_master_write_read_device((i2c_port_t)_cfg.i2c.port_num, _cfg.i2c.addr, write_data, write_len, read_data, read_len, 1000 / portTICK_PERIOD_MS);
    return (err == ESP_OK);
#endif
}

bool I2CBus::scan(uint8_t* found_addresses, size_t max_devices, size_t* found_count) {
    if (!_init) return false;
    if (!found_addresses || !found_count) return false;
    
    *found_count = 0;
    
    for (uint8_t addr = 0x08; addr < 0x78; addr++) {
        if (*found_count >= max_devices) break;
        
#if defined(ARDUINO)
        _wire->beginTransmission(addr);
        if (_wire->endTransmission() == 0) {
            found_addresses[*found_count] = addr;
            (*found_count)++;
        }
#else
        i2c_cmd_handle_t cmd = i2c_cmd_link_create();
        i2c_master_start(cmd);
        i2c_master_write_byte(cmd, (addr << 1) | I2C_MASTER_WRITE, true);
        i2c_master_stop(cmd);
        esp_err_t ret = i2c_master_cmd_begin((i2c_port_t)_cfg.i2c.port_num, cmd, 50 / portTICK_PERIOD_MS);
        i2c_cmd_link_delete(cmd);
        
        if (ret == ESP_OK) {
            found_addresses[*found_count] = addr;
            (*found_count)++;
        }
#endif
        delay(1); // Small delay between scans
    }
    
    return true;
}

bool I2CBus::probeAddress(uint8_t addr) {
    if (!_init) return false;
    if (addr < 0x08 || addr > 0x77) return false;
    
#if defined(ARDUINO)
    _wire->beginTransmission(addr);
    return (_wire->endTransmission() == 0);
#else
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (addr << 1) | I2C_MASTER_WRITE, true);
    i2c_master_stop(cmd);
    esp_err_t ret = i2c_master_cmd_begin((i2c_port_t)_cfg.i2c.port_num, cmd, 50 / portTICK_PERIOD_MS);
    i2c_cmd_link_delete(cmd);
    
    return (ret == ESP_OK);
#endif
}

// ==================================================================================
// SPIBus Implementation
// ==================================================================================

SPIBus::SPIBus(const BusConfig& config) : _cfg(config), _init(false) {
#if defined(ARDUINO)
    _spi = &SPI;
#endif
}

SPIBus::~SPIBus() {
    release();
}

bool SPIBus::init() {
    if (_init) return true;
#if defined(ARDUINO)
    _spi->begin(_cfg.spi.sclk, _cfg.spi.miso, _cfg.spi.mosi, _cfg.spi.cs);
    pinMode(_cfg.spi.cs, OUTPUT);
    digitalWrite(_cfg.spi.cs, HIGH);
#else
    spi_bus_config_t buscfg = {0};
    buscfg.mosi_io_num = _cfg.spi.mosi;
    buscfg.miso_io_num = _cfg.spi.miso;
    buscfg.sclk_io_num = _cfg.spi.sclk;
    buscfg.quadwp_io_num = -1;
    buscfg.quadhd_io_num = -1;
    buscfg.max_transfer_sz = 4096;

    esp_err_t ret = spi_bus_initialize((spi_host_device_t)_cfg.spi.host_id, &buscfg, SPI_DMA_CH_AUTO);
    if (ret != ESP_OK) return false;

    spi_device_interface_config_t devcfg = {0};
    devcfg.clock_speed_hz = _cfg.spi.freq;
    devcfg.mode = _cfg.spi.spi_mode;
    devcfg.spics_io_num = _cfg.spi.cs;
    devcfg.queue_size = 1;

    ret = spi_bus_add_device((spi_host_device_t)_cfg.spi.host_id, &devcfg, &_spi_handle);
    if (ret != ESP_OK) return false;
#endif
    _init = true;
    return true;
}

void SPIBus::release() {
    if (!_init) return;
#if defined(ARDUINO)
    _spi->end();
#else
    spi_bus_remove_device(_spi_handle);
    spi_bus_free((spi_host_device_t)_cfg.spi.host_id);
#endif
    _init = false;
}

bool SPIBus::write(const uint8_t* data, size_t len) {
    if (!_init) return false;
#if defined(ARDUINO)
    _spi->beginTransaction(SPISettings(_cfg.spi.freq, MSBFIRST, _cfg.spi.spi_mode));
    digitalWrite(_cfg.spi.cs, LOW);
#if defined(ESP32)
    _spi->transferBytes(data, nullptr, len);
#else
    for(size_t i=0; i<len; i++) _spi->transfer(data[i]);
#endif
    digitalWrite(_cfg.spi.cs, HIGH);
    _spi->endTransaction();
    return true;
#else
    spi_transaction_t t = {0};
    t.length = 8 * len;
    t.tx_buffer = data;
    t.rx_buffer = NULL;
    esp_err_t ret = spi_device_transmit(_spi_handle, &t);
    return (ret == ESP_OK);
#endif
}

bool SPIBus::read(uint8_t* data, size_t len) {
    if (!_init) return false;
#if defined(ARDUINO)
    _spi->beginTransaction(SPISettings(_cfg.spi.freq, MSBFIRST, _cfg.spi.spi_mode));
    digitalWrite(_cfg.spi.cs, LOW);
#if defined(ESP32)
    _spi->transferBytes(nullptr, data, len);
#else
    for(size_t i=0; i<len; i++) data[i] = _spi->transfer(0x00);
#endif
    digitalWrite(_cfg.spi.cs, HIGH);
    _spi->endTransaction();
    return true;
#else
    spi_transaction_t t = {0};
    t.length = 8 * len;
    t.tx_buffer = NULL;
    t.rx_buffer = data;
    esp_err_t ret = spi_device_transmit(_spi_handle, &t);
    return (ret == ESP_OK);
#endif
}

bool SPIBus::writeRead(const uint8_t* write_data, size_t write_len, uint8_t* read_data, size_t read_len) {
    if (!_init) return false;
#if defined(ARDUINO)
    _spi->beginTransaction(SPISettings(_cfg.spi.freq, MSBFIRST, _cfg.spi.spi_mode));
    digitalWrite(_cfg.spi.cs, LOW);
    
    if (write_len > 0) {
#if defined(ESP32)
        _spi->transferBytes(write_data, nullptr, write_len);
#else
        for(size_t i=0; i<write_len; i++) _spi->transfer(write_data[i]);
#endif
    }
    
    if (read_len > 0) {
#if defined(ESP32)
        _spi->transferBytes(nullptr, read_data, read_len);
#else
        for(size_t i=0; i<read_len; i++) read_data[i] = _spi->transfer(0x00);
#endif
    }

    digitalWrite(_cfg.spi.cs, HIGH);
    _spi->endTransaction();
    return true;
#else
    spi_transaction_t t = {0};
    if (write_len > 0) {
        t.length = 8 * write_len;
        t.tx_buffer = write_data;
        t.rx_buffer = NULL;
        if (read_len > 0) {
             t.flags = SPI_TRANS_CS_KEEP_ACTIVE;
        }
        esp_err_t ret = spi_device_transmit(_spi_handle, &t);
        if (ret != ESP_OK) return false;
    }
    
    if (read_len > 0) {
        memset(&t, 0, sizeof(t));
        t.length = 8 * read_len;
        t.tx_buffer = NULL;
        t.rx_buffer = read_data;
        esp_err_t ret = spi_device_transmit(_spi_handle, &t);
        if (ret != ESP_OK) return false;
    }
    
    return true;
#endif
}

// ==================================================================================
// GPIO Helper Functions Implementation
// ==================================================================================

namespace gpio {

int readPinWithRestore(int pin, int mode) {
    if (pin < 0) return -1;
    
#if defined(ARDUINO)
    // Save original pin state
    int original_mode = -1;
    
#if defined(ESP32)
    // For ESP32, we can't reliably get the current mode, so we'll just set and restore
    // Store if pin was output by checking if it's in the output enable register
    uint32_t reg_val = 0;
    if (pin < 32) {
        reg_val = REG_READ(GPIO_ENABLE_REG);
        original_mode = (reg_val & (1ULL << pin)) ? OUTPUT : INPUT;
    } else {
        reg_val = REG_READ(GPIO_ENABLE1_REG);
        original_mode = (reg_val & (1ULL << (pin - 32))) ? OUTPUT : INPUT;
    }
#endif
    
    // Set desired mode and read
    pinMode(pin, mode);
    int level = digitalRead(pin);
    
    // Restore original mode if we detected it
#if defined(ESP32)
    if (original_mode >= 0) {
        pinMode(pin, original_mode);
    }
#else
    // For other platforms, restore to INPUT as safe default
    pinMode(pin, INPUT);
#endif
    
    return level;
    
#else // ESP-IDF
    // Save original configuration
    gpio_config_t original_conf = {};
    bool was_input = false;
    bool was_output = false;
    
    // Check current configuration
    uint32_t iomux_reg = GPIO_PIN_MUX_REG[pin];
    if (iomux_reg) {
        // Simplified: just check if it was input or output
        uint32_t reg_val = REG_READ(GPIO_ENABLE_REG);
        if (pin < 32) {
            was_output = (reg_val & (1ULL << pin)) != 0;
        } else {
            reg_val = REG_READ(GPIO_ENABLE1_REG);
            was_output = (reg_val & (1ULL << (pin - 32))) != 0;
        }
        was_input = !was_output;
    }
    
    // Configure as input to read
    gpio_config_t io_conf = {};
    io_conf.intr_type = GPIO_INTR_DISABLE;
    io_conf.mode = (mode == OUTPUT) ? GPIO_MODE_OUTPUT : GPIO_MODE_INPUT;
    io_conf.pin_bit_mask = (1ULL << pin);
    io_conf.pull_down_en = GPIO_PULLDOWN_DISABLE;
    io_conf.pull_up_en = GPIO_PULLUP_DISABLE;
    gpio_config(&io_conf);
    
    // Read level
    int level = gpio_get_level((gpio_num_t)pin);
    
    // Restore original configuration
    if (was_output) {
        io_conf.mode = GPIO_MODE_OUTPUT;
        gpio_config(&io_conf);
    } else if (was_input) {
        io_conf.mode = GPIO_MODE_INPUT;
        gpio_config(&io_conf);
    } else {
        // If we couldn't determine, reset to input as safe default
        gpio_reset_pin((gpio_num_t)pin);
    }
    
    return level;
#endif
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
