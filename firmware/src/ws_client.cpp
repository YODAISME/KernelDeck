#include "ws_client.h"

void DeckWebSocketClient::begin(
    ConnectionCallback onConn,
    ChallengeCallback onChal,
    ResetCallback onReset,
    TelemetryCallback onTelem
) {
    this->onConnectionChange = onConn;
    this->onChallengeReceived = onChal;
    this->onResetIdle = onReset;
    this->onTelemetryReceived = onTelem;

    Serial.printf("[WS] Configuring connection to ws://%s:%d%s\n", PROXY_HOST, PROXY_PORT, PROXY_WS_PATH);

    ws.begin(PROXY_HOST, PROXY_PORT, PROXY_WS_PATH);
    ws.onEvent([this](WStype_t type, uint8_t* payload, size_t length) {
        this->handleEvent(type, payload, length);
    });
    
    // Auto-reconnect every 3 seconds if disconnected
    ws.setReconnectInterval(3000);
}

void DeckWebSocketClient::loop() {
    ws.loop();
}

bool DeckWebSocketClient::isConnected() const {
    return connected;
}

void DeckWebSocketClient::handleEvent(WStype_t type, uint8_t* payload, size_t length) {
    switch (type) {
        case WStype_DISCONNECTED:
            Serial.println("[WS] Disconnected from KernelDeck Proxy");
            connected = false;
            if (onConnectionChange) onConnectionChange(false);
            break;

        case WStype_CONNECTED:
            Serial.printf("[WS] Connected to KernelDeck Proxy at %s\n", (char*)payload);
            connected = true;
            lastPingTime = millis();
            if (onConnectionChange) onConnectionChange(true);
            break;

        case WStype_TEXT:
            parseTextMessage((char*)payload);
            break;

        case WStype_BIN:
        case WStype_ERROR:
        case WStype_FRAGMENT_TEXT_START:
        case WStype_FRAGMENT_BIN_START:
        case WStype_FRAGMENT:
        case WStype_FRAGMENT_FIN:
        case WStype_PING:
        case WStype_PONG:
            break;
    }
}

void DeckWebSocketClient::parseTextMessage(const char* text) {
    // PROTOCOL.md §8: Use ArduinoJson v7 (JsonDocument doc;) to prevent silent buffer truncation
    JsonDocument doc;
    DeserializationError err = deserializeJson(doc, text);
    if (err) {
        Serial.printf("[WS] Error: Malformed JSON received: %s\n", err.c_str());
        return;
    }

    const char* type = doc["type"] | "";

    if (strcmp(type, "PING") == 0) {
        // PING doubles as telemetry carrier (PROTOCOL.md Section 2)
        lastPingTime = millis();
        float spent = doc["spent"] | 0.0f;
        float ceiling = doc["ceiling"] | 0.0f;

        if (onTelemetryReceived) {
            onTelemetryReceived(spent, ceiling);
        }

        // Respond with PONG immediately
        sendPong();
    }
    else if (strcmp(type, "CHALLENGE") == 0) {
        // CHALLENGE issued from proxy
        ChallengeData chal;
        chal.requestId = doc["request_id"] | "";
        chal.cmd       = doc["cmd"] | "";
        chal.risk      = doc["risk"] | "CRITICAL";
        chal.cost      = doc["cost"] | "$0.00";
        chal.nonce     = doc["nonce"] | "";
        chal.active    = true;

        Serial.printf("[WS] CHALLENGE received: req_id=%s, cmd=%s\n", chal.requestId.c_str(), chal.cmd.c_str());

        if (onChallengeReceived) {
            onChallengeReceived(chal);
        }
    }
    else if (strcmp(type, "RESET_IDLE") == 0) {
        // RESET_IDLE received from proxy
        Serial.println("[WS] RESET_IDLE received: Reverting to idle state");
        if (onResetIdle) {
            onResetIdle();
        }
    }
    else {
        Serial.printf("[WS] Unknown message type ignored: %s\n", type);
    }
}

void DeckWebSocketClient::sendPong() {
    // PROTOCOL.md Section 2: { "type": "PONG" }
    JsonDocument doc;
    doc["type"] = "PONG";

    String jsonStr;
    serializeJson(doc, jsonStr);
    ws.sendTXT(jsonStr);
}

void DeckWebSocketClient::sendDecision(const String& requestId, const String& verdict) {
    // PROTOCOL.md Section 2: { "type": "DECISION", "request_id": "...", "verdict": "ALLOW" | "KILL" }
    JsonDocument doc;
    doc["type"] = "DECISION";
    doc["request_id"] = requestId;
    doc["verdict"] = verdict;

    String jsonStr;
    serializeJson(doc, jsonStr);
    ws.sendTXT(jsonStr);

    Serial.printf("[WS] Emitted DECISION: req_id=%s, verdict=%s\n", requestId.c_str(), verdict.c_str());
}
