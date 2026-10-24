#pragma once
#include <Arduino.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include "config.h"
#include "protocol.h"

/**
 * KernelDeck WebSocket Client for ESP32
 * Connects exclusively to /ws/deck on the KernelDeck Proxy.
 * Protocol Reference: PROTOCOL.md
 * Owner: B
 */
class DeckWebSocketClient {
public:
    typedef std::function<void(bool connected)> ConnectionCallback;
    typedef std::function<void(const ChallengeData& chal)> ChallengeCallback;
    typedef std::function<void()> ResetCallback;
    typedef std::function<void(float spent, float ceiling)> TelemetryCallback;

    void begin(
        ConnectionCallback onConn,
        ChallengeCallback onChal,
        ResetCallback onReset,
        TelemetryCallback onTelem
    );
    void loop();
    bool isConnected() const;
    void sendDecision(const String& requestId, const String& verdict);
    void sendPong();

private:
    WebSocketsClient ws;
    bool connected = false;
    unsigned long lastPingTime = 0;

    ConnectionCallback onConnectionChange;
    ChallengeCallback onChallengeReceived;
    ResetCallback onResetIdle;
    TelemetryCallback onTelemetryReceived;

    void handleEvent(WStype_t type, uint8_t* payload, size_t length);
    void parseTextMessage(const char* text);
};
