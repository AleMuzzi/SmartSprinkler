#!/usr/bin/env python3
"""
Generate SmartSprinkler KiCad schematic with embedded symbols.
Uses standard KiCad symbols embedded directly in the schematic.
"""

import json
import os
import uuid
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT_UUID = str(uuid.UUID("7f1e5c3a-9b2d-4c47-8a1e-d6f0a2b3c4d5"))

def nu():
    return str(uuid.uuid4())

def fmt(v):
    return f"{v:g}"

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
     "fp": "Module:Arduino_Nano",
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
     "x": 363.22, "y": 139.7, "nets": {"1": "Q1_C", "2": "+12V"}},
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
     "x": 363.22, "y": 80.01, "nets": {"1": "Q2_C", "2": "+12V"}},
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
     "x": 363.22, "y": 20.32, "nets": {"1": "Q3_C", "2": "+12V"}},
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
     "x": 363.22, "y": 200.03, "nets": {"1": "QP_C", "2": "+12V"}},
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

def build_lib_symbols():
    """Return minimal lib_symbols block - symbols must exist in KiCad standard libs or local .kicad_sym files"""
    return "  (lib_symbols)"

def build_symbol_instance(c):
    """Build a symbol instance (component placement in schematic)"""
    lib_id = f"{c['lib']}:{c['sym']}"
    lines = [
        "  (symbol",
        f'    (lib_id "{lib_id}")',
        f"    (at {fmt(c['x'])} {fmt(c['y'])} 0)",
        "    (unit 1)",
        "    (exclude_from_sim no)",
        "    (in_bom yes)",
        "    (on_board yes)",
        "    (dnp no)",
        f'    (uuid "{nu()}")',
        f'    (property "Reference" "{c["ref"]}" (at {fmt(c["x"])} {fmt(c["y"] + 13.5)} 0)',
        '      (effects (font (size 1.27 1.27))))',
        f'    (property "Value" "{c["val"]}" (at {fmt(c["x"])} {fmt(c["y"] - 13.5)} 0)',
        '      (effects (font (size 1.27 1.27))))',
    ]
    if "fp" in c:
        lines.append(f'    (property "Footprint" "{c["fp"]}" (at {fmt(c["x"])} {fmt(c["y"])} 0)')
        lines.append('      (effects (font (size 1.27 1.27)) (hide yes)))')
    lines.append(f'    (property "Datasheet" "" (at {fmt(c["x"])} {fmt(c["y"])} 0)')
    lines.append('      (effects (font (size 1.27 1.27)) (hide yes)))')
    for pin in c["nets"]:
        lines.append(f'    (pin "{pin}" (uuid "{nu()}"))')
    lines.append("    (instances")
    lines.append(f'      (project "SmartSprinkler"')
    lines.append(f'        (path "/{ROOT_UUID}"')
    lines.append(f'          (reference "{c["ref"]}")')
    lines.append("          (unit 1)")
    lines.append("        )")
    lines.append("      )")
    lines.append("    )")
    lines.append("  )")
    return "\n".join(lines)

def build_wire_and_label(c):
    """Build wire stubs + labels for each pin (approximate positioning for ERC)"""
    parts = []
    for pin, net in c["nets"].items():
        if net in ("NC", "OPEN"):
            # No-connect marker
            parts.append(f'  (no_connect (at {fmt(c["x"])} {fmt(c["y"])}) (uuid "{nu()}"))')
        else:
            # Wire + label
            offset = int(pin) * 2.54 if pin.isdigit() else 5.08
            tx, ty = c["x"] + 5.08, c["y"] + offset
            parts.append(f'  (wire (pts (xy {fmt(c["x"])} {fmt(c["y"])}) (xy {fmt(tx)} {fmt(ty)}))')
            parts.append(f'    (stroke (width 0) (type solid)) (uuid "{nu()}"))')
            parts.append(f'  (label "{net}" (at {fmt(tx)} {fmt(ty)} 0)')
            parts.append(f'    (effects (font (size 1.27 1.27)) (justify left)) (uuid "{nu()}"))')
    return "\n".join(parts)

def build_schematic():
    lines = [
        "(kicad_sch",
        "  (version 20231120)",
        '  (generator "eeschema")',
        '  (generator_version "8.0")',
        f'  (uuid "{ROOT_UUID}")',
        '  (paper "A3")',
        '  (title_block',
        '    (title "SmartSprinkler Controller Board")',
        '    (rev "1.0")',
        '    (date "2026-09-08")',
        '    (company "SmartSprinkler")',
        "  )",
        build_lib_symbols(),
    ]
    for c in COMPONENTS:
        lines.append(build_symbol_instance(c))
    for c in COMPONENTS:
        lines.append(build_wire_and_label(c))
    lines.append('  (sheet_instances (path "/" (page "1")))')
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
    sch = os.path.join(HERE, "SmartSprinkler.kicad_sch")
    if os.path.exists(sch):
        shutil.copy2(sch, sch + ".bak")
    
    with open(sch, "w") as f:
        f.write(build_schematic())
    with open(os.path.join(HERE, "SmartSprinkler.kicad_pro"), "w") as f:
        f.write(build_pro())
    
    print("Generated SmartSprinkler.kicad_sch and SmartSprinkler.kicad_pro")

if __name__ == "__main__":
    main()
