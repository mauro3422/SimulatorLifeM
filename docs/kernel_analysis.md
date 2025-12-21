# Análisis de Kernels (Taichi GPU) 🧪⚙️

El rendimiento de LifeSimulator reside en sus kernels de Taichi escritos en Python pero compilados a SPIR-V/Vulkan.

## 1. `simulation_step_gpu` (Core Loop)

Este kernel se ejecuta en paralelo para cada partícula y realiza:
- **Cálculo de Fuerzas CHONPS**: Utiliza una matriz de afinidad (`AFINIDAD_MATRIX`) para determinar la atracción/repulsión entre elementos.
- **Integración de Verlet**: Actualiza posiciones basándose en velocidades previas y la aceleración calculada, manteniendo la estabilidad energética.
- **Detección de Enlaces DPG**: Implementa un sistema de enlaces dinámicos que se forman automáticamente al entrar en el radio de equilibrio y se rompen al exceder el límite de tensión.

## 2. `apply_force_pulse` (Interacción)

Kernel disparado por eventos de usuario (Shockwaves):
- Calcula vectores de repulsión radial desde el punto del clic.
- Aplica un impulso de aceleración instantáneo que escala inversamente con la distancia al cuadrado (Lógica de campo gravitatorio/eléctrico).

## 3. `update_grid` (Optimización Espacial)

- Divide el mundo de 15,000x15,000 en una grilla de búsqueda.
- Permite que cada átomo solo verifique colisiones con sus vecinos cercanos, reduciendo la complejidad de $O(N^2)$ a $O(N)$.
# Análisis de Flujo de Kernels - QuimicPYTHON

## Resumen del Problema
Los tiempos de ejecución no escalan con el número de partículas visibles porque varios kernels todavía iteran O(N) en lugar de O(active).

## Flujo de Ejecución por Frame

### 1. FÍSICA (`run_simulation_fast`) - simulation_gpu.py

```mermaid
graph TD
    A[update_grid] -->|O(N)| B[physics_pre_step]
    B -->|O(active)| C[resolve_constraints_grid x3]
    C -->|O(active)| D[physics_post_step]
    D -->|O(active)| E[check_bonding_gpu]
    E -->|O(active)| F[apply_bond_forces_gpu]
```

| Kernel | Complejidad | Status |
|--------|-------------|--------|
| `update_grid()` | O(N) | ⚠️ NECESARIO - construye visible_indices |
| `physics_pre_step()` | O(active) | ✅ OPTIMIZADO |
| `resolve_constraints_grid()` | O(active) | ✅ OPTIMIZADO |
| `physics_post_step()` | O(active) | ✅ OPTIMIZADO |
| `check_bonding_gpu()` | O(active) | ✅ OPTIMIZADO |
| `apply_bond_forces_gpu()` | O(active) | ✅ OPTIMIZADO |

### 2. RENDERIZADO (main.py)

```mermaid
graph TD
    G[normalize_and_count_gpu] -->|O(N)| H[update_borders]
    H -->|O(1)| I[clear_bond_vertices]
    I -->|O(1)| J[prepare_bond_lines]
    J -->|O(N)| K[canvas.circles]
    K -->|O(N)| L[canvas.lines]
```

| Kernel | Complejidad | Status | Tiempo Estimado |
|--------|-------------|--------|-----------------|
| `normalize_and_count_gpu()` | O(N) | ❌ BOTTLENECK | ~240ms |
| `update_borders()` | O(1) | ✅ OK | <1ms |
| `clear_bond_vertices()` | O(1) | ✅ OK | <1ms |
| `prepare_bond_lines()` | O(N) | ❌ BOTTLENECK | ~20ms |
| `canvas.circles()` | O(N) | ❌ BOTTLENECK | ~365ms |
| `canvas.lines()` | O(bonds) | ⚠️ OK | ~10ms |

## Bottlenecks Identificados

### 1. `normalize_and_count_gpu()` en main.py (240ms)
- Itera las 6000 partículas para normalizar posiciones
- El early-exit ayuda pero el loop overhead domina
- **Solución**: Usar visible_indices exportado de simulation_gpu.py

### 2. `prepare_bond_lines()` en main.py (~20ms)
- Itera las 6000 partículas buscando enlaces
- **Solución**: Iterar solo visible_indices

### 3. `canvas.circles()` (365ms)
- La API de Taichi GGUI recibe el campo completo de 6000 partículas
- Aunque partículas con radius=0 no se dibujan, el overhead existe
- **Solución**: Crear buffer compactado de solo partículas visibles

## Próximos Pasos

1. Exportar `visible_indices` y `n_visible` desde simulation_gpu.py
2. Modificar `normalize_and_count_gpu` para usar visible_indices
3. Modificar `prepare_bond_lines` para usar visible_indices
4. Crear buffer compactado para canvas.circles (complejo)

## Conclusión

La física ahora es O(active), pero el renderizado sigue siendo O(N). 
El mayor problema es `canvas.circles()` que consume ~365ms cada frame 
porque Taichi GGUI no tiene forma de pasar solo un subconjunto de partículas.
