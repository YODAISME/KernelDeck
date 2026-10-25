#include "display.h"

void DisplayManager::begin() {
    if (TFT_BL >= 0) {
        pinMode(TFT_BL, OUTPUT);
        digitalWrite(TFT_BL, HIGH); // Backlight enabled
    }

    // TPM408-2.8 ST7789 Initialization (Portrait 240x320)
    tft.init(TFT_WIDTH, TFT_HEIGHT);
    tft.setRotation(TFT_ROTATION);
    tft.invertDisplay(false); // Disable Adafruit default INVON table hack
    tft.setTextWrap(false);   // Never rely on automatic wrapping
    tft.fillScreen(COLOR_CANVAS);

    initSnowflakes();
}

void DisplayManager::drawHeaderPill(const char* title, uint16_t bgColor, uint16_t textColor) {
    int16_t w = tft.width();
    tft.fillRoundRect(10, 8, w - 20, 32, 16, bgColor);
    tft.drawRoundRect(10, 8, w - 20, 32, 16, COLOR_BLACK);

    tft.setFont(&FreeSansBold9pt7b);
    tft.setTextColor(textColor);
    
    int16_t x1, y1;
    uint16_t tw, th;
    tft.getTextBounds(title, 0, 0, &x1, &y1, &tw, &th);
    int16_t x = 10 + (w - 20 - tw) / 2;
    tft.setCursor(x, 28);
    tft.print(title);
}

void DisplayManager::drawVectorDot(int16_t cx, int16_t cy, int16_t r, uint16_t color) {
    tft.fillCircle(cx, cy, r, color);
    tft.drawCircle(cx, cy, r, COLOR_BLACK);
}

void DisplayManager::drawVectorCross(int16_t cx, int16_t cy, int16_t size, uint16_t color) {
    tft.drawLine(cx - size, cy - size, cx + size, cy + size, color);
    tft.drawLine(cx - size + 1, cy - size, cx + size, cy + size - 1, color);
    tft.drawLine(cx - size, cy + size, cx + size, cy - size, color);
    tft.drawLine(cx - size + 1, cy + size, cx + size, cy - size - 1, color);
}

void DisplayManager::drawAlertIcon(int16_t cx, int16_t cy) {
    // Yellow Alert Triangle (compact, fits beside title in top container)
    tft.fillTriangle(cx, cy - 8, cx - 8, cy + 6, cx + 8, cy + 6, 0xFD20); // Amber Yellow
    tft.drawTriangle(cx, cy - 8, cx - 8, cy + 6, cx + 8, cy + 6, COLOR_BLACK);
    // Exclamation mark: vertical stem + dot
    tft.fillRect(cx - 1, cy - 4, 2, 5, COLOR_BLACK);
    tft.drawPixel(cx - 1, cy + 3, COLOR_BLACK);
    tft.drawPixel(cx, cy + 3, COLOR_BLACK);
}

bool DisplayManager::drawFittedText(const RectBox& box, const char* text, const GFXfont* const* fontList, size_t fontCount, uint16_t textColor, uint16_t bgColor, bool centerH, bool centerV) {
    if (!text || text[0] == '\0') return false;

    tft.setTextWrap(false);

    // 1. Clear the box with fillRect before drawing
    tft.fillRect(box.x, box.y, box.w, box.h, bgColor);

    const GFXfont* chosenFont = NULL;
    int16_t chosenX1 = 0, chosenY1 = 0;
    uint16_t chosenW = 0, chosenH = 0;
    bool found = false;

    // 2. Measure and pick largest font from fontList that fits inside box
    for (size_t i = 0; i < fontCount; i++) {
        const GFXfont* f = fontList[i];
        tft.setFont(f);
        tft.setTextSize(1);

        int16_t x1, y1;
        uint16_t tw, th;
        tft.getTextBounds(text, 0, 0, &x1, &y1, &tw, &th);

        if (tw <= box.w && th <= box.h) {
            chosenFont = f;
            chosenX1 = x1;
            chosenY1 = y1;
            chosenW = tw;
            chosenH = th;
            found = true;
            break;
        }
    }

    // 3. Fallback if none fit completely: use smallest/last font in list and clip to box.w
    String renderStr = text;
    if (!found && fontCount > 0) {
        chosenFont = fontList[fontCount - 1];
        tft.setFont(chosenFont);
        tft.setTextSize(1);

        int16_t x1, y1;
        uint16_t tw, th;
        tft.getTextBounds(renderStr.c_str(), 0, 0, &x1, &y1, &tw, &th);

        while (tw > box.w && renderStr.length() > 0) {
            renderStr.remove(renderStr.length() - 1);
            tft.getTextBounds(renderStr.c_str(), 0, 0, &x1, &y1, &tw, &th);
        }
        chosenX1 = x1;
        chosenY1 = y1;
        chosenW = tw;
        chosenH = th;
    }

    tft.setFont(chosenFont);
    tft.setTextSize(1);
    tft.setTextColor(textColor, bgColor);

    // 4. Compute cursor position (center or left-align)
    int16_t cursorX = centerH ? (box.x + (box.w - chosenW) / 2 - chosenX1) : (box.x - chosenX1);
    int16_t cursorY = centerV ? (box.y + (box.h - chosenH) / 2 - chosenY1) : (box.y - chosenY1);

    tft.setCursor(cursorX, cursorY);
    tft.print(renderStr);
    return true;
}

