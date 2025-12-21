# 🧬 LifeSimulator - Knowledge Transfer Document

> **Fecha**: 2025-12-21
> **Estado**: Producción (Estable)
> **Repositorio**: `mauro3422/SimulatorLifeM`

---

## 🏗️ Arquitectura del Sistema

### Flujo de Datos
1. **Taichi** ejecuta la física en GPU (posiciones, velocidades, enlaces).
2. **NumPy** transfiere datos visibles (`visible_indices`) a buffers de ModernGL.
3. **ModernGL** renderiza partículas y enlaces con shaders GLSL.
4. **ImGui** superpone la interfaz de usuario encima del render.

---

## 📁 Estructura de Archivos Clave

| Archivo | Responsabilidad |
|---------|-----------------|
| `main.py` | Loop principal, renderer, UI, input. (~820 líneas) |
| `src/config.py` | Configuración global, carga de átomos JSON. |
| `src/ui_config.py` | Paleta de colores, dimensiones, widgets reutilizables. |
| `src/systems/simulation_gpu.py` | Kernels de Taichi (física, química, grid espacial). |
| `data/atoms/*.json` | Definiciones de átomos (CHONPS) en formato Data-Driven. |

---

## 🎮 Sistema de Controles (Modo Piloto)

| Tecla | Acción |
|-------|--------|
| **Tab (Mantener)** | Acelera `time_scale` gradualmente hasta 15.0x. Al soltar, **mantiene** la velocidad. |
| **Doble Tab** | Toggle Pausa. |
| **Espacio** | Reset instantáneo a 1.0x (Velocidad Óptima). |
| **Mouse Wheel** | Zoom in/out. |
| **Middle Mouse Drag** | Pan (mover cámara). |
| **Left Click** | Seleccionar átomo. Segundo click: ver molécula. Tercero: deseleccionar. |
| **F3** | Toggle panel de debug/telemetría. |

---

## 🧪 Sistema Químico (CHONPS)

**Elementos**: Carbono, Hidrógeno, Oxígeno, Nitrógeno, Fósforo, Azufre.

- **Afinidades**: Definidas en `data/atoms/*.json` (matriz de probabilidades de enlace).
- **Eventos Evolutivos**: Mutación (cambio de tipo), Efecto Túnel (teletransportación cuántica).
- **Contadores**: `total_bonds_count`, `total_mutations`, `total_tunnels`.

---

## 🛠️ Correcciones Recientes (Importante)

1. **Buffer Overflow (Crash al seleccionar moléculas grandes)**:
   - `vbo_select` expandido de 40KB a 800KB.
   - Guardia de escritura añadida en `ParticleRenderer.render()`.

2. **Tab "Epiléptico"**:
   - Refactorizado a máquina de estados (`tab_just_pressed` vs `tab_held`).
   - `last_tab_time = 0` tras doble-tap para evitar triple-tap.

3. **Slider vs Botones**:
   - Botones de velocidad eliminados. Slider es el control principal.

---

## ⚠️ Deuda Técnica / Código "Sucio"

| Área | Problema | Sugerencia |
|------|----------|------------|
| `main.py` | Demasiado grande (820 líneas). | Extraer `InputHandler`, `Renderer`, `SimulationLoop` a módulos. |
| `update()` | Mezcla input, física y render. | Separar en `handle_input()`, `step_simulation()`, `prepare_render()`. |
| `gui()` | Lógica de paneles mezclada. | Crear funciones `draw_control_panel()`, `draw_monitor_panel()`, etc. |
| `AppState` | Acumula muchos atributos. | Considerar dataclass o NamedTuple para grupos de estado. |

---

## 📋 Checklist de Refactorización Sugerida

- [ ] Extraer `class InputHandler` para toda la lógica de teclado/mouse.
- [ ] Extraer `class SimLoop` para el bucle de simulación (`run_simulation_fast`).
- [ ] Mover `ParticleRenderer` a `src/renderer/particle_renderer.py`.
- [ ] Crear `src/ui/panels/` con archivos separados para cada panel ImGui.
- [ ] Añadir type hints (PEP 484) a funciones principales.
- [ ] Documentar kernels de Taichi con docstrings detallados.

---

## 🚀 Próximos Pasos Potenciales

1. **Guardar/Cargar Estado**: Serializar posiciones, enlaces y configuración a JSON.
2. **Editor de Moléculas**: UI para diseñar moléculas manualmente.
3. **Log Persistente**: Exportar eventos químicos a archivo CSV.
4. **Optimización Avanzada**: Implementar Frustum Culling real, LOD para moléculas lejanas.

---

## 💡 Cómo Retomar Contexto

Si cambias de conversación, simplemente pégame este documento al inicio y estaré al día. También puedo leer `docs/architecture.md` y `README.md` para refrescar detalles específicos.

---

*Documento generado automáticamente por Antigravity para transferencia de conocimiento.*
