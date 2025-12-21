# Convenciones de Código - LifeSimulator

Este documento describe las convenciones de sintaxis usadas en el código
para facilitar la organización, auditoría y mantenimiento.

## Patrones de Comentarios

El script `scripts/code_audit.py` detecta automáticamente estos patrones.

### Secciones con `===`

Usamos líneas de `=` para delimitar secciones lógicas en archivos grandes:

```python
# ===================================================================
# NOMBRE DE LA SECCIÓN
# ===================================================================
```

**Propósito**: Separar visualmente bloques de código relacionados.

### Prioridades

| Símbolo | Significado | Uso |
|---------|-------------|-----|
| `# !!!` o `# CRITICAL` | Crítico | Código de seguridad, errores graves |
| `# !!` o `# WARNING` | Advertencia | Posibles problemas, cambios breaking |
| `# !` o `# IMPORTANT` | Importante | Notas que no deben ignorarse |
| `# NOTE` | Nota | Información contextual |

Ejemplo:
```python
# !!! CRITICAL: No modificar sin revisar impacto en GPU
# !! WARNING: Esta función es O(N²), evitar en loops
# ! IMPORTANT: Requiere inicialización de Taichi
```

### Tareas Pendientes

| Tag | Significado |
|-----|-------------|
| `# TODO` | Tarea pendiente |
| `# FIXME` | Bug conocido por arreglar |
| `# HACK` | Solución temporal/sucia |
| `# XXX` | Requiere atención |
| `# BUG` | Bug documentado |

Ejemplo:
```python
# TODO: Implementar cache para esta operación
# FIXME: Crash cuando n_particles > 10000
# HACK: Workaround para bug de Taichi v1.7
```

### Optimización

| Tag | Significado |
|-----|-------------|
| `# OPTIMIZE` | Oportunidad de optimización |
| `# PERF` | Nota de performance |
| `# SLOW` | Código lento conocido |

### Refactorización

| Tag | Significado |
|-----|-------------|
| `# REFACTOR` | Necesita reestructuración |
| `# CLEANUP` | Código a limpiar |
| `# DEAD` | Código muerto (probablemente eliminar) |

## Estructura de Archivos

### Orden Recomendado

```python
"""
Docstring del módulo
====================
Descripción breve.
"""
import ...

# ===================================================================
# CONSTANTES
# ===================================================================
CONST_A = ...

# ===================================================================
# CLASES / FUNCIONES PRINCIPALES
# ===================================================================
class MyClass:
    ...

# ===================================================================
# FUNCIONES AUXILIARES
# ===================================================================
def helper():
    ...
```

## Ejecución del Script de Auditoría

```bash
python scripts/code_audit.py
```

El script genera:
- Salida en consola (resumida)
- Archivo completo en `scripts/audit_report.txt`

### Métricas Reportadas

1. **Resumen general**: Total archivos, líneas, KB
2. **Archivos por tamaño**: Top 15 con líneas de código
3. **Funciones más grandes**: Top 10
4. **TODOs/FIXMEs encontrados**: Con ubicación
5. **Secciones (===)**: Conteo total
6. **Imports no usados**: Por archivo
7. **Kernels Taichi**: Detectados automáticamente
