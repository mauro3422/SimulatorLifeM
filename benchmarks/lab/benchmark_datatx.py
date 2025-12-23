import taichi as ti
import numpy as np
import time

# Init Taichi
ti.init(arch=ti.vulkan)

# Define fields of different sizes
# Small: 4KB (1000 floats)
# Medium: 200KB (50k floats)
# Large: 4MB (1M floats)

field_small = ti.field(dtype=ti.f32, shape=1000)
field_med = ti.field(dtype=ti.f32, shape=50000)
field_large = ti.field(dtype=ti.f32, shape=1000000)

def bench(name, field, iters=100):
    # Warmup
    field.to_numpy()
    
    t0 = time.perf_counter()
    for i in range(iters):
        # Force sync before? No, let's measure full download cost
        _ = field.to_numpy()
    t1 = time.perf_counter()
    
    avg_us = ((t1 - t0) / iters) * 1_000_000
    print(f"{name}: {avg_us:.1f} us per call")
    return avg_us

def main():
    print("--- BENCHMARK DATA TRANSFER (to_numpy) ---")
    
    s = bench("Small (4KB)", field_small)
    m = bench("Medium (200KB)", field_med)
    l = bench("Large (4MB)", field_large)
    
    print("\nANALYSIS:")
    if abs(m - s) < 100:
        print("Latency DOMINATES bandwidth. (Fixed overhead per call)")
    else:
        print("Bandwidth affects speed significantly.")

if __name__ == "__main__":
    main()
