import taichi as ti
import time
import numpy as np

# Initialize Taichi
ti.init(arch=ti.vulkan)

# Mock constants
MAX_PARTICLES = 10000
MAX_VALENCE = 4

# Initialize fields mock
molecule_id = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)
next_molecule_id = ti.field(dtype=ti.i32, shape=())
needs_propagate = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)
enlaces_idx = ti.field(dtype=ti.i32, shape=(MAX_PARTICLES, MAX_VALENCE))
enlaces_idx.fill(-1)
num_enlaces = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)
is_active = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)

@ti.kernel
def init_system():
    next_molecule_id[None] = MAX_PARTICLES + 1
    for i in range(MAX_PARTICLES):
        is_active[i] = 1
        molecule_id[i] = i
        needs_propagate[i] = 0

@ti.kernel
def create_linear_chain(start_idx: int, length: int):
    """Creates a linear chain A-B-C-D..."""
    for k in range(length - 1):
        i = start_idx + k
        j = start_idx + k + 1
        
        # Link i-j
        idx_i = ti.atomic_add(num_enlaces[i], 1)
        idx_j = ti.atomic_add(num_enlaces[j], 1)
        enlaces_idx[i, idx_i] = j
        enlaces_idx[j, idx_j] = i
        
        # Merge IDs (simulate formation)
        mol_i = molecule_id[i]
        mol_j = molecule_id[j]
        if mol_i < mol_j:
            molecule_id[j] = mol_i
            needs_propagate[j] = 1
        else:
            molecule_id[i] = mol_j
            needs_propagate[i] = 1

@ti.kernel
def propagate_molecule_ids():
    """Exact copy of the production kernel"""
    for i in range(MAX_PARTICLES):
        if is_active[i] and needs_propagate[i]:
            my_mol = molecule_id[i]
            n_b = num_enlaces[i]
            needs_propagate[i] = 0
            for b in range(n_b):
                neighbor = enlaces_idx[i, b]
                if neighbor != -1:
                    if my_mol < molecule_id[neighbor]:
                         molecule_id[neighbor] = my_mol
                         needs_propagate[neighbor] = 1

@ti.kernel
def create_realistic_cluster(start_idx: int, size: int):
    """Creates a small cluster (fully connected for torture, or linear for diameter test)."""
    # Create linear chain of 'size' (diameter = size)
    for k in range(size - 1):
        i = start_idx + k
        j = start_idx + k + 1
        
        # Link i-j
        idx_i = ti.atomic_add(num_enlaces[i], 1)
        idx_j = ti.atomic_add(num_enlaces[j], 1)
        enlaces_idx[i, idx_i] = j
        enlaces_idx[j, idx_j] = i
        
        # Merge logic (simulation)
        mol_i = molecule_id[i]
        mol_j = molecule_id[j]
        if mol_i < mol_j:
            molecule_id[j] = mol_i
            needs_propagate[j] = 1
        else:
            molecule_id[i] = mol_j
            needs_propagate[i] = 1

def run_benchmark():
    print(f"🚀 Starting Benchmark: Realistic Molecule Propagation (N={MAX_PARTICLES})")
    print("   Scenario: 1000 molecules of size 10 (avg game molecule size)")
    
    init_system()
    
    # Create 1000 molecules of size 10
    MOL_SIZE = 10
    N_MOLECULES = MAX_PARTICLES // MOL_SIZE
    
    t0 = time.time()
    for m in range(N_MOLECULES):
        base_idx = m * MOL_SIZE
        create_realistic_cluster(base_idx, MOL_SIZE)
    ti.sync()
    print(f"   Creation Time: {(time.time()-t0)*1000:.2f} ms")
    
    # Measure Convergence
    print("2. Measuring Propagation Convergence...")
    frames = 0
    t_start = time.time()
    while True:
        dirty_sum = needs_propagate.to_numpy().sum()
        if dirty_sum == 0:
            break
            
        propagate_molecule_ids()
        ti.sync()
        frames += 1
        if frames > 100: # Should be fast
            print("   ⚠️ Not converging quickly!")
            break
            
    t_end = time.time()
    print(f"   Converged in {frames} frames")
    print(f"   Total Time: {(t_end - t_start)*1000:.2f} ms")
    print(f"   Avg Time per Frame: {(t_end - t_start)*1000/max(1,frames):.4f} ms")
    
    # Verify correctness
    ids = molecule_id.to_numpy()
    # Each cluster should have 1 unique ID. Total unique IDs should be N_MOLECULES (ideally)
    # or at least, each cluster atoms must share same ID.
    
    error_count = 0
    unique_ids_count = len(np.unique(ids))
    print(f"   Total Unique IDs: {unique_ids_count} (Expected approx {N_MOLECULES})")
    
    # Check consistency per cluster
    for m in range(N_MOLECULES):
        base = m * MOL_SIZE
        cluster_ids = ids[base : base+MOL_SIZE]
        if len(np.unique(cluster_ids)) > 1:
            error_count += 1
            
    if error_count == 0:
        print("   ✅ CORRECTNESS VERIFIED (All clusters consistent)")
    else:
        print(f"   ❌ FAILED: {error_count} broken clusters")

if __name__ == "__main__":
    run_benchmark()
