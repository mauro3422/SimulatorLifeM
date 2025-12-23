import taichi as ti
import numpy as np
import time
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import Taichi Fields (This initializes Taichi)
from src.systems.taichi_fields import pos, colors, n_visible, is_active
from src.systems.simulation_gpu import run_simulation_fast
import src.config.system_constants as const
from src.renderer.opengl_kernels import (
    compact_render_data, render_pos, render_col
)

def main():
    print("[HEADLESS] Inicializando...")
    
    # Init Data (7000 Particles)
    NUM = 7000
    pos_np = np.zeros((const.MAX_PARTICLES, 2), dtype=np.float32)
    pos_np[:NUM] = np.random.rand(NUM, 2) * const.WORLD_SIZE
    pos.from_numpy(pos_np)
    
    act_np = np.zeros(const.MAX_PARTICLES, dtype=np.int32)
    act_np[:NUM] = 1
    is_active.from_numpy(act_np)
    
    # IMPORTANTE: Setear n_particles
    from src.systems.taichi_fields import n_particles
    n_particles[None] = NUM
    
    print("[HEADLESS] Iniciando Loop (Sin Render)...")
    
    t_physics_sum = 0
    t_compact_sum = 0
    t_transfer_sum = 0
    frames = 100
    
    for i in range(frames):
        # 1. Physics (includes Sync)
        t0 = time.perf_counter()
        run_simulation_fast(1)
        ti.sync() # Force wait for physics
        t1 = time.perf_counter()
        
        # 2. Compaction (includes Sync)
        compact_render_data()
        ti.sync() # Force wait for compaction
        t2 = time.perf_counter()
        
        # 3. Data Transfer (Pure transfer if already synced?)
        _ = render_pos.to_numpy()[:NUM]
        _ = render_col.to_numpy()[:NUM]
        t3 = time.perf_counter()
        
        t_physics_sum += (t1 - t0)
        t_compact_sum += (t2 - t1)
        t_transfer_sum += (t3 - t2)
        
    print(f"--- RESULTADOS ({frames} Frames) ---")
    print(f"Physics Avg: {t_physics_sum/frames*1000:.3f} ms")
    print(f"Compact Avg: {t_compact_sum/frames*1000:.3f} ms")
    print(f"Transfer Avg: {t_transfer_sum/frames*1000:.3f} ms")
    
    with open("benchmark_headless.log", "w") as f:
        f.write(f"Physics: {t_physics_sum/frames*1000:.3f}\n")
        f.write(f"Compact: {t_compact_sum/frames*1000:.3f}\n")
        f.write(f"Transfer: {t_transfer_sum/frames*1000:.3f}\n")
    
    print("\nRESULTADOS GUARDADOS EN benchmark_headless.log")
    
    print("\nINTERPRETACIÓN:")
    print("Si Transfer Avg es > 1ms, el problema es el ancho de banda o latencia de Python->Driver.")
    print("Si Physics Avg es alto, Taichi es el cuello.")

if __name__ == "__main__":
    main()
