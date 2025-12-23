# Ideas y Notas de Desarrollo

## Ideas del Usuario (2025-12-23)

### Sistema de Juego
- Piloto molecular que "monta" una molécula
- Recolectar moléculas da stats/poderes
- Escalada: moléculas simples → ARN/ADN → célula
- Herramientas que automatizan/aceleran procesos
- Generador de ATP para energía

### Catálisis por Arcilla (Decisión 2025-12-23)
- **Opción A (IMPLEMENTAR)**: Catálisis realista
  - Aumentar atracción C-N en zonas de arcilla
  - Mayor probabilidad de enlaces cíclicos
  - Física realista, formación gradual observable
  
- **Opción C (FUTURO)**: Compresión de moléculas grandes
  - Moléculas 10+ átomos → 1 partícula con stats
  - Para escalar a estructuras complejas
  - Mejor rendimiento a escala

### Silicio para Arcilla Natural (Decisión 2025-12-23)
**OBJETIVO**: Que la física haga emerger estructuras de arcilla naturalmente

```
Si (Silicio) + O (Oxígeno) → SiO₄ (Tetraedro de silicato)
    ↓
Múltiples SiO₄ → Red cristalina (Arcilla)
    ↓
Arcilla formada atrae C, N → Cataliza bases nitrogenadas
```

**Propiedades del Si:**
- Valencia: 4 (como Carbono)
- Electronegatividad: 1.9 (menor que C)
- Afinidad alta con O (forma enlaces muy fuertes)
- Color: Gris/Marrón

**Física esperada:**
- Si-O: Enlaces MUY fuertes (afinidad alta, spring_k alto)
- Estructuras Si-O son rígidas (no se rompen fácil)
- Las estructuras formadas atraen C y N cercanos
- El sistema "emerge" sin código especial de zonas

### Tests Necesarios
- [ ] Verificar si A, T, G, C se forman naturalmente
- [x] Agregar Si como átomo
- [ ] Observar si Si-O forman estructuras
- [ ] Verificar si las estructuras catalizan formación

### UI/UX
- [x] Panel P: Solo mostrar moléculas con nombre (no transitorias)
- [ ] Limpiar base de datos del panel

### Moléculas Faltantes
- Uracilo (C4H4N2O2) - para ARN
- Desoxirribosa (C5H10O4) - azúcar del ADN
- Fosfato (PO4/H3PO4) - une nucleótidos
- ATP (C10H16N5O13P3) - energía
- **SiO₂ (Sílice)** - base de arcilla
- **Al₂Si₂O₅(OH)₄ (Caolinita)** - arcilla completa


