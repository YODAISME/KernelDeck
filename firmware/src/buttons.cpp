#include "buttons.h"

void ButtonManager::begin() {
    pinMode(PIN_BTN_ALLOW, INPUT_PULLUP);
    pinMode(PIN_BTN_KILL, INPUT_PULLUP);
    lastAllowReading = digitalRead(PIN_BTN_ALLOW);
    lastKillReading  = digitalRead(PIN_BTN_KILL);
    allowState       = lastAllowReading;
    killState        = lastKillReading;
}

ButtonAction ButtonManager::poll() {
    unsigned long now = millis();
    ButtonAction action = BTN_NONE;

    // --- Poll ALLOW Button ---
    bool readingAllow = digitalRead(PIN_BTN_ALLOW);
    if (readingAllow != lastAllowReading) {
        lastAllowDebounceTime = now;
    }
    if ((now - lastAllowDebounceTime) > DEBOUNCE_MS) {
        if (readingAllow != allowState) {
            allowState = readingAllow;
            // Active LOW: transition to LOW indicates press
            if (allowState == LOW) {
                action = BTN_ALLOW;
            }
        }
    }
    lastAllowReading = readingAllow;

    // If ALLOW was triggered, return immediately (ALLOW takes precedence)
    if (action != BTN_NONE) {
        return action;
    }

    // --- Poll KILL Button ---
    bool readingKill = digitalRead(PIN_BTN_KILL);
    if (readingKill != lastKillReading) {
        lastKillDebounceTime = now;
    }
    if ((now - lastKillDebounceTime) > DEBOUNCE_MS) {
        if (readingKill != killState) {
            killState = readingKill;
            // Active LOW: transition to LOW indicates press
            if (killState == LOW) {
                action = BTN_KILL;
            }
        }
    }
    lastKillReading = readingKill;

    return action;
}
