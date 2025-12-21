# 🧬 LifeSimulator - Knowledge Transfer Document

> **Fecha**: 2025-12-21 (Actualizado)
> **Estado**: Producción (Refactorizado)
> **Repositorio**: `mauro3422/SimulatorLifeM`

---

## 🏗️ Arquitectura del Sistema

### Flujo de Datos
1. **Taichi** ejecuta la física en GPU (posiciones, velocidades, enlaces).
2. **NumPy** transfiere datos visibles (`visible_indices`) a buffers de ModernGL.
3. **ModernGL** renderiza partículas y enlaces con shaders GLSL.
4. **ImGui** superpone la interfaz de usuario encima del render.

---

## 📁 Estructura de Archivos

### Arquitectura Modular (Post-Refactorización)

```
LifeSimulator/
├── main.py                     (323 líneas) - Orquestador principal
├── src/
│   ├── config/
│   │   ├── __init__.py         - Exports centralizados
│   │   ├── simulation.py       - Parámetros de simulación
│   │   ├── atoms.py            - Carga de átomos JSON
│   │   ├── ui.py               - Paleta, widgets ImGui
│   │   └── system_constants.py - Constantes de escala/tamaño
│   │
│   ├── core/
│   │   ├── context.py          (279 líneas) - Singleton AppContext
│   │   ├── event_system.py     - Timeline, eventos
│   │   └── input_handler.py    - Teclado/mouse
│   │
│   ├── systems/
│   │   ├── taichi_fields.py    - Campos Taichi centralizados
│   │   ├── physics_constants.py - Constantes físicas
│   │   ├── physics_kernels.py  - Kernels de física
│   │   ├── chemistry_kernels.py - Kernels de química
│   │   ├── simulation_gpu.py   (256 líneas) - Orquestador GPU
│   │   └── molecule_detector.py - (Pendiente integrar)
│   │
│   ├── renderer/
│   │   ├── camera.py           - Sistema de cámara
│   │   ├── particle_renderer.py - Renderer ModernGL
│   │   └── opengl_kernels.py   - Kernels para OpenGL
│   │
│   └── ui/panels/
│       ├── control_panel.py    - Panel de controles
│       ├── monitor_panel.py    - Monitor de estadísticas
│       ├── telemetry_panel.py  - Telemetría
│       └── inspector_panel.py  - Inspector de átomos
│
├── scripts/
│   ├── code_audit.py           - Script de auditoría v3.0
│   └── audit_report.txt        - Último reporte generado
│
└── docs/
    ├── KNOWLEDGE_TRANSFER.md   - Este documento
    ├── architecture.md         - Arquitectura detallada
    ├── code_conventions.md     - Convenciones de código
    └── features.md             - Características
```

### Métricas Actuales
| Directorio | Archivos | Líneas |
|------------|----------|--------|
| `src/systems/` | 6 | ~1,000 |
| `src/core/` | 3 | ~650 |
| `src/config/` | 5 | ~530 |
| `src/renderer/` | 3 | ~465 |
| `src/ui/panels/` | 5 | ~280 |
| **Total** | **27** | **~3,840** |

---

## 🎮 Sistema de Controles

| Tecla | Acción |
|-------|--------|
| **Tab (Mantener)** | Acelera `time_scale` hasta 15.0x. Al soltar, mantiene velocidad. |
| **Doble Tab** | Toggle Pausa. |
| **Espacio** | Reset a 1.0x. |
| **Mouse Wheel** | Zoom in/out. |
| **Middle Mouse Drag** | Pan (mover cámara). |
| **Left Click** | Seleccionar átomo → molécula → deseleccionar. |
| **F3** | Toggle panel de debug. |

---

## 🧪 Sistema Químico (CHONPS)

**Elementos**: Carbono, Hidrógeno, Oxígeno, Nitrógeno, Fósforo, Azufre.

- **Afinidades**: Definidas en `data/atoms/*.json`.
- **Kernels de química** en `src/systems/chemistry_kernels.py`:
  - `check_bonding_gpu` - Formación de enlaces
  - `apply_bond_forces_gpu` - Fuerzas de resorte
  - `apply_evolutionary_effects_gpu` - Mutación y túnel

---

## ✅ Refactorización Completada

| Tarea | Estado |
|-------|--------|
| Extraer `InputHandler` | ✅ |
| Extraer `ParticleRenderer` | ✅ |
| Crear `src/ui/panels/` | ✅ |
| Unificar `AppContext` | ✅ |
| Centralizar config en paquete | ✅ |
| Dividir `simulation_gpu.py` | ✅ |
| Extraer kernels OpenGL | ✅ |
| Script de auditoría v3.0 | ✅ |

---

## 📋 Pendiente

- [ ] Evaluar/integrar `molecule_detector.py`
- [ ] Añadir type hints (PEP 484)
- [ ] Guardar/Cargar estado a JSON
- [ ] Log persistente de eventos

---

## 🔧 Herramientas de Desarrollo

### Script de Auditoría
```bash
python scripts/code_audit.py
```
Genera `scripts/audit_report.txt` con:
- Archivos por tamaño
- Funciones más grandes
- Kernels Taichi
- TODOs/FIXMEs
- Imports no usados

### Convenciones de Código
Ver `docs/code_conventions.md` para patrones de comentarios reconocidos.

---

*Documento actualizado 2025-12-21 tras refactorización completa.*
