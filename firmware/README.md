# KernelDeck — Firmware

Owner: **B**

## Overview
The firmware runs on an ESP32 microcontroller with an **ST7789 SPI TFT display** and two physical pushbuttons (**ALLOW** and **KILL**). It forms the physical out-of-band safety interlock between the human operator and the AI agent proxy.

---

## Hardware Pinout (Default ESP32 Mapping)

### Physical Pushbuttons (Active LOW, internal `INPUT_PULLUP`)
| Button | Pin | Color | Action |
|---|---|---|---|
| **ALLOW** | `GPIO 12` | Green | Sends `{"type":"DECISION","verdict":"ALLOW"}` |
| **KILL** | `GPIO 14` | Red | Sends `{"type":"DECISION","verdict":"KILL"}` |

### ST7789 SPI TFT Display (240x240)
| Display Pin | ESP32 Pin | Function |
|---|---|---|
| **GND** | `GND` | Ground |
| **VCC** | `3.3V` / `5V` | Power |
| **SCL / SCK** | `GPIO 18` | SPI Clock |
| **SDA / MOSI** | `GPIO 23` | SPI MOSI Data |
| **RES / RST** | `GPIO 4` | Reset |
| **DC** | `GPIO 2` | Data / Command |
| **CS** | `GPIO 5` | Chip Select (set to `-1` in `config.h` if your module has no CS) |
| **BLK / BL** | `GPIO 15` | Backlight (optional, or tie to 3.3V) |

All pins and screen dimensions are configurable in [`firmware/include/config.h`](include/config.h).

---

## Key Design Principles ([`PROTOCOL.md`](../PROTOCOL.md))

1. **ArduinoJson v7 Dynamic Buffering (§8)**:
   - Uses `JsonDocument doc;` to safely parse arbitrary length command strings without silent truncation crashes.
2. **Flicker-Free Telemetry Redraw (§8)**:
   - Proxy sends `PING` every 5 seconds carrying spend and ceiling telemetry.
   - The screen only redraws the small numerical bounding box when numbers change, leaving the rest of the display completely untouched.
3. **Stateless Reconnect (§4)**:
   - Reconnects to `ws://<HOST>:8080/ws/deck` automatically if connection is lost.
   - Always resets to `STATE_IDLE` upon boot and reconnection.

---

## State Machine

```
[BOOT / CONNECTING] ──> [STATE_IDLE] (Green, displays spend/ceiling)
                              │
                    inbound CHALLENGE
                              │
                              ▼
                      [STATE_CHALLENGE] (Amber/Red, buttons active)
                              │
                ┌─────────────┴─────────────┐
           ALLOW Button                 KILL Button
                │                           │
                ▼                           ▼
        [STATE_RESOLVED]            [STATE_RESOLVED]
        (Flash "ALLOWED")           (Flash "KILLED")
                │                           │
                └─────────────┬─────────────┘
                        500ms timer
                              │
                              ▼
                        [STATE_IDLE]
```

---

## Building and Flashing

### Option A: Using PlatformIO (Recommended)
1. Edit [`firmware/include/config.h`](include/config.h) with your WiFi SSID, Password, and Proxy IP.
2. Build and upload:
   ```bash
   cd firmware
   pio run --target upload
   pio device monitor -b 115200
   ```

### Option B: Using Arduino IDE
1. Install **ESP32 Board Support** via Board Manager.
2. Install required libraries from Library Manager:
   - `ArduinoJson` (v7.x)
   - `WebSockets` by Markus Sattler
   - `Adafruit GFX Library`
   - `Adafruit ST7789 and ST7735 Library`
3. Open `src/main.cpp`, configure `config.h`, select `ESP32 Dev Module`, and click **Upload**.
