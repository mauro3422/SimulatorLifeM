# 🧪 LifeSimulator: High-Performance Molecular Engine

[![GitHub License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Taichi Lang](https://img.shields.io/badge/Physics-Taichi-red.svg)](https://www.taichi-lang.org/)
[![ModernGL](https://img.shields.io/badge/Render-ModernGL-cyan.svg)](https://moderngl.readthedocs.io/)

**LifeSimulator** es un motor de simulación molecular masiva diseñado para explorar la estabilidad química y la evolución emergente en tiempo real. Utiliza un pipeline híbrido de **GPU Computing (Taichi)** para la física y **OpenGL Moderno (ModernGL)** para el renderizado de alta fidelidad.

## 🚀 Performance (v3.0 - Ultra-Loop)

| Métrica | Valor |
|---------|-------|
| **FPS** | 90-106 (zoom alto) |
| **Partículas** | 5,000-10,000 |
| **Latencia DataTx** | <0.5ms |
| **Pipeline** | Universal GPU Buffer |

## ✨ Características Principales

- **⚙️ Motor de Física Masivo**: Simulación de miles de partículas CHONPS con "Total Fusion" (física + química en un solo pass GPU).
- **🏭 Química Realista (140+ Moléculas)**: Catálogo enriquecido con Aminoácidos, Nucleobases y Azúcares con lore científico detallado.
- **🛡️ Auditoría Científica**: Flujo de trabajo para filtrar basura, validar química emergente y expandir el blocklist (600+ fórmulas).
- **🏭 Fábrica Molecular**: Evolución desde un átomo a una compleja fábrica de biopolímeros con gestión de recursos.
- **⚛️ Quimidex**: Sistema de enciclopedia interactiva con auditoría de moléculas desconocidas y buffs educativos.
- **🌋 Zonas de Catálisis**: Entornos con física alterada (Arcilla, Ventilas Termales) que dictan la evolución.
- **🥊 Competencia Biota**: Próxima implementación de IA competitiva luchando por la sopa primordial.

## 🛠️ Stack Tecnológico

- **Lenguaje**: Python 3.13
- **Física**: [Taichi Lang](https://github.com/taichi-dev/taichi) (Vulkan/Cuda Backend)
- **Renderizado**: [ModernGL](https://github.com/moderngl/moderngl) (OpenGL Core Profile)
- **UI/UX**: [Dear ImGui](https://github.com/ocornut/imgui) (via imgui-bundle)

## 🕹️ Controles

| Entrada | Acción |
| :--- | :--- |
| **Clic Izquierdo** | Seleccionar Átomo / Molécula |
| **Ctrl + Clic** | Lanzar Pulso de Fuerza |
| **Tab (Mantener)** | 🏎️ Acelerador de Tiempo |
| **Doble Tab** | ⏸️ Pausar / Reanudar |
| **Espacio** | Reset a Velocidad 1.0x |
| **Rueda Mouse** | Zoom Dinámico |
| **F3** | Modo Debug |

## 🚀 Instalación

```bash
git clone https://github.com/mauro3422/SimulatorLifeM.git
cd SimulatorLifeM
pip install -r requirements.txt
python main.py
```

## 📂 Estructura del Proyecto

```
LifeSimulator/
├── main.py                 # Orquestador principal
├── src/
│   ├── systems/            # Física, Química, Kernels GPU
│   ├── renderer/           # OpenGL, Shaders, Cámara
│   ├── config/             # Constantes, UI Config
│   └── core/               # Utils, Performance Logger
├── benchmarks/             # 📊 Scripts de benchmark
│   ├── monitor.py          # Monitor de performance
│   └── results/            # Logs de benchmarks
├── docs/                   # Documentación técnica
└── logs/                   # Logs de aplicación
```

## 📊 Benchmarks

```bash
# Ver métricas de performance
python benchmarks/monitor.py

# Ejecutar benchmark completo
python benchmarks/benchmark_gpu.py
```

## 📜 Licencia

MIT License. Ver `LICENSE` para detalles.

---
*Desarrollado con ❤️ para la exploración de la vida artificial.*