void DisplayManager::drawWrappedCmd(const RectBox& box, const String& cmd, int maxLines, uint16_t textColor, uint16_t bgColor) {
    if (cmd.length() == 0) return;

    tft.setTextWrap(false);
    tft.fillRect(box.x, box.y, box.w, box.h, bgColor);

    tft.setFont(NULL); // Built-in 5x7 ASCII font (6px width, 8px height)
    tft.setTextSize(1);
    tft.setTextColor(textColor, bgColor);

    int16_t lineHeight = 9;
    int totalLen = cmd.length();
    int charIdx = 0;

    for (int line = 0; line < maxLines && charIdx < totalLen; line++) {
        int lineStart = charIdx;

        if (line == maxLines - 1) {
            // Final line: measure remainder
            String rem = cmd.substring(lineStart);
            int16_t x1, y1;
            uint16_t tw, th;
            tft.getTextBounds(rem.c_str(), 0, 0, &x1, &y1, &tw, &th);

            if (tw <= box.w) {
                tft.setCursor(box.x, box.y + line * lineHeight);
                tft.print(rem);
                break;
            } else {
                // Truncate from the END with "..."
                while (rem.length() > 0) {
                    String candidate = rem + "...";
                    tft.getTextBounds(candidate.c_str(), 0, 0, &x1, &y1, &tw, &th);
                    if (tw <= box.w) {
                        tft.setCursor(box.x, box.y + line * lineHeight);
                        tft.print(candidate);
                        break;
                    }
                    rem.remove(rem.length() - 1);
                }
                break;
            }
        } else {
            // Non-final line: wrap at character level
            int lineLen = 0;
            while (charIdx < totalLen) {
                String candidate = cmd.substring(lineStart, charIdx + 1);
                int16_t x1, y1;
                uint16_t tw, th;
                tft.getTextBounds(candidate.c_str(), 0, 0, &x1, &y1, &tw, &th);
                if (tw > box.w) {
                    break;
                }
                charIdx++;
                lineLen++;
            }

            if (lineLen == 0 && charIdx < totalLen) {
                charIdx++;
            }

            String currentLine = cmd.substring(lineStart, charIdx);
            tft.setCursor(box.x, box.y + line * lineHeight);
            tft.print(currentLine);
        }
    }
}

void DisplayManager::showBootScreen() {
    currentRenderedState = STATE_BOOT;
    tft.setTextWrap(false);
    int16_t w = tft.width();
    tft.fillScreen(COLOR_CANVAS);
    
    drawHeaderPill("KERNELDECK", COLOR_SKY, COLOR_TEXT_DARK);
    
    // Main Surface Card
    tft.fillRoundRect(10, 48, w - 20, 255, 12, COLOR_SURFACE);
    tft.drawRoundRect(10, 48, w - 20, 255, 12, COLOR_BLACK);

    tft.setFont(&FreeSerifBold9pt7b);
    tft.setTextColor(COLOR_TEXT_DARK);
    tft.setCursor(20, 75);
    tft.print("Physical Safety Interlock");

    tft.setFont(&FreeSans9pt7b);
    tft.setTextColor(COLOR_TEXT_MUTED);
    tft.setCursor(20, 98);
    tft.print("Hardware Boundary v1.0");

    tft.drawFastHLine(20, 110, w - 40, COLOR_CANVAS);

    tft.setTextColor(COLOR_TEXT_DARK);
    tft.setCursor(20, 135);
    tft.print("Display: ST7789 2.8in (OK)");
    
    tft.setCursor(20, 160);
    tft.print("ALLOW: GPIO 12 (Left)");

    tft.setCursor(20, 185);
    tft.print("KILL:  GPIO 14 (Right)");

    tft.setCursor(20, 210);
    tft.print("Gate:  GPIO 27 (LOCK)");

    tft.setTextColor(COLOR_TEXT_MUTED);
    tft.setCursor(20, 260);
    tft.print("Starting services...");
}

