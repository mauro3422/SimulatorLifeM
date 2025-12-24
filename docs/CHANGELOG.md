# Changelog - LifeSimulator

Todos los cambios notables del proyecto se documentan en este archivo.

## [3.3.0] - 2024-12-24 - The Grand Molecule Audit & Database Expansion

### 🧪 Auditoría Química Masiva
- **Nuevo**: Procesamiento completo de `enriched_discoveries.json` (599 moléculas auditadas).
- **Enriquecimiento**: Catálogo ampliado a **142 moléculas** con lore científico detallado.
- **Categorías**: Nuevos Aminoácidos, Nucleobases, Azúcares y Radicales reactivos.
- **Blocklist**: Ampliación a **611 fórmulas bloqueadas** para asegurar realismo químico.
- **Workflow**: Documentado flujo de auditoría técnica en `.agent/workflows/molecule-audit.md`.

### 🛠️ Herramientas de Mantenimiento
- **Nuevo**: `scripts/cleanup_enriched.py` - Eliminación de duplicados.
- **Nuevo**: `scripts/clean_impossible.py` - Filtro de física rota.
- **Nuevo**: `scripts/clean_prefixes.py` - Filtro de terminología genérica.
- **Nuevo**: `scripts/migrate_survivors.py` - Automatización de migración y lore final.

## [3.2.0] - 2024-12-23 - Unified Monitoring & Deep Code Cleanup

### 🛠️ LifeMonitor CLI Unificado
- **Nuevo**: `scripts/monitor.py` - Centro de mando para diagnóstico y benchmarking.
  - `--mode audit`: Auditoría química completa con métricas de salud.
  - `--mode forensic`: Análisis profundo de geometría VSEPR.
  - `--mode tune`: Optimización de parámetros (wrapper a legacy).
  - `--mode bench`: Stress test de hardware con escalado de partículas.
- **Nuevas Métricas**: Emergence Velocity, Z-Stability, Energy Volatility.

### 🧪 Fábrica Molecular (v3.5.0 - Early Access)
- **Nuevo**: `ZoneManager` con **Ventilas Termales** (Energía/Entropía) y **Depósitos de Arcilla** (Catálisis).
- **Nuevo**: Mecánica de **Tractor Beam** para átomos de Carbono (Atracción de recursos).
- **Refactor**: Renombrado global de **Pokedex** a **Quimidex** para alineación temática.
- **Mejora**: Integración de metabolismo (Gasto/Ganancia de ATP) en `ProgressionManager`.

### 🧩 Inteligencia Química Unificada
- **Refactor**: `MolecularAnalyzer` ahora contiene métodos estáticos `get_molecule_indices()` y `get_formula()`.
- **Refactor**: `MoleculeDetector` delega a `MolecularAnalyzer`, eliminando 30+ líneas de código duplicado.

### 🧹 Limpieza y Organización
- **Nuevo**: `scripts/dev_tools.py` - Suite de desarrollo (auditoría de código, estadísticas).
- **Movidos**: Benchmarks sintéticos a `benchmarks/lab/`.
- **Archivados**: Scripts legacy a `scripts/archives/`.
- **Hardening**: Comparaciones explícitas `!= 0` en todos los kernels para compatibilidad Vulkan.

### 📊 Métricas del Proyecto
- **64 archivos Python**, 11,973 líneas, 32 Kernels Taichi, 32 Clases.

---

## [3.1.0] - 2024-12-22 - Phase 3 Completion & Discoveries

### 🚀 Estabilización Química
- **Solucionado**: Error de colapso de partículas a (0,0) mediante inicialización unificada de GPU.
- **Nuevo**: Benchmarking avanzado en `advanced_molecular_analyzer.py` con 99.8% de persistencia de enlaces.
- **Mejora**: Medición de ángulos VSEPR en 3D real (2.5D integrado).

### ✨ Descubrimiento de Moléculas
  - **Inorgánicas**: Ozono (O3), Hidroxilo (H1O1), Hidroperoxilo (H1O2), Dióxido de Nitrógeno (N1O2).
  - **Orgánicas**: Ácido Carbónico (C1H2O3), Metanimina (C1H3N1), Metanodiol (C1H4O2), Subóxido de Carbono (C3O2).
- **Renombrado**: Pokedex -> Quimidex.

## [3.0.0] - 2024-12-21 - Ultra-Loop V3

### 🚀 Optimizaciones Mayores

#### Universal GPU Buffer
- **Nuevo**: Buffer unificado que contiene stats, partículas, enlaces y highlights en un solo bloque de memoria.
- **Impacto**: Reducción del 80% en latencia de transferencia GPU→CPU.
- **Archivos**: `src/renderer/opengl_kernels.py`

#### Total Fusion Kernels  
- **Nuevo**: `kernel_post_step_fused` combina física básica + reglas avanzadas en un solo dispatch.
- **Impacto**: Reducción del 40% en llamadas al driver GPU.
- **Archivos**: `src/systems/physics_kernels.py`, `src/systems/simulation_gpu.py`

#### Zero-Copy Slicing
- **Nuevo**: Extracción de datos mediante vistas NumPy sin copias de memoria.
- **Impacto**: Reducción del 20% en uso de memoria durante transferencias.

### ✨ Nuevas Características

- **Sistema de Reglas Modulares**: `ti.func` para reglas de física inyectables.
  - `apply_brownian_i`: Agitación térmica
  - `apply_coulomb_repulsion_i`: Repulsión electrostática
  - `apply_metabolism_i`: Ejemplo de regla personalizada

### 📊 Métricas de Performance

| Antes | Después | Mejora |
|-------|---------|--------|
| 60 FPS | 100+ FPS | +66% |
| 2ms DataTx | 0.5ms DataTx | -75% |
| 4 syncs/frame | 1 sync/frame | -75% |

### 🗂️ Reorganización

- **Nueva carpeta**: `benchmarks/` con todos los scripts de evaluación.
- **Nuevo script**: `benchmarks/monitor.py` para visualización de métricas.
- **Movidos**: Logs a `benchmarks/results/` y `logs/`.

---

## [2.0.0] - 2024-12-20 - Fused Kernels

### Optimizaciones
- Kernels de física fusionados (pre-step, post-step, bonding).
- Reducción de dispatches GPU de 8 a 4 por frame.

---

## [1.0.0] - 2024-12-18 - Release Inicial

### Enlaces Avanzados
- [x] Enlaces dobles (C=C, C=O) - Parcialmente vía afinidad VSEPR
- [ ] Enlaces triples (C=C, N=N)
- [x] Energia de enlace variable (Spring-based)
- [x] Angulos de enlace preferidos (VSEPR 3D)
- UI con ImGui y renderizado ModernGL.
- Controles de cámara y selección molecular.
