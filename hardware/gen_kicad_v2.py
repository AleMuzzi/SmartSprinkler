#!/usr/bin/env python3
"""
SmartSprinkler KiCad schematic generator (v2).
Reads real symbol definitions from KiCad standard libraries and embeds them.
Uses standard KiCad symbols + custom ESP32-CAM and Arduino Nano.
"""

import json
import os
import re
import uuid
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
KICAD_SYMBOLS = "/Applications/KiCad/kicad.app/Contents/SharedSupport/symbols"
ROOT_UUID = str(uuid.UUID("7f1e5c3a-9b2d-4c47-8a1e-d6f0a2b3c4d5"))

def nu():
    return str(uuid.uuid4())

def fmt(v):
    return f"{v:g}"

# --------------------------------------------------------------------------
# Symbol extraction from KiCad libraries
# --------------------------------------------------------------------------

def extract_symbol(lib_file, sym_name):
    """Extract a complete symbol definition from a KiCad symbol library file.
    KiCad 10 libraries use tab indentation, so we search for \t(symbol "NAME" pattern."""
    path = os.path.join(KICAD_SYMBOLS, lib_file)
    return extract_symbol_from_file(path, sym_name)

def extract_symbol_block(lib_file, sym_name, prefix=""):
    """Extract symbol and prefix all inner symbol names."""
    sym = extract_symbol(lib_file, sym_name)
    # The top-level symbol starts with (symbol "NAME" ...)
    # Inner symbols start with (symbol "NAME_0_1" and (symbol "NAME_1_1"
    # We need to rename them to PREFIX:NAME_0_1 etc.

    # Replace the top-level symbol name
    sym = sym.replace(f'(symbol "{sym_name}"', f'(symbol "{prefix}{sym_name}"', 1)

    # Find and replace inner symbol names
    inner_pattern = r'\(symbol "' + re.escape(sym_name) + r'_'
    pos = 0
    while True:
        match = re.search(inner_pattern, sym[pos:])
        if not match:
            break
        start = pos + match.start()
        # Find the closing quote
        quote_start = sym.find('"', start + 9)
        old_name = sym[start+9:quote_start]
        new_name = f"{prefix}{old_name}"
        sym = sym[:start+9] + new_name + sym[quote_start:]
        pos = start + 9 + len(new_name)

    return sym

def extract_symbol_from_file(filepath, sym_name):
    """Extract a complete symbol definition from a file.
    Handles both tab-indented (KiCad 10) and space-indented formats."""
    with open(filepath, 'r') as f:
        content = f.read()

    # Try both tab-indented and non-indented patterns
    for prefix in ['\t(symbol "', '(symbol "']:
        pattern = prefix + sym_name + '"'
        start = content.find(pattern)
        if start != -1:
            # Verify this is a top-level symbol (not a sub-symbol like "R_0_1")
            # Check that the character before the match is not a digit or underscore
            if start > 0:
                prev_char = content[start-1]
                if prev_char.isdigit() or prev_char == '_':
                    continue  # Skip this match, look for the next one

            # Count parentheses to find matching close
            depth = 0
            pos = start
            while pos < len(content):
                if content[pos] == '(':
                    depth += 1
                elif content[pos] == ')':
                    depth -= 1
                    if depth == 0:
                        return content[start:pos+1]
                pos += 1
            break

    raise ValueError(f"Symbol '{sym_name}' not found in {filepath}")

