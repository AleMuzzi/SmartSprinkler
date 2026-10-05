# SmartSprinkler PCB Layout Guide

## Overview
This guide provides step-by-step instructions for routing the SmartSprinkler controller board PCB.

## Board Specifications
- **Dimensions**: 100mm × 80mm (suggested)
- **Layers**: 2 (F.Cu, B.Cu)
- **Thickness**: 1.6mm FR4
- **Copper weight**: 1oz (35µm)

## Design Rules
- **Default trace width**: 0.25mm
- **Power traces**: 1.0mm (5V, 3V3, GND)
- **High current traces**: 2.0mm (12V input, pump/valve outputs)
- **Clearance**: 0.2mm (default), 0.3mm (power), 0.5mm (high current)
- **Via sizes**: 0.6mm/0.3mm (signal), 0.8mm/0.4mm (power)

## Placement Zones

```
+--------------------------------------------------+
| [POWER INPUT]     [BUCK CONVERTER]    [LDO]     |
| 12V terminal      LM2596              AMS1117   |
|                                                  |
| [ARDUINO NANO]                      [ESP32-CAM] |
| Socket headers                       Full board |
|                                                  |
| [SENSORS]                                       |
| Soil (x4), DHT22, Float                         |
|                                                  |
| [VALVE DRIVERS]                                 |
| 3× relay + 1× pump relay                        |
|                                                  |
| [OUTPUT CONNECTORS]                              |
| Valve terminals, Pump terminal, Prog header     |
+--------------------------------------------------+
```

## Routing Order

### Step 1: Power Rails (Critical)
1. Route **12V input** from J1 to buck converter (U1 pin 1) - use 2.0mm trace
2. Route **GND plane** - pour copper on B.Cu layer
3. Route **+5V_RAW** from buck output to:
   - Jumper JP1
   - Arduino Nano 5V pin
   - Sensor connectors (VCC pins)
4. Route **+3V3** from LDO output to ESP32-CAM 3V3 pin (1.0mm trace)
5. Route **ESP_5V** from jumper to:
   - LDO input (pin 3)
   - ESP32-CAM 5V pin (pin 40)

### Step 2: High Current Paths
1. **Pump relay** (K4): 12V coil + NO contact to J11
2. **Valve relays** (K1-K3): 12V coil + NO contacts to J8-J10
3. Use 2.0mm traces for all 12V outputs to valve/pump connectors

### Step 3: Signal Traces
1. **UART level divider** (Nano TX → ESP32 RX):
   - R1 (1k): Nano D1 → junction
   - R2 (2k): junction → GND
   - Junction → ESP32 GPIO14 (pin 13)
2. **Valve control signals**:
   - Nano D6 → R3 → Q1 base
   - Nano D7 → R4 → Q2 base
   - Nano D8 → R5 → Q3 base
3. **Pump control signal**:
   - ESP32 GPIO12 (pin 14) → R6 → Q4 base
4. **Sensor signals**:
   - Soil sensors: Nano A0-A3 (pins 27-24)
   - DHT22: Nano D2 (pin 5)
   - Float switch: Nano D5 (pin 8) or available GPIO

### Step 4: Relay Driver Circuits
For each relay (valve 1-3 + pump):
1. Base resistor (1k) → NPN base
2. Collector → relay coil pin 1 + diode anode
3. Emitter → GND
4. Diode cathode → 12V
5. Relay NO contact → output connector

## Component Placement Tips

### Power Section
- Place electrolytic capacitors close to buck converter
- Add decoupling capacitors near ESP32-CAM and Arduino Nano
- Keep 12V traces short and wide

### Relay Section
- Position relays near board edge for easy access to output terminals
- Add flyback diodes (1N4007) across each relay coil
- Ensure adequate clearance for relay package height

### ESP32-CAM
- Position camera connector facing board edge
- Allow space for FPC cable routing
- Keep antenna area clear of copper (if applicable)

### Arduino Nano
- Use 2×15 socket headers
- Position near sensors for short signal traces
- Allow USB connector access for programming

## Manufacturing Notes
- Generate Gerber files with extended X2 format
- Use 1.6mm FR4, 1oz copper
- Solder mask: Green (or preferred color)
- Silkscreen: White
- Surface finish: HASL (or ENIG for better reliability)

## Verification Checklist
- [ ] All nets connected (run DRC)
- [ ] Power traces sized correctly
- [ ] Decoupling capacitors placed
- [ ] Flyback diodes across relay coils
- [ ] Clearances maintained
- [ ] No copper under ESP32-CAM antenna
- [ ] Output connectors labeled on silkscreen
- [ ] Mounting holes added (3mm, 4 corners)
- [ ] Board outline on Edge.Cuts layer

## KiCad CLI Commands
```bash
# Update PCB from schematic
kicad-cli pcb import netlist SmartSprinkler.kicad_pcb netlist.ipc

# Run DRC
kicad-cli pcb drc SmartSprinkler.kicad_pcb --output drc_report.rpt

# Export Gerber
kicad-cli pcb export gerber SmartSprinkler.kicad_pcb --output-dir gerbers/

# Export drill file
kicad-cli pcb export drill SmartSprinkler.kicad_pcb --output-dir gerbers/
```
