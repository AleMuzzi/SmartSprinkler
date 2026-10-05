Ecco l'elenco completo dei collegamenti da fare, organizzato per sezione. Le violazioni ERC sono 170 errori + 87 warning. I warning su library/footprint li puoi ignorare (sono problemi del generator). Concentrati sugli **errori**.

---

## 1. ALIMENTAZIONE - Connessioni base

### Net +12V
| Da | A |
|---|---|
| J1 pin 1 | +12V (power symbol) |
| U1 pin 1 (VIN) | +12V |
| C1 pin 1 | +12V |
| C2 pin 1 | +12V |
| K1-K4 pin 2 (coil) | +12V |
| D1-D4 pin 2 (anodo) | +12V |
| #PWR07 (+12V symbol) | +12V |

### Net GND
| Da | A |
|---|---|
| J1 pin 2 | GND |
| U1 pin 2 + pin 4 | GND |
| U2 pin 1 | GND |
| C1-C6 pin 2 | GND |
| Q1-Q4 pin 3 (E / Emitter) | GND |
| U4 pin 4 + pin 30 (GND) | GND |
| U3 pin 1 + pin 15 + pin 38 (GND) | GND |
| U3 pin 39 (EP) | GND |
| J2-J5 pin 3 | GND |
| J6 pin 4 | GND |
| J7 pin 3 | GND |
| J8-J11 pin 2 | GND |
| J12 pin 2 | GND |
| R2 pin 2 | GND |

### Net +5V_RAW
| Da | A |
|---|---|
| U1 pin 5 (OUT) | +5V_RAW |
| C3 pin 1 | +5V_RAW |
| C4 pin 1 | +5V_RAW |
| JP1 pin 1 | +5V_RAW |
| J2-J5 pin 1 | +5V_RAW |
| J6 pin 1 | +5V_RAW |
| J7 pin 1 | +5V_RAW |
| U4 pin 16 (VIN) | +5V_RAW |

### Net ESP_5V
| Da | A |
|---|---|
| JP1 pin 2 | ESP_5V |
| U2 pin 3 (IN) | ESP_5V |
| U3 pin 40 (5V) | ESP_5V |
| J12 pin 6 | ESP_5V |

### Net +3V3
| Da | A |
|---|---|
| U2 pin 2 (OUT) | +3V3 |
| C6 pin 1 | +3V3 |
| U3 pin 2 (3V3) | +3V3 |
| J12 pin 1 | +3V3 |
| #PWR05 (+3V3 symbol) | +3V3 |

---

## 2. ESP32-CAM (U3) - Pin da collegare

| Pin | Funzione | Collegamento |
|---|---|---|
| 1 | GND | GND |
| 2 | 3V3 | +3V3 |
| 3 | EN | Collegare a +3V3 (pull-up, attiva il chip) |
| 4 | SENSOR_VP/GPIO36 | SOIL_0 (o NC se non usato) |
| 5 | SENSOR_VN/GPIO39 | SOIL_1 (o NC) |
| 6 | GPIO34 | SOIL_2 (o NC) |
| 7 | GPIO35 | SOIL_3 (o NC) |
| 8 | GPIO32 | DHT_DATA |
| 9 | GPIO33 | NC (no connect) |
| 10 | GPIO25 | NC |
| 11 | GPIO26 | NC |
| 12 | GPIO27 | NC |
| 13 | GPIO14/ADC2_6 | NC |
| 14 | GPIO12 | PUMP_CTRL |
| 15 | GND | GND |
| 16 | GPIO13 | NC |
| 17 | SD2/GPIO9 | NC (flash pin, non usare) |
| 18 | SD3/GPIO10 | NC (flash pin) |
| 19 | CMD/GPIO11 | NC (flash pin) |
| 20 | CLK/GPIO6 | NC (flash pin) |
| 21 | SDO/GPIO7 | NC (flash pin) |
| 22 | SDI/GPIO8 | NC (flash pin) |
| 23 | GPIO15 | NC |
| 24 | GPIO2 | NC |
| 25 | GPIO0 | NC (o BOOT se serve programmare) |
| 26 | GPIO4 | NC |
| 27 | GPIO16 | NC |
| 28 | GPIO17 | NC |
| 29 | GPIO5 | NC |
| 30 | GPIO18 | NC |
| 31 | GPIO19 | NC |
| 32 | NC | NC |
| 33 | GPIO21/SDA | NC |
| 34 | U0RXD/GPIO3 | PROG_RXD |
| 35 | U0TXD/GPIO1 | PROG_TXD |
| 36 | GPIO22/SCL | NC |
| 37 | GPIO23 | NC |
| 38 | GND | GND |
| 39 | EP | GND |
| 40 | 5V | ESP_5V |

**Nota per i pin NC**: o li colleghi a un net reale, oppure nel schematico devi mettere un **no-connect** (X rosso) su ogni pin NC per silenziare l'ERC.

---

## 3. ARDUINO NANO (U4) - Pin da collegare

