#include "display.h"

#define COLOR_DARK_GREEN  0x03E0
#define COLOR_DARK_RED    0x7800
#define COLOR_DARK_GRAY   0x2104
#define COLOR_LIGHT_GRAY  0xBDD7

void DisplayManager::begin() {
    if (TFT_BL >= 0) {
        pinMode(TFT_BL, OUTPUT);
        digitalWrite(TFT_BL, HIGH); // Backlight enabled
    }

    // TPM408-2.8 ST7789 Initialization
    tft.init(TFT_WIDTH, TFT_HEIGHT);
    tft.setRotation(TFT_ROTATION);
    tft.fillScreen(ST77XX_BLACK);
}

void DisplayManager::drawHeader(const char* title, uint16_t bgColor, uint16_t textColor) {
    int16_t w = tft.width();
    tft.fillRect(0, 0, w, 32, bgColor);
    tft.setTextSize(2);
    tft.setTextColor(textColor);
    
    int16_t x = max(10, (int)(w - (strlen(title) * 12)) / 2);
    tft.setCursor(x, 8);
    tft.print(title);
}

void DisplayManager::showBootScreen() {
    currentRenderedState = STATE_BOOT;
    int16_t w = tft.width();
    tft.fillScreen(ST77XX_BLACK);
    
    drawHeader("KERNELDECK", ST77XX_CYAN, ST77XX_BLACK);
    
    tft.setTextSize(1);
    tft.setTextColor(COLOR_LIGHT_GRAY);
    tft.setCursor(20, 50);
    tft.println("Physical Safety Interlock");
    tft.setCursor(20, 65);
    tft.println("Hardware Boundary v0.1.0");

    tft.drawFastHLine(20, 85, w - 40, COLOR_DARK_GRAY);

    tft.setTextColor(ST77XX_GREEN);
    tft.setCursor(20, 100);
    tft.println("Display: TPM408 2.8\" ST7789 (OK)");
    tft.setCursor(20, 115);
    tft.println("ALLOW Button: GPIO 12");
    tft.setCursor(20, 130);
    tft.println("KILL Button:  GPIO 14");
    tft.setCursor(20, 145);
    tft.println("Output Control: GPIO 27 (ACTIVE LOW/ISOLATED)");

    tft.setTextColor(COLOR_LIGHT_GRAY);
    tft.setCursor(20, 185);
    tft.println("Initializing system...");
}

void DisplayManager::showConnecting(const char* stage, const char* detail) {
    currentRenderedState = STATE_CONNECTING;
    tft.fillScreen(ST77XX_BLACK);

    drawHeader("CONNECTING", ST77XX_YELLOW, ST77XX_BLACK);

    tft.setTextSize(2);
    tft.setTextColor(ST77XX_WHITE);
    tft.setCursor(20, 65);
    tft.println(stage);

    tft.setTextSize(1);
    tft.setTextColor(COLOR_LIGHT_GRAY);
    tft.setCursor(20, 105);
    tft.println(detail);

    tft.setCursor(20, 140);
    tft.println("Target Proxy:");
    tft.setTextColor(ST77XX_CYAN);
    tft.setCursor(20, 155);
    tft.print(PROXY_HOST);
    tft.print(":");
    tft.println(PROXY_PORT);

    tft.setTextColor(COLOR_DARK_GRAY);
    tft.setCursor(20, 195);
    tft.println("Awaiting network handshake...");
}

void DisplayManager::renderTelemetryBox(float spent, float ceiling) {
    int16_t w = tft.width();
    int16_t boxX = 20;
    int16_t boxW = w - 40;

    // Erase and redraw numerical values only (flicker-free bounding box)
    tft.fillRect(boxX + 5, 135, boxW - 10, 42, ST77XX_BLACK);

    tft.setTextSize(2);
    tft.setTextColor(ST77XX_GREEN);
    tft.setCursor(boxX + 15, 137);
    tft.print("SPENT: $");
    tft.print(spent, 2);

    tft.setTextColor(COLOR_LIGHT_GRAY);
    tft.setCursor(boxX + 15, 158);
    tft.print("CEIL:  $");
    tft.print(ceiling, 2);
}

void DisplayManager::showIdle(TelemetryData& telem, bool forceFullRedraw) {
    int16_t w = tft.width();

    if (currentRenderedState != STATE_IDLE || forceFullRedraw) {
        currentRenderedState = STATE_IDLE;
        tft.fillScreen(ST77XX_BLACK);

        // Header: Green armed banner
        drawHeader("ARMED // SAFE", ST77XX_GREEN, ST77XX_BLACK);

        // System status
        tft.setTextSize(1);
        tft.setTextColor(COLOR_LIGHT_GRAY);
        tft.setCursor(20, 45);
        tft.print("Proxy:    ");
        tft.setTextColor(ST77XX_GREEN);
        tft.println("CONNECTED");

        tft.setTextColor(COLOR_LIGHT_GRAY);
        tft.setCursor(20, 60);
        tft.print("Gate Out: ");
        tft.setTextColor(ST77XX_RED);
        tft.println("ISOLATED / LOCKED (GPIO 27)");

        tft.setTextColor(COLOR_LIGHT_GRAY);
        tft.setCursor(20, 75);
        tft.print("Display:  ");
        tft.setTextColor(ST77XX_CYAN);
        tft.println("TPM408-2.8 ST7789");

        tft.drawFastHLine(15, 92, w - 30, COLOR_DARK_GRAY);

        // Telemetry container box
        int16_t boxX = 15;
        int16_t boxW = w - 30;
        tft.drawRect(boxX, 105, boxW, 85, COLOR_DARK_GREEN);
        tft.fillRect(boxX + 1, 106, boxW - 2, 20, COLOR_DARK_GREEN);
        
        tft.setTextSize(1);
        tft.setTextColor(ST77XX_WHITE);
        tft.setCursor(boxX + 10, 112);
        tft.print("TELEMETRY / BUDGET LIMIT");

        // Render initial values
        renderTelemetryBox(telem.spent, telem.ceiling);
        telem.markClean();

        // Footer status
        tft.setTextSize(1);
        tft.setTextColor(COLOR_LIGHT_GRAY);
        tft.setCursor(20, 210);
        tft.print("Listening on /ws/deck...");
        return;
    }

    // PROTOCOL.md §8: Partial redraw only when numbers change
    if (telem.hasChanged()) {
        renderTelemetryBox(telem.spent, telem.ceiling);
        telem.markClean();
    }
}

