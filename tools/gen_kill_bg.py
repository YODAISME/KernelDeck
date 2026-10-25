#!/usr/bin/env python3
"""
gen_kill_bg.py
Converts assets/kill_screen.png (240x320) into RGB565 PROGMEM array
in firmware/include/kill_bg.h for KernelDeck ESP32 firmware.
"""

import os
from PIL import Image


def to_rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    src_path = os.path.join(project_root, "assets", "kill_screen.png")
    out_header = os.path.join(project_root, "firmware", "include", "kill_bg.h")

    if not os.path.exists(src_path):
        raise FileNotFoundError(f"Missing {src_path}")

    im = Image.open(src_path).convert("RGB")
    if im.size != (240, 320):
        raise ValueError(f"Expected 240x320, got {im.size}")

    pixels = list(im.getdata())
    rgb565 = [to_rgb565(r, g, b) for r, g, b in pixels]

    print(f"Writing {out_header} ({len(rgb565)} pixels)...")
    with open(out_header, "w") as f:
        f.write("#pragma once\n")
        f.write("#include <Arduino.h>\n\n")
        f.write("/**\n")
        f.write(" * Pixel Art Kill Confirmation Background (240x320 RGB565)\n")
        f.write(" * Ice Bear Axe Cleave with 'EXECUTION BLOCKED' Red Alert Pill\n")
        f.write(" */\n\n")
        f.write(f"const uint16_t kill_bg[{len(rgb565)}] PROGMEM = {{\n")

        for i in range(0, len(rgb565), 16):
            chunk = rgb565[i : i + 16]
            line = "    " + ", ".join(f"0x{val:04X}" for val in chunk)
            if i + 16 < len(rgb565):
                line += ","
            f.write(line + "\n")

        f.write("};\n")

    size_kb = len(rgb565) * 2 / 1024
    print(f"Generated {out_header} successfully ({size_kb:.1f} KB).")


if __name__ == "__main__":
    main()
