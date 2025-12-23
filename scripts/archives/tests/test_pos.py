import taichi as ti
import numpy as np
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

ti.init(arch=ti.vulkan)

from src.systems.taichi_fields import pos, pos_old, n_particles, is_active, sim_bounds, temperature
from src.systems.simulation_gpu import (
    kernel_pre_step_fused, kernel_resolve_constraints, 
    kernel_post_step_fused, update_partial_charges
)

print("Testing position persistence with ALL kernels...")

N = 10
n_particles[None] = N
sim_bounds.from_numpy(np.array([0, 0, 15000, 15000], dtype=np.float32))
temperature[None] = 0.0 # No thermal jitter for this test

p_np = np.ones((10000, 2), dtype=np.float32) * 7500.0
pos.from_numpy(p_np)

active_np = np.zeros(10000, dtype=np.int32)
active_np[:N] = 1
is_active.from_numpy(active_np)

ti.sync()
print(f"Initial Pos[0]: {pos.to_numpy()[0]}")

from src.systems.taichi_fields import world_width, world_height
world_width[None] = 15000.0
world_height[None] = 15000.0

pos_old.from_numpy(p_np)

for f in range(5):
    kernel_post_step_fused(10.0, 0)
    ti.sync()
    print(f"Frame {f} Pos[0]: {pos.to_numpy()[0]}")