void DisplayManager::showChallenge(const ChallengeData& chal) {
    currentRenderedState = STATE_CHALLENGE;
    int16_t w = tft.width();
    tft.fillScreen(ST77XX_BLACK);

    // Flashing red header
    drawHeader("! CHALLENGE !", ST77XX_RED, ST77XX_WHITE);

    // Risk and cost line
    tft.setTextSize(1);
    tft.setTextColor(ST77XX_YELLOW);
    tft.setCursor(15, 40);
    tft.print("RISK: ");
    tft.print(chal.risk.length() ? chal.risk.c_str() : "CRITICAL");

    tft.setTextColor(ST77XX_WHITE);
    tft.setCursor(w - 110, 40);
    tft.print("COST: ");
    tft.print(chal.cost.length() ? chal.cost.c_str() : "$0.04");

    // Command container box
    int16_t boxW = w - 24;
    tft.drawRect(12, 55, boxW, 115, ST77XX_RED);
    tft.fillRect(13, 56, boxW - 2, 18, COLOR_DARK_RED);
    tft.setTextSize(1);
    tft.setTextColor(ST77XX_WHITE);
    tft.setCursor(18, 61);
    tft.print("SUSPENDED COMMAND");

    // Render command text (max 64 chars wrapped)
    tft.setTextSize(2);
    tft.setTextColor(ST77XX_YELLOW);
    tft.setCursor(18, 82);

    String displayCmd = chal.cmd;
    if (displayCmd.length() > 64) {
        displayCmd = displayCmd.substring(0, 61) + "...";
    }

    int charsPerLine = w > 240 ? 24 : 16;
    if (displayCmd.length() <= (size_t)charsPerLine) {
        tft.println(displayCmd);
    } else {
        tft.println(displayCmd.substring(0, charsPerLine));
        tft.setCursor(18, 102);
        tft.println(displayCmd.substring(charsPerLine, min((size_t)(charsPerLine * 2), displayCmd.length())));
        if (displayCmd.length() > (size_t)(charsPerLine * 2)) {
            tft.setCursor(18, 122);
            tft.println(displayCmd.substring(charsPerLine * 2, min((size_t)(charsPerLine * 3), displayCmd.length())));
        }
    }

    // Request ID small tag
    tft.setTextSize(1);
    tft.setTextColor(COLOR_LIGHT_GRAY);
    tft.setCursor(18, 153);
    tft.print("ID: ");
    tft.print(chal.requestId);

    // Bottom Physical Button Prompts
    int16_t btnW = (w - 36) / 2;
    tft.fillRect(12, 185, btnW, 44, ST77XX_GREEN);
    tft.setTextSize(2);
    tft.setTextColor(ST77XX_BLACK);
    tft.setCursor(20 + (btnW - 60) / 2, 200);
    tft.print("ALLOW");

    tft.fillRect(12 + btnW + 12, 185, btnW, 44, ST77XX_RED);
    tft.setTextSize(2);
    tft.setTextColor(ST77XX_WHITE);
    tft.setCursor(12 + btnW + 12 + (btnW - 48) / 2, 200);
    tft.print("KILL");
}

void DisplayManager::showResolved(const String& verdict) {
    currentRenderedState = STATE_RESOLVED;
    int16_t w = tft.width();
    
    if (verdict == "ALLOW") {
        tft.fillScreen(ST77XX_GREEN);
        tft.setTextSize(3);
        tft.setTextColor(ST77XX_BLACK);
        int16_t x = max(20, (int)(w - 126) / 2);
        tft.setCursor(x, 80);
        tft.print("ALLOWED");
        
        tft.setTextSize(2);
        tft.setCursor(max(20, (int)(w - 216) / 2), 125);
        tft.print("OUT CONTROL: HIGH");

        tft.setTextSize(1);
        tft.setCursor(max(20, (int)(w - 162) / 2), 160);
        tft.print("Hardware Gate Asserted");
    } else {
        tft.fillScreen(ST77XX_RED);
        tft.setTextSize(3);
        tft.setTextColor(ST77XX_WHITE);
        int16_t x = max(20, (int)(w - 108) / 2);
        tft.setCursor(x, 80);
        tft.print("KILLED");
        
        tft.setTextSize(2);
        tft.setCursor(max(20, (int)(w - 204) / 2), 125);
        tft.print("OUT CONTROL: LOW");

        tft.setTextSize(1);
        tft.setCursor(max(20, (int)(w - 162) / 2), 160);
        tft.print("Hardware Gate Isolated");
    }
}
