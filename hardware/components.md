Entrambi usano `(extends ...)` - ereditano i pin dal simbolo base. Hanno gli stessi pin dei parent. Ecco la lista completa:

---

## TUTTI I COMPONENTI CON I LORO PIN

---

### **J1** — `Conn_01x02_Pin` — Ingresso 12V
| Pin | Nome | Tipo |
|-----|------|------|
| 1 | Pin_1 | passivo |
| 2 | Pin_2 | passivo |

---

### **U1** — `LM2596T-5` — Buck converter 12V→5V (eredita da LM2596T-12)
| Pin | Nome | Tipo |
|-----|------|------|
| 1 | IN | ingresso potenza |
| 2 | GND | ingresso potenza |
| 3 | NC | passivo |
| 4 | GND | ingresso potenza |
| 5 | OUT | uscita potenza |

---

### **U2** — `AMS1117-3.3` — LDO 5V→3.3V (eredita da AP1117-15)
| Pin | Nome | Tipo |
|-----|------|------|
| 1 | GND/ADJ | ingresso potenza |
| 2 | Vout/Tab | uscita potenza |
| 3 | Vin | ingresso potenza |

---

### **U3** — `ESP32-CAM` — Modulo WiFi + Camera (40 pin)
| Pin | Nome | Tipo |
|-----|------|------|
| 1 | GND | ingresso potenza |
| 2 | 3V3 | ingresso potenza |
| 3 | EN | ingresso |
| 4 | SENSOR_VP/GPIO36 | ingresso |
| 5 | SENSOR_VN/GPIO39 | ingresso |
| 6 | GPIO34 | bidirezionale |
| 7 | GPIO35 | bidirezionale |
| 8 | GPIO32 | bidirezionale |
| 9 | GPIO33 | bidirezionale |
| 10 | GPIO25 | bidirezionale |
| 11 | GPIO26 | bidirezionale |
| 12 | GPIO27 | bidirezionale |
| 13 | GPIO14/ADC2_6 | bidirezionale |
| 14 | GPIO12 | bidirezionale |
| 15 | GND | ingresso potenza |
| 16 | GPIO13 | bidirezionale |
| 17 | SD2/GPIO9 | bidirezionale |
| 18 | SD3/GPIO10 | bidirezionale |
| 19 | CMD/GPIO11 | bidirezionale |
| 20 | CLK/GPIO6 | bidirezionale |
| 21 | SDO/GPIO7 | bidirezionale |
| 22 | SDI/GPIO8 | bidirezionale |
| 23 | GPIO15 | bidirezionale |
| 24 | GPIO2 | bidirezionale |
| 25 | GPIO0 | bidirezionale |
| 26 | GPIO4 | bidirezionale |
| 27 | GPIO16 | bidirezionale |
| 28 | GPIO17 | bidirezionale |
| 29 | GPIO5 | bidirezionale |
| 30 | GPIO18 | bidirezionale |
| 31 | GPIO19 | bidirezionale |
| 32 | NC | passivo |
| 33 | GPIO21/SDA | bidirezionale |
| 34 | U0RXD/GPIO3 | bidirezionale |
| 35 | U0TXD/GPIO1 | bidirezionale |
| 36 | GPIO22/SCL | bidirezionale |
| 37 | GPIO23 | bidirezionale |
| 38 | GND | ingresso potenza |
| 39 | EP (exposed pad) | passivo |
| 40 | 5V | ingresso potenza |

---

