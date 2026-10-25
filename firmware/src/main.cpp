/**
 * KernelDeck ESP32 Firmware — Main Application
 * ============================================
 * Target: ESP32 + TPM408-2.8 (2.8" ST7789 TFT) + ALLOW / KILL Buttons + Output Control Pin
 * Owner: B
 * Protocol Reference: PROTOCOL.md
 */

#include <Arduino.h>
#include <WiFi.h>

#include "config.h"
#include "protocol.h"
#include "buttons.h"
#include "display.h"
#include "ws_client.h"

// Subsystem Instances
DisplayManager       display;
ButtonManager        buttons;
DeckWebSocketClient  wsClient;

// State Machine Globals
DeckState      currentState        = STATE_BOOT;
ChallengeData  activeChallenge;
TelemetryData  telemetry;
unsigned long  stateTransitionTime = 0;
unsigned long  challengeStartMs    = 0;
int            lastTickSec         = 30;
bool           buttonsLocked       = false;
unsigned long  lastWiFiRetryTime   = 0;

void setOutControl(bool enabled) {
    bool pinLevel = enabled ? (OUT_CONTROL_ACTIVE_HIGH ? HIGH : LOW)
                            : (OUT_CONTROL_ACTIVE_HIGH ? LOW : HIGH);
    digitalWrite(PIN_OUT_CONTROL, pinLevel);
    Serial.printf("[GATE OUT] Output Control is %s (GPIO %d = %s)\n",
                  enabled ? "ASSERTED / UNLOCKED" : "ISOLATED / LOCKED",
                  PIN_OUT_CONTROL,
                  pinLevel == HIGH ? "HIGH" : "LOW");
}

void transitionToState(DeckState newState) {
    currentState = newState;
    stateTransitionTime = millis();
}

void connectWiFi() {
    Serial.printf("[WIFI] Connecting to SSID: %s\n", WIFI_SSID);
    display.showConnecting("WiFi Connection", WIFI_SSID);

    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASS);

    unsigned long startAttempt = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - startAttempt < 10000) {
        delay(250);
        Serial.print(".");
    }
    Serial.println();

    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("[WIFI] Connected! IP: %s\n", WiFi.localIP().toString().c_str());
        // Sync local time via SNTP (UTC+05:30 IST: 19800s, 0 daylight saving)
        configTime(19800, 0, "pool.ntp.org", "time.google.com");
        display.showConnecting("Connecting Proxy", PROXY_WS_PATH);
    } else {
        Serial.println("[WIFI] Failed to connect. Will retry in background loop.");
        display.showConnecting("WiFi Failed", "Retrying in background...");
    }
}

void setup() {
    Serial.begin(115200);
    delay(100);

    Serial.println("\n==========================================");
    Serial.println("   KERNELDECK HARDWARE DECK (TPM408-2.8)  ");
    Serial.println("==========================================");

    // 1. Initialize Hardware Output Control Pin (Strict Fail-Closed Default)
    pinMode(PIN_OUT_CONTROL, OUTPUT);
    setOutControl(false);

    // 2. Initialize ST7789 Display & Show Boot Screen
    display.begin();
    display.showBootScreen();
    delay(400);

    // 3. Initialize Physical Buttons
    buttons.begin();

    // 4. Connect to WiFi Network
    connectWiFi();

    // 5. Configure WebSocket Client Callbacks (PROTOCOL.md)
    wsClient.begin(
        // On Connection Status Change
        [](bool connected) {
            if (connected) {
                Serial.println("[APP] Hardware connected to Proxy. Switching to STATE_IDLE.");
                setOutControl(false);
                activeChallenge.clear();
                buttonsLocked = false;
                transitionToState(STATE_IDLE);
                display.showIdle(telemetry, true, true);
            } else {
                Serial.println("[APP] Hardware disconnected from Proxy.");
                setOutControl(false); // Immediate hardware lockdown
                activeChallenge.clear();
                buttonsLocked = false;
                display.resetChallengeAnimations();
                transitionToState(STATE_CONNECTING);
                display.showConnecting("Proxy Disconnected", "Reconnecting to /ws/deck...");
            }
        },

        // On Inbound CHALLENGE Message
        [](const ChallengeData& chal) {
            Serial.printf("[APP] Received CHALLENGE for '%s'. Switching to STATE_CHALLENGE.\n", chal.cmd.c_str());
            setOutControl(false); // Ensure gate output is isolated while awaiting decision
            activeChallenge = chal;
            challengeStartMs = millis();
            lastTickSec = 30;
            buttonsLocked = false;
            transitionToState(STATE_CHALLENGE);
            display.showChallenge(activeChallenge);
        },

        // On Inbound RESET_IDLE Message
        []() {
            Serial.println("[APP] Received RESET_IDLE. Reverting to STATE_IDLE.");
            setOutControl(false);
            activeChallenge.clear();
            buttonsLocked = false;
            display.resetChallengeAnimations();
            transitionToState(STATE_IDLE);
            display.showIdle(telemetry, wsClient.isConnected(), true);
        },

        // On Telemetry Received from PING
        [](float spent, float ceiling) {
            telemetry.spent = spent;
            telemetry.ceiling = ceiling;

            // Only update display if currently in IDLE state
            if (currentState == STATE_IDLE) {
                // PROTOCOL.md §8: Partial redraw only when values change (forceFullRedraw = false)
                display.showIdle(telemetry, wsClient.isConnected(), false);
            }
        }
    );
}

