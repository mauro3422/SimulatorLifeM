# 🧬 LifeSimulator - Game Design Document (GDD)

## Visión del Juego

**Género:** Simulación / Roguelike / Evolución  
**Inspiraciones:** Binding of Isaac + Factorio + Spore (nivel molecular)  
**Premisa:** Sos una célula primitiva que debe sobrevivir, evolucionar y competir recolectando átomos y construyendo tu ADN.

---

## 🎯 Core Loop

```
EXPLORAR → RECOLECTAR → PROCESAR → EVOLUCIONAR → COMPETIR
    ↑                                                ↓
    ←←←←←←←← SOBREVIVIR Y REPETIR ←←←←←←←←←←←←←←←←←←←
```

---

## 🧑‍🌾 Concepto: "Granjero Atómico" & Fábrica Molecular

El jugador controla una entidad molecular que evoluciona hacia una **Fábrica de Vida**:
- **Recolección**: Atracción pasiva de átomos (Tractor Beam) según valencia libre.
- **Procesamiento**: Ensamblaje manual y automático en zonas de catálisis.
- **Quimidex**: Registro educativo de todos los descubrimientos con buffs específicos por grupo funcional.
- **Automatización**: Uso de ARN como "cinta perforada" para dictar la producción de bots obreros.
- **Competencia**: Lucha por recursos limitados contra Biota IA (bots recolectores y parásitos).

---

## ⚛️ Sistema de Átomos

### Nivel 1 - Básicos (Disponibles al inicio)
| Átomo | Uso |
|-------|-----|
| H | Abundante, base de todo |
| C | Esqueleto de la vida |
| N | Para ADN y proteínas |
| O | Respiración, agua |
| S | Puentes, resistencia |
| P | ADN, ATP, energía |

### Nivel 2+ - Raros (Exploración)
| Átomo | Ubicación | Poder |
|-------|-----------|-------|
| Fe | Zonas volcánicas | Hemoglobina (transporta O₂) |
| Mg | Charcos verdes | Clorofila (fotosíntesis) |
| Zn | Meteoritos | Enzimas rápidas |
| Cu | Cuevas profundas | Cadena respiratoria |

---

## 🧬 Sistema Genético

### ADN/ARN
- **ATGC** = Las 4 "letras" del código
- Cada letra es una molécula (15+ átomos)
- Requieren **ARCILLA** para formar anillos
- El **orden** determina qué proteína produces

### Traducción
```
ADN → ARN → Proteína → Función
```

### Automatización
- **Ribosoma** = Lee ARN, produce proteínas automáticamente
- **Polimerasa** = Copia ADN/ARN
- **ATP Sintasa** = Genera energía

---

## 💪 Sistema de Poderes

Los poderes vienen de **cofactores** (átomos raros + proteínas):

| Poder | Cofactor | Cómo conseguir |
|-------|----------|----------------|
| 🔥 Resistencia Calor | S en proteínas | Prolina, Cisteína |
| 🧊 Resistencia Frío | Anticongelantes | Glicerol, Alanina |
| ⚡ Más Energía | ATP + Fe | Hemoglobina, Citocromo |
| 🛡️ Anti-Radiación | Zn + Cu | Superóxido dismutasa |
| 🌿 Fotosíntesis | Mg | Clorofila |
| 🧠 Velocidad Copia | Más ribosomas | ARN + energía |

---

## 🎮 Progresión

### Fase 1: Sopa Primordial (Actual)
- Formar moléculas básicas y estables (H₂O, CH₄, H2).
- Gestión de energía (ATP) y supervivencia básica.

### Fase 2: Fábrica de Arcilla (En Desarrollo)
- Uso de **Arcilla** para cerrar anillos y estabilizar polímeros.
- Implementación de la **Quimidex** para auditoría educativa.

### Fase 3: Ventilas y Entropía
- Exploración de **Ventilas Termales** para reacciones de alta energía.
- Primeros encuentros con **Bots Químicos** (Competencia IA).

### Fase 4: Codificación ARN
- Primera cadena de ARN funcional.
- Automatización de recolección vía bots obreros.

### Fase 5: Biota Completa
- Replicación autónoma y ecosistemas complejos.

---

## 👾 Enemigos

| Tipo | Comportamiento |
|------|---------------|
| **Bacterias rivales** | Compiten por átomos |
| **Virus** | Secuestran tu ADN |
| **Fagos** | Destruyen células |
| **Depredadores** | Células grandes te comen |

### Modos
- **Survival** - Oleadas de enemigos
- **Race** - Quién evoluciona primero
- **Arena** - PvP
- **Sandbox** - Sin enemigos

---

## 🛠️ Máquinas/Orgánulos

| Máquina | Función | Requisitos |
|---------|---------|------------|
| Ribosoma | Lee ARN → Proteínas | ARN + aminoácidos |
| Polimerasa | Copia ADN/ARN | ATP + nucleótidos |
| ATP Sintasa | Genera energía | Membrana + H⁺ |
| Horno de Arcilla | Cierra anillos | Arcilla + átomos |

---

## 📊 Monedas/Recursos

| Recurso | Uso |
|---------|-----|
| **ATP** | Energía para acciones |
| **Nucleótidos** | Construir ADN/ARN |
| **Aminoácidos** | Construir proteínas |
| **Cofactores** | Poderes especiales |

---

## 🎓 Valor Educativo

El jugador aprende de forma interactiva:
- **Tabla Periódica**: Propiedades físicas reales de cada átomo.
- **Quimidex Educativa**: Explicaciones sobre grupos funcionales (Alcoholes, Aminas, etc.).
- **Bioquímica**: El camino del ARN/ADN y por qué ciertas estructuras son estables.
- **Evolución**: Adaptación a entornos extremos (calor, competencia).

---

*Documento actualizado: 2025-12-23*
