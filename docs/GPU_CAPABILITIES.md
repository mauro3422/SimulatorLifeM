# GPU Capabilities & Diagnostics Guide

Este documento describe las capacidades GPU del sistema actual y cómo extraer información de diagnóstico para optimizaciones futuras.

---

## Sistema Actual

| Componente | Valor |
|------------|-------|
| **GPU** | AMD Radeon RX 570 Series |
| **OpenGL Version** | 3.3 (330) |
| **Total Extensions** | 285 |
| **Backend Taichi** | Vulkan |
| **Taichi Version** | 1.7.4 |

---

## Comandos de Diagnóstico

### 1. Información Básica OpenGL

```powershell
# Versión y Renderer
python -c "import moderngl; ctx = moderngl.create_standalone_context(); print('OpenGL Version:', ctx.version_code); print('Renderer:', ctx.info['GL_RENDERER'])"
```

### 2. Extensiones de Buffer (Relevantes para Optimización)

```powershell
# Listar extensiones de buffer
python -c "import moderngl; ctx = moderngl.create_standalone_context(); exts = [e for e in ctx.extensions if 'buffer' in e.lower() or 'storage' in e.lower()]; print('Buffer Extensions:', exts)"
```

### 3. Verificar Extensión Específica

```powershell
# Verificar soporte de buffers persistentes (GPU-Only Rendering)
python -c "import moderngl; ctx = moderngl.create_standalone_context(); print('ARB_buffer_storage:', 'GL_ARB_buffer_storage' in ctx.extensions)"
```

### 4. Información Completa del Contexto

```powershell
# Toda la info disponible
python -c "import moderngl; ctx = moderngl.create_standalone_context(); import pprint; pprint.pprint(ctx.info)"
```

### 5. Capacidades Taichi

```powershell
# Tipos disponibles para interop
python -c "import taichi as ti; ti.init(); print([x for x in dir(ti.types) if 'arr' in x.lower() or 'ext' in x.lower() or 'texture' in x.lower()])"

# Test NDArray con Vulkan
python -c "import taichi as ti; ti.init(arch=ti.vulkan); n = ti.ndarray(dtype=ti.f32, shape=(10,)); print('ndarray funciona'); print('from_numpy:', hasattr(n, 'from_numpy')); print('to_numpy:', hasattr(n, 'to_numpy'))"
```

---

## Extensiones OpenGL Relevantes

### Extensiones Disponibles (RX 570)

| Extensión | Descripción | Uso Potencial |
|-----------|-------------|---------------|
| `GL_ARB_buffer_storage` | Buffers inmutables persistentes | **GPU-Only Rendering** - mapeo directo GPU→VBO |
| `GL_ARB_map_buffer_range` | Mapeo parcial de buffers | Actualización eficiente de sub-rangos |
| `GL_ARB_shader_storage_buffer_object` | SSBOs | Compute shaders, datos compartidos |
| `GL_ARB_sparse_buffer` | Buffers dispersos | Memoria virtual para datos grandes |
| `GL_ARB_copy_buffer` | Copia GPU→GPU | Evitar roundtrips CPU |
| `GL_ARB_clear_buffer_object` | Limpieza eficiente | Reset de buffers sin CPU |
| `GL_ARB_pixel_buffer_object` | PBOs para texturas | Async texture uploads |
| `GL_ARB_uniform_buffer_object` | UBOs | Uniforms compartidos eficientes |

### Extensiones de Alto Rendimiento

```
GL_ARB_buffer_storage         ✅ Habilitado
GL_ARB_map_buffer_range       ✅ Habilitado  
GL_ARB_shader_storage_buffer_object ✅ Habilitado
GL_ARB_compute_shader         ✅ (implícito en 4.3+)
```

---

## Estrategias de Optimización por Extensión

### 1. GL_ARB_buffer_storage (Persistent Mapped Buffers)

**Concepto**: Crear un buffer inmutable mapeado permanentemente a memoria CPU.

```python
# Pseudo-código (requiere PyOpenGL directo, no ModernGL)
import OpenGL.GL as gl

# Crear buffer inmutable
buffer_id = gl.glGenBuffers(1)
gl.glBindBuffer(gl.GL_ARRAY_BUFFER, buffer_id)
gl.glBufferStorage(
    gl.GL_ARRAY_BUFFER, 
    size_bytes,
    None,
    gl.GL_MAP_WRITE_BIT | gl.GL_MAP_PERSISTENT_BIT | gl.GL_MAP_COHERENT_BIT
)

# Mapear una vez, usar siempre
ptr = gl.glMapBufferRange(
    gl.GL_ARRAY_BUFFER, 0, size_bytes,
    gl.GL_MAP_WRITE_BIT | gl.GL_MAP_PERSISTENT_BIT | gl.GL_MAP_COHERENT_BIT
)
```

