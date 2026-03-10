#ifndef M5_AUTODETECT_IDF_SPI_H
#define M5_AUTODETECT_IDF_SPI_H

#include <stddef.h>
#include <stdint.h>

#include "driver/spi_master.h"

class IdfSpiDevice {
public:
    IdfSpiDevice(int host_id, int mosi, int miso, int sclk, int cs, uint32_t freq, int spi_mode);
    ~IdfSpiDevice();

    bool init();
    void release();
    bool write(const uint8_t* data, size_t len);
    bool read(uint8_t* data, size_t len);
    bool writeRead(const uint8_t* write_data, size_t write_len, uint8_t* read_data, size_t read_len);

private:
    int _host_id;
    int _mosi;
    int _miso;
    int _sclk;
    int _cs;
    uint32_t _freq;
    int _spi_mode;
    bool _initialized;
    spi_device_handle_t _handle;
};

#endif