void DisplayManager::showConnecting(const char* stage, const char* detail) {
    currentRenderedState = STATE_CONNECTING;
    tft.setTextWrap(false);
    int16_t w = tft.width();
    tft.fillScreen(COLOR_CANVAS);

    drawHeaderPill("CONNECTING", COLOR_CORAL, COLOR_TEXT_DARK);

    tft.fillRoundRect(10, 48, w - 20, 255, 12, COLOR_SURFACE);
    tft.drawRoundRect(10, 48, w - 20, 255, 12, COLOR_BLACK);

    tft.setFont(&FreeSerifBold9pt7b);
    tft.setTextColor(COLOR_TEXT_DARK);
    tft.setCursor(20, 80);
    tft.print(stage);

    tft.setFont(&FreeSans9pt7b);
    tft.setTextColor(COLOR_TEXT_MUTED);
    tft.setCursor(20, 115);
    tft.print(detail);

    tft.drawFastHLine(20, 135, w - 40, COLOR_CANVAS);

    tft.setTextColor(COLOR_TEXT_DARK);
    tft.setCursor(20, 165);
    tft.print("Target Proxy:");

    tft.setFont(&FreeSansBold9pt7b);
    tft.setCursor(20, 190);
    tft.printf("%s:%d", PROXY_HOST, PROXY_PORT);

    tft.setFont(&FreeSans9pt7b);
    tft.setTextColor(COLOR_TEXT_MUTED);
    tft.setCursor(20, 250);
    tft.print("Awaiting handshake...");
}

void DisplayManager::drawTopPill(float spent, float ceiling, bool isConnected) {
    tft.setTextWrap(false);
    int16_t w = tft.width();
    int16_t pillX = 8;
    int16_t pillY = 6;
    int16_t pillW = w - 16;
    int16_t pillH = 32;

    // Draw Midnight Navy Pixel Art Floating Pill
    tft.fillRoundRect(pillX, pillY, pillW, pillH, 16, COLOR_NIGHT_PILL);
    tft.drawRoundRect(pillX, pillY, pillW, pillH, 16, COLOR_PILL_BORDER);

    // Vector connection dot
    drawVectorDot(pillX + 14, pillY + 16, 3, isConnected ? COLOR_SAFE_GREEN : COLOR_ALERT_RED);

    // Status label
    tft.setFont(&FreeSansBold9pt7b);
    tft.setTextColor(COLOR_WHITE);
    tft.setCursor(pillX + 23, pillY + 21);
    tft.print(isConnected ? "ARMED" : "OFFLINE");

    // Separator
    tft.setTextColor(COLOR_PILL_BORDER);
    tft.print(" | ");

    // Telemetry text
    tft.setTextColor(COLOR_WHITE);
    tft.printf("$%.2f", spent);

    tft.setFont(&FreeSans9pt7b);
    tft.setTextColor(COLOR_SKY);
    tft.printf(" / $%.2f", ceiling);
}

uint16_t DisplayManager::getPixelAt(int16_t x, int16_t y) {
    if (x < 0 || x >= 240 || y < 0 || y >= 320) return COLOR_BLACK;

    if (currentRenderedState == STATE_IDLE) {
        return pgm_read_word(&ice_bear_bg[y * 240 + x]);
    }
#if CHALLENGE_ANIMATIONS
    else if (currentRenderedState == STATE_CHALLENGE) {
        // If within bear bounding rect, return pixel from the current animated bear frame
        if (x >= BEAR_X && x < (BEAR_X + BEAR_W) && y >= BEAR_Y && y < (BEAR_Y + BEAR_H)) {
            int16_t bx = x - BEAR_X;
            int16_t by = y - BEAR_Y;
            return pgm_read_word(&bear_frames[currentBearFrame][by * BEAR_W + bx]);
        }
        return pgm_read_word(&challenge_bg[y * 240 + x]);
    }
#endif
    else if (currentRenderedState == STATE_CHALLENGE) {
        return pgm_read_word(&challenge_bg[y * 240 + x]);
    }
    return COLOR_BLACK;
}

