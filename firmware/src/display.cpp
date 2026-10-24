#include "display.h"

#define COLOR_DARK_GREEN  0x03E0
#define COLOR_DARK_RED    0x7800
#define COLOR_DARK_GRAY   0x2104
#define COLOR_LIGHT_GRAY  0xBDD7

void DisplayManager::begin() {
    if (TFT_BL >= 0) {
        pinMode(TFT_BL, OUTPUT);
        digitalWrite(TFT_BL, HIGH); // Backlight on
    }

    tft.init(TFT_WIDTH, TFT_HEIGHT);
    tft.setRotation(TFT_ROTATION);
    tft.fillScreen(ST77XX_BLACK);
}

void DisplayManager::drawHeader(const char* title, uint16_t bgColor, uint16_t textColor) {
    tft.fillRect(0, 0, TFT_WIDTH, 32, bgColor);
    tft.setTextSize(2);
    tft.setTextColor(textColor);
    
    // Center title roughly
    int16_t x = max(10, (TFT_WIDTH - (int)(strlen(title) * 12)) / 2);
    tft.setCursor(x, 8);
    tft.print(title);
}

void DisplayManager::showBootScreen() {
    currentRenderedState = STATE_BOOT;
    tft.fillScreen(ST77XX_BLACK);
    
    drawHeader("KERNELDECK", ST77XX_CYAN, ST77XX_BLACK);
    
    tft.setTextSize(1);
    tft.setTextColor(COLOR_LIGHT_GRAY);
    tft.setCursor(20, 60);
    tft.println("Physical Safety Interlock");
    tft.setCursor(20, 75);
    tft.println("Hardware Boundary v0.1.0");

    tft.drawFastHLine(20, 95, 200, COLOR_DARK_GRAY);

    tft.setTextColor(ST77XX_GREEN);
    tft.setCursor(20, 115);
    tft.println("ST7789 Display: OK");
    tft.setCursor(20, 130);
    tft.println("ALLOW Button: GPIO 12");
    tft.setCursor(20, 145);
    tft.println("KILL Button:  GPIO 14");

    tft.setTextColor(COLOR_LIGHT_GRAY);
    tft.setCursor(20, 180);
    tft.println("Initializing system...");
}

void DisplayManager::showConnecting(const char* stage, const char* detail) {
    currentRenderedState = STATE_CONNECTING;
    tft.fillScreen(ST77XX_BLACK);

    drawHeader("CONNECTING", ST77XX_YELLOW, ST77XX_BLACK);

    tft.setTextSize(2);
    tft.setTextColor(ST77XX_WHITE);
    tft.setCursor(20, 70);
    tft.println(stage);

    tft.setTextSize(1);
    tft.setTextColor(COLOR_LIGHT_GRAY);
    tft.setCursor(20, 110);
    tft.println(detail);

    tft.setCursor(20, 150);
    tft.println("Target Proxy:");
    tft.setTextColor(ST77XX_CYAN);
    tft.setCursor(20, 165);
    tft.print(PROXY_HOST);
    tft.print(":");
    tft.println(PROXY_PORT);

    tft.setTextColor(COLOR_DARK_GRAY);
    tft.setCursor(20, 210);
    tft.println("Awaiting network handshake...");
}

void DisplayManager::renderTelemetryBox(float spent, float ceiling) {
    // Exact bounding box inside telemetry area
    // Box dimensions: x=15, y=115, w=210, h=65
    tft.fillRect(20, 130, 200, 45, ST77XX_BLACK);

    tft.setTextSize(2);
    tft.setTextColor(ST77XX_GREEN);
    tft.setCursor(25, 132);
    tft.print("SPENT: $");
    tft.print(spent, 2);

    tft.setTextColor(COLOR_LIGHT_GRAY);
    tft.setCursor(25, 155);
    tft.print("CEIL:  $");
    tft.print(ceiling, 2);
}

