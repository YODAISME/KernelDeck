#pragma once
#include <Arduino.h>
#include "config.h"
#include "protocol.h"

/**
 * Non-Blocking Physical Button Controller with Software Debouncing
 * Owner: B
 */
class ButtonManager {
public:
    void begin();
    ButtonAction poll();

private:
    bool lastAllowReading = HIGH;
    bool lastKillReading  = HIGH;
    bool allowState       = HIGH;
    bool killState        = HIGH;
    unsigned long lastAllowDebounceTime = 0;
    unsigned long lastKillDebounceTime  = 0;
};