void DisplayManager::eraseSnowflake(const Snowflake& flake) {
    if (flake.oldX < 0 || flake.oldY < 0) return;
    for (uint8_t dy = 0; dy < flake.size; dy++) {
        for (uint8_t dx = 0; dx < flake.size; dx++) {
            int16_t px = flake.oldX + dx;
            int16_t py = flake.oldY + dy;
            if (px >= 0 && px < 240 && py >= 0 && py < 320) {
                tft.drawPixel(px, py, getPixelAt(px, py));
            }
        }
    }
}

void DisplayManager::drawSnowflake(const Snowflake& flake) {
    if (flake.size == 1) {
        tft.drawPixel(flake.x, flake.y, flake.color);
    } else {
        tft.fillRect(flake.x, flake.y, 2, 2, flake.color);
    }
}

void DisplayManager::initSnowflakesForState(DeckState state) {
    int minY = (state == STATE_IDLE) ? (CLOCK_Y + CLOCK_DIGIT_H + 4) : 56;
    int maxY = (state == STATE_IDLE) ? 315 : 252;

    for (int i = 0; i < NUM_SNOWFLAKES; i++) {
        flakes[i].x = random(4, 235);
        flakes[i].y = random(minY, maxY);
        flakes[i].oldX = -1;
        flakes[i].oldY = -1;
        flakes[i].size = (i % 3 == 0) ? 2 : 1; // 2px flakes fall faster
        flakes[i].speed = (flakes[i].size == 2) ? random(2, 4) : random(1, 3);
        flakes[i].drift = (i % 3 == 0) ? 1 : ((i % 3 == 1) ? -1 : 0);
        flakes[i].color = (i % 4 == 0) ? COLOR_SKY : COLOR_WHITE;
    }
    lastSnowTick = millis();
}

void DisplayManager::initSnowflakes() {
    initSnowflakesForState(STATE_IDLE);
}

void DisplayManager::resetChallengeAnimations() {
    currentBearFrame = 0;
    breathSeqIdx = 0;
    lastBreathTick = 0;

    isGlinting = false;
    activeGlintX = -1;
    activeGlintY = -1;
    nextGlintTime = 0;
    glintEndTime = 0;

    for (int i = 0; i < NUM_SNOWFLAKES; i++) {
        flakes[i].oldX = -1;
        flakes[i].oldY = -1;
    }
}

void DisplayManager::drawClockGlyph(int16_t x, int16_t y, uint8_t glyphIdx) {
    if (glyphIdx >= CLOCK_GLYPH_COUNT) return;
    const uint8_t* data = clock_glyphs[glyphIdx];
    uint16_t lineBuf[CLOCK_DIGIT_W];

    for (int16_t py = 0; py < CLOCK_DIGIT_H; py++) {
        int bgBase = (y + py) * 240 + x;
        for (int16_t px = 0; px < CLOCK_DIGIT_W; px++) {
            lineBuf[px] = pgm_read_word(&ice_bear_bg[bgBase + px]);
        }

        int rowOffset = py * (CLOCK_DIGIT_W / 2);
        for (int16_t px = 0; px < CLOCK_DIGIT_W; px++) {
            uint8_t byteVal = pgm_read_byte(&data[rowOffset + (px / 2)]);
            uint8_t colIdx = (px % 2 == 0) ? (byteVal >> 4) : (byteVal & 0x0F);
            if (colIdx > 0) {
                lineBuf[px] = pgm_read_word(&clock_palette[colIdx]);
            }
        }
        tft.drawRGBBitmap(x, y + py, lineBuf, CLOCK_DIGIT_W, 1);
    }
}

void DisplayManager::eraseClockSlot(int slot) {
    int16_t x = CLOCK_X + slot * CLOCK_DIGIT_W;
    int16_t y = CLOCK_Y;
    for (int16_t py = 0; py < CLOCK_DIGIT_H; py++) {
        tft.drawRGBBitmap(x, y + py, (const uint16_t*)&ice_bear_bg[(y + py) * 240 + x], CLOCK_DIGIT_W, 1);
    }
}

