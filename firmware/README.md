# KernelDeck — Firmware

Owner: **B**

## Overview
The firmware runs on an ESP32 microcontroller with a **TPM408-2.8 (2.8" 240x320 ST7789 TFT LCD)**, two physical pushbuttons (**ALLOW** and **KILL**), and a physical **Hardware Output Control** gate pin. It forms the physical, out-of-band safety interlock between the human operator and the AI agent proxy.

---

## Complete Hardware Pinout (ESP32 & TPM408-2.8)

### 1. Physical Pushbuttons (Active LOW, internal `INPUT_PULLUP`)
| Button | Pin | Color | Action |
|---|---|---|---|
| **ALLOW** | `GPIO 12` | Green | Sends `{"type":"DECISION","verdict":"ALLOW"}` & asserts Output Control |
| **KILL** | `GPIO 14` | Red | Sends `{"type":"DECISION","verdict":"KILL"}` & locks Output Control |

### 2. Hardware Output Control (Interlock Relay / Enable Signal)
| Control Line | ESP32 Pin | Logic | State Description |
|---|---|---|---|
| **OUT_CONTROL** | `GPIO 27` | Active HIGH | **LOW** = Isolated / Interlocked (Boot, Idle, Kill, Timeout, Offline)<br>**HIGH** = Authorized / Unlocked (Operator ALLOW) |

### 3. TPM408-2.8 Display Module (2.8" 240x320, ST7789 Driver)
| TPM408-2.8 Pin | Description | ESP32 GPIO Pin (VSPI) |
|---|---|---|
| **VCC / VDD** | Power Supply (3.3V / 5V) | `3V3` or `VIN` (5V) |
| **GND** | Ground | `GND` |
| **CS** | Display Chip Select | `GPIO 15` |
| **RESET / RST** | Hardware Reset | `GPIO 4` |
| **DC / RS** | Data / Command Control | `GPIO 2` |
| **SDI / MOSI** | SPI Data Input | `GPIO 23` (VSPI MOSI) |
| **SCK / CLK** | SPI Clock | `GPIO 18` (VSPI SCK) |
| **SDO / MISO** | SPI Data Output (Optional) | `GPIO 19` (VSPI MISO) |
| **LED / BLK** | Display Backlight Control | `GPIO 21` (or tied to `3V3`) |

All pins and screen dimensions are centralized in [`firmware/include/config.h`](include/config.h).

---

## Key Design Principles ([`PROTOCOL.md`](../PROTOCOL.md))

1. **Dual Hardware Gating (Out-of-Band)**:
   - Digital Gate: Emits `DECISION` payload (`ALLOW` or `KILL`) back to proxy over `/ws/deck`.
   - Physical Gate: Drives `PIN_OUT_CONTROL` (`GPIO 27`) to physically enable or cut off downstream power/circuits.
2. **ArduinoJson v7 Dynamic Buffering (§8)**:
   - Uses `JsonDocument doc;` to parse arbitrary length command strings without silent truncation crashes.
3. **Flicker-Free Telemetry Redraw (§8)**:
   - Proxy sends `PING` every 5 seconds carrying spend and ceiling telemetry.
   - The screen only redraws the small numerical bounding box when numbers change, leaving the rest of the display completely untouched.
4. **Stateless Reconnect (§4)**:
   - Reconnects to `ws://<HOST>:8080/ws/deck` automatically if connection is lost.
   - Always resets to `STATE_IDLE` upon boot and reconnection, ensuring immediate fail-closed isolation of the Output Control pin.

---

## State Machine

```
[BOOT / CONNECTING] ──> [STATE_IDLE] (Green, Gate Isolated)
                              │
                    inbound CHALLENGE
                              │
                              ▼
                      [STATE_CHALLENGE] (Red/Amber alert, buttons active)
                              │
                ┌─────────────┴─────────────┐
           ALLOW Button                 KILL Button
                │                           │
                ▼                           ▼
        [STATE_RESOLVED]            [STATE_RESOLVED]
        (OUT_CONTROL: HIGH)         (OUT_CONTROL: LOW)
        (Flash "ALLOWED")           (Flash "KILLED")
                │                           │
                └─────────────┬─────────────┘
                        600ms timer
                              │
                              ▼
                        [STATE_IDLE] (OUT_CONTROL returns to LOW)
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
