"""
Minimal debug script to verify bonding parameters on GPU.
Mimics stress test conditions exactly.
"""
import sys
import os
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import taichi as ti
ti.init(arch=ti.vulkan, offline_cache=True)

from src.systems.taichi_fields import (
    n_particles, pos, is_active, total_bonds_count, manos_libres, 
    num_enlaces, enlaces_idx, atom_types, VALENCIAS_MAX, AFINIDAD_MATRIX, 
    prob_enlace_base, rango_enlace_max, grid_count, grid_pids
)
from src.config import system_constants as sys_cfg
from src.systems.simulation_gpu import kernel_pre_step_fused, kernel_bonding

# Constants
GRID_CELL_SIZE = sys_cfg.GRID_CELL_SIZE
print(f"[CONFIG] GRID_CELL_SIZE = {GRID_CELL_SIZE}")
print(f"[CONFIG] GRID_RES = {sys_cfg.GRID_RES}")
print(f"[CONFIG] MAX_PER_CELL = {sys_cfg.MAX_PER_CELL}")

# Initialize like stress test
N = 5000  # Same as stress test
n_particles[None] = N

# Spawn in 500x500 cluster like stress test
SPAWN_AREA = 500.0
center = sys_cfg.WORLD_SIZE / 2.0  # 7500
pos_data = np.zeros((sys_cfg.MAX_PARTICLES, 2), dtype=np.float32)
pos_data[:N] = (np.random.rand(N, 2) * SPAWN_AREA) + (center - SPAWN_AREA / 2.0)
pos.from_numpy(pos_data)

# All active
is_active_np = np.zeros(sys_cfg.MAX_PARTICLES, dtype=np.int32)
is_active_np[:N] = 1
is_active.from_numpy(is_active_np)

# Types and Valences
atoms = np.random.randint(0, 6, size=sys_cfg.MAX_PARTICLES, dtype=np.int32)
atom_types.from_numpy(atoms)

valences = np.array([1, 4, 2, 3, 5, 6], dtype=np.int32)
VALENCIAS_MAX.from_numpy(valences)

manos = np.zeros(sys_cfg.MAX_PARTICLES, dtype=np.float32)
manos[:N] = 4.0  # Everyone gets 4 hands
manos_libres.from_numpy(manos)

# Affinity
AFINIDAD_MATRIX.fill(1.0)

# Bonding parameters - SAME AS STRESS TEST
prob_enlace_base[None] = 1.0  # 100%
rango_enlace_max[None] = 200.0  # Same as stress test

# Reset counters
total_bonds_count[None] = 0
num_enlaces.fill(0)
enlaces_idx.fill(-1)

# Build grid
kernel_pre_step_fused()
ti.sync()

# Debug: Check grid
grid_count_np = grid_count.to_numpy()
print(f"\n[GRID] Max cells with particles: {np.max(grid_count_np)}")
print(f"[GRID] Total particles in grid: {np.sum(grid_count_np)}")

# Calculate expected cell for center
cx_cell = int(center / GRID_CELL_SIZE)
print(f"[GRID] Expected center cell: ({cx_cell}, {cx_cell})")
print(f"[GRID] Particles in center cell: {grid_count_np[cx_cell, cx_cell]}")

# Debug: Particle positions
pos_np = pos.to_numpy()[:N]
print(f"\n[PARTICLES] Min pos: {pos_np.min(axis=0)}")
print(f"[PARTICLES] Max pos: {pos_np.max(axis=0)}")
print(f"[PARTICLES] Range: {pos_np.max(axis=0) - pos_np.min(axis=0)}")

# Debug: Sample distances between first 10 particles
print(f"\n[DISTANCES] Sample distances between particles:")
for i in range(min(5, N)):
    for j in range(i+1, min(10, N)):
        dist = np.linalg.norm(pos_np[i] - pos_np[j])
        print(f"  P{i}-P{j}: {dist:.2f} units")

print(f"\n[PARAMS] prob_enlace_base = {prob_enlace_base[None]}")
print(f"[PARAMS] rango_enlace_max = {rango_enlace_max[None]}")
print(f"[PARAMS] manos_libres sum = {manos_libres.to_numpy()[:N].sum()}")

# Now call bonding
kernel_bonding()
ti.sync()

bonds = total_bonds_count[None]
print(f"\n[RESULT] Bonds formed: {bonds}")
if bonds > 0:
    print("SUCCESS: Bonding works!")
else:
    print("FAILURE: Still no bonds.")