void DisplayManager::updateClock(bool forceRedraw) {
    if (currentRenderedState != STATE_IDLE) return;
    unsigned long now = millis();
    if (!forceRedraw && now - lastClockTick < 500) return; // Check clock every 500ms
    lastClockTick = now;

    struct tm timeinfo;
    int hour = 0, minute = 0, second = 0;
    if (getLocalTime(&timeinfo, 0)) {
        hour = timeinfo.tm_hour;
        minute = timeinfo.tm_min;
        second = timeinfo.tm_sec;
    } else {
        unsigned long sec = millis() / 1000;
        hour = (sec / 3600) % 24;
        minute = (sec / 60) % 60;
        second = sec % 60;
    }

    int8_t currentDigits[5];
    currentDigits[0] = hour / 10;
    currentDigits[1] = hour % 10;
    currentDigits[2] = CLOCK_COLON_SLOT;
    currentDigits[3] = minute / 10;
    currentDigits[4] = minute % 10;

    bool colonVisible = (second % 2 == 0);

    for (int i = 0; i < 5; i++) {
        if (i == 2) { // Colon slot
            if (forceRedraw || colonVisible != lastColonVisible) {
                if (colonVisible) {
                    drawClockGlyph(CLOCK_X + 2 * CLOCK_DIGIT_W, CLOCK_Y, CLOCK_COLON_SLOT);
                } else {
                    eraseClockSlot(2);
                }
            }
        } else { // Digit slots
            if (forceRedraw || currentDigits[i] != lastRenderedDigits[i]) {
                drawClockGlyph(CLOCK_X + i * CLOCK_DIGIT_W, CLOCK_Y, currentDigits[i]);
                lastRenderedDigits[i] = currentDigits[i];
            }
        }
    }
    lastColonVisible = colonVisible;
}

void DisplayManager::updateSnowflakes() {
    if (currentRenderedState != STATE_IDLE) return;

    // Service clock tick
    updateClock(false);

    if (millis() - lastSnowTick < 45) return; // ~22 FPS non-blocking animation
    lastSnowTick = millis();

    for (int i = 0; i < NUM_SNOWFLAKES; i++) {
        // 1. Erase old snowflake position
        eraseSnowflake(flakes[i]);

        // 2. Advance snowflake position
        flakes[i].y += flakes[i].speed;
        flakes[i].x += flakes[i].drift;

        // Wrap around at bottom boundary
        if (flakes[i].y >= 318) {
            flakes[i].y = (CLOCK_Y + CLOCK_DIGIT_H + random(4, 20));
            flakes[i].x = random(4, 236);
        }

        // Avoid colliding with clock box
        if (flakes[i].x >= (CLOCK_X - 2) && flakes[i].x <= (CLOCK_X + 5 * CLOCK_DIGIT_W + 2) &&
            flakes[i].y >= (CLOCK_Y - 2) && flakes[i].y <= (CLOCK_Y + CLOCK_DIGIT_H + 2)) {
            flakes[i].y = CLOCK_Y + CLOCK_DIGIT_H + 4;
        }

        if (flakes[i].x < 2) flakes[i].x = 236;
        if (flakes[i].x > 236) flakes[i].x = 2;

        // 3. Draw new snowflake position
        drawSnowflake(flakes[i]);
        flakes[i].oldX = flakes[i].x;
        flakes[i].oldY = flakes[i].y;
    }
}

