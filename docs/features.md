# Características de LifeSimulator 🧬✨

LifeSimulator ofrece un set de herramientas interactivas diseñadas para la exploración científica de sistemas emergentes.

## 🖱️ Sistema de Picking e Inspección

- **Selección por Clic**: Permite identificar átomos individuales y ver sus propiedades químicas (Masa, Valencia, Descripción).
- **Ciclo de Selección Inteligente**:
    - **1er Clic**: Selecciona y bloquea un átomo focal.
    - **2do Clic**: Escanea dinámicamente toda la molécula conectada y la resalta como un conjunto.
    - **3er Clic**: Desebloquea y limpia la inspección.

## 🌈 Resaltado Dinámico (Real-time tracking)

- El resaltado molecular no es estático; si un átomo se une a la molécula seleccionada durante la simulación, el borde se expande para incluirlo instantáneamente.
- **Jerarquía Visual**: El átomo foco brilla en Blanco-Dorado, mientras que la estructura se ilumina en Cian Eléctrico.

## ⚛️ Quimidex (Enciclopedia Molecular)

Sistema de registro y descubrimiento con enfoque educativo:
- **Catálogo de Fórmulas**: Registro de todas las moléculas estables encontradas.
- **Auditoría Automática**: Las moléculas complejas desconocidas (>= 6 átomos) se exportan a `data/unknown_molecules.json` para su posterior identificación.
- **Filtro de Junk**: Las estructuras transitorias e inestables se ocultan automáticamente para mantener la pureza de los datos científicos.
- **Buffs por Molécula**: Cada entrada en la Quimidex otorga mejoras físicas (Velocidad, Estabilidad, Atracción) basadas en su composición química.

## 📊 Análisis Molecular Avanzado
Panel de telemetría de alta resolución que muestra:
- **Estabilidad Temporal**: Tracking de frames de vida promedio por fórmula.
- **Top Formaciones**: Ranking de las moléculas más exitosas en la sopa.
- **Salud del Ecosistema**: Métricas de energía volátil y estabilidad en el eje Z (2.5D).

## 🌪️ Interacción Térmica y Cinética

- **Pulso de Fuerza (CTRL + Clic)**: Genera una onda de choque que dispersa partículas, permitiendo probar la estabilidad de las uniones químicas.
- **Control de Tiempo**: Slider dinámico para acelerar o pausar la evolución del sistema.

## 🏭 Fábrica y Progresión
- **Tractor Beam**: Atracción pasiva de átomos basada en las manos libres (valencia) del Carbono.
- **Sinergia Hub**: El átomo de Carbono permite acumular múltiples buffs químicos simultáneamente.
- **Evolución por Consumo**: El ATP gestiona las acciones del jugador, obligando a una recolección eficiente.

## 🌋 Zonas de Catálisis Especial
Entornos con parámetros físicos modificados para fomentar la complejidad:
- **Depósitos de Arcilla**: Aumentan la probabilidad de enlace y estabilizan anillos moleculares (precursores de ARN).
- **Ventilas Termales**: Zonas de alta energía para reacciones difíciles, con riesgo de ruptura por entropía.

## 💻 Core de Simulación
- **Motor GPU Vulkan**: Simulación 100% en GPU usando Taichi con backend Vulkan.
- **Mundo Gigante**: Espacio de simulación de **5000x5000** unidades (25 millones de área).
- **Densidad Masiva**: Soporte optimizado para **5000+** partículas simultáneas a FPS estables.
- **Grilla Espacial (Spatial Grid)**: Optimización O(N) para detección de colisiones y enlaces.

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
