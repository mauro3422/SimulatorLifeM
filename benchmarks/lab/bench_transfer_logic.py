import taichi as ti
import time
import numpy as np

ti.init(arch=ti.vulkan)

MAX_N = 10000
field = ti.field(dtype=ti.f32, shape=(MAX_N, 6))

def benchmark():
    # Warmup
    _ = field.to_numpy()
    
    # 1. Full Download
    times_full = []
    for _ in range(100):
        start = time.perf_counter()
        data = field.to_numpy()
        times_full.append(time.perf_counter() - start)
    
    # 2. Sliced Download (if supported efficiently)
    # Note: field[:100] returns a 'SnodeRef' or similar in some versions
    times_partial = []
    for _ in range(100):
        start = time.perf_counter()
        # In Taichi, you can't directly slice a field for to_numpy() effectively 
        # unless it's an ndarray or we use a copy kernel.
        # Let's see if we can trick it.
        try:
             # This is the test: does this actually transfer less data?
             # Probably not, it usually downloads the whole field and then slices in Python.
             data = field.to_numpy()[:500] 
        except:
             pass
        times_partial.append(time.perf_counter() - start)

    print(f"Full download (10k): {np.mean(times_full)*1000:.3f}ms")
    print(f"Slice download (500): {np.mean(times_partial)*1000:.3f}ms")

benchmark()