void DisplayManager::updateChallengeAnimations(int secondsRemaining) {
#if CHALLENGE_ANIMATIONS
    if (currentRenderedState != STATE_CHALLENGE) return;
    unsigned long now = millis();

    // 1. Breathing Sequence: 0 -> 1 -> 2 -> 1 repeating
    static const uint8_t breathSequence[4] = {0, 1, 2, 1};
    // Shorten period as 30s countdown nears 0: 450ms at 30s -> 250ms at 0s
    unsigned long breathPeriod = 250 + (secondsRemaining * 200UL) / 30UL;

    bool bearFrameChanged = false;
    if (now - lastBreathTick >= breathPeriod) {
        lastBreathTick = now;
        breathSeqIdx = (breathSeqIdx + 1) % 4;
        uint8_t nextFrame = breathSequence[breathSeqIdx];
        if (nextFrame != currentBearFrame) {
            currentBearFrame = nextFrame;
            bearFrameChanged = true;
        }
    }

    bool snowTick = (now - lastSnowTick >= 60); // Snow updated every ~60ms

    // DRAW ORDER PER TICK: erase flakes -> bear frame (if changed) -> glint -> flakes

    // 1. Erase flakes (restore underlying background / bear pixels)
    if (snowTick) {
        for (int i = 0; i < NUM_SNOWFLAKES; i++) {
            eraseSnowflake(flakes[i]);
        }
    }

    // 2. Bear frame (if changed)
    if (bearFrameChanged) {
        tft.drawRGBBitmap(BEAR_X, BEAR_Y, bear_frames[currentBearFrame], BEAR_W, BEAR_H);
    }

    // 3. Axe Glint: 2x2 white sparkle at blade tip for ~150ms every 3-4s
    int8_t glintOffsetY = (currentBearFrame == 1) ? -1 : ((currentBearFrame == 2) ? -2 : 0);
    int16_t targetGlintX = AXE_GLINT_X;
    int16_t targetGlintY = AXE_GLINT_Y + glintOffsetY;

    if (!isGlinting) {
        if (nextGlintTime == 0) {
            nextGlintTime = now + random(3000, 4000);
        } else if (now >= nextGlintTime) {
            isGlinting = true;
            glintEndTime = now + 150;
            activeGlintX = targetGlintX;
            activeGlintY = targetGlintY;
            tft.fillRect(activeGlintX, activeGlintY, 2, 2, COLOR_WHITE);
        }
    } else {
        // If glinting and bear frame shifted, reposition glint
        if (bearFrameChanged && (activeGlintX != targetGlintX || activeGlintY != targetGlintY)) {
            // Restore old position
            for (int dy = 0; dy < 2; dy++) {
                for (int dx = 0; dx < 2; dx++) {
                    tft.drawPixel(activeGlintX + dx, activeGlintY + dy, getPixelAt(activeGlintX + dx, activeGlintY + dy));
                }
            }
            activeGlintX = targetGlintX;
            activeGlintY = targetGlintY;
            tft.fillRect(activeGlintX, activeGlintY, 2, 2, COLOR_WHITE);
        }

        // Check if 150ms glint duration ended
        if (now >= glintEndTime) {
            isGlinting = false;
            nextGlintTime = now + random(3000, 4000);
            for (int dy = 0; dy < 2; dy++) {
                for (int dx = 0; dx < 2; dx++) {
                    tft.drawPixel(activeGlintX + dx, activeGlintY + dy, getPixelAt(activeGlintX + dx, activeGlintY + dy));
                }
            }
            activeGlintX = -1;
            activeGlintY = -1;
        }
    }

    // 4. Flakes: advance and draw
    if (snowTick) {
        lastSnowTick = now;
        for (int i = 0; i < NUM_SNOWFLAKES; i++) {
            flakes[i].y += flakes[i].speed;
            flakes[i].x += flakes[i].drift;

            // Restrict to scene area: between countdown bar (y=228..250, x=90..150) and buttons (y>=258)
            // Title & command box at y<=54
            bool hitCountdown = (flakes[i].x >= 88 && flakes[i].x <= 152 && flakes[i].y >= 226 && flakes[i].y <= 252);
            bool hitBottom = (flakes[i].y >= 256);

            if (hitCountdown || hitBottom) {
                flakes[i].y = 56;
                flakes[i].x = random(4, 235);
            }
            if (flakes[i].x < 2) flakes[i].x = 236;
            if (flakes[i].x > 236) flakes[i].x = 2;

            drawSnowflake(flakes[i]);
            flakes[i].oldX = flakes[i].x;
            flakes[i].oldY = flakes[i].y;
        }
    }
#endif
}

void DisplayManager::showIdle(TelemetryData& telem, bool isWsConnected, bool forceFullRedraw) {
    if (currentRenderedState != STATE_IDLE || forceFullRedraw) {
        currentRenderedState = STATE_IDLE;
        resetChallengeAnimations();
        
        // 1. Draw Ice Bear pixel art background directly from flash
        tft.drawRGBBitmap(0, 0, ice_bear_bg, 240, 320);

        // 2. Draw Pixel Art Style Floating Top Pill
        drawTopPill(telem.spent, telem.ceiling, isWsConnected);

        // 3. Draw Pixel Art Clock on Idle Sky
        updateClock(true);

        // 4. Re-seed snowflakes
        initSnowflakesForState(STATE_IDLE);
        telem.markClean();
        return;
    }

    // Partial update only when telemetry changes
    if (telem.hasChanged()) {
        drawTopPill(telem.spent, telem.ceiling, isWsConnected);
        telem.markClean();
    }
}

