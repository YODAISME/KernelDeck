#pragma once
#include <Arduino.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include <Fonts/FreeSerifBold9pt7b.h>
#include <Fonts/FreeSansBold9pt7b.h>
#include <Fonts/FreeSans9pt7b.h>
#include "config.h"
#include "protocol.h"
#include "../include/ice_bear_bg.h"
#include "../include/challenge_bg.h"
#include "../include/kill_bg.h"
#include "../include/allow_bg.h"
#include "../include/clock_digits.h"
#if CHALLENGE_ANIMATIONS
#include "../include/bear_frames.h"
#endif

#define CLOCK_X 10
#define CLOCK_Y 46

// -----------------------------------------------------------------------------
// "Liquid Light" Exact RGB565 Color Tokens
// -----------------------------------------------------------------------------
#define COLOR_CANVAS     0xFFDE  // #FAF9F7 (250, 249, 247) Warm Off-White
#define COLOR_SURFACE    0xEF7D  // #EFEEEC (239, 238, 236) Soft Card Surface
#define COLOR_TEXT_DARK  0x19C3  // #1A1C1B (26, 28, 27) Deep Charcoal Text
#define COLOR_TEXT_MUTED 0x5AEB  // #5F5E5B (95, 94, 91) Warm Slate Text
#define COLOR_CORAL      0xFDB4  // #FFB4A2 (255, 180, 162) Pastel Coral
#define COLOR_MINT       0xB797  // #B2F2BB (178, 242, 187) Pastel Mint Green
#define COLOR_SKY        0xA69F  // #A2D2FF (162, 210, 255) Pastel Sky Blue
#define COLOR_ALERT_RED  0xF800  // High-Impact Pure Red
#define COLOR_SAFE_GREEN 0x07E0  // High-Impact Emerald Green
#define COLOR_BLACK      0x0000  // Pitch Black
#define COLOR_WHITE      0xFFFF  // Pure White
#define COLOR_NIGHT_PILL 0x0866  // Deep Midnight Navy (#081224) for top pixel pill
#define COLOR_PILL_BORDER 0x5396 // Muted Cyan/Slate Border (#5070B0)

#define NUM_SNOWFLAKES 18

struct RectBox {
    int16_t x;
    int16_t y;
    int16_t w;
    int16_t h;
};

struct Snowflake {
    int16_t x;
    int16_t y;
    int16_t oldX;
    int16_t oldY;
    uint8_t speed;
    int8_t  drift;
    uint16_t color;
    uint8_t size; // 1 or 2 px
};

/**
 * ST7789 Display Manager for KernelDeck Hardware
 * Idle Mode: Ice Bear Pixel Art with Falling Snow particles.
 * Challenge Mode: Custom Challenge Background with Top Alert Pill & Live Countdown.
 * Owner: B
 */
class DisplayManager {
public:
    void begin();
    void showBootScreen();
    void showConnecting(const char* stage, const char* detail);
    void showIdle(TelemetryData& telem, bool isWsConnected, bool forceFullRedraw = false);
    void showChallenge(const ChallengeData& chal);
    void updateCountdown(int secondsRemaining);
    void showExpired();
    void showResolved(const String& verdict);
    void updateSnowflakes();
    void updateChallengeAnimations(int secondsRemaining);
    void resetChallengeAnimations();
    void updateClock(bool forceRedraw = false);

    bool drawFittedText(const RectBox& box, const char* text, const GFXfont* const* fontList, size_t fontCount, uint16_t textColor, uint16_t bgColor, bool centerH = true, bool centerV = true);

    template <size_t N>
    bool drawFittedText(const RectBox& box, const char* text, const GFXfont* const (&fontList)[N], uint16_t textColor, uint16_t bgColor, bool centerH = true, bool centerV = true) {
        return drawFittedText(box, text, fontList, N, textColor, bgColor, centerH, centerV);
    }

    void drawWrappedCmd(const RectBox& box, const String& cmd, int maxLines = 2, uint16_t textColor = COLOR_WHITE, uint16_t bgColor = 0x1882);

private:
    Adafruit_ST7789 tft = Adafruit_ST7789(TFT_CS, TFT_DC, TFT_RST);
    DeckState currentRenderedState = STATE_BOOT;
    int lastRenderedSeconds = -1;
    unsigned long lastSnowTick = 0;
    Snowflake flakes[NUM_SNOWFLAKES];

    // Challenge screen animations state
    uint8_t currentBearFrame = 0;
    uint8_t breathSeqIdx = 0;
    unsigned long lastBreathTick = 0;

    bool isGlinting = false;
    int16_t activeGlintX = -1;
    int16_t activeGlintY = -1;
    unsigned long nextGlintTime = 0;
    unsigned long glintEndTime = 0;

    // Clock state on idle screen
    int8_t lastRenderedDigits[5] = {-1, -1, -1, -1, -1};
    bool lastColonVisible = false;
    unsigned long lastClockTick = 0;

    void drawClockGlyph(int16_t x, int16_t y, uint8_t glyphIdx);
    void eraseClockSlot(int slot);

    void initSnowflakes();
    void initSnowflakesForState(DeckState state);
    uint16_t getPixelAt(int16_t x, int16_t y);
    void eraseSnowflake(const Snowflake& flake);
    void drawSnowflake(const Snowflake& flake);

    void drawTopPill(float spent, float ceiling, bool isConnected);
    void drawHeaderPill(const char* title, uint16_t bgColor, uint16_t textColor);
    void drawVectorDot(int16_t cx, int16_t cy, int16_t r, uint16_t color);
    void drawVectorCross(int16_t cx, int16_t cy, int16_t size, uint16_t color);
    void drawAlertIcon(int16_t cx, int16_t cy);
};
