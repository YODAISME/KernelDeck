/**
 * KernelDeck ESP32 Firmware — Main Application
 * ============================================
 * Target: ESP32 + ST7789 SPI TFT Display (240x240) + ALLOW / KILL Buttons
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
unsigned long  lastWiFiRetryTime   = 0;

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
        display.showConnecting("Connecting Proxy", PROXY_WS_PATH);
    } else {
        Serial.println("[WIFI] Failed to connect. Will retry in background loop.");
        display.showConnecting("WiFi Failed", "Retrying in background...");
    }
}

void setup() {
    Serial.begin(115200);
    delay(200);

    Serial.println("\n==========================================");
    Serial.println("       KERNELDECK ESP32 HARDWARE DECK     ");
    Serial.println("==========================================");

    // 1. Initialize Display & Show Boot Screen
    display.begin();
    display.showBootScreen();
    delay(1200);

    // 2. Initialize Physical Buttons
    buttons.begin();

    // 3. Connect to WiFi Network
    connectWiFi();

    // 4. Configure WebSocket Client Callbacks (PROTOCOL.md)
    wsClient.begin(
        // On Connection Status Change
        [](bool connected) {
            if (connected) {
                Serial.println("[APP] Hardware connected to Proxy. Switching to STATE_IDLE.");
                activeChallenge.clear();
                transitionToState(STATE_IDLE);
                display.showIdle(telemetry, true);
            } else {
                Serial.println("[APP] Hardware disconnected from Proxy.");
                activeChallenge.clear();
                transitionToState(STATE_CONNECTING);
                display.showConnecting("Proxy Disconnected", "Reconnecting to /ws/deck...");
            }
        },

        // On Inbound CHALLENGE Message
        [](const ChallengeData& chal) {
            Serial.printf("[APP] Received CHALLENGE for '%s'. Switching to STATE_CHALLENGE.\n", chal.cmd.c_str());
            activeChallenge = chal;
            transitionToState(STATE_CHALLENGE);
            display.showChallenge(activeChallenge);
        },

        // On Inbound RESET_IDLE Message
        []() {
            Serial.println("[APP] Received RESET_IDLE. Reverting to STATE_IDLE.");
            activeChallenge.clear();
            transitionToState(STATE_IDLE);
            display.showIdle(telemetry, true);
        },

        // On Telemetry Received from PING
        [](float spent, float ceiling) {
            telemetry.spent = spent;
            telemetry.ceiling = ceiling;

            // Only update display if currently in IDLE state
            if (currentState == STATE_IDLE) {
                // PROTOCOL.md §8: Partial redraw only when values change (forceFullRedraw = false)
                display.showIdle(telemetry, false);
            }
        }
    );
}

void loop() {
    // 1. Service WebSocket Client Network Loop
    wsClient.loop();

    // 2. WiFi Auto-Reconnect Watchdog
    if (WiFi.status() != WL_CONNECTED) {
        if (millis() - lastWiFiRetryTime > 10000) {
            lastWiFiRetryTime = millis();
            Serial.println("[WIFI] Connection lost. Attempting reconnection...");
            WiFi.reconnect();
        }
    }

    // 3. State Machine Logic
    switch (currentState) {
        case STATE_BOOT:
        case STATE_CONNECTING:
            // Handled via callbacks and connection attempts
            break;

        case STATE_IDLE:
            // Idle screen is maintained; periodic PING updates telemetry box
            break;

        case STATE_CHALLENGE: {
            // Poll physical pushbuttons
            ButtonAction action = buttons.poll();

            if (action == BTN_ALLOW) {
                Serial.println("\n[BUTTON] Operator pressed ALLOW switch!");
                wsClient.sendDecision(activeChallenge.requestId, "ALLOW");
                transitionToState(STATE_RESOLVED);
                display.showResolved("ALLOW");
            } 
            else if (action == BTN_KILL) {
                Serial.println("\n[BUTTON] Operator pressed KILL switch!");
                wsClient.sendDecision(activeChallenge.requestId, "KILL");
                transitionToState(STATE_RESOLVED);
                display.showResolved("KILL");
            }
            break;
        }

        case STATE_RESOLVED: {
            // Show transient confirmation (~500ms) before returning to idle (PROTOCOL.md Section 4)
            if (millis() - stateTransitionTime >= RESOLVED_FLASH_MS) {
                Serial.println("[APP] Transient confirmation ended. Reverting to STATE_IDLE.");
                activeChallenge.clear();
                transitionToState(STATE_IDLE);
                display.showIdle(telemetry, true);
            }
            break;
        }
    }

    delay(5); // Yield to ESP32 RTOS scheduler
}