void DisplayManager::showChallenge(const ChallengeData& chal) {
    currentRenderedState = STATE_CHALLENGE;
    lastRenderedSeconds = -1;
    resetChallengeAnimations();
    tft.setTextWrap(false);
    int16_t w = tft.width();

    // 1. Draw Challenge Screen Background from PROGMEM
    tft.drawRGBBitmap(0, 0, challenge_bg, 240, 320);

    // 2. Top Challenge Pill Container
    // Dimensions: x=8, y=6, w=224, h=48
    tft.fillRoundRect(8, 6, w - 16, 48, 14, 0x1882); // Dark Crimson Navy
    tft.drawRoundRect(8, 6, w - 16, 48, 14, COLOR_ALERT_RED);
    tft.drawRoundRect(9, 7, w - 18, 46, 13, COLOR_ALERT_RED);

    // Row 1: Alert Icon + Title + Risk Level Badge
    drawAlertIcon(23, 18);

    // Title: "CHALLENGE" (amber yellow, fits beside icon without overlapping)
    const GFXfont* titleFonts[] = { &FreeSansBold9pt7b, &FreeSans9pt7b, NULL };
    RectBox titleBox = { 34, 9, 116, 17 };
    drawFittedText(titleBox, "CHALLENGE", titleFonts, 0xFD20, 0x1882, false, true);

    // Risk Badge: "[CRITICAL]" in its own badge
    String riskText = chal.risk.length() > 0 ? chal.risk : "CRITICAL";
    RectBox badgeBox = { 154, 9, 70, 17 };
    tft.fillRoundRect(badgeBox.x, badgeBox.y, badgeBox.w, badgeBox.h, 4, COLOR_ALERT_RED);
    tft.drawRoundRect(badgeBox.x, badgeBox.y, badgeBox.w, badgeBox.h, 4, COLOR_WHITE);
    const GFXfont* badgeFonts[] = { NULL }; // 5x7 classic fits badges cleanly (8 chars * 6 = 48px)
    RectBox badgeInner = { (int16_t)(badgeBox.x + 2), (int16_t)(badgeBox.y + 1), (int16_t)(badgeBox.w - 4), (int16_t)(badgeBox.h - 2) };
    drawFittedText(badgeInner, riskText.c_str(), badgeFonts, COLOR_WHITE, COLOR_ALERT_RED, true, true);

    // Row 2: Command line wrapped over up to 2 lines (never removes the beginning)
    RectBox cmdBox = { 14, 29, 212, 21 };
    drawWrappedCmd(cmdBox, chal.cmd, 2, COLOR_WHITE, 0x1882);

    // 3. Countdown Mini-Pill
    updateCountdown(30);

    // 4. Bottom Physical Button Pill Guides (ALLOW on Left, KILL on Right)
    int16_t btnW = 105;
    int16_t btnH = 54;
    int16_t btnY = 258;

    const GFXfont* btnFonts[] = { &FreeSansBold9pt7b, &FreeSans9pt7b, NULL };

    // LEFT: ALLOW (Green / GPIO 12)
    tft.fillRoundRect(10, btnY, btnW, btnH, 14, COLOR_BLACK);
    tft.drawRoundRect(10, btnY, btnW, btnH, 14, COLOR_SAFE_GREEN);
    tft.drawRoundRect(11, btnY + 1, btnW - 2, btnH - 2, 13, COLOR_SAFE_GREEN);
    RectBox allowBox = { 14, (int16_t)(btnY + 4), (int16_t)(btnW - 8), (int16_t)(btnH - 8) };
    drawFittedText(allowBox, "ALLOW", btnFonts, COLOR_WHITE, COLOR_BLACK, true, true);

    // RIGHT: KILL (Red / GPIO 14)
    tft.fillRoundRect(125, btnY, btnW, btnH, 14, COLOR_BLACK);
    tft.drawRoundRect(125, btnY, btnW, btnH, 14, COLOR_ALERT_RED);
    tft.drawRoundRect(126, btnY + 1, btnW - 2, btnH - 2, 13, COLOR_ALERT_RED);
    RectBox killBox = { 129, (int16_t)(btnY + 4), (int16_t)(btnW - 8), (int16_t)(btnH - 8) };
    drawFittedText(killBox, "KILL", btnFonts, COLOR_WHITE, COLOR_BLACK, true, true);

    // Initialize challenge animations
    initSnowflakesForState(STATE_CHALLENGE);
    lastBreathTick = millis();
    nextGlintTime = millis() + random(1000, 2500);
}

