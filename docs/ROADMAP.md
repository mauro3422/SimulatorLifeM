# QuimicPYTHON Roadmap
> De Quimica Basica a Vida Emergente

## Estado Actual

### Fisica Implementada
- [x] Colisiones con grid espacial
- [x] Enlaces quimicos (spring-based)
- [x] Movimiento Browniano (agitacion termica)
- [x] Repulsion de Coulomb (electronegatividad)
- [x] Afinidad quimica (H-O, C-C preferidos)

### Sistema de Eventos
- [x] Timeline con contador de frames
- [x] Deteccion de H2O (agua)
- [x] Deteccion de cadenas de carbono
- [x] Deteccion de moleculas complejas (5+ atomos)
- [x] Historial de eventos exportable a JSON

### UI/Controles
- [x] Panel DEBUG con stats (F3)
- [x] Controles de velocidad (Tab/Hold)
- [x] Quimidex (Ex-Pokedex) funcional
- [x] Panel de Análisis Molecular con filtrado de Junk
- [x] Auditoría automática de Desconocidas (JSON)
- [x] Zoom y pan de cámara
- [x] Kernel renderer optimizado

### Performance Implementado (v3.0)
- [x] Universal GPU Buffer (transferencia única)
- [x] Total Fusion Kernels (física fusionada)
- [x] Zero-Copy Slicing (NumPy views)
- [x] Compute Culling (física solo en área visible)
- [x] Benchmarks organizados en `benchmarks/`

### Performance Futuro (Opcional)
- [ ] Hibernación de Partículas (v_min < 0.01 por N frames → sleep)
- [ ] GPU Instancing Puro (eliminar to_numpy)
- [ ] Sub-stepping Estocástico (procesar N% aleatorio)

---

### Fase 1: Esqueleto y Fábrica (1-2 semanas)
- [x] Backbone de Carbono (Sinergia de buffs)
- [x] Mecánica de 'Tractor Beam' inicial (Atracción pasiva)
- [x] **Auditoría Masiva de Moléculas**: Limpieza de 599 desconocidas y catalogación profesional.
- [ ] Implementación de Ventilas Termales (Física de alta energía)
- [ ] Spawn de estructuras pre-formadas en zonas de catálisis

### Fase 2: Proto-Bioquimica & Competencia (2-3 semanas)
- [ ] Bots Químicos (IA básica de recolección)
- [ ] Sistema de "Depredación" (Virus/Parásitos moleculares)
- [x] **Base de Datos Bioquímica**: Aminoácidos, bases nitrogenadas y azúcares con lore científico.

### Sistema de Eras (Contextual)
- **Era 1: Caos Primordial**: Solo átomos sueltos y moléculas simples.
- **Era 2: Era de la Arcilla**: Aparición de polímeros y anillos (Primeras fábricas).
- **Era 3: El Gran Filtro**: Competencia masiva entre Biota IA y el jugador.

---

## Fase 3: Vida Emergente (4-6 semanas)

### Replicacion
- [ ] Moleculas que pueden copiarse
- [ ] Plantillas moleculares (proto-ARN)
- [ ] Errores de copia (mutaciones)

### Metabolismo
- [ ] Consumo de energia (ATP-like)
- [ ] Degradacion de moleculas
- [ ] Ciclos de reacciones

### Estructuras Celulares
- [ ] Membranas cerradas
- [ ] Interior vs exterior
- [ ] Transporte selectivo

### Evolucion
- [ ] Seleccion natural (competencia)
- [ ] Fitness basado en estabilidad
- [ ] Arbol genealogico molecular

---

## Fase 4: Narracion con LLM (Paralelo)

- [ ] Exportar eventos a JSON
- [ ] API para consultas del LLM
- [ ] Detectar patrones evolutivos
- [ ] Generar "documentales" de la simulacion

---

## Limitaciones de Taichi GGUI

### Lo que SI puede hacer
- Paneles rectangulares con texto
- Sliders, checkboxes, buttons
- Render de circulos/lineas via kernels
- Canvas con set_image()

### Lo que NO puede hacer
- Widgets avanzados (tabs, graficos)
- Texto con formato (negrita, colores)
- Simbolos en teclado (+, -, etc)
- Ventanas flotantes/modales

### Alternativas Futuras
- Dear ImGui (via taichi-imgui)
- Pygame overlay
- Ventana web (Flask + canvas)

---

*Ultima actualizacion: 2024-12-22*
