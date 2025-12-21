# Arquitectura de LifeSimulator 🧬🏗️

LifeSimulator utiliza un pipeline híbrido optimizado para el procesamiento paralelo masivo en la GPU.

## 🛠️ Pipeline de Datos (Vulkan/OpenGL)

El sistema está diseñado para evitar la latencia de transferencia entre la CPU y la GPU:

1.  **Física (Taichi Lang)**: Los kernels de Taichi procesan la integración de Verlet, colisiones y enlaces químicos directamente en los registros de la GPU.
2.  **Sincronización Zero-Copy**: Los datos de posición y color se exponen a través de buffers de Taichi que son consumidos directamente por **ModernGL**.
3.  **Renderizado (ModernGL)**: Se utilizan VAOs (Vertex Array Objects) para dibujar miles de puntos y líneas con una sola llamada de dibujo, permitiendo mantener +60 FPS con 10,000+ partículas.

## 🎨 Arquitectura de UI (`src/ui_config.py`)

Hemos estandarizado la interfaz bajo un modelo **Data-Driven**:

- **UIConfig**: Centraliza todos los tokens de diseño (colores, fuentes, espaciados).
- **UIWidgets**: Componentes de ImGui reutilizables (dashboards, logs, HUDs dinámicos).
- **Layout Adaptativo**: Los paneles se calculan en base a la resolución actual de la ventana, asegurando que el simulador sea usable desde resoluciones portátiles hasta 4K.

## 📂 Directorios Clave

- `src/systems/`: Lógica de simulación y shaders.
- `src/renderer/`: Gestión de cámara y proyección NDC.
- `src/config.py`: Definición de la ontología química (Propiedades CHONPS).
ordenadas
El sistema utiliza tres espacios de coordenadas distintos que deben ser sincronizados:

1.  **World Space (Mundo)**:
    *   Coordenadas flotantes reales de la simulación.
    *   Rango: `[0, 0]` a `[5000, 5000]` (definido como `WORLD_SIZE`).
    *   Usado por: `simulation_gpu.py` (física), `pos` field, `cam_x/cam_y`.

2.  **Normalized Space (Taichi GGUI)**:
    *   Coordenadas de renderizado requeridas por Taichi (`canvas.circles`, `canvas.lines`).
    *   Rango: `[0.0, 0.0]` (abajo-izq) a `[1.0, 1.0]` (arriba-der).
    *   Transformación (Kernel `normalize_positions_with_zoom` en `main.py`):
        ```python
        rel_x = (pos_world - cam_x) * zoom
        norm_x = (rel_x / WORLD_SIZE) + offset_x
        ```
    *   *Nota*: La UI ocupa el 25% derecho, por lo que el centro de la simulación en pantalla es `x=0.375` (mitad de 0.75).

3.  **Culling Space (Visible Box)**:
    *   Cálculo en CPU (`main.py`) para determinar qué enviar a GPU.
    *   Fórmula de Área Visible:
        ```python
        width_visible = (0.75 * WORLD_SIZE) / zoom
        height_visible = (1.0 * WORLD_SIZE) / zoom
        ```
    *   Margen: Se agrega un borde (`margin`) para evitar "popping" visual.

## Componentes Principales
El proyecto utiliza un patrón de **Contexto de Mundo** para mantener el estado de la simulación separado de la lógica de procesamiento.

- **`src/core/universe.py`**: Contiene la clase `Universe`, que es el almacén de datos (NumPy arrays para posiciones, velocidades, etc.).
- **`src/systems/`**: Contiene módulos sin estado (stateless) que operan sobre el `Universe`.
  - `physics.py`: Maneja gravedad, rebotes, colisiones y temperatura.
  - `chemistry.py`: Maneja la formación y mantenimiento de enlaces covalentes (regla de valencias).

## Sistema de UI Modular
La interfaz de usuario está separada en `src/renderer/ui/` para permitir su escalado sin ensuciar el renderizado principal.
- **Widgets**: Componentes básicos (Sliders con tooltips, Botones).
- **Panels**: Composiciones complejas (Panel de control, Tarjetas de información).

## Flujo de Datos
1. `main.py` inicializa el `Universe` y los `Panels`.
2. En cada frame, se llama a `loop_procesamiento()` que ejecuta los sistemas.
3. El `ControlPanel` modifica directamente los parámetros en `sim_config`, afectando los sistemas en el siguiente frame.