### **U4** — `Arduino_Nano` — MCU (30 pin)
| Pin | Nome | Tipo |
|-----|------|------|
| 1 | D1/TX | bidirezionale |
| 2 | D0/RX | bidirezionale |
| 3 | ~RESET | bidirezionale |
| 4 | GND | ingresso potenza |
| 5 | D2 | bidirezionale |
| 6 | D3~ | bidirezionale |
| 7 | D4 | bidirezionale |
| 8 | D5~ | bidirezionale |
| 9 | D6~ | bidirezionale |
| 10 | D7 | bidirezionale |
| 11 | D8 | bidirezionale |
| 12 | D9~ | bidirezionale |
| 13 | D10~ | bidirezionale |
| 14 | D11~ | bidirezionale |
| 15 | D12 | bidirezionale |
| 16 | VIN | ingresso potenza |
| 17 | 5V | uscita potenza |
| 18 | ~RESET | bidirezionale |
| 19 | 3V3 | uscita potenza |
| 20 | A7 | bidirezionale |
| 21 | A6 | bidirezionale |
| 22 | A5/SCL | bidirezionale |
| 23 | A4/SDA | bidirezionale |
| 24 | A3 | bidirezionale |
| 25 | A2 | bidirezionale |
| 26 | A1 | bidirezionale |
| 27 | A0 | bidirezionale |
| 28 | AREF | ingresso potenza |
| 29 | D13/SCK | bidirezionale |
| 30 | GND | ingresso potenza |

---

### **C1, C3** — `C_Polarized` — Condensatore polarizzato
| Pin | Nome | Tipo |
|-----|------|------|
| 1 | + | passivo |
| 2 | - | passivo |

---

### **C2, C4, C5, C6** — `C` — Condensatore
| Pin | Nome | Tipo |
|-----|------|------|
| 1 | ~ | passivo |
| 2 | ~ | passivo |

---

### **JP1** — `Jumper_2_Bridged` — Saldabile jumper
| Pin | Nome | Tipo |
|-----|------|------|
| 1 | A | passivo |
| 2 | B | passivo |

---

### **R1–R6** — `R` — Resistore
| Pin | Nome | Tipo |
|-----|------|------|
| 1 | ~ | passivo |
| 2 | ~ | passivo |

---

### **Q1–Q4** — `Q_NPN_CBE` — Transistor NPN 2N2222A
| Pin | Nome | Tipo |
|-----|------|------|
| B | Base | ingresso |
| C | Collettore | passivo |
| E | Emettore | passivo |

---

### **D1–D4** — `D` — Diodo 1N4007
| Pin | Nome | Tipo |
|-----|------|------|
| 1 | K (catodo) | passivo |
| 2 | A (anodo) | passivo |

---

### **K1–K4** — `Relay_SPDT` — Relè SPDT 12V
| Pin | Nome | Tipo |
|-----|------|------|
| A1 | Bobina + | passivo |
| A2 | Bobina - | passivo |
| 11 | COM (comune) | passivo |
| 12 | NO (normalmente aperto) | passivo |
| 14 | NC (normalmente chiuso) | passivo |

---

### **J2–J5** — `Conn_01x03_Pin` — Connettore sensore suolo
| Pin | Nome | Tipo |
|-----|------|------|
| 1 | Pin_1 | passivo |
| 2 | Pin_2 | passivo |
| 3 | Pin_3 | passivo |

---

### **J6** — `Conn_01x04_Pin` — Connettore DHT22
| Pin | Nome | Tipo |
|-----|------|------|
| 1 | Pin_1 | passivo |
| 2 | Pin_2 | passivo |
| 3 | Pin_3 | passivo |
| 4 | Pin_4 | passivo |

---

### **J7** — `Conn_01x03_Pin` — Connettore float switch
| Pin | Nome | Tipo |
|-----|------|------|
| 1 | Pin_1 | passivo |
| 2 | Pin_2 | passivo |
| 3 | Pin_3 | passivo |

---

### **J8–J11** — `Conn_01x02_Pin` — Connettore valvola/pompa
| Pin | Nome | Tipo |
|-----|------|------|
| 1 | Pin_1 | passivo |
| 2 | Pin_2 | passivo |

---

### **J12** — `Conn_01x06_Pin` — Header programmazione
| Pin | Nome | Tipo |
|-----|------|------|
| 1 | Pin_1 | passivo |
| 2 | Pin_2 | passivo |
| 3 | Pin_3 | passivo |
| 4 | Pin_4 | passivo |
| 5 | Pin_5 | passivo |
| 6 | Pin_6 | passivo |