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
- [x] Panel DEBUG con stats
- [x] Controles de velocidad (Q/E/P)
- [x] Zoom y pan de camara
- [x] Kernel renderer optimizado

---

## Fase 1: Mejoras de Quimica (1-2 semanas)

### Nuevos Atomos
- [ ] P (Fosforo) - esencial para ADN/ATP
- [ ] S (Azufre) - puentes disulfuro
- [ ] Fe (Hierro) - catalizador

### Enlaces Avanzados
- [ ] Enlaces dobles (C=C, C=O)
- [ ] Enlaces triples (C=C, N=N)
- [ ] Energia de enlace variable
- [ ] Angulos de enlace preferidos

### Reacciones Quimicas
- [ ] Sistema de reacciones: A + B -> AB
- [ ] Energia de activacion
- [ ] Productos de reaccion

---

## Fase 2: Proto-Bioquimica (2-3 semanas)

### Moleculas Predefinidas
- [ ] Aminoacidos basicos (glicina, alanina)
- [ ] Bases nitrogenadas (A, T, G, C, U)
- [ ] Azucares simples (ribosa)
- [ ] Fosfatos

### Comportamientos Emergentes
- [ ] Catalisis (enzimas primitivas)
- [ ] Auto-ensamblaje de estructuras
- [ ] Formacion de membranas (lipidos)

### Sistema de Eras
- [ ] Era 1: "Sopa Primordial" (0-10k frames)
- [ ] Era 2: "Quimica Compleja" (10k-50k)
- [ ] Era 3: "Proto-Vida" (50k+)

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

*Ultima actualizacion: 2024-12-21*
