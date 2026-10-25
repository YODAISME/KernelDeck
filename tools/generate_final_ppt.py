#!/usr/bin/env python3
"""
generate_final_ppt.py
Generates the complete, high-impact final Review 3 presentation for KernelDeck
based strictly on Review 3 Template.pptx.
"""

import os
import shutil
import pptx
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

def main():
    src_template = r"C:\Users\where\Downloads\Review 3 Template.pptx"
    out_dir = r"c:\Users\where\Documents\c2c_2026"
    out_pptx = os.path.join(out_dir, "KernelDeck_Review_3_Final.pptx")
    out_downloads = r"C:\Users\where\Downloads\KernelDeck_Review_3_Final.pptx"

    if not os.path.exists(src_template):
        raise FileNotFoundError(f"Template not found: {src_template}")

    prs = Presentation(src_template)
    print(f"Loaded template with {len(prs.slides)} slides.")

    # Color palette
    NAVY_DARK = RGBColor(15, 23, 42)      # #0F172A
    BLUE_ACCENT = RGBColor(37, 99, 235)   # #2563EB
    RED_ALERT = RGBColor(220, 38, 38)     # #DC2626
    GREEN_SAFE = RGBColor(16, 185, 129)   # #10B981
    SLATE_TEXT = RGBColor(51, 65, 85)     # #334155
    MUTED_TEXT = RGBColor(100, 116, 139)  # #64748B
    WHITE = RGBColor(255, 255, 255)

    def set_font(run, name="Calibri", size_pt=14, bold=False, color=SLATE_TEXT):
        run.font.name = name
        run.font.size = Pt(size_pt)
        run.font.bold = bold
        run.font.color.rgb = color

    # =========================================================================
    # SLIDE 1: Title Slide
    # =========================================================================
    s1 = prs.slides[0]
    title_box = s1.shapes[0]
    sub_box = s1.shapes[1]

    # Title text
    tf1 = title_box.text_frame
    tf1.clear()
    p1 = tf1.paragraphs[0]
    p1.text = "KernelDeck"
    p1.font.name = "Calibri"
    p1.font.size = Pt(40)
    p1.font.bold = True
    p1.font.color.rgb = BLUE_ACCENT
    p1.alignment = PP_ALIGN.CENTER

    p1_sub = tf1.add_paragraph()
    p1_sub.text = "Out-of-Band Physical Control Plane & Hardware Safety Interlock for Autonomous AI Development Agents"
    p1_sub.font.name = "Calibri"
    p1_sub.font.size = Pt(20)
    p1_sub.font.bold = True
    p1_sub.font.color.rgb = NAVY_DARK
    p1_sub.alignment = PP_ALIGN.CENTER

    p1_track = tf1.add_paragraph()
    p1_track.text = "Track 2: Agentic AI  |  Problem 3: Simulated Consequences Before Real Action"
    p1_track.font.name = "Calibri"
    p1_track.font.size = Pt(15)
    p1_track.font.color.rgb = RED_ALERT
    p1_track.font.bold = True
    p1_track.alignment = PP_ALIGN.CENTER

    # Subtitle / Team Members
    tf_sub = sub_box.text_frame
    tf_sub.clear()
    p_team = tf_sub.paragraphs[0]
    p_team.text = "Team: KernelDeck"
    p_team.font.name = "Calibri"
    p_team.font.size = Pt(17)
    p_team.font.bold = True
    p_team.font.color.rgb = NAVY_DARK
    p_team.alignment = PP_ALIGN.CENTER

    members = [
        ("Sanchit Gupta", "25BCE0282", "Proxy & Security Architecture"),
        ("Prisha Tyagi", "25BCE0297", "Firmware & Hardware Interlock"),
        ("Pushpanvitha P", "25BCB0081", "Agent CLI & Execution Boundary"),
        ("Divyadarshini Lakshminarayanan", "25BCB0120", "Dashboard & Telemetry Stream"),
        ("M Sarvesh", "25BEC0140", "Integration, Benchmarks & Safety Validation"),
    ]

    for name, reg, role in members:
        pm = tf_sub.add_paragraph()
        pm.text = f"{name} ({reg})  —  {role}"
        pm.font.name = "Calibri"
        pm.font.size = Pt(13)
        pm.font.color.rgb = SLATE_TEXT
        pm.alignment = PP_ALIGN.CENTER

    # =========================================================================
    # SLIDE 2: Problem Statement & Objectives
    # =========================================================================
    s2 = prs.slides[1]
    s2.shapes.title.text = "Problem Statement & Objectives"
    c2 = s2.shapes[1]
    tf2 = c2.text_frame
    tf2.clear()

    def add_bullet(tf, bold_prefix, text, level=0, size_pt=14, prefix_col=NAVY_DARK):
        p = tf.add_paragraph() if tf.paragraphs and tf.paragraphs[0].text else tf.paragraphs[0]
        p.level = level
        p.space_after = Pt(6)
        if bold_prefix:
            r1 = p.add_run()
            r1.text = bold_prefix + " "
            set_font(r1, "Calibri", size_pt, bold=True, color=prefix_col)
        r2 = p.add_run()
        r2.text = text
        set_font(r2, "Calibri", size_pt, bold=False, color=SLATE_TEXT)

    add_bullet(tf2, "Context:", "Autonomous AI coding agents (Claude Code, Cursor, Devin) now independently execute terminal commands, modify codebases, and interact with cloud resources.", 0, 15, BLUE_ACCENT)
    add_bullet(tf2, "The Critical Problem — No Consequence Boundary:", "High-stakes operations (e.g. 'rm -rf ./database', destructive database drops, runaway API token loops) execute without physical blast-radius evaluation. Software agents lack physical consequence perception.", 0, 15, RED_ALERT)
    add_bullet(tf2, "The 'Key Under the Doormat' Vulnerability:", "Storing production credentials in local .env files exposes high-privilege keys. A compromised agent subshell or prompt injection can leak secrets and act unsupervised.", 1, 14)
    add_bullet(tf2, "Software Dashboards & Modals Fail:", "On-screen IDE popups and modal confirmation dialogs get buried under active windows, can be auto-dismissed by scripts, or bypassed within the same user permission context.", 1, 14)
    add_bullet(tf2, "Project Objectives:", "", 0, 15, GREEN_SAFE)
    add_bullet(tf2, "1. Out-of-Band Physical Authority:", "Enforce a mandatory physical tactile button press (ALLOW/KILL) on an external microcontroller before privileged commands can execute.", 1, 14)
    add_bullet(tf2, "2. Zero-Trust Credential Isolation:", "Relocate API keys into a secure proxy vault; developer machines only hold non-privileged dummy tokens.", 1, 14)
    add_bullet(tf2, "3. Strict Fail-Closed Security:", "Guarantee 100% hardware isolation (GPIO 27 relay isolated at 0V) whenever hardware disconnects or times out.", 1, 14)

    # =========================================================================
    # SLIDE 3: Proposed Solution & Key Innovation
    # =========================================================================
    s3 = prs.slides[2]
    s3.shapes.title.text = "Proposed Solution & Key Innovation"
    c3 = s3.shapes[1]
    # Resize placeholder to left half to make room for hardware screenshot trio
    c3.left = Inches(0.8)
    c3.top = Inches(1.8)
    c3.width = Inches(6.8)
    c3.height = Inches(5.2)

    tf3 = c3.text_frame
    tf3.clear()

    add_bullet(tf3, "The KernelDeck Solution:", "A dual-layer security control plane combining an intelligent, transparent API proxy with a dedicated desktop hardware console (ESP32 + 2.8\" SPI TFT + physical buttons).", 0, 14, BLUE_ACCENT)
    add_bullet(tf3, "Key Architectural Innovations:", "", 0, 14, NAVY_DARK)
    add_bullet(tf3, "• Out-of-Band Physical Isolation:", "\"You cannot code-review your way out of a locked door.\" The safety boundary is enforced in hardware silicon and physical copper (GPIO 27 relay), unreachable by compromised host software.", 1, 13)
    add_bullet(tf3, "• Transparent In-Flight Request Freezing:", "The proxy pauses the agent's HTTP connection mid-flight upon detecting a risky pattern. Safe read operations pass at wire speed (<50 ms); destructive operations halt until human resolution.", 1, 13)
    add_bullet(tf3, "• Physical Tactical Authority:", "Developers inspect exact command parameters, risk level (CRITICAL), and cost on the deck, then physically press ALLOW (GPIO 12) or KILL (GPIO 14).", 1, 13)
    add_bullet(tf3, "• Glanceable Pixel-Art Human State Engine:", "Retro 16-bit Ice Bear states (Idle Clock, 30s Countdown, Post-Kill Cleave) provide intuitive, zero-cognitive-overhead status awareness.", 1, 13)

    # Embed hardware screens trio on right half
    trio_path = os.path.join(out_dir, "assets", "hardware_screens_trio.png")
    if os.path.exists(trio_path):
        s3.shapes.add_picture(trio_path, Inches(7.8), Inches(2.2), width=Inches(4.9))

    # =========================================================================
    # SLIDE 4: System Architecture & Workflow (Agentic AI Track Evidence)
    # =========================================================================
    s4 = prs.slides[3]
    s4.shapes.title.text = "System Architecture & Workflow"
    c4 = s4.shapes[1]
    c4.left = Inches(0.8)
    c4.top = Inches(1.8)
    c4.width = Inches(6.2)
    c4.height = Inches(5.2)

    tf4 = c4.text_frame
    tf4.clear()

    add_bullet(tf4, "Four-Tier Distributed Architecture:", "", 0, 14, NAVY_DARK)
    add_bullet(tf4, "1. Agent CLI (Python 3.11):", "Autonomous terminal development tool communicating with local proxy endpoint; catches structured hardware error envelopes.", 1, 13)
    add_bullet(tf4, "2. Security Proxy (Node.js):", "Ingress vault managing policy denylists, $2.50 spend ceiling, 30s in-memory hold pool, and WebSocket multiplexer.", 1, 13)
    add_bullet(tf4, "3. ESP32 Hardware Deck (Firmware):", "ESP32 microcontroller (240MHz) with 240x320 ST7789 TFT, physical buttons, and hardware interlock gate pin (GPIO 27).", 1, 13)
    add_bullet(tf4, "4. Operator Dashboard (Web):", "Real-time audit interface streaming live WebSocket telemetry, hardware health, and historical decision traces.", 1, 13)
    add_bullet(tf4, "Execution Lifecycle & Failure Semantics:", "", 0, 14, BLUE_ACCENT)
    add_bullet(tf4, "• Safe Calls:", "Transparent passthrough to Gemini 2.0 Flash in <50 ms.", 1, 13)
    add_bullet(tf4, "• Policy Violation:", "Paused mid-flight; CHALLENGE emitted to hardware over /ws/deck.", 1, 13)
    add_bullet(tf4, "• ALLOW vs KILL:", "ALLOW forwards upstream (GPIO 27 HIGH); KILL terminates with HTTP 403 HARDWARE_DENIED (GPIO 27 LOW).", 1, 13)
    add_bullet(tf4, "• Fail-Closed Timeout:", "30s countdown expiry auto-aborts with HTTP 408 HARDWARE_TIMEOUT.", 1, 13)

    # Embed architecture diagram on right half
    arch_path = os.path.join(out_dir, "assets", "architecture_diagram.png")
    if os.path.exists(arch_path):
        s4.shapes.add_picture(arch_path, Inches(7.2), Inches(2.1), width=Inches(5.5))

    # =========================================================================
    # SLIDE 5: Technology Stack & Implementation (Edge AI Track Evidence)
    # =========================================================================
    s5 = prs.slides[4]
    s5.shapes.title.text = "Technology Stack & Implementation"
    c5 = s5.shapes[1]
    tf5 = c5.text_frame
    tf5.clear()

    add_bullet(tf5, "Edge Hardware & Firmware Subsystem (ESP32):", "", 0, 15, NAVY_DARK)
    add_bullet(tf5, "• Target SoC:", "Espressif ESP32-D0WD-V3 (Dual-Core 240MHz, 320 KB SRAM, 4 MB Flash, Arduino Framework, PlatformIO).", 1, 14)
    add_bullet(tf5, "• Display Engine:", "TPM408-2.8 240x320 SPI TFT (ST7789 driver) @ 40MHz SPI bus with scanline line-buffered DMA bursts (drawRGBBitmap <1.5 ms per digit slot).", 1, 14)
    add_bullet(tf5, "• Memory Footprint:", "RAM: 14.4% (47,124 / 327,680 bytes)  |  Flash: 75.6% (1,486,429 / 1,966,080 bytes on min_spiffs.csv). Over 470 KB headroom.", 1, 14)
    add_bullet(tf5, "• Output Interlock Gate:", "GPIO 27 active-high hardware relay/gate; automatically isolates (0V) whenever deck disconnects or times out.", 1, 14)
    add_bullet(tf5, "• Non-Blocking Clock & Particles:", "SNTP time synchronization (IST UTC+5:30) with differential digit rendering (220x72 px) and 18-flake collision-aware snow.", 1, 14)
    add_bullet(tf5, "Host & Cloud Software Stack:", "", 0, 15, BLUE_ACCENT)
    add_bullet(tf5, "• Security Proxy:", "Node.js v20, Express, ws WebSocket multiplexer, high-resolution timer hold pool, regex/AST command tokenizer.", 1, 14)
    add_bullet(tf5, "• Agent CLI Terminal:", "Python 3.11, Rich interactive UI formatting, OpenAI SDK client wrapper, tool schema execution boundary.", 1, 14)
    add_bullet(tf5, "• Operator Dashboard:", "HTML5/CSS3/ES6 JavaScript, real-time WebSocket telemetry listener, audit event ledger.", 1, 14)
    add_bullet(tf5, "• Upstream AI Model:", "Google Gemini 2.0 Flash via OpenAI-compatible chat.completions endpoint.", 1, 14)

    # =========================================================================
    # SLIDE 6: Key Features & Functionalities
    # =========================================================================
    s6 = prs.slides[5]
    s6.shapes.title.text = "Key Features & Functionalities"
    c6 = s6.shapes[1]
    # Split layout: text on left, image on right
    c6.left = Inches(0.8)
    c6.top = Inches(1.8)
    c6.width = Inches(7.5)
    c6.height = Inches(5.2)

    tf6 = c6.text_frame
    tf6.clear()

    add_bullet(tf6, "1. Zero-Exposure Credential Security:", "API keys remain locked in the proxy vault. Host laptops hold only dummy tokens; compromised local processes cannot leak upstream secrets.", 0, 13, BLUE_ACCENT)
    add_bullet(tf6, "2. Real-Time Policy Interception (<50ms):", "Evaluates agent tool-call payloads against destructive command denylists (rm -rf, DROP TABLE, mkfs, unauthorized chmod) in <1 ms.", 0, 13, RED_ALERT)
    add_bullet(tf6, "3. Physical Emergency Stop (KILL):", "Hardware tactile button triggers immediate HTTP 403 rejection, physically locks the GPIO 27 gate pin to 0V, and prevents accidental damage.", 0, 13, RED_ALERT)
    add_bullet(tf6, "4. Financial Velocity Braking:", "Tracks cumulative dollar spend against hard ceilings ($2.50). Trips an automatic freeze if agent token burn velocity spikes unexpectedly.", 0, 13, GREEN_SAFE)
    add_bullet(tf6, "5. Glanceable Pixel-Art Human State Engine:", "16-bit retro artwork renders distinct operational states: Idle (2x digital clock & snow), Challenge (Ice Bear battle stance & 30s countdown), and Kill (Axe Cleave with red 'EXECUTION BLOCKED' pill).", 0, 13, NAVY_DARK)
    add_bullet(tf6, "6. Tamper-Evident Audit Logging:", "Every interception, operator decision, timestamp, and raw payload is broadcast over WebSocket and archived for security review.", 0, 13, BLUE_ACCENT)

    # Embed kill screen screenshot on right
    kill_img = os.path.join(out_dir, "assets", "kill_screen.png")
    if os.path.exists(kill_img):
        s6.shapes.add_picture(kill_img, Inches(8.8), Inches(2.1), width=Inches(3.8))

    # =========================================================================
    # SLIDE 7: Live Demo / Working Prototype (Clean Placeholder per instructions)
    # =========================================================================
    s7 = prs.slides[6]
    s7.shapes.title.text = "Live Demo / Working Prototype"
    c7 = s7.shapes[1]
    tf7 = c7.text_frame
    tf7.clear()

    add_bullet(tf7, "Live Hardware Demonstration Setup:", "", 0, 16, BLUE_ACCENT)
    add_bullet(tf7, "• Bench Configuration:", "Physical ESP32 Hardware Deck (COM7 / Wi-Fi) + Local Agent CLI Terminal + Real-Time Operator Dashboard.", 1, 15)
    add_bullet(tf7, "Demonstration Scenarios Executed On-Stage:", "", 0, 16, NAVY_DARK)
    add_bullet(tf7, "1. Benign Operations (Transparent Passthrough):", "Agent reads project files and makes harmless code edits. Operations execute at wire speed with zero interruption.", 1, 14)
    add_bullet(tf7, "2. High-Stakes Interception ('rm -rf ./database'):", "Agent attempts destructive filesystem command. Request instantly freezes mid-flight; physical ESP32 deck lights up with red alert and 30s countdown.", 1, 14)
    add_bullet(tf7, "3. Operator Physical KILL Decision:", "Operator presses the physical KILL button (GPIO 14). Terminal aborts with HTTP 403; hardware deck displays pixel-art 'EXECUTION BLOCKED'; GPIO 27 gate isolated.", 1, 14)
    add_bullet(tf7, "4. Fail-Closed Proof:", "Disconnecting the hardware causes any subsequent risky actions to fail immediately (HTTP 503 HARDWARE_OFFLINE).", 1, 14)

    # =========================================================================
    # SLIDE 8: Future Scope
    # =========================================================================
    s8 = prs.slides[7]
    s8.shapes.title.text = "Future Scope"
    c8 = s8.shapes[1]
    tf8 = c8.text_frame
    tf8.clear()

    add_bullet(tf8, "1. Hardware Cryptographic Decision Signing (HMAC-SHA256):", "Integrate an ATECC608A secure element onto the deck to cryptographically sign every ALLOW/KILL decision with on-chip hardware private keys, preventing bus-level spoofing.", 0, 14, BLUE_ACCENT)
    add_bullet(tf8, "2. Stepped Rotary Encoder for Deep Payload Inspection:", "Add a rotary dial allowing developers to scroll through multi-line diffs, code patches, and SQL migrations directly on the 2.8\" display before authorizing.", 0, 14, NAVY_DARK)
    add_bullet(tf8, "3. Enterprise Multi-Signature Hardware Mesh:", "Deploy multi-deck consensus policies where high-blast-radius actions (production database migrations, AWS infrastructure teardowns) require physical dual-key confirmation.", 0, 14, BLUE_ACCENT)
    add_bullet(tf8, "4. On-Device TinyML Consequence Predictor:", "Deploy quantized Edge AI models directly onto the ESP32-S3 (TensorFlow Lite for Microcontrollers) to evaluate blast-radius and anomaly scores on-device completely offline.", 0, 14, GREEN_SAFE)
    add_bullet(tf8, "5. Native IDE & Agent Ecosystem Integrations:", "Provide drop-in plugins for Cursor, Claude Code, Windsurf, and VS Code, routing all background agent actions through the physical deck.", 0, 14, NAVY_DARK)

    # =========================================================================
    # SLIDE 9: Conclusion
    # =========================================================================
    s9 = prs.slides[8]
    s9.shapes.title.text = "Conclusion"
    c9 = s9.shapes[1]
    tf9 = c9.text_frame
    tf9.clear()

    add_bullet(tf9, "Closing the Autonomous Agent Safety Gap:", "", 0, 16, BLUE_ACCENT)
    add_bullet(tf9, "• The Human Remains in Physical Authority:", "KernelDeck proves that software agents can operate at high velocity without relinquishing developer control. By decoupling the security gate into dedicated hardware, safety is guaranteed in silicon.", 1, 14)
    add_bullet(tf9, "• Out-of-Band Security is Non-Negotiable:", "\"You cannot code-review your way out of a locked door.\" Effective oversight cannot share the same memory, processes, or operating system as the agent being supervised.", 1, 14)
    add_bullet(tf9, "• Frictionless Developer Experience:", "Safe requests pass transparently at wire speed (<50 ms); physical attention is demanded only when predetermined risk thresholds are violated.", 1, 14)
    add_bullet(tf9, "Summary of Achievements:", "", 0, 16, NAVY_DARK)
    add_bullet(tf9, "• Fully Operational Production Prototype:", "Integrated ESP32 firmware, Node.js proxy, Python Agent CLI, and live Web Dashboard fully tested and verified.", 1, 14)
    add_bullet(tf9, "• Rigorous Safety Integrity:", "Tested and proven against real destructive filesystem commands with 100% fail-closed reliability.", 1, 14)
    add_bullet(tf9, "KernelDeck: Making Autonomous AI Development Safer By Design.", "", 0, 16, GREEN_SAFE)

    # =========================================================================
    # SLIDE 10: Technical Evidence & Track Alignment (Rubric Compliance Table)
    # =========================================================================
    s10 = prs.slides[9]
    s10.shapes.title.text = "Technical Evidence & Track Alignment (Rubric Compliance)"
    table_shape = s10.shapes[1]
    tbl = table_shape.table

    # Format header row
    headers = ["Track", "Required Technical Evidence", "KernelDeck Implementation & Verification"]
    # Re-create table contents cleanly
    # Table dimensions: row count is currently 5, cols 2 -> adjust
    print(f"Slide 10 table rows: {len(tbl.rows)}, cols: {len(tbl.columns)}")
    
    # We will update table cell texts with technical evidence
    evidence_rows = [
        ("Agentic AI\n(Primary Track)",
         "Agent workflow, tools & integrations, task execution, and failure handling.",
         "• Workflow: Full OpenAI-compatible chat.completions tool-calling loop; requests held mid-flight.\n"
         "• Tools & Integrations: Shell command executor, filesystem boundary, proxy middleware, WebSocket multiplexer.\n"
         "• Task Execution: Preview-before-commit gating with 30s TTL hold pool and real-time dashboard audit trail.\n"
         "• Failure Handling: Strict fail-closed semantics (HARDWARE_DENIED 403, HARDWARE_OFFLINE 503, HARDWARE_TIMEOUT 408)."),
        ("Edge AI\n(Hardware Interlock)",
         "Target device, on-device latency, memory/resource usage, and offline capability.",
         "• Target Device: Espressif ESP32 Dev Module (240MHz Xtensa LX6, TPM408-2.8 ST7789 TFT display).\n"
         "• Latency: <1.5 ms display scanline DMA burst, 35ms button debounce, <50 ms WebSocket round-trip.\n"
         "• Resource Usage: RAM: 14.4% (47 KB / 328 KB) | Flash: 75.6% (1.48 MB / 1.96 MB on min_spiffs.csv).\n"
         "• Offline Capability: Physical relay gate (GPIO 27) maintains 0V fail-closed isolation whenever disconnected."),
        ("AI Safety &\nGovernance",
         "Consequence simulation, spend controls, and auditable human oversight.",
         "• Consequence Preview: Dangerous commands previewed on out-of-band screen before execution.\n"
         "• Spend Velocity Braking: Hard token cost ceiling ($2.50) automatically halts runaway agent loops.\n"
         "• Audit Trail: WebSocket event ledger records all tool calls, timestamps, and physical decisions."),
        ("Physical\nSecurity Enclave",
         "Out-of-band authority and zero-trust credential isolation.",
         "• Credential Vault: Real API keys locked in proxy vault; zero exposure to compromised local .env files.\n"
         "• Hardware Isolation: Interlock enforced in silicon; impossible for malware to fake physical button press.")
    ]

    # Check if table has 2 or 3 columns
    if len(tbl.columns) == 2:
        # Update rows for 2-column table
        for idx, (track, req, impl) in enumerate(evidence_rows, start=1):
            if idx < len(tbl.rows):
                tbl.cell(idx, 0).text = f"{track}\n\nRequired:\n{req}"
                tbl.cell(idx, 1).text = impl
                # Format cell fonts
                for p in tbl.cell(idx, 0).text_frame.paragraphs:
                    p.font.name = "Calibri"
                    p.font.size = Pt(11)
                    p.font.bold = True
                for p in tbl.cell(idx, 1).text_frame.paragraphs:
                    p.font.name = "Calibri"
                    p.font.size = Pt(11)
    
    # Save output presentations
    prs.save(out_pptx)
    prs.save(out_downloads)
    print(f"Saved final presentation to:\n  1. {out_pptx}\n  2. {out_downloads}")

if __name__ == "__main__":
    main()
