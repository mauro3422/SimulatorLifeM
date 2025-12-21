# Características de QuimicPYTHON

## Core de Simulación
- **Motor GPU Vulkan**: Simulación 100% en GPU usando Taichi con backend Vulkan.
- **Mundo Gigante**: Espacio de simulación de **5000x5000** unidades (25 millones de área).
- **Densidad Masiva**: Soporte optimizado para **5000+** partículas simultáneas a ~50 FPS.
- **Grilla Espacial (Spatial Grid)**: Optimización O(N) para detección de colisiones.

## Optimizaciones de Rendimiento (v2.0)
- **Buffer Compactado (O(active))**: Física y química solo procesan partículas en pantalla.
- **Kernel Renderer Custom**: Renderizado directo a buffer de imagen, evitando overhead de GGUI.
- **Profiling Detallado**: Logs de tiempo por sección (Events, Input, Phys, RenderPrep, Canvas, UI, Show).

## Sistema de Enlaces (Chemistry)
- **Regla de Valencias**: Cada átomo respeta su capacidad de enlace (C=4, O=2, H=1, N=3, Cl=1).
- **Enlace Covalente**: Basado en distancia y valencias disponibles.
- **Física de Resortes**: Enlaces elásticos con damping para evitar vibraciones infinitas.
- **Frustum Culling**: Solo dibuja enlaces visibles en pantalla.

## Renderizado (Kernel Renderer)
- **Dibujo por Pixels**: Círculos y líneas dibujados directamente con kernels GPU.
- **Grosor de Enlaces**: 3 pixels para visibilidad clara.
- **Bordes Suaves**: Antialiasing simple en bordes de círculos.
- **Estilo Retro**: Píxeles definidos con estética minimalista.

## Interfaz y Controles
- **Zoom de Precisión**: Rango 2.5x a 10.0x con Click Derecho + Arrastrar.
- **Navegación**: WASD/Flechas con clamping a bordes del mundo.
- **Panel Informativo**: FPS, zoom, partículas activas, distancias a bordes.
- **Modo Debug (G)**: Visualización de cajas de simulación y pantalla.

## Sistema de Telemetría
- **Logs de Eventos**: Registro en `logs/` con rotación automática.
- **Profiling por Sección**: Tiempos de Events, Input, Phys, RenderPrep, Canvas, UI, Show.
- **Contador de Partículas**: Activas vs. Esperadas con sistema de culling.

## Estructura de Archivos
- `src/core/`: Núcleo del estado del universo.
- `src/systems/`: Física y química GPU (simulation_gpu.py).
- `src/renderer/`: Motor gráfico (kernel_renderer.py, camera.py, ui/).
- `docs/`: Documentación técnica.
- `logs/`: Archivos de log de sesiones.