**Limitación con Taichi**: Taichi 1.7+ no soporta `ext_arr` para escribir directamente a punteros externos. El flujo sigue siendo:
- GPU (Taichi) → `to_numpy()` → CPU → `vbo.write()` → GPU (OpenGL)

### 2. GL_ARB_copy_buffer (GPU-to-GPU Copy)

**Concepto**: Si Taichi pudiera escribir a un SSBO de OpenGL, podríamos copiar entre buffers sin CPU.

```python
gl.glCopyBufferSubData(
    gl.GL_COPY_READ_BUFFER,  # Fuente (SSBO de Taichi)
    gl.GL_COPY_WRITE_BUFFER, # Destino (VBO de rendering)
    0, 0, size_bytes
)
```

**Estado**: Requiere investigación de interop Taichi-OpenGL.

### 3. Optimización Actual: Slice Sync (Implementado ✅)

Reducir el tamaño de transferencia:
- **Antes**: 10,000 partículas × 12 floats × 4 bytes = **480KB/frame**
- **Después**: 3,000 partículas × 6 floats × 4 bytes = **72KB/frame**
- **Mejora**: ~85% reducción en data transfer

---

## Vulkan Backend (Taichi)

### Ventajas de Vulkan sobre OpenGL

| Aspecto | OpenGL | Vulkan |
|---------|--------|--------|
| Driver overhead | Alto | Bajo |
| Multi-threading | Limitado | Nativo |
| Memory management | Automático | Manual (más control) |
| Validation layers | Limitado | Completo |

### Verificar Backend Activo

```powershell
# Ver qué backend está usando Taichi
python -c "import taichi as ti; ti.init(); print('Arch:', ti.cfg.arch)"
```

### Forzar Vulkan

```python
import taichi as ti
ti.init(arch=ti.vulkan)  # Forzar Vulkan
```

---

## Diagnóstico de Rendimiento

### Script de Benchmark Rápido

```python
# benchmark_gpu.py
import moderngl
import numpy as np
import time

ctx = moderngl.create_standalone_context()
print(f"GPU: {ctx.info['GL_RENDERER']}")
print(f"OpenGL: {ctx.version_code}")

# Test de transferencia
sizes = [1000, 5000, 10000, 50000]
for n in sizes:
    data = np.random.rand(n, 4).astype('float32')
    vbo = ctx.buffer(reserve=n * 16)
    
    start = time.perf_counter()
    for _ in range(100):
        vbo.write(data.tobytes())
    elapsed = (time.perf_counter() - start) * 10  # ms per write
    
    print(f"  {n:6d} particles: {elapsed:.2f} ms/write")
```

### Métricas Clave a Monitorear

| Métrica | Target | Actual |
|---------|--------|--------|
| FPS | >45 | ~32 |
| Physics | <5ms | ~4ms ✅ |
| Data Transfer | <2ms | ~16ms ❌ |
| Render | <1ms | ~0.2ms ✅ |
| Chemistry | 0ms (async) | 0ms ✅ |

---

## Roadmap de Optimización

### Fase Actual (V4 Slice Sync) ✅
- NDArrays reducidos a 3000 elementos max
- UI desacoplada de GPU queries
- Chemistry en thread separado

### Fase Siguiente (V5 - Investigación)
1. **PyOpenGL híbrido**: Usar PyOpenGL para buffers persistentes + ModernGL para shaders
2. **Compute Shaders**: Mover transformaciones de cámara a GPU
3. **Double Buffering**: Escribir al VBO mientras el anterior se renderiza

### Fase Futura (V6 - Experimental)
1. **Taichi-Vulkan Interop**: Investigar si Vulkan permite zero-copy
2. **wgpu-py**: Backend WebGPU como alternativa moderna
3. **Metal (macOS)**: Si se porta a Mac

---

## Referencias

- [ModernGL Documentation](https://moderngl.readthedocs.io/)
- [Taichi NDArray Guide](https://docs.taichi-lang.org/docs/ndarray)
- [OpenGL Buffer Storage](https://www.khronos.org/opengl/wiki/Buffer_Object#Buffer_Object_Usage)
- [Vulkan-OpenGL Interop](https://www.khronos.org/opengl/wiki/Vulkan_Interop)
