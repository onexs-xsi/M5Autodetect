#ifndef M5_AUTODETECT_H
#define M5_AUTODETECT_H

#include <stdint.h>
#include "M5Autodetect_Bus.h"
#include "M5Autodetect_Data.h"

class M5Autodetect {
public:
    enum debug_t {
        debug_none = 0,
        debug_basic,
        debug_verbose
    };

private:
    const m5::autodetect::DeviceInfo* _device_info = nullptr;
    debug_t _debug = debug_none;

public:
    M5Autodetect();
    void begin(debug_t debug = debug_none);
    const m5::autodetect::DeviceInfo* detect();
    
    const m5::autodetect::DeviceInfo* getDetectedInfo() const;

    static m5::autodetect::Bus* createBus(const m5::autodetect::BusConfig& config);
};

#endif
