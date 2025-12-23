# 🧬 Referencia Biológica - LifeSimulator

## Orden Evolutivo Real

```
1. ARN (primero) - El "mundo de ARN"
   └── Puede almacenar información Y catalizar reacciones
   
2. ADN (después) - Más estable
   └── Solo almacena información
   └── Requiere ARN para funcionar
   
3. Proteínas - Las "máquinas"
   └── ARN las codifica
   └── Hacen todo el trabajo
```

---

## Escalas Reales

| Estructura | Cantidad Real | Para el Juego |
|------------|--------------|---------------|
| 1 Nucleótido | 15-20 átomos | 15-20 átomos |
| 1 Codón (3 nucleótidos) | ~50 átomos | ~50 átomos |
| Gen mínimo funcional | ~300 nucleótidos | 10-50 nucleótidos |
| ADN Humano | 6 mil millones pares | Automatización |

### Automatización (Tu idea)

El jugador debe crear "fábricas moleculares" que copien automáticamente:
- **Ribosoma** = Lee ARN → produce proteínas
- **Polimerasa** = Copia ADN/ARN
- **ATP Sintasa** = Genera energía

---

## Moléculas para Poderes/Stats

### 🔥 Resistencia al Calor
```
Moléculas necesarias:
├── Proteínas con S (azufre) - Puentes disulfuro
├── Prolina (C5H9NO2) - Rigidez estructural
└── Trehalosa (C12H22O11) - Protector térmico

Efecto: +Resistencia a temperatura
```

### 🧊 Resistencia al Frío
```
Moléculas necesarias:
├── Glicerol (C3H8O3) - Anticongelante natural
├── Proteínas AFP (con Alanina repetida)
└── Lípidos insaturados - Membranas flexibles

Efecto: +Resistencia a congelamiento
```

### ⚡ Más Energía
```
Moléculas necesarias:
├── ATP (C10H16N5O13P3) - Moneda de energía
├── NAD+ (C21H27N7O14P2) - Transportador de electrones
└── Citocromo C (contiene Fe) - Cadena respiratoria

Efecto: +Velocidad de acciones
```

### 🛡️ Resistencia a Radiación
```
Moléculas necesarias:
├── Melanina (polímero de tirosina)
├── Glutatión (C10H17N3O6S) - Antioxidante
├── Superóxido dismutasa (contiene Zn, Cu, Mn)

Efecto: +Resistencia a daño UV/radiación
```

### 🧠 Velocidad de Procesamiento (Lectura ADN)
```
Moléculas necesarias:
├── Más ribosomas (proteína + ARN)
├── Helicasa (enzima que abre ADN)
├── ATP extra para el proceso

Efecto: +Velocidad de copia/lectura
```

---

## Componentes de una Célula Mínima

### 1. Membrana (Compartimento)
```
Fosfolípidos:
├── Cabeza: Fosfato + Glicerol (hidrofílica)
└── Cola: Ácidos grasos (hidrofóbica)

Fórmula ejemplo: C42H82NO8P (Fosfatidilcolina)
```

### 2. Sistema de Energía
```
ATP Sintasa:
├── Parte F0: Canal de protones
└── Parte F1: Sintetiza ATP

ADP + Pi + Energía → ATP
```

### 3. Sistema de Información
```
ADN → Transcripción → ARN → Traducción → Proteína
        (ARN Polimerasa)      (Ribosoma)
```

### 4. Sistema de Copia
```
ADN Polimerasa:
├── Lee la cadena original
├── Copia nucleótido por nucleótido
└── Produce réplica exacta
```

---

## Progresión del Jugador

### Fase 1: Química Básica
```
Meta: Formar aminoácidos
Logro: Glicina (C2H5NO2) - el más simple
```

### Fase 2: Nucleótidos
```
Meta: Formar A, U, G, C
Requiere: Arcilla para cerrar anillos
Logro: Primer nucleótido
```

### Fase 3: ARN Primitivo
```
Meta: Cadena de 10+ nucleótidos
Logro: Puede "codificar" algo simple
```

### Fase 4: Ribozima
```
Meta: ARN que cataliza reacciones
Logro: Primera "enzima" de ARN
```

### Fase 5: Proteínas
```
Meta: ARN produce primera proteína
Logro: Acceso a poderes especiales
```

### Fase 6: Membrana
```
Meta: Encerrar todo en una vesícula
Logro: Primera proto-célula
```

### Fase 7: ADN
```
Meta: Convertir información de ARN a ADN
Logro: Almacenamiento estable
```

### Fase 8: Automatización
```
Meta: Crear copiadoras automáticas
Logro: La célula se replica sola
```

---

## Tabla de Átomos → Función

| Átomo | Rol Biológico | Para el Juego |
|-------|--------------|---------------|
| C | Esqueleto de toda la vida | Base de todo |
| H | Enlaces, energía | Abundante |
| O | Respiración, agua | Energía |
| N | ADN, proteínas | Información |
| P | ADN, ATP, membranas | Energía + Datos |
| S | Puentes disulfuro | Resistencia |
| Fe | Hemoglobina, enzimas | Transporte O2 |
| Mg | Clorofila | Fotosíntesis |
| Ca | Estructura | Huesos/Concha |
| Zn | Enzimas | Catálisis |
| Cu | Enzimas | Catálisis |

---

## Mecánica de Catálisis por Arcilla

### Cómo Funciona en la Vida Real
1. **Superficie de concentración**: Moléculas se adhieren a la arcilla
2. **Orientación**: La arcilla orienta las moléculas favorablemente
3. **Estabilización**: Protege intermediarios frágiles
4. **Liberación**: El producto formado se libera

### Implementación en el Juego

#### Opción A: Catálisis Realista (ACTUAL)
- En zonas de arcilla, aumenta la fuerza de atracción C-N
- Mayor probabilidad de formar enlaces cíclicos (anillos)
- Las moléculas mantienen todos sus átomos individuales
- Física realista: el jugador observa la formación gradual

#### Opción C: Compresión de Moléculas (FUTURO)
- Moléculas muy grandes (10+ átomos) se "comprimen" en 1 partícula
- Reduce carga de partículas para mejor rendimiento
- La partícula comprimida tiene stats basados en su composición
- Permite escalar a estructuras más complejas (proteínas, ADN)

### Flujo de Formación de Bases Nitrogenadas
```
Zona Arcilla
    │
    ▼
[Fragmentos C, N, H, O] ──atracción aumentada──▶ [Ciclo C-N]
    │                                                │
    ▼                                                ▼
Si ciclo estable (5-6 miembros) ──────────▶ Base Nitrogenada
    │                                       (A, G, C, T, U)
    ▼
Liberación al medio
```

---

*Actualizado: 2025-12-23*

