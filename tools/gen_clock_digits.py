#!/usr/bin/env python3
"""
gen_clock_digits.py
Generates 4-bit palette-packed pixel art clock digits (0-9 and ':')
from C:\\Users\\where\\Documents\\projects\\pipa\\digits\\final_digits.png
scaled 2x (44x72 px) for the 240x320 TFT display
and exports them to firmware/include/clock_digits.h.
"""

import os
from PIL import Image

SCALE = 2
BASE_W = 22
BASE_H = 36
DIGIT_W = BASE_W * SCALE  # 44
DIGIT_H = BASE_H * SCALE  # 72
NUM_GLYPHS = 11  # 0..9 and 10 is ':'
GLYPH_BYTES = (DIGIT_W * DIGIT_H) // 2  # 1584 bytes per glyph


def to_rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    src_path = r"C:\Users\where\Documents\projects\pipa\digits\final_digits.png"
    out_header = os.path.join(project_root, "firmware", "include", "clock_digits.h")

    if not os.path.exists(src_path):
        raise FileNotFoundError(f"Missing source file: {src_path}")

    orig_im = Image.open(src_path).convert("RGBA")
    # Scale 2x with nearest neighbor to preserve crisp pixel-art edges
    im = orig_im.resize((orig_im.width * SCALE, orig_im.height * SCALE), Image.NEAREST)

    # Determine 16-color palette from original
    colors = orig_im.getcolors()
    opaque = [c for c in colors if c[1][3] > 0]
    opaque.sort(key=lambda x: x[0], reverse=True)

    palette = [(0, 0, 0, 0)]
    for c in opaque[:15]:
        palette.append(c[1])

    def find_nearest_palette_idx(rgba):
        if rgba[3] < 50:
            return 0
        best_idx = 1
        best_dist = 999999
        r, g, b = rgba[:3]
        for i, p_col in enumerate(palette[1:], start=1):
            pr, pg, pb = p_col[:3]
            dist = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
            if dist < best_dist:
                best_dist = dist
                best_idx = i
        return best_idx

    # Pack glyphs
    packed_glyphs = []
    for g in range(NUM_GLYPHS):
        indices = []
        for y in range(DIGIT_H):
            for x in range(DIGIT_W):
                px = im.getpixel((g * DIGIT_W + x, y))
                indices.append(find_nearest_palette_idx(px))

        bytes_arr = []
        for i in range(0, len(indices), 2):
            b = ((indices[i] & 0x0F) << 4) | (indices[i + 1] & 0x0F)
            bytes_arr.append(b)
        packed_glyphs.append(bytes_arr)

    print(f"Writing {out_header}...")
    with open(out_header, "w") as f:
        f.write("#pragma once\n")
        f.write("#include <Arduino.h>\n\n")
        f.write("/**\n")
        f.write(" * Pixel Art Clock Digits (0-9 and ':')\n")
        f.write(" * Source: projects/pipa/digits/final_digits.png (scaled 2x)\n")
        f.write(f" * Formatted as 4-bit indexed palette ({DIGIT_W}x{DIGIT_H} px, {GLYPH_BYTES} bytes/glyph)\n")
        f.write(" */\n\n")
        f.write(f"#define CLOCK_DIGIT_W     {DIGIT_W}\n")
        f.write(f"#define CLOCK_DIGIT_H     {DIGIT_H}\n")
        f.write(f"#define CLOCK_GLYPH_COUNT {NUM_GLYPHS}\n")
        f.write(f"#define CLOCK_GLYPH_BYTES {GLYPH_BYTES}\n")
        f.write("#define CLOCK_COLON_SLOT  10\n\n")

        # 16-color palette
        f.write("// 16-color RGB565 palette (index 0 is transparent)\n")
        f.write("const uint16_t clock_palette[16] PROGMEM = {\n")
        for i, col in enumerate(palette):
            r, g, b = col[:3]
            val565 = to_rgb565(r, g, b) if i > 0 else 0x0000
            comment = "transparent" if i == 0 else f"RGB({r},{g},{b})"
            comma = "," if i < 15 else ""
            f.write(f"    0x{val565:04X}{comma} // {i}: {comment}\n")
        f.write("};\n\n")

        # Packed digit data
        for g in range(NUM_GLYPHS):
            name = f"clock_glyph_{g}" if g < 10 else "clock_glyph_colon"
            label = f"Digit '{g}'" if g < 10 else "Colon ':'"
            f.write(f"// {label} ({DIGIT_W}x{DIGIT_H}, 4-bit packed)\n")
            f.write(f"const uint8_t {name}[CLOCK_GLYPH_BYTES] PROGMEM = {{\n")
            data = packed_glyphs[g]
            for i in range(0, len(data), 16):
                line = "    " + ", ".join(f"0x{b:02X}" for b in data[i : i + 16])
                if i + 16 < len(data):
                    line += ","
                f.write(line + "\n")
            f.write("};\n\n")

        f.write("// Pointers to all 11 glyphs (0..9 and 10 for colon)\n")
        f.write("const uint8_t* const clock_glyphs[CLOCK_GLYPH_COUNT] = {\n")
        for g in range(10):
            f.write(f"    clock_glyph_{g},\n")
        f.write("    clock_glyph_colon\n")
        f.write("};\n")

    total_sz = len(packed_glyphs) * GLYPH_BYTES + 32
    print(f"Generated {out_header} successfully! Total flash size: {total_sz} bytes ({total_sz/1024:.2f} KB)")


if __name__ == "__main__":
    main()