| Pin | Funzione | Collegamento |
|---|---|---|
| 1 | D1/TX | NANO_TX |
| 2 | D0/RX | NANO_RX |
| 3 | ~RESET | Collegare a +5V_RAW (pull-up) oppure NC con no-connect |
| 4 | GND | GND |
| 5 | D2 | DHT_DATA |
| 6 | D3~ | VALVE1 |
| 7 | D4 | VALVE2 |
| 8 | D5~ | VALVE3 |
| 9 | D6~ | NC |
| 10 | D7 | NC |
| 11 | D8 | NC |
| 12 | D9~ | NC |
| 13 | D10~ | NC |
| 14 | D11~ | NC |
| 15 | D12 | NC |
| 16 | VIN | +5V_RAW |
| 17 | 5V | NC (output, non collegare se JP1 è popolato) |
| 18 | ~RESET | NC |
| 19 | 3V3 | NC (output) |
| 20 | A7 | NC |
| 21 | A6 | NC |
| 22 | A5/SCL | NC |
| 23 | A4/SDA | NC |
| 24 | A3 | SOIL_3 |
| 25 | A2 | SOIL_2 |
| 26 | A1 | SOIL_1 |
| 27 | A0 | SOIL_0 |
| 28 | AREF | NC (o condensatore 100nF verso GND) |
| 29 | D13/SCK | NC |
| 30 | GND | GND |

---

## 4. DRIVER VALVOLE/PORTA (per ogni canale: Q1-D1-K1-J8, Q2-D2-K2-J9, Q3-D3-K3-J10, Q4-D4-K4-J11)

Ogni canale è identico. Ecco il collegamento per **un canale** (ripetere per tutti e 4):

| Componente | Pin | Collegamento |
|---|---|---|
| R3/R4/R5/R6 (1kΩ) pin 1 | Net segnale | VALVE1/VALVE2/VALVE3/PUMP_CTRL |
| R3/R4/R5/R6 (1kΩ) pin 2 | Base transistor | Q1_B/Q2_B/Q3_B/QP_B |
| Q1/Q2/Q3/Q4 (2N2222) B | Base | Da resistenza |
| Q1/Q2/Q3/Q4 (2N2222) C | Collector | Relay coil pin 1 + Diode K |
| Q1/Q2/Q3/Q4 (2N2222) E | Emitter | GND |
| D1/D2/D3/D4 (1N4007) K | Catodo | Collector transistor + Relay pin 1 |
| D1/D2/D3/D4 (1N4007) A | Anodo | +12V |
| K1/K2/K3/K4 Relay pin 1 | Coil | Collector transistor |
| K1/K2/K3/K4 Relay pin 2 | Coil | +12V |
| K1/K2/K3/K4 Relay pin 3 | COM (comune) | VALVE1_P/VALVE2_P/VALVE3_P/PUMP_P |
| K1/K2/K3/K4 Relay pin 12 | NO (normalmente aperto) | NC |
| K1/K2/K3/K4 Relay pin 14 | NC (normalmente chiuso) | NC |
| J8/J9/J10/J11 pin 1 | Valve/Pump + | VALVE1_P/VALVE2_P/VALVE3_P/PUMP_P |
| J8/J9/J10/J11 pin 2 | Valve/Pump - | GND |

---

## 5. CONNETTORI SENSORI

### J6 (DHT22) - 4 pin
| Pin | Collegamento |
|---|---|
| 1 | +5V_RAW |
| 2 | DHT_DATA |
| 3 | NC (no connect) |
| 4 | GND |

### J7 (Float switch) - 3 pin
| Pin | Collegamento |
|---|---|
| 1 | +5V_RAW |
| 2 | FLOAT_SIG |
| 3 | GND |

**Nota**: FLOAT_SIG non è collegato a nulla! Devi decidere a quale pin ESP32 o Nano collegarlo e aggiungere il net nel generator.

### J2-J5 (Soil sensors) - 3 pin ciascuno
| Pin | Collegamento |
|---|---|
| 1 | +5V_RAW |
| 2 | SOIL_0/SOIL_1/SOIL_2/SOIL_3 |
| 3 | GND |

---

## 6. DIVISORE DI TENSIONE (Level Shifter Nano TX → ESP32 RX)

| Componente | Pin | Collegamento |
|---|---|---|
| R1 (1kΩ) pin 1 | In | NANO_TX |
| R1 (1kΩ) pin 2 | Out | NANO_TX_3V3 |
| R2 (2kΩ) pin 1 | In | NANO_TX_3V3 |
| R2 (2kΩ) pin 2 | Out | GND |

**Nota**: NANO_TX_3V3 deve andare a U3 pin 34 (U0RXD/GPIO3) - il pin RX dell'ESP32.

---

## 7. J12 (Header Programmazione) - 6 pin

| Pin | Collegamento |
|---|---|
| 1 | +3V3 |
| 2 | GND |
| 3 | PROG_TXD |
| 4 | PROG_RXD |
| 5 | EN |
| 6 | ESP_5V |

PROG_TXD e PROG_RXD devono essere collegati rispettivamente ai pin TX e RX dell'ESP32 (pin 35 e 34).

---

## 8. POWER FLAGS

Power flags già presenti:
- **#PWR01** su +12V
- **#PWR02** su +5V
- **#PWR03** su +3V3

L'errore "power output to power output" su #PWR01/#PWR02/#PWR03 è perché i power symbol (+12V, +5V, +3V3) sono già "power output" e i PWR_FLAG lo sono anche loro. **Puoi eliminare i PWR_FLAG** se i power symbol sono sufficienti per ERC (dipende dalla versione di KiCad). In alternativa, collega il PWR_FLAG a un pin di OUTPUT reale (es. U1 pin 5 per +5V_RAW, U2 pin 2 per +3V3).

---

## Riepilogo azioni prioritarie

1. **Aggiungi wire per tutti i pin di potenza** (GND, +12V, +5V_RAW, +3V3, ESP_5V)
2. **Metti no-connect (X) su tutti i pin NC** che non userai
3. **Collega FLOAT_SIG** a un pin ESP32/Nano
4. **Aggiungi il pull-up su EN** dell'ESP32 (pin 3 a +3V3)
5. **Correggi i PWR_FLAG** o rimuovili