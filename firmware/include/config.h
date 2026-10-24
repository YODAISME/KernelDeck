#pragma once

/**
 * KernelDeck ESP32 Hardware Configuration
 * =======================================
 * Target Display: TPM408-2.8 (2.8" 240x320 TFT, ST7789 Driver)
 * Output Control: Hardware Interlock Relay / Gate Control Pin
 * Owner: B
 * Protocol Reference: PROTOCOL.md
 */

// -----------------------------------------------------------------------------
// WiFi & Proxy Connection Details
// -----------------------------------------------------------------------------
#ifndef WIFI_SSID
#define WIFI_SSID "YOUR_WIFI_SSID"
#endif

#ifndef WIFI_PASS
#define WIFI_PASS "YOUR_WIFI_PASSWORD"
#endif

// IP address of machine running KernelDeck Proxy (e.g. 192.168.x.x)
#ifndef PROXY_HOST
#define PROXY_HOST "192.168.1.100"
#endif

#define PROXY_PORT     8080
#define PROXY_WS_PATH  "/ws/deck"

// -----------------------------------------------------------------------------
// Physical Button Pin Assignments
// -----------------------------------------------------------------------------
// Pushbuttons wired to Ground with internal INPUT_PULLUP (Active LOW)
#define PIN_BTN_ALLOW  12   // Green momentary switch (ALLOW)
#define PIN_BTN_KILL   14   // Red momentary switch (KILL)
#define DEBOUNCE_MS    35   // Debounce delay in milliseconds

// -----------------------------------------------------------------------------
// Output Control Pin (Hardware Relay / External Interlock Gate)
// -----------------------------------------------------------------------------
// Drives physical relay, optocoupler, or external enable signal:
// - LOW  = Safe / Interlocked / Isolated (Default, Kill, Offline, Timeout)
// - HIGH = Unlocked / Execution Authorized (Operator ALLOW)
#define PIN_OUT_CONTROL         27
#define OUT_CONTROL_ACTIVE_HIGH true

// -----------------------------------------------------------------------------
// TPM408-2.8 TFT Display Pin Assignments (ST7789 SPI)
// -----------------------------------------------------------------------------
// Standard VSPI Pinout for ESP32 & TPM408 2.8" ST7789 Module
#define TFT_CS         15   // Display Chip Select
#define TFT_DC         2    // Data / Command pin (RS)
#define TFT_RST        4    // Hardware Reset pin
#define TFT_MOSI       23   // SPI MOSI / SDI
#define TFT_SCLK       18   // SPI Clock / SCK
#define TFT_MISO       19   // SPI MISO / SDO (optional)
#define TFT_BL         21   // Display Backlight control (LED / BLK)

// Screen Geometry & Orientation
// TPM408-2.8 native resolution is 240x320
#define TFT_WIDTH      240
#define TFT_HEIGHT     320
#define TFT_ROTATION   1    // 1 = Landscape (320x240), 0 = Portrait (240x320)

// -----------------------------------------------------------------------------
// Timing Constants
// -----------------------------------------------------------------------------
#define RESOLVED_FLASH_MS  600   // Duration to show transient ALLOWED/KILLED banner
#define PING_TIMEOUT_MS    12000 // 2 missed pings threshold (proxy pings every 5s)
