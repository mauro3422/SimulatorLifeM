import taichi as ti
import time
import numpy as np

# Init Taichi
ti.init(arch=ti.vulkan)

# Config
N = 5000
DATA_DIM = 6
ITERS = 100

print(f"Benchmarking overhead for N={N}...")

# Fields
pos = ti.Vector.field(2, dtype=ti.f32, shape=N)
packed = ti.field(dtype=ti.f32, shape=(N, DATA_DIM))
field_stats = ti.field(dtype=ti.i32, shape=4)

@ti.kernel
def compute_heavy():
    for i in range(N):
        # Fake heavy work
        val = 0.0
        for k in range(100):
            val += ti.sin(float(i+k))
        pos[i] = ti.Vector([val, val])

@ti.kernel
def pack_data():
    for i in range(N):
        packed[i, 0] = pos[i].x
        packed[i, 1] = pos[i].y
        packed[i, 2] = 1.0

def benchmark():
    # Warmup
    for _ in range(10):
        compute_heavy()
        pack_data()
        ti.sync()

    t_start = time.perf_counter()
    
    times_launch = []
    times_sync = [] # Real Compute
    times_transfer = []
    
    for _ in range(ITERS):
        t0 = time.perf_counter()
        
        # 1. Dispatch
        compute_heavy()
        pack_data()
        
        t1 = time.perf_counter()
        
        # 2. Sync (Compute Wait)
        ti.sync()
        
        t2 = time.perf_counter()
        
        # 3. Transfer
        data = packed.to_numpy()
        stats = field_stats.to_numpy()
        
        t3 = time.perf_counter()
        
        times_launch.append((t1 - t0) * 1000)
        times_sync.append((t2 - t1) * 1000)
        times_transfer.append((t3 - t2) * 1000)

    print("-" * 40)
    print(f"Avg Launch (Python Overhead): {np.mean(times_launch):.3f} ms")
    print(f"Avg Sync (GPU Compute):       {np.mean(times_sync):.3f} ms")
    print(f"Avg Transfer (to_numpy):      {np.mean(times_transfer):.3f} ms")
    print("-" * 40)
    
    total = np.mean(times_launch) + np.mean(times_sync) + np.mean(times_transfer)
    print(f"Total per frame: {total:.3f} ms")
    print(f"Max POTENTIAL FPS: {1000/total:.1f}")

if __name__ == "__main__":
    benchmark()
