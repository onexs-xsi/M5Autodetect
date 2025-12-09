#ifndef M5_AUTODETECT_H
#define M5_AUTODETECT_H

#include <stdint.h>
#include <Print.h>
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
    Print* _serial = nullptr;  // Pointer to output stream (Serial, Serial1, etc.)

public:
    M5Autodetect();
    
    // begin with optional serial output
    void begin(debug_t debug = debug_none, Print* serial = nullptr);
    
    // Run auto-detection and return best matching device info
    const m5::autodetect::DeviceInfo* detect();
    
    // Get last detected device info (nullptr if not detected yet)
    const m5::autodetect::DeviceInfo* getDetectedInfo() const;
    
    // Get board_t enum value for the detected device
    m5::autodetect::board_t getBoard() const;
    
    // Get board name string for the detected device
    const char* getBoardName() const;

    // Create a bus instance based on configuration
    static m5::autodetect::Bus* createBus(const m5::autodetect::BusConfig& config);
};

#endif
