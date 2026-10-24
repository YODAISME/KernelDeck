#pragma once
#include <Arduino.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include "config.h"
#include "protocol.h"

/**
 * ST7789 Display Manager for KernelDeck Hardware
 * Handles state machine rendering and flicker-free partial telemetry updates.
 * Owner: B
 */
class DisplayManager {
public:
    void begin();
    void showBootScreen();
    void showConnecting(const char* stage, const char* detail);
    void showIdle(TelemetryData& telem, bool forceFullRedraw = false);
    void showChallenge(const ChallengeData& chal);
    void showResolved(const String& verdict);

private:
    Adafruit_ST7789 tft = Adafruit_ST7789(TFT_CS, TFT_DC, TFT_RST);
    DeckState currentRenderedState = STATE_BOOT;

    void drawHeader(const char* title, uint16_t bgColor, uint16_t textColor);
    void renderTelemetryBox(float spent, float ceiling);
};