void loop() {
    // 1. Service WebSocket Client Network Loop (MUST run on every loop)
    wsClient.loop();

    // 2. WiFi Auto-Reconnect Watchdog
    if (WiFi.status() != WL_CONNECTED) {
        if (millis() - lastWiFiRetryTime > 10000) {
            lastWiFiRetryTime = millis();
            Serial.println("[WIFI] Connection lost. Attempting reconnection...");
            setOutControl(false); // Fail-closed isolation
            WiFi.reconnect();
        }
    }

    // 3. State Machine Logic (Non-blocking millis() scheduler)
    switch (currentState) {
        case STATE_BOOT:
        case STATE_CONNECTING:
            // Handled via callbacks and connection attempts
            break;

        case STATE_IDLE:
            // Non-blocking snowflakes animation over Ice Bear pixel art background
            display.updateSnowflakes();
            break;

        case STATE_CHALLENGE: {
            // Local 30s countdown tracking (PROTOCOL: CHALLENGE carries no TTL parameter)
            unsigned long elapsed = millis() - challengeStartMs;
            int remaining = 30 - (elapsed / 1000);
            if (remaining < 0) remaining = 0;

            if (remaining != lastTickSec) {
                lastTickSec = remaining;
                display.updateCountdown(remaining);
            }

            if (remaining == 0) {
                // Local 30s expired: lock out buttons and show expired message
                if (!buttonsLocked) {
                    buttonsLocked = true;
                    Serial.println("[CHALLENGE] 30s local TTL expired. Disabling buttons, awaiting RESET_IDLE.");
                    display.resetChallengeAnimations();
                    display.showExpired();
                }
                // Never resolve locally. Await proxy's RESET_IDLE.
            } else if (!buttonsLocked) {
                // Service non-blocking challenge animations (breathing, axe glint, falling snow)
                display.updateChallengeAnimations(remaining);

                // Poll physical pushbuttons
                ButtonAction action = buttons.poll();

                if (action == BTN_ALLOW) {
                    buttonsLocked = true; // Prevent duplicate button presses
                    Serial.println("\n[BUTTON] Operator pressed ALLOW switch (Left / GPIO 12)!");
                    setOutControl(true); // Physically assert output control gate
                    display.resetChallengeAnimations();
                    wsClient.sendDecision(activeChallenge.requestId, "ALLOW");
                    transitionToState(STATE_RESOLVED);
                    display.showResolved("ALLOW");
                } 
                else if (action == BTN_KILL) {
                    buttonsLocked = true; // Prevent duplicate button presses
                    Serial.println("\n[BUTTON] Operator pressed KILL switch (Right / GPIO 14)!");
                    setOutControl(false); // Enforce lockdown
                    display.resetChallengeAnimations();
                    wsClient.sendDecision(activeChallenge.requestId, "KILL");
                    transitionToState(STATE_RESOLVED);
                    display.showResolved("KILL");
                }
            }
            break;
        }

        case STATE_RESOLVED: {
            // Show transient confirmation (~600ms) before returning to idle (PROTOCOL.md Section 4)
            if (millis() - stateTransitionTime >= RESOLVED_FLASH_MS) {
                Serial.println("[APP] Transient confirmation ended. Reverting to STATE_IDLE.");
                setOutControl(false); // Return to default interlocked isolation
                activeChallenge.clear();
                buttonsLocked = false;
                transitionToState(STATE_IDLE);
                display.showIdle(telemetry, wsClient.isConnected(), true);
            }
            break;
        }
    }

    delay(5); // Yield 5ms to ESP32 RTOS scheduler
}
