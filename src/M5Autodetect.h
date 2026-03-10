#ifndef M5_AUTODETECT_H
#define M5_AUTODETECT_H

#include <stdint.h>

#include "bus/M5Autodetect_Bus.h"
#include "data/M5Autodetect_DeviceData.h"
#include "platform/M5Autodetect_Runtime.h"

class M5Autodetect {
public:
    enum debug_t {
        debug_none = 0,
        debug_error,
        debug_warn,
        debug_info,
        debug_debug,
        debug_verbose
    };

private:
    const m5::autodetect::DeviceInfo* _device_info = nullptr;
    debug_t _debug = debug_none;
    Print* _serial = nullptr;

    void logMessage(debug_t level, const char* message) const;
    void logPrintf(debug_t level, const char* format, ...) const;

public:
    M5Autodetect();
    
    void begin(debug_t debug = debug_none, Print* serial = nullptr);

    const m5::autodetect::DeviceInfo* detect();

    const m5::autodetect::DeviceInfo* getDetectedInfo() const;

    m5::autodetect::board_t getBoard() const;

    const char* getBoardName() const;

    bool boardHasPsram() const;

    bool isPsramDetected() const;

    const char* getPsramStatusText() const;

    static m5::autodetect::Bus* createBus(const m5::autodetect::BusConfig& config);
};

#endif