def build_lib_symbols():
    """Build the lib_symbols block with all needed symbol definitions."""
    lib_symbols = {}

    # Standard KiCad symbols
    standard_symbols = {
        "Connector:Conn_01x02_Pin": ("Connector.kicad_sym", "Conn_01x02_Pin"),
        "Connector:Conn_01x03_Pin": ("Connector.kicad_sym", "Conn_01x03_Pin"),
        "Connector:Conn_01x04_Pin": ("Connector.kicad_sym", "Conn_01x04_Pin"),
        "Connector:Conn_01x06_Pin": ("Connector.kicad_sym", "Conn_01x06_Pin"),
        "Device:R": ("Device.kicad_sym", "R"),
        "Device:C": ("Device.kicad_sym", "C"),
        "Device:C_Polarized": ("Device.kicad_sym", "C_Polarized"),
        "Device:D": ("Device.kicad_sym", "D"),
        "Device:Q_NPN_CBE": ("Device.kicad_sym", "Q_NPN"),
        "Regulator_Switching:LM2596T-5": ("Regulator_Switching.kicad_sym", "LM2596T-5"),
        "Regulator_Linear:AMS1117-3.3": ("Regulator_Linear.kicad_sym", "AMS1117-3.3"),
        "Relay:Relay_SPDT": ("Relay.kicad_sym", "Relay_SPDT"),
        "Jumper:Jumper_2_Bridged": ("Jumper.kicad_sym", "Jumper_2_Bridged"),
        "power:+12V": ("power.kicad_sym", "+12V"),
        "power:+5V": ("power.kicad_sym", "+5V"),
        "power:+3V3": ("power.kicad_sym", "+3V3"),
        "power:GND": ("power.kicad_sym", "GND"),
        "power:PWR_FLAG": ("power.kicad_sym", "PWR_FLAG"),
    }

    # Custom symbols (from our local libraries)
    custom_symbols = {
        "smartsprinkler:ESP32-CAM": (os.path.join(HERE, "lib/esp32/ESP32-CAM.kicad_sym"), "ESP32-CAM"),
        "nano:Arduino_Nano": (os.path.join(HERE, "lib/nano/Arduino_Nano.kicad_sym"), "Arduino_Nano"),
    }

    # Extract all symbols
    for lib_id, (lib_file, sym_name) in {**standard_symbols, **custom_symbols}.items():
        try:
            if lib_file.startswith("/") or lib_file.startswith("."):
                # Custom library - full path
                filepath = lib_file
            else:
                # Standard KiCad library
                filepath = os.path.join(KICAD_SYMBOLS, lib_file)

            sym_def = extract_symbol_from_file(filepath, sym_name)

            # Only clean up custom symbols that are still in KiCad 7/8 format
            if (lib_file.startswith("/") or lib_file.startswith(".")) and '(id ' in sym_def:
                # Remove (id N) from properties - KiCad 7 format
                sym_def = re.sub(r' \(id \d+\)', '', sym_def)
                # Fix "hide" -> "(hide yes)" in property effects: ") hide)" -> ") (hide yes))"
                sym_def = re.sub(r'\) hide\)', ') (hide yes))', sym_def)
                # Remove ;; comments
                sym_def = re.sub(r'\n\s*;;[^\n]*', '', sym_def)

            # Normalize indentation if needed (for legacy symbol files)
            has_tabs = '\t' in sym_def
            has_space_indent = any(line.startswith('    ') for line in sym_def.split('\n')[:10])
            if has_space_indent and not has_tabs:
                lines = sym_def.split('\n')
                normalized = []
                for line in lines:
                    stripped = line.lstrip()
                    if stripped:
                        leading = len(line) - len(stripped)
                        if leading > 0:
                            tabs = '\t' * (leading // 4)
                            line = tabs + stripped
                    normalized.append(line)
                sym_def = '\n'.join(normalized)

            # Replace the top-level symbol name with full lib_id
            sym_def = sym_def.replace(f'(symbol "{sym_name}"', f'(symbol "{lib_id}"', 1)

            # Rename inner sub-symbols to use the suffix (part after ':') instead of original name
            # e.g., Q_NPN_0_1 -> Q_NPN_CBE_0_1 when parent is Device:Q_NPN_CBE
            # KiCad requires inner names to match: {parent_suffix}_{unit}_{variant}
            suffix = lib_id.split(":")[-1]  # "Device:Q_NPN_CBE" -> "Q_NPN_CBE"
            if suffix != sym_name:
                # Parent was renamed, update inner symbols too
                inner_pattern = re.compile(r'\(symbol "' + re.escape(sym_name) + r'_(\d+_\d+)"')
                sym_def = inner_pattern.sub(
                    lambda m: f'(symbol "{suffix}_{m.group(1)}"',
                    sym_def
                )

            lib_symbols[lib_id] = sym_def

        except Exception as e:
            print(f"WARNING: Failed to extract {lib_id}: {e}")

    return lib_symbols

# --------------------------------------------------------------------------
# Component instances with connectivity
# --------------------------------------------------------------------------

COMPONENTS = [
    # Power input
    {"ref": "J1", "lib": "Connector", "sym": "Conn_01x02_Pin", "val": "12V_IN",
     "fp": "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
     "x": 40.64, "y": 190.5, "nets": {"1": "+12V", "2": "GND"}},

    # Power flags
    {"ref": "#PWR01", "lib": "power", "sym": "PWR_FLAG", "val": "PWR_FLAG",
     "x": 25.4, "y": 170.18, "nets": {"1": "+12V"}},
    {"ref": "#PWR02", "lib": "power", "sym": "PWR_FLAG", "val": "PWR_FLAG",
     "x": 81.28, "y": 127, "nets": {"1": "+5V"}},
    {"ref": "#PWR03", "lib": "power", "sym": "PWR_FLAG", "val": "PWR_FLAG",
     "x": 226.06, "y": 127, "nets": {"1": "+3V3"}},

    # Buck converter
    {"ref": "U1", "lib": "Regulator_Switching", "sym": "LM2596T-5", "val": "LM2596T-5",
     "fp": "Package_TO_SOT_THT:TO-220-5_Vertical",
     "x": 99.06, "y": 190.5, "nets": {"1": "+12V", "2": "GND", "3": "NC", "4": "GND", "5": "+5V_RAW"}},

    # Capacitors
    {"ref": "C1", "lib": "Device", "sym": "C_Polarized", "val": "470uF",
     "fp": "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm",
     "x": 99.06, "y": 215.9, "nets": {"1": "+12V", "2": "GND"}},
    {"ref": "C2", "lib": "Device", "sym": "C", "val": "100nF",
     "fp": "Capacitor_THT:C_Disc_D4.7mm_W2.5mm_P5.00mm",
     "x": 99.06, "y": 165.1, "nets": {"1": "+12V", "2": "GND"}},
    {"ref": "C3", "lib": "Device", "sym": "C_Polarized", "val": "470uF",
     "fp": "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm",
     "x": 149.86, "y": 215.9, "nets": {"1": "+5V_RAW", "2": "GND"}},
    {"ref": "C4", "lib": "Device", "sym": "C", "val": "100nF",
     "fp": "Capacitor_THT:C_Disc_D4.7mm_W2.5mm_P5.00mm",
     "x": 149.86, "y": 165.1, "nets": {"1": "+5V_RAW", "2": "GND"}},

    # Jumper 5V bypass
    {"ref": "JP1", "lib": "Jumper", "sym": "Jumper_2_Bridged", "val": "Jumper",
     "fp": "Jumper:SolderJumper-2_P1.3mm_Bridged_Pad1.0x1.5mm",
     "x": 177.8, "y": 190.5, "nets": {"1": "+5V_RAW", "2": "ESP_5V"}},

    # LDO 3.3V
    {"ref": "U2", "lib": "Regulator_Linear", "sym": "AMS1117-3.3", "val": "AMS1117-3.3",
     "fp": "Package_TO_SOT_SMD:SOT-223-3_TabPin2",
     "x": 203.2, "y": 190.5, "nets": {"1": "GND", "2": "+3V3", "3": "ESP_5V"}},
    {"ref": "C5", "lib": "Device", "sym": "C", "val": "10uF",
     "fp": "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm",
     "x": 203.2, "y": 165.1, "nets": {"1": "ESP_5V", "2": "GND"}},
    {"ref": "C6", "lib": "Device", "sym": "C", "val": "10uF",
     "fp": "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm",
     "x": 203.2, "y": 215.9, "nets": {"1": "+3V3", "2": "GND"}},

    # Power labels
    {"ref": "#PWR04", "lib": "power", "sym": "+5V", "val": "+5V",
     "x": 119.38, "y": 248.92, "nets": {"1": "+5V_RAW"}},
    {"ref": "#PWR05", "lib": "power", "sym": "+3V3", "val": "+3V3",
     "x": 360.68, "y": 129.54, "nets": {"1": "+3V3"}},
    {"ref": "#PWR06", "lib": "power", "sym": "GND", "val": "GND",
     "x": 139.7, "y": 289.56, "nets": {"1": "GND"}},
    {"ref": "#PWR07", "lib": "power", "sym": "+12V", "val": "+12V",
     "x": 391.16, "y": 60.96, "nets": {"1": "+12V"}},

    # ESP32-CAM (custom)
    {"ref": "U3", "lib": "smartsprinkler", "sym": "ESP32-CAM", "val": "ESP32-CAM",
     "fp": "smartsprinkler:ESP32-CAM",
     "x": 350.52, "y": 170.18, "nets": {
         "1": "GND", "2": "+3V3", "3": "EN", "40": "ESP_5V", "13": "NANO_TX_3V3",
         "14": "PUMP_CTRL", "34": "PROG_RXD", "35": "PROG_TXD"}},

    # Arduino Nano (custom)
    {"ref": "U4", "lib": "nano", "sym": "Arduino_Nano", "val": "Arduino_Nano",
     "fp": "smartsprinkler:Arduino_Nano",
     "x": 180.34, "y": 170.18, "nets": {
         "5": "DHT_DATA", "6": "VALVE1", "7": "VALVE2", "8": "VALVE3",
         "10": "+5V_RAW", "4": "GND", "1": "NANO_TX", "2": "NANO_RX",
         "24": "SOIL_3", "25": "SOIL_2", "26": "SOIL_1", "27": "SOIL_0"}},

    # Level divider (Nano TX -> ESP32 RX)
    {"ref": "R1", "lib": "Device", "sym": "R", "val": "1k",
     "fp": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
     "x": 251.46, "y": 205.74, "nets": {"1": "NANO_TX", "2": "NANO_TX_3V3"}},
    {"ref": "R2", "lib": "Device", "sym": "R", "val": "2k",
     "fp": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
     "x": 251.46, "y": 236.22, "nets": {"1": "NANO_TX_3V3", "2": "GND"}},

    # Soil sensors
    {"ref": "J2", "lib": "Connector", "sym": "Conn_01x03_Pin", "val": "SOIL_0",
     "fp": "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
     "x": 45.72, "y": 271.78, "nets": {"1": "+5V_RAW", "2": "SOIL_0", "3": "GND"}},
    {"ref": "J3", "lib": "Connector", "sym": "Conn_01x03_Pin", "val": "SOIL_1",
     "fp": "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
     "x": 101.6, "y": 271.78, "nets": {"1": "+5V_RAW", "2": "SOIL_1", "3": "GND"}},
    {"ref": "J4", "lib": "Connector", "sym": "Conn_01x03_Pin", "val": "SOIL_2",
     "fp": "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
     "x": 157.48, "y": 271.78, "nets": {"1": "+5V_RAW", "2": "SOIL_2", "3": "GND"}},
    {"ref": "J5", "lib": "Connector", "sym": "Conn_01x03_Pin", "val": "SOIL_3",
     "fp": "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
     "x": 213.36, "y": 271.78, "nets": {"1": "+5V_RAW", "2": "SOIL_3", "3": "GND"}},

    # DHT22
    {"ref": "J6", "lib": "Connector", "sym": "Conn_01x04_Pin", "val": "DHT22",
     "fp": "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
     "x": 45.72, "y": 231.14, "nets": {"1": "+5V_RAW", "2": "DHT_DATA", "3": "NC", "4": "GND"}},

    # Float switch
    {"ref": "J7", "lib": "Connector", "sym": "Conn_01x03_Pin", "val": "FLOAT",
     "fp": "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
     "x": 241.3, "y": 231.14, "nets": {"1": "+5V_RAW", "2": "FLOAT_SIG", "3": "GND"}},

    # Valve relay drivers (3x)
    {"ref": "R3", "lib": "Device", "sym": "R", "val": "1k",
     "fp": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
     "x": 302.26, "y": 101.6, "nets": {"1": "VALVE1", "2": "Q1_B"}},
    {"ref": "Q1", "lib": "Device", "sym": "Q_NPN_CBE", "val": "2N2222A",
     "fp": "Package_TO_SOT_THT:TO-92_Inline",
     "x": 332.74, "y": 101.6, "nets": {"1": "Q1_B", "2": "Q1_C", "3": "GND"}},
    {"ref": "D1", "lib": "Device", "sym": "D", "val": "1N4007",
     "fp": "Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal",
     "x": 363.22, "y": 139.7, "nets": {"1": "+12V", "2": "Q1_C"}},
    {"ref": "K1", "lib": "Relay", "sym": "Relay_SPDT", "val": "Relay_12V",
     "fp": "Relay_THT:Relay_SPDT_Hongfa_HF32F-G_5V",
     "x": 393.7, "y": 101.6, "nets": {"1": "Q1_C", "2": "+12V", "3": "VALVE1_P", "4": "+12V", "5": "NC"}},
    {"ref": "J8", "lib": "Connector", "sym": "Conn_01x02_Pin", "val": "VALVE1",
     "fp": "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
     "x": 444.5, "y": 101.6, "nets": {"1": "VALVE1_P", "2": "GND"}},

    {"ref": "R4", "lib": "Device", "sym": "R", "val": "1k",
     "fp": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
     "x": 302.26, "y": 41.91, "nets": {"1": "VALVE2", "2": "Q2_B"}},
    {"ref": "Q2", "lib": "Device", "sym": "Q_NPN_CBE", "val": "2N2222A",
     "fp": "Package_TO_SOT_THT:TO-92_Inline",
     "x": 332.74, "y": 41.91, "nets": {"1": "Q2_B", "2": "Q2_C", "3": "GND"}},
    {"ref": "D2", "lib": "Device", "sym": "D", "val": "1N4007",
     "fp": "Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal",
     "x": 363.22, "y": 80.01, "nets": {"1": "+12V", "2": "Q2_C"}},
    {"ref": "K2", "lib": "Relay", "sym": "Relay_SPDT", "val": "Relay_12V",
     "fp": "Relay_THT:Relay_SPDT_Hongfa_HF32F-G_5V",
     "x": 393.7, "y": 41.91, "nets": {"1": "Q2_C", "2": "+12V", "3": "VALVE2_P", "4": "+12V", "5": "NC"}},
    {"ref": "J9", "lib": "Connector", "sym": "Conn_01x02_Pin", "val": "VALVE2",
     "fp": "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
     "x": 444.5, "y": 41.91, "nets": {"1": "VALVE2_P", "2": "GND"}},

    {"ref": "R5", "lib": "Device", "sym": "R", "val": "1k",
     "fp": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
     "x": 302.26, "y": -17.78, "nets": {"1": "VALVE3", "2": "Q3_B"}},
    {"ref": "Q3", "lib": "Device", "sym": "Q_NPN_CBE", "val": "2N2222A",
     "fp": "Package_TO_SOT_THT:TO-92_Inline",
     "x": 332.74, "y": -17.78, "nets": {"1": "Q3_B", "2": "Q3_C", "3": "GND"}},
    {"ref": "D3", "lib": "Device", "sym": "D", "val": "1N4007",
     "fp": "Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal",
     "x": 363.22, "y": 20.32, "nets": {"1": "+12V", "2": "Q3_C"}},
    {"ref": "K3", "lib": "Relay", "sym": "Relay_SPDT", "val": "Relay_12V",
     "fp": "Relay_THT:Relay_SPDT_Hongfa_HF32F-G_5V",
     "x": 393.7, "y": -17.78, "nets": {"1": "Q3_C", "2": "+12V", "3": "VALVE3_P", "4": "+12V", "5": "NC"}},
    {"ref": "J10", "lib": "Connector", "sym": "Conn_01x02_Pin", "val": "VALVE3",
     "fp": "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
     "x": 444.5, "y": -17.78, "nets": {"1": "VALVE3_P", "2": "GND"}},

    # Pump relay
    {"ref": "R6", "lib": "Device", "sym": "R", "val": "1k",
     "fp": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
     "x": 302.26, "y": 161.93, "nets": {"1": "PUMP_CTRL", "2": "QP_B"}},
    {"ref": "Q4", "lib": "Device", "sym": "Q_NPN_CBE", "val": "2N2222A",
     "fp": "Package_TO_SOT_THT:TO-92_Inline",
     "x": 332.74, "y": 161.93, "nets": {"1": "QP_B", "2": "QP_C", "3": "GND"}},
    {"ref": "D4", "lib": "Device", "sym": "D", "val": "1N4007",
     "fp": "Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal",
     "x": 363.22, "y": 200.03, "nets": {"1": "+12V", "2": "QP_C"}},
    {"ref": "K4", "lib": "Relay", "sym": "Relay_SPDT", "val": "Relay_12V",
     "fp": "Relay_THT:Relay_SPDT_Hongfa_HF32F-G_5V",
     "x": 393.7, "y": 161.93, "nets": {"1": "QP_C", "2": "+12V", "3": "PUMP_P", "4": "+12V", "5": "NC"}},
    {"ref": "J11", "lib": "Connector", "sym": "Conn_01x02_Pin", "val": "PUMP",
     "fp": "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
     "x": 444.5, "y": 161.93, "nets": {"1": "PUMP_P", "2": "GND"}},

    # Programming header
    {"ref": "J12", "lib": "Connector", "sym": "Conn_01x06_Pin", "val": "PROG",
     "fp": "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical",
     "x": 441.96, "y": 243.84, "nets": {"1": "+3V3", "2": "GND", "3": "PROG_TXD", "4": "PROG_RXD", "5": "EN", "6": "ESP_5V"}},
]

# --------------------------------------------------------------------------
# Build schematic
# --------------------------------------------------------------------------

def build_symbol_instance(c):
    """Build a symbol instance (component placement in schematic)"""
    lib_id = f"{c['lib']}:{c['sym']}"
    lines = [
        "\t(symbol",
        f'\t\t(lib_id "{lib_id}")',
        f"\t\t(at {fmt(c['x'])} {fmt(c['y'])} 0)",
        "\t\t(unit 1)",
        "\t\t(exclude_from_sim no)",
        "\t\t(in_bom yes)",
        "\t\t(on_board yes)",
        "\t\t(dnp no)",
        f'\t\t(uuid "{nu()}")',
        f'\t\t(property "Reference" "{c["ref"]}" (at {fmt(c["x"])} {fmt(c["y"] + 13.5)} 0)',
        '\t\t\t(effects (font (size 1.27 1.27))))',
        f'\t\t(property "Value" "{c["val"]}" (at {fmt(c["x"])} {fmt(c["y"] - 13.5)} 0)',
        '\t\t\t(effects (font (size 1.27 1.27))))',
    ]
    if "fp" in c:
        lines.append(f'\t\t(property "Footprint" "{c["fp"]}" (at {fmt(c["x"])} {fmt(c["y"])} 0)')
        lines.append('\t\t\t(effects (font (size 1.27 1.27)) (hide yes)))')
    lines.append(f'\t\t(property "Datasheet" "" (at {fmt(c["x"])} {fmt(c["y"])} 0)')
    lines.append('\t\t\t(effects (font (size 1.27 1.27)) (hide yes)))')
    for pin in c["nets"]:
        lines.append(f'\t\t(pin "{pin}" (uuid "{nu()}"))')
    lines.append("\t\t(instances")
    lines.append(f'\t\t\t(project "SmartSprinkler"')
    lines.append(f'\t\t\t\t(path "/{ROOT_UUID}"')
    lines.append(f'\t\t\t\t\t(reference "{c["ref"]}")')
    lines.append("\t\t\t\t\t(unit 1)")
    lines.append("\t\t\t\t)")
    lines.append("\t\t\t)")
    lines.append("\t\t)")
    lines.append("\t)")
    return "\n".join(lines)

def build_wire_and_label(c):
    """Build wire stubs + labels for each pin (approximate positioning for ERC)"""
    parts = []
    for pin, net in c["nets"].items():
        if net in ("NC", "OPEN"):
            parts.append(f'\t(no_connect (at {fmt(c["x"])} {fmt(c["y"])}) (uuid "{nu()}"))')
        else:
            offset = int(pin) * 2.54 if pin.isdigit() else 5.08
            tx, ty = c["x"] + 5.08, c["y"] + offset
            parts.append(f'\t(wire (pts (xy {fmt(c["x"])} {fmt(c["y"])}) (xy {fmt(tx)} {fmt(ty)}))')
            parts.append(f'\t\t(stroke (width 0) (type solid)) (uuid "{nu()}"))')
            parts.append(f'\t(label "{net}" (at {fmt(tx)} {fmt(ty)} 0)')
            parts.append(f'\t\t(effects (font (size 1.27 1.27)) (justify left)) (uuid "{nu()}"))')
    return "\n".join(parts)

def build_schematic(lib_symbols):
    lines = [
        "(kicad_sch",
        "\t(version 20250114)",
        '\t(generator "eeschema")',
        '\t(generator_version "9.0")',
        f'\t(uuid "{ROOT_UUID}")',
        '\t(paper "A3")',
        '\t(title_block',
        '\t\t(title "SmartSprinkler Controller Board")',
        '\t\t(rev "1.0")',
        '\t\t(date "2026-09-08")',
        '\t\t(company "SmartSprinkler")',
        "\t)",
    ]

    # Embed lib_symbols
    lines.append("\t(lib_symbols")
    for lib_id, sym_def in sorted(lib_symbols.items()):
        # Preserve original tab indentation, just add one extra tab for nesting under lib_symbols
        for line in sym_def.split('\n'):
            if line.strip():
                lines.append(f"\t{line}")
            else:
                lines.append("")
    lines.append("\t)")

    # Add symbol instances
    for c in COMPONENTS:
        lines.append(build_symbol_instance(c))

    # Add wires + labels
    for c in COMPONENTS:
        lines.append(build_wire_and_label(c))

    lines.append('\t(sheet_instances (path "/" (page "1")))')
    lines.append(")")
    return "\n".join(lines)

def build_pro():
    return json.dumps({
        "board": {"3dviewports": [], "design_settings": {
            "defaults": {"apply_defaults_to_fp_fields": False, "apply_defaults_to_new_footprints": False},
            "drc_exclusions": [], "rules": {
                "min_clearance": 0.2, "min_copper_edge_clearance": 0.25, "min_hole_clearance": 0.25,
                "min_microvia_diameter": 0.2, "min_microvia_drill": 0.1, "min_silk_clearance": 0.0,
                "min_track_width": 0.2, "min_via_annular_width": 0.2, "min_via_diameter": 0.6,
                "min_via_drill": 0.3, "use_height_for_length_calcs": True,
            },
            "track_widths": [0.25, 0.5, 1.0, 2.0], "via_sizes": [], "diff_pair_dimensions": [],
        }, "layer_presets": [], "viewports": []},
        "boards": [], "cvpcb": {"equivalence_files": []},
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": "SmartSprinkler.kicad_pro", "version": 3},
        "net_settings": {"classes": [{
            "name": "Default", "schematic_only": False, "track_width": 0.25,
            "clearance": 0.2, "via_diameter": 0.6, "via_drill": 0.3,
            "via_smd_diameter": 0, "via_smd_drill": 0, "diff_pair_gap": 0, "diff_pair_via_gap": 0,
        }], "meta": {"version": 3}},
        "pcbnew": {"last_paths": {}, "page_layout_descr_file": ""},
        "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
        "sheets": [[ROOT_UUID, ROOT_UUID, "Root", "SmartSprinkler.kicad_sch"]],
        "text_variables": {},
    }, indent=2)

def main():
    # Build lib_symbols from KiCad libraries
    print("Reading symbol definitions from KiCad libraries...")
    lib_symbols = build_lib_symbols()
    print(f"Extracted {len(lib_symbols)} symbols:")
    for lib_id in sorted(lib_symbols.keys()):
        print(f"  - {lib_id}")

    # Generate schematic
    sch = os.path.join(HERE, "SmartSprinkler.kicad_sch")
    if os.path.exists(sch):
        shutil.copy2(sch, sch + ".bak")

    with open(sch, "w") as f:
        f.write(build_schematic(lib_symbols))
    with open(os.path.join(HERE, "SmartSprinkler.kicad_pro"), "w") as f:
        f.write(build_pro())

    print("\nGenerated SmartSprinkler.kicad_sch and SmartSprinkler.kicad_pro")

if __name__ == "__main__":
    main()
