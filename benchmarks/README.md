# 📊 Benchmarks - LifeSimulator

Esta carpeta contiene herramientas de evaluación de rendimiento para el motor de simulación.

## Scripts Disponibles

| Script | Descripción | Uso |
|--------|-------------|-----|
| `benchmark_gpu.py` | Benchmark completo de GPU (física + render) | `python benchmark_gpu.py` |
| `benchmark_physics_stages.py` | Mide cada etapa del pipeline de física | `python benchmark_physics_stages.py` |
| `benchmark_bottlenecks.py` | Identifica cuellos de botella específicos | `python benchmark_bottlenecks.py` |
| `benchmark_headless.py` | Benchmark sin ventana (puro cómputo) | `python benchmark_headless.py` |
| `benchmark_datatx.py` | Mide transferencia GPU→CPU | `python benchmark_datatx.py` |
| `bench_transfer_logic.py` | Test de slicing vs full transfer | `python bench_transfer_logic.py` |
| `test_partial_transfer.py` | Prueba de transferencia parcial | `python test_partial_transfer.py` |
| `monitor.py` | **Monitor de performance en tiempo real** | `python monitor.py` |

## Estructura de Resultados

```
results/
├── benchmark_datatx.log      # Logs de transferencia
├── benchmark_headless.log    # Logs de modo headless
├── benchmark_stages.log      # Logs por etapa de física
├── benchmark_output.txt      # Salida general
└── latest_run.json           # Último benchmark (JSON)
```

## Ejecutar Monitor

```bash
# Ver métricas del último benchmark
python monitor.py

# Ver métricas en vivo (conectado a simulación)
python monitor.py --live

# Exportar resultados a JSON
python monitor.py --export results/export.json
```

## Métricas Clave

- **FPS**: Frames por segundo promedio
- **Physics**: Tiempo de cálculo de física (ms)
- **DataTx**: Tiempo de transferencia GPU→CPU (ms)
- **n_visible**: Partículas visibles en pantalla
- **n_simulated**: Partículas procesadas por física

## Optimizaciones Implementadas (v3.0)

| Optimización | Impacto |
|--------------|---------|
| Universal GPU Buffer | -80% latencia DataTx |
| Total Fusion Kernels | -40% dispatches GPU |
| Zero-Copy Slicing | -20% uso de memoria |
| Compute Culling | Variable según zoom |

---
*Última actualización: 2024-12-21*
