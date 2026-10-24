#pragma once
#include <Arduino.h>

/**
 * KernelDeck Wire Protocol Structures & State Definitions
 * =======================================================
 * Protocol Reference: PROTOCOL.md
 */

// Hardware State Machine States (PROTOCOL.md Section 4)
enum DeckState {
    STATE_BOOT,        // Displaying boot logo and system info
    STATE_CONNECTING,  // Establishing WiFi / WebSocket connection
    STATE_IDLE,        // Green idle screen displaying spend and ceiling telemetry
    STATE_CHALLENGE,   // Amber/red alert screen displaying risky command and cost
    STATE_RESOLVED     // Transient (~500ms) confirmation screen before returning to idle
};

// Physical Button Action Values
enum ButtonAction {
    BTN_NONE,
    BTN_ALLOW,
    BTN_KILL
};

// Inbound CHALLENGE Payload (PROTOCOL.md Section 2)
struct ChallengeData {
    String requestId;
    String cmd;
    String risk;
    String cost;
    String nonce;
    bool active = false;

    void clear() {
        requestId = "";
        cmd = "";
        risk = "";
        cost = "";
        nonce = "";
        active = false;
    }
};

// Telemetry State Delivered via periodic PING (PROTOCOL.md Section 2)
struct TelemetryData {
    float spent = 0.0f;
    float ceiling = 0.0f;
    float prevSpent = -1.0f;
    float prevCeiling = -1.0f;
    bool dirty = true;

    bool hasChanged() const {
        return (spent != prevSpent) || (ceiling != prevCeiling);
    }

    void markClean() {
        prevSpent = spent;
        prevCeiling = ceiling;
        dirty = false;
    }
};
