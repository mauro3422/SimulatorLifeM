
import sys
import os
import time
import numpy as np
import taichi as ti

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.systems.taichi_fields import n_particles, pos, is_active, total_bonds_count, manos_libres, num_enlaces, enlaces_idx, atom_types, VALENCIAS_MAX, AFINIDAD_MATRIX, prob_enlace_base, rango_enlace_max
from src.systems.simulation_gpu import simulation_step_gpu
from src.config import system_constants as sys_cfg

def run_mini_test():
    # 1. Init Data
    N = 1000
    n_particles[None] = N
    
    # 5 elements
    atoms = np.random.randint(0, 6, size=N, dtype=np.int32)
    atom_types.from_numpy(np.pad(atoms, (0, sys_cfg.MAX_PARTICLES - N), constant_values=0))
    
    # Valences
    valences = np.array([1, 4, 2, 3, 5, 6], dtype=np.int32)
    VALENCIAS_MAX.from_numpy(valences)
    
    manos = np.zeros(sys_cfg.MAX_PARTICLES, dtype=np.float32)
    manos[:N] = valences[atoms]
    manos_libres.from_numpy(manos)
    
    # Affinities
    AFINIDAD_MATRIX.fill(1.0)
    prob_enlace_base[None] = 1.0
    rango_enlace_max[None] = 100.0
    
    # Positions: All in one cluster at world center
    center = sys_cfg.WORLD_SIZE / 2.0
    pos_data = np.random.normal(center, 5.0, (sys_cfg.MAX_PARTICLES, 2)).astype(np.float32)
    pos.from_numpy(pos_data)
    
    is_active_np = np.zeros(sys_cfg.MAX_PARTICLES, dtype=np.int32)
    is_active_np[:N] = 1
    is_active.from_numpy(is_active_np)
    
    total_bonds_count[None] = 0
    num_enlaces.fill(0)
    enlaces_idx.fill(-1)
    
    # 2. Run 5 steps
    print(f"🚀 Starting Mini-Test (N={N}, Cluster at {center})")
    for i in range(5):
        simulation_step_gpu(1)
        ti.sync()
        bonds = total_bonds_count[None]
        print(f"Step {i} | Bonds: {bonds}")
    
    # Final Summary
    final_bonds = total_bonds_count[None]
    print(f"🏁 Final Bonds: {final_bonds}")
    if final_bonds > 0:
        print("✅ SUCCESS: Bonds are forming!")
    else:
        print("❌ FAILURE: Still sterile.")

if __name__ == "__main__":
    run_mini_test()
