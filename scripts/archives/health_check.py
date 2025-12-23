import sys
import os
import time
import numpy as np

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import taichi as ti
from src.systems import simulation_gpu
import src.config as cfg  # Correct import via __init__.py
from src.core.perf_logger import PerfLogger

def run_health_check():
    print("🏥 Starting System Health Audit...")
    
    # Initialize Taichi
    ti.init(arch=ti.vulkan, offline_cache=True)
    
    # Setup
    print("[1/4] Initializing Physics Engine...")
    # simulation_gpu.init_molecule_ids() # Removed due to kernel issues
    simulation_gpu.molecule_id.fill(-1)
    
    # Spawn 5000 particles (Stress Test)
    print("[2/4] Spawning 5000 particles...")
    np.random.seed(42)
    pos = np.random.rand(5000, 2) * 5000.0 + 5000.0
    simulation_gpu.update_particles_subset(
        indices=np.arange(5000),
        new_pos=pos,
        new_active=np.ones(5000, dtype=np.int32)
    )
    
    # Warmup
    print("[3/4] Warming up (50 frames)...")
    for _ in range(50):
        simulation_gpu.run_simulation_fast(1)
    
    # Benchmark
    print("[4/4] Benchmarking (200 frames)...")
    t_start = time.perf_counter()
    
    frame_times = []
    
    for i in range(200):
        t0 = time.perf_counter()
        simulation_gpu.run_simulation_fast(1)
        ti.sync() # Ensure GPU finished
        t1 = time.perf_counter()
        frame_times.append((t1 - t0) * 1000.0)
        
        if i % 50 == 0:
            print(f"    - Frame {i}/200: {frame_times[-1]:.2f}ms")
            
    avg_physics = np.mean(frame_times)
    min_physics = np.min(frame_times)
    max_physics = np.max(frame_times)
    
    print("\n📊 AUDIT RESULTS 📊")
    print(f"-------------------")
    print(f"Physics Latency (Avg): {avg_physics:.2f} ms")
    print(f"Physics Latency (Min): {min_physics:.2f} ms")
    print(f"Physics Latency (Max): {max_physics:.2f} ms")
    print(f"Estimated Max FPS (Physics Only): {1000.0 / avg_physics:.1f} FPS")
    
    print("\n✅ Diagnosis:")
    if avg_physics < 16.0:
        print("    STATUS: EXCELLENT (Target 60 FPS feasible)")
    elif avg_physics < 33.0:
        print("    STATUS: GOOD (Target 30 FPS feasible)")
    else:
        print("    STATUS: WARNING (optimization needed for playable FPS)")

if __name__ == "__main__":
    run_health_check()
