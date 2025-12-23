import taichi as ti
import numpy as np
import time
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Init Taichi
from src.systems.taichi_fields import pos, is_active, n_particles
from src.systems.simulation_gpu import (
    physics_pre_step, update_grid, resolve_constraints_grid, 
    apply_bond_forces_gpu, physics_post_step, check_bonding_gpu,
    apply_brownian_motion_gpu, apply_coulomb_repulsion_gpu, apply_evolutionary_effects_gpu
)
import src.config.system_constants as const

def main():
    print("--- DESGLOSE DE FÍSICA (TIEMPOS REALES CON SYNC) ---")
    
    # Setup 2000 particles
    NUM = 2000
    n_particles[None] = NUM
    pos_np = np.random.rand(NUM, 2).astype(np.float32) * const.WORLD_SIZE
    pos.from_numpy(pos_np)
    is_active.fill(1)
    
    iters = 100
    t_pre = 0
    t_pbd = 0
    t_post = 0
    t_chem_bond = 0
    t_adv = 0
    
    # Warmup
    physics_pre_step()
    ti.sync()
    
    t_start = time.perf_counter()
    
    for i in range(iters):
        # 1. Pre
        t0 = time.perf_counter()
        physics_pre_step()
        ti.sync()
        t1 = time.perf_counter()
        t_pre += (t1 - t0)
        
        # 2. PBD (Solver Loop)
        for _ in range(3): # SOLVER_ITERATIONS default
            update_grid()
            resolve_constraints_grid()
            apply_bond_forces_gpu()
        ti.sync()
        t2 = time.perf_counter()
        t_pbd += (t2 - t1)
        
        # 3. Post
        physics_post_step()
        ti.sync()
        t3 = time.perf_counter()
        t_post += (t3 - t2)
        
        # 4. Chem Bond
        check_bonding_gpu()
        ti.sync()
        t4 = time.perf_counter()
        t_chem_bond += (t4 - t3)
        
        # 5. Adv
        apply_brownian_motion_gpu()
        apply_coulomb_repulsion_gpu()
        apply_evolutionary_effects_gpu()
        ti.sync()
        t5 = time.perf_counter()
        t_adv += (t5 - t4)
    
    total_time = time.perf_counter() - t_start
    avg_total = (total_time / iters) * 1000
    
    print(f"\nResultados para {NUM} partículas (Promedio de {iters} frames):")
    print(f"Total Physics: {avg_total:.3f} ms")
    print(f"  - Pre-Step:  {t_pre/iters*1000:.3f} ms")
    print(f"  - PBD Loop:  {t_pbd/iters*1000:.3f} ms (El mas pesado usualmente)")
    print(f"  - Post-Step: {t_post/iters*1000:.3f} ms")
    print(f"  - Chem Bond: {t_chem_bond/iters*1000:.3f} ms")
    print(f"  - Advanced:  {t_adv/iters*1000:.3f} ms")

if __name__ == "__main__":
    main()