void DisplayManager::showIdle(TelemetryData& telem, bool forceFullRedraw) {
    // If transitioning from another state or forced, do a full screen draw
    if (currentRenderedState != STATE_IDLE || forceFullRedraw) {
        currentRenderedState = STATE_IDLE;
        tft.fillScreen(ST77XX_BLACK);

        // Header: Green armed banner
        drawHeader("ARMED // SAFE", ST77XX_GREEN, ST77XX_BLACK);

        // System status
        tft.setTextSize(1);
        tft.setTextColor(COLOR_LIGHT_GRAY);
        tft.setCursor(20, 48);
        tft.print("Proxy:    ");
        tft.setTextColor(ST77XX_GREEN);
        tft.println("CONNECTED");

        tft.setTextColor(COLOR_LIGHT_GRAY);
        tft.setCursor(20, 64);
        tft.print("Physical: ");
        tft.setTextColor(ST77XX_GREEN);
        tft.println("MONITORING");

        tft.drawFastHLine(15, 82, 210, COLOR_DARK_GRAY);

        // Telemetry container box
        tft.drawRect(15, 95, 210, 95, COLOR_DARK_GREEN);
        tft.fillRect(16, 96, 208, 20, COLOR_DARK_GREEN);
        tft.setTextSize(1);
        tft.setTextColor(ST77XX_WHITE);
        tft.setCursor(25, 102);
        tft.print("TELEMETRY / BUDGET LIMIT");

        // Render initial values
        renderTelemetryBox(telem.spent, telem.ceiling);
        telem.markClean();

        // Footer status
        tft.setTextSize(1);
        tft.setTextColor(COLOR_LIGHT_GRAY);
        tft.setCursor(20, 215);
        tft.print("Listening on /ws/deck...");
        return;
    }

    // PROTOCOL.md §8: Partial redraw only when spent or ceiling values actually change!
    // Prevents visible screen flicker and memory fragmentation during the 5s PING cycle.
    if (telem.hasChanged()) {
        renderTelemetryBox(telem.spent, telem.ceiling);
        telem.markClean();
    }
}

void DisplayManager::showChallenge(const ChallengeData& chal) {
    currentRenderedState = STATE_CHALLENGE;
    tft.fillScreen(ST77XX_BLACK);

    // Flashing red header
    drawHeader("! CHALLENGE !", ST77XX_RED, ST77XX_WHITE);

    // Risk and cost line
    tft.setTextSize(1);
    tft.setTextColor(ST77XX_YELLOW);
    tft.setCursor(15, 42);
    tft.print("RISK: ");
    tft.print(chal.risk.length() ? chal.risk.c_str() : "CRITICAL");

    tft.setTextColor(ST77XX_WHITE);
    tft.setCursor(140, 42);
    tft.print("COST: ");
    tft.print(chal.cost.length() ? chal.cost.c_str() : "$0.04");

    // Command container box
    tft.drawRect(12, 58, 216, 115, ST77XX_RED);
    tft.fillRect(13, 59, 214, 18, COLOR_DARK_RED);
    tft.setTextSize(1);
    tft.setTextColor(ST77XX_WHITE);
    tft.setCursor(18, 64);
    tft.print("SUSPENDED COMMAND");

    // Render command text (word-wrapped cleanly, max 64 chars)
    tft.setTextSize(2);
    tft.setTextColor(ST77XX_YELLOW);
    tft.setCursor(18, 85);

    String displayCmd = chal.cmd;
    if (displayCmd.length() > 64) {
        displayCmd = displayCmd.substring(0, 61) + "...";
    }

    // Print with basic line wrapping for 240px width
    if (displayCmd.length() <= 16) {
        tft.println(displayCmd);
    } else {
        tft.println(displayCmd.substring(0, 16));
        tft.setCursor(18, 105);
        tft.println(displayCmd.substring(16, min((size_t)32, displayCmd.length())));
        if (displayCmd.length() > 32) {
            tft.setCursor(18, 125);
            tft.println(displayCmd.substring(32, min((size_t)48, displayCmd.length())));
        }
    }

    // Request ID small tag
    tft.setTextSize(1);
    tft.setTextColor(COLOR_LIGHT_GRAY);
    tft.setCursor(18, 155);
    tft.print("ID: ");
    tft.print(chal.requestId);

    // Bottom Physical Button Prompts
    // Green button on left, Red button on right
    tft.fillRect(12, 185, 100, 42, ST77XX_GREEN);
    tft.setTextSize(2);
    tft.setTextColor(ST77XX_BLACK);
    tft.setCursor(20, 198);
    tft.print("ALLOW");

    tft.fillRect(128, 185, 100, 42, ST77XX_RED);
    tft.setTextSize(2);
    tft.setTextColor(ST77XX_WHITE);
    tft.setCursor(148, 198);
    tft.print("KILL");
}

void DisplayManager::showResolved(const String& verdict) {
    currentRenderedState = STATE_RESOLVED;
    
    if (verdict == "ALLOW") {
        tft.fillScreen(ST77XX_GREEN);
        tft.setTextSize(3);
        tft.setTextColor(ST77XX_BLACK);
        tft.setCursor(45, 90);
        tft.print("ALLOWED");
        
        tft.setTextSize(1);
        tft.setCursor(50, 130);
        tft.print("Operator Authorized Action");
    } else {
        tft.fillScreen(ST77XX_RED);
        tft.setTextSize(3);
        tft.setTextColor(ST77XX_WHITE);
        tft.setCursor(65, 90);
        tft.print("KILLED");
        
        tft.setTextSize(1);
        tft.setCursor(45, 130);
        tft.print("Execution Aborted Locally");
    }
}
