#pragma once

/**
 * KernelDeck ESP32 Hardware Configuration
 * =======================================
 * Target Display: ST7789 SPI TFT (240x240 / 240x320)
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

// IP address of the machine running the KernelDeck Proxy (e.g. 192.168.x.x)
#ifndef PROXY_HOST
#define PROXY_HOST "192.168.1.100"
#endif

#define PROXY_PORT     8080
#define PROXY_WS_PATH  "/ws/deck"

// -----------------------------------------------------------------------------
// Physical Button Pin Assignments
// -----------------------------------------------------------------------------
// Wired to Ground with internal INPUT_PULLUP (Active LOW)
#define PIN_BTN_ALLOW  12   // Green button (ALLOW)
#define PIN_BTN_KILL   14   // Red button (KILL)
#define DEBOUNCE_MS    35   // Debounce delay in milliseconds

// -----------------------------------------------------------------------------
// ST7789 TFT Display SPI Pin Assignments
// -----------------------------------------------------------------------------
// Standard ESP32 VSPI pins
#define TFT_CS         5    // Chip select (set to -1 if your ST7789 module has no CS pin)
#define TFT_DC         2    // Data/Command pin
#define TFT_RST        4    // Reset pin (set to -1 if tied to EN/3.3V)
#define TFT_MOSI       23   // SPI Data Out (SDA / MOSI)
#define TFT_SCLK       18   // SPI Clock (SCL / SCLK)
#define TFT_BL         15   // Backlight control (optional, set to -1 if tied to 3.3V)

// Screen Dimensions & Orientation
#define TFT_WIDTH      240
#define TFT_HEIGHT     240
#define TFT_ROTATION   2    // 0, 1, 2, or 3 depending on mounting orientation

// -----------------------------------------------------------------------------
// Timing Constants
// -----------------------------------------------------------------------------
#define RESOLVED_FLASH_MS  600   // Duration to show transient ALLOWED/KILLED banner
#define PING_TIMEOUT_MS    12000 // 2 missed pings threshold (proxy pings every 5s)