void DisplayManager::updateCountdown(int secondsRemaining) {
    if (secondsRemaining == lastRenderedSeconds) return;
    lastRenderedSeconds = secondsRemaining;

    tft.setTextWrap(false);

    int16_t pillW = 60;
    int16_t pillH = 22;
    int16_t pillX = (tft.width() - pillW) / 2; // 90
    int16_t pillY = 228;

    uint16_t timerBorder = (secondsRemaining <= 10) ? COLOR_ALERT_RED : 0xFD20;

    // Mini-pill countdown update (no flicker, no whole-screen redraw)
    tft.fillRoundRect(pillX, pillY, pillW, pillH, 10, COLOR_BLACK);
    tft.drawRoundRect(pillX, pillY, pillW, pillH, 10, timerBorder);

    String timerText = String(secondsRemaining) + "s";
    const GFXfont* timerFonts[] = { &FreeSansBold9pt7b, &FreeSans9pt7b, NULL };
    RectBox timerBox = { (int16_t)(pillX + 2), (int16_t)(pillY + 2), (int16_t)(pillW - 4), (int16_t)(pillH - 4) };
    drawFittedText(timerBox, timerText.c_str(), timerFonts, timerBorder, COLOR_BLACK, true, true);
}

void DisplayManager::showExpired() {
    resetChallengeAnimations();
    tft.setTextWrap(false);

    int16_t pillW = 60;
    int16_t pillH = 22;
    int16_t pillX = (tft.width() - pillW) / 2;
    int16_t pillY = 228;

    tft.fillRoundRect(pillX, pillY, pillW, pillH, 10, COLOR_BLACK);
    tft.drawRoundRect(pillX, pillY, pillW, pillH, 10, COLOR_ALERT_RED);

    const GFXfont* timerFonts[] = { NULL };
    RectBox timerBox = { (int16_t)(pillX + 2), (int16_t)(pillY + 2), (int16_t)(pillW - 4), (int16_t)(pillH - 4) };
    drawFittedText(timerBox, "EXPIRED", timerFonts, COLOR_ALERT_RED, COLOR_BLACK, true, true);
}

void DisplayManager::showResolved(const String& verdict) {
    currentRenderedState = STATE_RESOLVED;
    resetChallengeAnimations();
    tft.setTextWrap(false);
    
    if (verdict == "KILL") {
        // Draw 16-bit pixel art Kill screen (Axe Cleave with 'EXECUTION BLOCKED' red pill)
        tft.drawRGBBitmap(0, 0, kill_bg, 240, 320);
        return;
    }

    if (verdict == "ALLOW") {
        // Draw 16-bit pixel art Allow screen (Ice Bear Approves with 'APPROVED' green pill)
        tft.drawRGBBitmap(0, 0, allow_bg, 240, 320);
        return;
    }

    int16_t w = tft.width();
    tft.fillScreen(COLOR_CANVAS);
    
    if (verdict == "ALLOW") {
        drawHeaderPill("APPROVED", COLOR_MINT, COLOR_TEXT_DARK);

        tft.fillRoundRect(10, 48, w - 20, 255, 12, COLOR_SURFACE);
        tft.drawRoundRect(10, 48, w - 20, 255, 12, COLOR_SAFE_GREEN);
        drawVectorDot(120, 95, 12, COLOR_SAFE_GREEN);

        tft.setFont(&FreeSerifBold9pt7b);
        tft.setTextColor(COLOR_TEXT_DARK);
        tft.setCursor(28, 140);
        tft.print("EXECUTION AUTHORIZED");

        tft.setFont(&FreeSansBold9pt7b);
        tft.setTextColor(COLOR_SAFE_GREEN);
        tft.setCursor(28, 175);
        tft.print("OUT CONTROL: HIGH");

        tft.setFont(&FreeSans9pt7b);
        tft.setTextColor(COLOR_TEXT_MUTED);
        tft.setCursor(28, 205);
        tft.print("Hardware Gate Asserted");
    } else {
        drawHeaderPill("REJECTED", COLOR_CORAL, COLOR_TEXT_DARK);

        tft.fillRoundRect(10, 48, w - 20, 255, 12, COLOR_SURFACE);
        tft.drawRoundRect(10, 48, w - 20, 255, 12, COLOR_ALERT_RED);
        drawVectorCross(120, 95, 12, COLOR_ALERT_RED);

        tft.setFont(&FreeSerifBold9pt7b);
        tft.setTextColor(COLOR_TEXT_DARK);
        tft.setCursor(40, 140);
        tft.print("EXECUTION KILLED");

        tft.setFont(&FreeSansBold9pt7b);
        tft.setTextColor(COLOR_ALERT_RED);
        tft.setCursor(28, 175);
        tft.print("OUT CONTROL: LOW");

        tft.setFont(&FreeSans9pt7b);
        tft.setTextColor(COLOR_TEXT_MUTED);
        tft.setCursor(28, 205);
        tft.print("Hardware Gate Isolated");
    }
}
