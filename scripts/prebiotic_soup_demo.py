"""
🧪 Prebiotic Emergence Demo
==========================
Este script recrea una 'Sopa Caliente' de alta densidad para observar 
la formación espontánea de moléculas y el agrupamiento hidrofóbico.
"""
import taichi as ti
import numpy as np
import time
import sys
import os

# Añadir el raíz del proyecto al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.advanced_molecular_analyzer import init_simulation_gpu, run_benchmark
from src.systems.taichi_fields import (
    pos, pos_old, is_active, atom_types, temperature,
    prob_enlace_base, rango_enlace_max, medium_polarity,
    n_particles, molecule_id, sync_atomic_data
)
from src.systems.simulation_gpu import init_molecule_ids
import src.config.system_constants as sys_cfg

def setup_emergence_demo():
    print("🔥 Iniciando Demo de Emergencia Prebiótica...")
    
    # 1. Configurar Datos Atómicos (Taichi ya se inicializa al importar campos)
    sync_atomic_data()
    
    # 2. Inicializar 5000 partículas en un espacio reducido (Alta Densidad)
    n_demo = 5000
    init_simulation_gpu(n_demo)
    
    # Composición: Mucho Carbono e Hidrógeno para ver cadenas
    # [C, H, N, O, P, S]
    types_np = np.random.choice(
        [0, 1, 2, 3, 4, 5],
        size=sys_cfg.MAX_PARTICLES,
        p=[0.35, 0.40, 0.05, 0.15, 0.025, 0.025]
    ).astype(np.int32)
    atom_types.from_numpy(types_np)
    
    # Spawn en un cluster central muy apretado
    center = sys_cfg.WORLD_SIZE / 2
    cluster_size = 500.0
    pos_np = np.zeros((sys_cfg.MAX_PARTICLES, 2), dtype=np.float32)
    pos_np[:n_demo] = (np.random.rand(n_demo, 2) - 0.5) * cluster_size + center
    pos.from_numpy(pos_np)
    pos_old.from_numpy(pos_np)
    
    # 3. Forzar condiciones de alta reactividad
    temperature[None] = 20.0       # Calor extremo para romper simetría
    prob_enlace_base[None] = 1.0   # Súper reactivo
    rango_enlace_max[None] = 350.0 # Rango extendido
    medium_polarity[None] = 1.0    # Agua pura (para forzar efecto hidrofóbico)
    
    active_np = np.zeros(sys_cfg.MAX_PARTICLES, dtype=np.int32)
    active_np[:n_demo] = 1
    is_active.from_numpy(active_np)
    
    init_molecule_ids()
    ti.sync()
    print("✅ Sopa Prebiótica lista. Iniciando reacción...")

if __name__ == "__main__":
    setup_emergence_demo()
    # Ejecutamos 5000 frames para dar tiempo a la emergencia
    run_benchmark(frames=5000)
    print("\n🏁 Demo finalizada. Revisa 'chemical_health_report.md' para ver qué emergió.")
