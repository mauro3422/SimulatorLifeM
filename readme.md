# 🧪 LifeSimulator: High-Performance Molecular Engine

[![GitHub License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Taichi Lang](https://img.shields.io/badge/Physics-Taichi-red.svg)](https://www.taichi-lang.org/)
[![ModernGL](https://img.shields.io/badge/Render-ModernGL-cyan.svg)](https://moderngl.readthedocs.io/)

**LifeSimulator** es un motor de simulación molecular masiva diseñado para explorar la estabilidad química y la evolución emergente en tiempo real. Utiliza un pipeline híbrido de **GPU Computing (Taichi)** para la física y **OpenGL Moderno (ModernGL)** para el renderizado de alta fidelidad.

![Preview](https://raw.githubusercontent.com/mauro3422/SimulatorLifeM/main/docs/media/preview.png) *(Placeholder por imagen real)*

## ✨ Características Principales

- **⚙️ Motor de Física Masivo**: Simulación de miles de partículas CHONPS (Carbono, Hidrógeno, Oxígeno, Nitrógeno, Fósforo, Azufre) con enlaces dinámicos y fuerzas interatómicas.
- **🧬 Selección Molecular Dinámica**: Sistema de "Picking" inteligente que detecta y resalta estructuras moleculares completas en tiempo real mientras se forman o rompen.
- **📊 Monitor Científico**: Dashboard en tiempo real que mide transiciones energéticas, formación de enlaces y actividad catalítica.
- **🎨 Interfaz Premium**: UI basada en Glassmorphism con temas de color Cian Eléctrico y Blanco-Oro, optimizada para resolución 1280x720+.
- **🚀 Pipeline 100% GPU**: Transferencia de datos eficiente entre Taichi y ModernGL sin cuellos de botella en la CPU.

## 🛠️ Stack Tecnológico

- **Lenguaje**: Python 3.13
- **Física**: [Taichi Lang](https://github.com/taichi-dev/taichi) (Vulkan/Cuda/OpenGL Backend)
- **Renderizado**: [ModernGL](https://github.com/moderngl/moderngl) (OpenGL Core Profile)
- **UI/UX**: [Dear ImGui](https://github.com/ocornut/imgui) (via imgui-bundle)
- **Matemáticas**: NumPy

## 🕹️ Controles (Modo Piloto)

| Entrada | Acción |
| :--- | :--- |
| **Clic Izquierdo** | Seleccionar Átomo / Segundo clic: Ver Molécula / Tercero: Deseleccionar |
| **Ctrl + Clic Izquierdo** | Lanzar Pulso de Fuerza (Shockwave) |
| **Tab (Mantener)** | 🏎️ Acelerador: Aumenta la velocidad gradualmente. Al soltar, la velocidad se **mantiene**. |
| **Doble Tab** | ⏸️ Pausar / Reanudar Simulación |
| **Espacio** | 🔄 Reset a Velocidad Óptima (1.0x) |
| **Rueda del Mouse** | Zoom Dinámico |
| **Clic Rueda (Hold)** | Panear Cámara |
| **F3** | Alternar Modo Debug |

## 🚀 Instalación

1. **Clonar el repositorio**:
   ```bash
   git clone https://github.com/mauro3422/SimulatorLifeM.git
   cd SimulatorLifeM
   ```

2. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Ejecutar**:
   ```bash
   python main.py
   ```

## 📂 Estructura del Proyecto

- `main.py`: Punto de entrada, orquestador de UI y Renderizado.
- `src/ui_config.py`: Configuración centralizada de estética y widgets.
- `src/systems/simulation_gpu.py`: Kernels de física en Taichi.
- `src/config.py`: Parámetros globales de simulación y tabla periódica.
- `docs/`: Documentación técnica detallada sobre arquitectura y kernels.

## 📜 Licencia

Este proyecto está bajo la licencia MIT. Consulta el archivo `LICENSE` para más detalles.

---
*Desarrollado con ❤️ para la exploración de la vida artificial.*